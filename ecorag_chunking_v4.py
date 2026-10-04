# ============================================================
# EcoRAG - Stage 1 & 2 (v4): clean, section-aware, token-safe chunking
# ============================================================
# Pipeline:
#   PDF -> Markdown per page -> clean elements (headings, paragraphs, tables, footnotes)
#   -> repair broken paragraphs/headings -> sections -> chunks (< 512 tokens)
# Footnotes/references are kept OUT of the content chunks. They are stored as
# metadata on the chunks that cite them, plus in separate "references" chunks.
# No embeddings, vector DB, retrieval or LLM yet.

# --- 0. Install libraries ---
!pip install -q pymupdf pymupdf4llm tokenizers

import json
import re
from collections import Counter, defaultdict

import pymupdf        # PyMuPDF (the newer name for "fitz")
import pymupdf4llm    # PDF -> Markdown converter (detects headings & tables)
from tokenizers import Tokenizer


# --- 1. Settings ---
PDF_PATH = None    # None = upload in Colab; or set a file path to skip the upload dialog
DOC_TITLE = None   # None = PDF metadata, else the document's main heading, else file name

TOKENIZER_MODEL = "BAAI/bge-small-en-v1.5"  # embedding model we plan to use later
MODEL_MAX_TOKENS = 512    # that model's hard input limit
MAX_EMBED_TOKENS = 480    # hard cap for header + chunk text (safety margin below 512)
TARGET_TOKENS = 320       # stop adding paragraphs once the chunk text reaches about this
MAX_BODY_TOKENS = 400     # chunk text limit while building (header is added on top)
MIN_TOKENS = 80           # chunks smaller than this get merged with a neighbour
SECTION_TAIL_TOKENS = 120 # keep a short end-of-section tail in the chunk instead of orphaning it
OVERLAP_TOKENS = 50       # repeat up to this many tokens of whole sentences in the next chunk
HEADING_MAX_CHARS = 120   # short text without end punctuation may be a heading


# --- 2. Load the PDF ---
if PDF_PATH is None:
    from google.colab import files
    print("Please choose a PDF file to upload...")
    uploaded = files.upload()
    if not uploaded:
        raise ValueError("No file was uploaded. Please run the cell again and pick a PDF.")
    PDF_PATH = list(uploaded.keys())[0]

with pymupdf.open(PDF_PATH) as doc:
    num_pages = len(doc)
    pdf_title = ((doc.metadata or {}).get("title") or "").strip()
source_name = re.split(r"[\\/]", PDF_PATH)[-1]


# --- 3. Tokenizer and small text helpers ---
tokenizer = Tokenizer.from_pretrained(TOKENIZER_MODEL)
tokenizer.no_truncation()   # we want the REAL length, not a length capped at 512

def count_tokens(text):
    return len(tokenizer.encode(text, add_special_tokens=False).ids)

SENTENCE_BOUNDARY = re.compile(r'(?<=[.!?])\s+(?=[A-Z0-9"“(])')
HEADING_LINE = re.compile(r"^(#{1,6})\s+(.*)$")
LIST_ITEM = re.compile(r"^([-*•]|\d+[.)])\s+")
CAPTION = re.compile(r"^(Table|Figure|Box|Chart|Map)\s*\d+", re.IGNORECASE)
FOOTNOTE_LINE = re.compile(r"^(?:>\s*|[-*]\s+)?(\d{1,3})\s+(\S.*)$")
PICTURE_TEXT = re.compile(r"<!--\s*Start of picture text\s*-->.*?<!--\s*End of picture text\s*-->", re.S)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
SUPERSCRIPT = re.compile(r"<sup>\s*([^<]*?)\s*</sup>")
CITE_MARK = re.compile(r"\s*\{\{fn:([^}]*)\}\}")
DOT_LEADER = re.compile(r"\.{5,}")
FRONT_MATTER = re.compile(r"acknowledg|table of contents|^contents$|^\(front matter\)$", re.IGNORECASE)
DANGLING_WORD = re.compile(r"\b(the|and|of|in|for|to|a|an|on|with|from|by|or)$", re.IGNORECASE)

def split_sentences(text):
    """Split text at '.', '!' or '?' followed by a capital letter, number or quote."""
    return SENTENCE_BOUNDARY.split(text)

def ends_sentence(text):
    """True if the text ends like a finished sentence."""
    return text.rstrip('"”’)]').endswith((".", "!", "?", ":", ";"))

def is_heading_like(text):
    """Short text that doesn't end like a sentence: a heading, label or caption."""
    return len(text) <= HEADING_MAX_CHARS and not ends_sentence(text)

def is_list_item(text):
    return bool(LIST_ITEM.match(text))

def normalise(text):
    """Lowercase, digits -> '#', no punctuation: used to compare repeated lines."""
    return re.sub(r"[^a-z# ]", "", re.sub(r"\d+", "#", text.lower())).strip()

def clean_inline(text):
    """Remove Markdown/HTML formatting left over from the PDF conversion."""
    text = text.replace("<br>", " ")
    text = re.sub(r"</?(u|sup|sub|b|i|em|strong)>", "", text)
    text = text.replace("**", "")
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"\1", text)     # _italic_ -> italic
    text = " ".join(text.split())
    return re.sub(r"\s+([,.;:])", r"\1", text)               # "report ." -> "report."

def pull_citations(text):
    """Remove footnote markers from text and return (clean_text, [footnote numbers])."""
    numbers = []
    for group in CITE_MARK.findall(text):
        numbers += [int(n) for n in re.findall(r"\d+", group)]
    return CITE_MARK.sub("", text), numbers


# --- 4. Convert each page to Markdown and split it into elements ---
# Element types: heading, paragraph, table, footnote.
def parse_page(markdown, page_number):
    markdown = PICTURE_TEXT.sub("", markdown)       # text inside charts/pictures = noise
    markdown = HTML_COMMENT.sub("", markdown)
    # Mark footnote references like <sup>12</sup> so we can record them later
    markdown = SUPERSCRIPT.sub(
        lambda m: "{{fn:" + m.group(1) + "}}" if re.fullmatch(r"[\d,\s–-]+", m.group(1)) else m.group(1),
        markdown)

    elements, paragraph_lines, table_lines = [], [], []

    def add_paragraph(raw):
        text, cites = pull_citations(raw)
        # A fully bold short line is a sub-heading, e.g. "**Stop routine flaring**"
        bold = re.fullmatch(r"\*\*([^*]+)\*\*", text.strip())
        if bold and is_heading_like(clean_inline(bold.group(1))):
            elements.append({"type": "heading", "level": 6, "text": clean_inline(bold.group(1)),
                             "page": page_number, "cites": cites})
            return
        # A bold run-in heading at the start: "**Stop routine flaring** Routine flaring ..."
        run_in = re.match(r"\*\*([^*]{3,80})\*\*\s+(?=[A-Z])", text)
        if run_in and not ends_sentence(clean_inline(run_in.group(1))):
            elements.append({"type": "heading", "level": 6, "text": clean_inline(run_in.group(1)),
                             "page": page_number, "cites": []})
            text = text[run_in.end():]
        text = clean_inline(text)
        text = re.sub(r"^[*•]\s+", "- ", text)                 # one bullet style
        if text:
            elements.append({"type": "paragraph", "text": text, "page": page_number, "cites": cites})

    def flush():
        if paragraph_lines:
            text = ""
            for line in paragraph_lines:
                if text.endswith("-") and text[-2:-1].isalpha():
                    text += line                                # "short-" + "lived"
                else:
                    text = f"{text} {line}" if text else line
            add_paragraph(text)
            paragraph_lines.clear()
        if table_lines:
            rows = [clean_inline(CITE_MARK.sub("", r)) for r in table_lines]
            rows = [r for r in rows if not DOT_LEADER.search(r)]   # drop table-of-contents rows
            if any(re.search(r"[A-Za-z]", r) for r in rows):
                elements.append({"type": "table", "text": "\n".join(rows),
                                 "page": page_number, "cites": []})
            table_lines.clear()

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            flush()
            continue

        # Footnotes / references at the bottom of the page, e.g. "> 12 IPCC AR6 WG I 2021"
        footnote = FOOTNOTE_LINE.match(line)
        if footnote and ("<u>" in line or line.startswith(">")):
            flush()
            text, _ = pull_citations(footnote.group(2))
            elements.append({"type": "footnote", "number": int(footnote.group(1)),
                             "text": clean_inline(text), "page": page_number})
            continue

        # Skip image placeholders, photo credits, rules, code fences and bare page numbers
        if (line.startswith("![") or "intentionally omitted" in line
                or re.match(r"^\**photo\b", line, re.IGNORECASE)
                or re.fullmatch(r"[-*_=]{3,}", line) or line.startswith("```")
                or line.isdigit()):
            continue

        heading = HEADING_LINE.match(line)
        if heading:
            text, cites = pull_citations(heading.group(2))
            text = clean_inline(text)
            if re.search(r"[A-Za-z]", text) and len(text) <= 150:
                flush()
                elements.append({"type": "heading", "level": len(heading.group(1)),
                                 "text": text, "page": page_number, "cites": cites})
                continue
            line = heading.group(2)          # not a real heading: treat as normal text

        if line.startswith("|"):
            if paragraph_lines:
                flush()
            table_lines.append(line)
            continue

        if table_lines:
            flush()
        if LIST_ITEM.match(line):
            flush()                          # each list item is its own paragraph
        paragraph_lines.append(line)

    flush()
    return elements

print("Converting PDF to Markdown (this can take a moment)...")
page_markdowns = pymupdf4llm.to_markdown(PDF_PATH, page_chunks=True)

elements = []
for page_index, page_data in enumerate(page_markdowns):
    elements.extend(parse_page(page_data["text"], page_index + 1))

footnotes = {}   # footnote number -> {"text", "page"}
for e in elements:
    if e["type"] == "footnote":
        footnotes.setdefault(e["number"], {"text": e["text"], "page": e["page"]})
elements = [e for e in elements if e["type"] != "footnote"]

if not elements:
    raise ValueError("No text found in this PDF. It may be scanned images (needs OCR).")


# --- 5. Fix headings ---
# 5a. Figure/table captions are not section headings.
for e in elements:
    if e["type"] == "heading" and CAPTION.match(e["text"]) and not e["text"].lower().startswith("box"):
        e["type"] = "paragraph"

# 5b. Headings numbered like other headings ("ACTION 7", "Box 1") but printed as
#     plain text get promoted to the same heading level as their siblings.
prefix_levels = defaultdict(Counter)
for e in elements:
    if e["type"] == "heading":
        prefix = re.match(r"^([A-Za-z]+)\s*\d+", e["text"])
        if prefix:
            prefix_levels[prefix.group(1).lower()][e["level"]] += 1
for e in elements:
    if e["type"] == "paragraph" and len(e["text"]) <= HEADING_MAX_CHARS and not ends_sentence(e["text"]):
        prefix = re.match(r"^([A-Za-z]+)\s*\d+", e["text"])
        if prefix and prefix.group(1).lower() in prefix_levels:
            e["type"] = "heading"
            e["level"] = prefix_levels[prefix.group(1).lower()].most_common(1)[0][0]

# 5c. Headings cut off by the layout ("... ACTIONS IN THE" + later "FOSSIL FUEL SECTOR")
for i, e in enumerate(elements):
    if e["type"] == "heading" and DANGLING_WORD.search(e["text"]):
        for other in elements[i + 1:]:
            if other["page"] != e["page"]:
                break
            candidate = LIST_ITEM.sub("", other["text"])
            if (other["type"] == "paragraph" and len(candidate) <= 60
                    and (candidate.isupper() or candidate[:1].islower())):
                e["text"] += " " + candidate
                other["type"] = "removed"
                break
elements = [e for e in elements if e["type"] != "removed"]

# 5d. Chapter level = the highest heading level with 2+ different headings.
#     Levels above it hold the document title (repeated), which we don't need per chunk.
texts_per_level = defaultdict(set)
for e in elements:
    if e["type"] == "heading":
        texts_per_level[e["level"]].add(e["text"])
chapter_level = min((lvl for lvl, texts in texts_per_level.items() if len(texts) >= 2), default=1)
title_headings = [e["text"] for e in elements if e["type"] == "heading" and e["level"] < chapter_level]

doc_title = DOC_TITLE or pdf_title or (title_headings[0] if title_headings else source_name.rsplit(".", 1)[0])
elements = [e for e in elements if not (e["type"] == "heading" and e["level"] < chapter_level)]


# --- 6. Remove running headers/footers ---
# Short lines at the top of pages that repeat a chapter name (or repeat on many pages).
heading_keys = {normalise(e["text"]) for e in elements if e["type"] == "heading"}
first_on_page = defaultdict(list)
for e in elements:
    if len(first_on_page[e["page"]]) < 3:
        first_on_page[e["page"]].append(e)
top_counts = Counter(normalise(e["text"]) for items in first_on_page.values() for e in items
                     if e["type"] == "paragraph")
pages_with = defaultdict(set)     # short text -> pages it appears on
for e in elements:
    if e["type"] != "table" and len(e["text"]) <= HEADING_MAX_CHARS:
        pages_with[normalise(e["text"])].add(e["page"])

for items in first_on_page.values():
    for e in items:
        key = normalise(e["text"])
        if e["type"] == "paragraph" and len(e["text"]) <= HEADING_MAX_CHARS and (
                key in heading_keys or top_counts[key] >= 2):
            e["type"] = "removed"
seen_headings = set()
for e in elements:
    key = normalise(e["text"])
    if e["type"] == "heading" and key not in seen_headings:
        seen_headings.add(key)       # the first time a heading appears it is the real one
        continue
    if (e["type"] in ("paragraph", "heading") and len(e["text"]) <= HEADING_MAX_CHARS
            and len(pages_with[key]) >= max(3, num_pages // 3)):
        e["type"] = "removed"
removed_texts = [e["text"] for e in elements if e["type"] == "removed"]
elements = [e for e in elements if e["type"] != "removed"]


# --- 7. Repair paragraphs broken by page breaks, columns and figures ---
def unfinished(e):
    """A long paragraph that stops in the middle of a sentence."""
    return (e["type"] == "paragraph" and len(e["text"]) >= 100 and not is_list_item(e["text"])
            and not ends_sentence(e["text"]) and not CAPTION.match(e["text"]))

def join(target, piece):
    target["text"] = target["text"] + " " + piece["text"]
    target["cites"] = target["cites"] + piece["cites"]
    target.setdefault("pages", {target["page"]}).add(piece["page"])
    piece["type"] = "removed"

for e in elements:
    e["pages"] = {e["page"]}

# 7a. "(Source: ...)" lines belong to the caption/paragraph right before them.
for prev, e in zip(elements, elements[1:]):
    if (e["type"] == "paragraph" and e["text"].startswith("(Source") and prev["type"] == "paragraph"
            and prev["page"] == e["page"]):
        join(prev, e)
elements = [e for e in elements if e["type"] != "removed"]

# 7b. A paragraph starting in lowercase continues an unfinished sentence. Find that
#     sentence: first look backwards (same or previous page), then forwards on the
#     same page (PDF layouts sometimes store the second half first).
for i, e in enumerate(elements):
    if e["type"] != "paragraph" or not e["text"][:1].islower():
        continue
    target = None
    for prev in reversed(elements[:i]):
        if prev["page"] < e["page"] - 1:
            break
        if unfinished(prev):
            target = prev
            break
    if target is None:
        for nxt in elements[i + 1:]:
            if nxt["page"] != e["page"]:
                break
            if unfinished(nxt):
                target = nxt
                break
    if target is not None:
        join(target, e)
elements = [e for e in elements if e["type"] != "removed"]

# 7c. A long paragraph that still stops mid-sentence continues in the next paragraph.
for e, nxt in zip(elements, elements[1:]):
    if (unfinished(e) and nxt["type"] == "paragraph"
            and not is_list_item(nxt["text"]) and not is_heading_like(nxt["text"])
            and nxt["page"] - e["page"] <= 1):
        join(e, nxt)
elements = [e for e in elements if e["type"] != "removed"]


# --- 8. Assign chapter / section to every element ---
chapter = "(front matter)"
heading_stack = []
for e in elements:
    if e["type"] == "heading":
        if e["level"] <= chapter_level:
            chapter, heading_stack = e["text"], []
        else:
            while heading_stack and heading_stack[-1][0] >= e["level"]:
                heading_stack.pop()
            heading_stack.append((e["level"], e["text"]))
    e["chapter"] = chapter
    e["section"] = heading_stack[-1][1] if heading_stack else chapter   # most specific heading
    if FRONT_MATTER.search(chapter):
        e["content_type"] = "front_matter"
    elif e["type"] == "table":
        e["content_type"] = "table"
    else:
        e["content_type"] = "content"

# Which chapter cites each footnote (used to group the reference chunks)
footnote_chapter = {}
for e in elements:
    for n in e["cites"]:
        footnote_chapter.setdefault(n, e["chapter"])


# --- 9. Split only what is too long: paragraphs by sentence, tables by row ---
def pack(pieces, limit, joiner=" "):
    """Join pieces of text into groups whose token count stays within `limit`."""
    groups, current, current_tokens = [], [], 0
    for piece in pieces:
        piece_tokens = count_tokens(piece)
        if current and current_tokens + piece_tokens > limit:
            groups.append(joiner.join(current))
            current, current_tokens = [], 0
        current.append(piece)
        current_tokens += piece_tokens
    if current:
        groups.append(joiner.join(current))
    return groups

def split_table(text, limit):
    """Split a Markdown table into pieces, repeating the header rows in each piece."""
    rows = text.split("\n")
    if count_tokens(text) <= limit or len(rows) <= 3:
        return [text]
    header, body = rows[:2], rows[2:]
    budget = limit - count_tokens("\n".join(header))
    return ["\n".join(header) + "\n" + group for group in pack(body, budget, joiner="\n")]

def split_paragraph(text, limit):
    """Split a paragraph at sentence boundaries (between words only as a last resort)."""
    sentences = []
    for s in split_sentences(text):
        sentences.extend(pack(s.split(), limit) if count_tokens(s) > limit else [s])
    return pack(sentences, min(limit, TARGET_TOKENS))

units = []
for e in elements:
    if e["type"] == "table":
        pieces = split_table(e["text"], MAX_BODY_TOKENS)
    elif e["type"] == "paragraph" and count_tokens(e["text"]) > MAX_BODY_TOKENS:
        pieces = split_paragraph(e["text"], MAX_BODY_TOKENS)
    else:
        pieces = [e["text"]]
    for piece in pieces:
        units.append({**e, "text": piece, "tokens": count_tokens(piece)})

# Tokens remaining in the same section from each unit onwards (for the "tail" rule)
remaining_in_section = [0] * len(units)
running = 0
for i in range(len(units) - 1, -1, -1):
    if i == len(units) - 1 or units[i + 1]["section"] != units[i]["section"] \
            or units[i + 1]["chapter"] != units[i]["chapter"]:
        running = 0
    running += units[i]["tokens"]
    remaining_in_section[i] = running


# --- 10. Build chunks from whole units ---
def total_tokens(group):
    return sum(u["tokens"] for u in group)

def has_content(group):
    return any(u["type"] in ("paragraph", "table") and not u.get("is_overlap") for u in group)

def introduces(unit, next_unit):
    """True if `unit` is a heading/label or table caption that belongs with what follows."""
    if unit.get("is_overlap") or unit["type"] == "table":
        return False
    if unit["type"] == "heading" or is_heading_like(unit["text"]):
        return True
    return next_unit["type"] == "table" and len(unit["text"]) <= 250 and bool(CAPTION.match(unit["text"]))

def sentence_overlap(unit):
    """The last whole sentence(s) of a unit, up to OVERLAP_TOKENS, or None."""
    if is_list_item(unit["text"]):
        return None
    picked = []
    for sentence in reversed(split_sentences(unit["text"])):
        if count_tokens(" ".join([sentence] + picked)) > OVERLAP_TOKENS:
            break
        picked.insert(0, sentence)
    if not picked or len(picked) == len(split_sentences(unit["text"])):
        return None          # never repeat a whole paragraph
    text = " ".join(picked)
    return {**unit, "text": text, "tokens": count_tokens(text), "is_overlap": True, "cites": []}

def kind(unit):
    """Front matter never shares a chunk with main content."""
    return "front_matter" if unit["content_type"] == "front_matter" else "main"

groups, current = [], []
for i, unit in enumerate(units):
    if current and not has_content(current) and current[-1]["chapter"] != unit["chapter"]:
        current = []     # headings of a chapter with no text of its own (e.g. empty contents page)
    if has_content(current):
        last = current[-1]
        new_chapter = unit["chapter"] != last["chapter"] or kind(unit) != kind(last)
        new_section = unit["type"] == "heading" and total_tokens(current) >= MIN_TOKENS
        table_boundary = unit["type"] == "table" or last["type"] == "table"
        too_big = total_tokens(current) + unit["tokens"] > MAX_BODY_TOKENS
        short_tail = (remaining_in_section[i] <= SECTION_TAIL_TOKENS
                      and unit["section"] == last["section"] and unit["type"] != "heading")
        # Keep a bullet list together with its introduction ("... include:") when it fits
        inside_list = is_list_item(unit["text"]) and (is_list_item(last["text"]) or last["text"].endswith(":"))
        big_enough = total_tokens(current) >= TARGET_TOKENS and not short_tail and not inside_list

        if new_chapter or new_section or table_boundary or too_big or big_enough:
            carry = []
            if not new_chapter:
                # Keep headings/captions with the text they introduce
                while (current and introduces(current[-1], unit)
                       and total_tokens(carry) + current[-1]["tokens"] + unit["tokens"] <= MAX_BODY_TOKENS):
                    carry.insert(0, current.pop())
                # Overlap only inside the same section, and never around tables
                if (not carry and not new_section and not table_boundary
                        and current[-1]["section"] == unit["section"]):
                    overlap = sentence_overlap(current[-1])
                    if overlap and overlap["tokens"] + unit["tokens"] <= MAX_BODY_TOKENS:
                        carry = [overlap]
            if has_content(current):
                groups.append(current)
            else:
                carry = current + carry
            current = carry
    current.append(unit)
if current:
    groups.append(current)

# Merge chunks that are still very small into a neighbour from the same chapter
def real_tokens(group):
    return total_tokens([u for u in group if not u.get("is_overlap")])

def can_merge(a, b):
    return (a[-1]["chapter"] == b[0]["chapter"] and kind(a[-1]) == kind(b[0])
            and not any(u["type"] == "table" for u in a + b)
            and total_tokens(a) + real_tokens(b) <= MAX_BODY_TOKENS)

i = 0
while i < len(groups):
    g = groups[i]
    if real_tokens(g) < MIN_TOKENS and len(groups) > 1:
        if i > 0 and can_merge(groups[i - 1], g):
            groups[i - 1].extend(u for u in g if not u.get("is_overlap"))
            groups.pop(i)
            continue
        if i + 1 < len(groups) and can_merge(g, groups[i + 1]):
            groups[i + 1] = g + [u for u in groups[i + 1] if not u.get("is_overlap")]
            groups.pop(i)
            continue
    i += 1


# --- 11. Build the reference chunks (footnotes grouped by chapter) ---
reference_groups = defaultdict(list)
for n in sorted(footnotes):
    reference_groups[footnote_chapter.get(n, "(uncited)")].append(n)

reference_units = []
for chapter_name, numbers in reference_groups.items():
    lines = [f"[{n}] {footnotes[n]['text']}" for n in numbers]
    for piece in pack(lines, TARGET_TOKENS, joiner="\n"):
        nums = [int(x) for x in re.findall(r"^\[(\d+)\]", piece, re.M)]
        reference_units.append([{
            "type": "references", "text": piece, "tokens": count_tokens(piece),
            "pages": {footnotes[n]["page"] for n in nums}, "cites": [],
            "chapter": chapter_name, "section": "Footnotes", "content_type": "references",
        }])


# --- 12. Turn groups into chunk dictionaries (and make sure each fits the model) ---
def section_label(group):
    """Short 'Chapter › most specific heading' label (no full heading hierarchy)."""
    chapters, sections = [], []
    for u in group:
        if u.get("is_overlap"):
            continue
        if u["chapter"] not in chapters:
            chapters.append(u["chapter"])
        if u["section"] != u["chapter"] and u["section"] not in sections:
            sections.append(u["section"])
    if len(chapters) > 1:
        return " | ".join(chapters)
    if not sections:
        return chapters[0]
    extra = " …" if len(sections) > 2 else ""
    return f"{chapters[0]} › {' / '.join(sections[:2])}{extra}"

def make_embed_text(group):
    return f"Source: {doc_title}\nSection: {section_label(group)}\n\n" + \
           "\n\n".join(u["text"] for u in group)

def fit_to_model(group):
    """Split a group at unit boundaries (then sentences) until it fits MAX_EMBED_TOKENS."""
    if count_tokens(make_embed_text(group)) <= MAX_EMBED_TOKENS:
        return [group]
    if len(group) > 1:
        half, running, cut = total_tokens(group) / 2, 0, 1
        for j, u in enumerate(group[:-1]):
            running += u["tokens"]
            if running >= half:
                cut = j + 1
                break
        return fit_to_model(group[:cut]) + fit_to_model(group[cut:])
    unit = group[0]
    limit = MAX_EMBED_TOKENS - count_tokens(make_embed_text([{**unit, "text": ""}])) - 5
    pieces = (split_table(unit["text"], limit) if unit["type"] == "table"
              else split_paragraph(unit["text"], limit))
    if len(pieces) == 1:
        return [group]    # cannot be split further without breaking a sentence
    return [g for p in pieces for g in fit_to_model([{**unit, "text": p, "tokens": count_tokens(p)}])]

all_chunks = []
for group in [g for grp in groups + reference_units for g in fit_to_model(grp)]:
    pages, cites = set(), []
    for u in group:
        pages |= u["pages"]
        cites += [n for n in u["cites"] if n not in cites]
    text = "\n\n".join(u["text"] for u in group)
    types = {u["content_type"] for u in group}
    all_chunks.append({
        "chunk_id": len(all_chunks),
        "document_title": doc_title,
        "source": source_name,
        "content_type": "table" if "table" in types else types.pop(),  # content/table/references/front_matter
        "chapter": group[0]["chapter"],
        "section": section_label(group),
        "page_numbers": sorted(pages),
        "text": text,                             # clean text: show this / cite it
        "embed_text": make_embed_text(group),     # short context header + text: embed this later
        "tokens": count_tokens(make_embed_text(group)),
        "footnotes": cites,                       # footnote numbers cited in this chunk
        "references": [f"[{n}] {footnotes[n]['text']}" for n in cites if n in footnotes],
        "_last_unit": group[-1],                  # used for the quality report only
    })


# --- 13. Quality report ---
REFERENCE_PATTERN = re.compile(r"(^|\n)(\[\d+\]|>|\d{1,3}\s)[^\n]*\b(19|20)\d{2}\b|<u>|\{\{fn", re.M)

def ends_mid_sentence(chunk):
    last = chunk["_last_unit"]
    if (last["type"] in ("table", "heading", "references") or is_list_item(last["text"])
            or is_heading_like(last["text"])):     # titles/labels are not sentences
        return False
    text = re.sub(r"\s*\(Source:[^)]*\)$", "", last["text"])
    return not ends_sentence(text) and not CAPTION.match(text)

content_chunks = [c for c in all_chunks if c["content_type"] in ("content", "table")]
token_counts = [c["tokens"] for c in all_chunks]
mid_sentence = [c["chunk_id"] for c in all_chunks if ends_mid_sentence(c)]
ref_in_content = [c["chunk_id"] for c in content_chunks if REFERENCE_PATTERN.search(c["text"])]

print("\n" + "=" * 70)
print("EcoRAG CHUNKING REPORT (v4)")
print("=" * 70)
print(f"Document title:                  {doc_title}")
print(f"Pages:                           {num_pages}")
print(f"Footnotes/references extracted:  {len(footnotes)}")
print(f"Running headers/footers removed: {len(removed_texts)}")
print(f"Total chunks:                    {len(all_chunks)}  "
      f"{dict(Counter(c['content_type'] for c in all_chunks))}")
print(f"Tokens per chunk (with header):  min {min(token_counts)}, "
      f"avg {sum(token_counts) / len(token_counts):.0f}, max {max(token_counts)}")
print(f"Chunks > {MODEL_MAX_TOKENS} tokens:              {sum(t > MODEL_MAX_TOKENS for t in token_counts)}")
print(f"Chunks ending mid-sentence:      {len(mid_sentence)} {mid_sentence or ''}")
print(f"Content chunks containing reference/bibliography text: {len(ref_in_content)} {ref_in_content or ''}")
print(f"Dedicated reference chunks:      {sum(c['content_type'] == 'references' for c in all_chunks)}")
print(f"Chunks spanning 2+ pages:        {sum(len(c['page_numbers']) > 1 for c in all_chunks)}")

print("\nChunk size distribution (tokens incl. header):")
buckets = Counter((t // 50) * 50 for t in token_counts)
for b in sorted(buckets):
    print(f"  {b:>3}-{b + 49:<3} {'#' * buckets[b]} ({buckets[b]})")

print("\nChunks per chapter:")
for name, n in Counter(c["chapter"] for c in all_chunks).items():
    print(f"  {n:>3}  {name}")

if removed_texts:
    print("\nRemoved running headers/footers (check nothing important is here):")
    for text in sorted(set(removed_texts))[:12]:
        print("  ", repr(text))

for c in all_chunks:
    del c["_last_unit"]
with open("chunks.json", "w", encoding="utf-8") as f:
    json.dump(all_chunks, f, ensure_ascii=False, indent=2)
print("\nSaved all chunks to chunks.json")


# --- 14. Helpers for inspecting chunks ---
def show_chunk(chunk_id):
    c = all_chunks[chunk_id]
    print(f"\n--- Chunk {c['chunk_id']} | {c['content_type']} | pages {c['page_numbers']} "
          f"| {c['tokens']} tokens ---")
    print(c["embed_text"])
    if c["references"]:
        print("  references:", "; ".join(c["references"][:5]) + (" …" if len(c["references"]) > 5 else ""))

def search_chunks(phrase):
    hits = [c["chunk_id"] for c in all_chunks if phrase.lower() in c["text"].lower()]
    print(f"'{phrase}' found in chunks: {hits or 'none'}")
    for h in hits:
        show_chunk(h)


# --- 15. Five representative chunks from different chapters ---
print("\n" + "=" * 70)
print("REPRESENTATIVE CHUNKS")
print("=" * 70)
# Spread the picks over the document (10%, 30%, 50%, 70%, 90%) with no section twice
picked, used_sections = [], set()
for fraction in (0.1, 0.3, 0.5, 0.7, 0.9):
    start = int(fraction * len(content_chunks))
    for c in content_chunks[start:] + content_chunks[:start]:
        if c["section"] not in used_sections and c["chunk_id"] not in picked:
            picked.append(c["chunk_id"])
            used_sections.add(c["section"])
            break
for chunk_id in picked:
    show_chunk(chunk_id)
