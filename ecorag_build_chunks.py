# ============================================================
# EcoRAG - Stage 1 & 2 (batch): chunk EVERY PDF in a folder
# ============================================================
# Folder layout:
#   ecorag_data/pdfs/            <- put all your PDFs here (or point PDF_DIR at your own folder)
#   ecorag_data/chunks/          <- one chunks file per PDF (what the embedding stage reads)
#   ecorag_data/all_chunks.json  <- ALL chunks of ALL PDFs combined in one new JSON file
# The chunking logic is the validated v4 logic, now wrapped in chunk_pdf() and run per PDF.
# Re-running is cheap: PDFs that haven't changed since the last run are skipped.
# No embeddings, vector DB, retrieval or LLM here.

# --- 0. Install libraries ---
!pip install -q pymupdf pymupdf4llm tokenizers

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pymupdf        # PyMuPDF (the newer name for "fitz")
import pymupdf4llm    # PDF -> Markdown converter (detects headings & tables)
from tokenizers import Tokenizer


# --- 1. Settings ---
DATA_DIR = Path("ecorag_data")    # Colab tip: Path("/content/drive/MyDrive/ecorag_data") keeps files
PDF_DIR = DATA_DIR / "pdfs"       # the folder with ALL your PDFs
CHUNKS_DIR = DATA_DIR / "chunks"
COMBINED_FILE = DATA_DIR / "all_chunks.json"

DOC_TITLES = {            # optional short titles for PDFs without a usable title
    "Definitionsfornear-zeroandlow-emissionssteelandcementandunderlyingemissionsmeasurementmethodologies.pdf":
        "Definitions for Near-Zero and Low-Emissions Steel and Cement",
}
FORCE_RECHUNK = False     # True = re-chunk every PDF even if it hasn't changed
REMOVE_STALE_FILES = True # delete chunk files whose PDF is no longer in PDF_DIR
CHUNKER_VERSION = "v4.4"  # bump this when the chunking rules change, so all PDFs are re-chunked

TOKENIZER_MODEL = "BAAI/bge-small-en-v1.5"  # the embedding model used in the next stage
MODEL_MAX_TOKENS = 512    # that model's hard input limit
MAX_EMBED_TOKENS = 480    # hard cap for header + chunk text (safety margin below 512)
TARGET_TOKENS = 320       # stop adding paragraphs once the chunk text reaches about this
MAX_BODY_TOKENS = 400     # chunk text limit while building (header is added on top)
MIN_TOKENS = 80           # chunks smaller than this get merged with a neighbour
SECTION_TAIL_TOKENS = 120 # keep a short end-of-section tail in the chunk instead of orphaning it
OVERLAP_TOKENS = 50       # repeat up to this many tokens of whole sentences in the next chunk
HEADING_MAX_CHARS = 120   # short text without end punctuation may be a heading
RUNNING_HEADER_MAX_CHARS = 300  # repeated page headers/footers up to this long are removed
                                # (only when they recur on many pages, never for length alone)


# --- 2. Tokenizer and small text helpers ---
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
DOT_LEADER = re.compile(r"\.{5,}|�{3,}")   # "....." or "�����" (unreadable dots) in contents pages
FRONT_MATTER = re.compile(r"acknowledg|table of contents|^contents$|^\(front matter\)$"
                          r"|abbreviations|acronyms|glossary", re.IGNORECASE)
GLOSSARY_HEADING = re.compile(r"abbreviations|acronyms|glossary", re.IGNORECASE)
REFERENCES_HEADING = re.compile(r"^(references|bibliography|works cited|literature cited|"
                                r"reference list|sources)$", re.IGNORECASE)
TOC_HEADING = re.compile(r"^(table of )?contents$", re.IGNORECASE)
# Section names that start a new chapter even when the PDF prints them as plain text
KNOWN_SECTION = re.compile(r"^(executive summary|summary|foreword|preface|introduction|overview|"
                           r"key (findings|messages|recommendations)|conclusions?|chapter \d+|"
                           r"annex [a-z0-9]+|appendix [a-z0-9]+)$", re.IGNORECASE)
DANGLING_WORD = re.compile(r"\b(the|and|of|in|for|to|a|an|on|with|from|by|or)$", re.IGNORECASE)

def make_document_id(source_filename):
    """Stable, readable ID from the PDF file name: 'UN Report 2025.pdf' -> 'un-report-2025'."""
    return re.sub(r"[^a-z0-9]+", "-", Path(source_filename).stem.lower()).strip("-")

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
    text = re.sub(r"</?(u|sup|sub|b|i|em|strong|mark|s|del|strike|ins|span|small)\b[^>]*>", "", text)
    text = text.replace("**", "").replace("~~", "")          # bold / strikethrough marks
    text = re.sub(r"\b(?:[A-Z] ){3,}[A-Z]\b",                # letter-spaced "S U M M A R Y"
                  lambda m: m.group(0).replace(" ", ""), text)
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"\1", text)     # _italic_ -> italic
    text = " ".join(text.split())
    return re.sub(r"\s+([,.;:])", r"\1", text)               # "report ." -> "report."

def pull_citations(text):
    """Remove footnote markers from text and return (clean_text, [footnote numbers])."""
    numbers = []
    for group in CITE_MARK.findall(text):
        numbers += [int(n) for n in re.findall(r"\d+", group)]
    return CITE_MARK.sub("", text), numbers


# --- 3. Turn one page of Markdown into elements (heading, paragraph, table, footnote) ---
def parse_page(markdown, page_number):
    # Some PDFs store the dot in "3.3" as an unreadable glyph that arrives as "�"
    markdown = re.sub(r"(\d)�(\d)", r"\1.\2", markdown)
    markdown = re.sub(r"(?:https?://|www)\S+", lambda m: m.group(0).replace("�", "."), markdown)
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


# --- 4. Helpers for repairing paragraphs and building chunks ---
def unfinished(e):
    """A long paragraph that stops in the middle of a sentence."""
    return (e["type"] == "paragraph" and len(e["text"]) >= 100 and not is_list_item(e["text"])
            and not ends_sentence(e["text"]) and not CAPTION.match(e["text"])
            and not e.get("in_refs"))     # bibliography entries often end without a full stop

def join(target, piece):
    target["text"] = target["text"] + " " + piece["text"]
    target["cites"] = target["cites"] + piece["cites"]
    target.setdefault("pages", {target["page"]}).add(piece["page"])
    piece["type"] = "removed"

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

def split_glossary(text, limit):
    """Split a run-together abbreviations list ("ADB Asian Development Bank AFOLU ...")
    before acronym-like words, so cuts land at the start of an entry."""
    entries, current = [], []
    for word in text.split():
        is_term = (re.fullmatch(r"[A-Z0-9][\w+&$/.-]*", word)          # e.g. ADB, CH4D, 3-NOP
                   and any(ch.isupper() for ch in word)                  # not plain numbers like "19"
                   and sum(ch.isupper() or ch.isdigit() for ch in word) >= 2)
        if is_term and len(current) >= 2:     # a term needs at least one word of definition
            entries.append(" ".join(current))
            current = []
        current.append(word)
    if current:
        entries.append(" ".join(current))
    return pack(entries, min(limit, TARGET_TOKENS))

def total_tokens(group):
    return sum(u["tokens"] for u in group)

def real_tokens(group):
    return total_tokens([u for u in group if not u.get("is_overlap")])

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
    """Front matter and bibliography never share a chunk with main content."""
    if unit["content_type"] in ("front_matter", "references"):
        return unit["content_type"]
    return "main"

def can_merge(a, b):
    return (a[-1]["chapter"] == b[0]["chapter"] and kind(a[-1]) == kind(b[0])
            and not any(u["type"] == "table" for u in a + b)
            and total_tokens(a) + real_tokens(b) <= MAX_BODY_TOKENS)

def section_label(group):
    """Short 'Chapter › most specific heading' label (no full heading hierarchy)."""
    chapters, sections = [], []
    for u in group:
        if u.get("is_overlap"):
            continue
        if u["chapter"] not in chapters:
            chapters.append(u["chapter"])
        if u["section"].lower() != u["chapter"].lower() and u["section"] not in sections:
            sections.append(u["section"])
    if len(chapters) > 1:
        return " | ".join(chapters)
    if not sections:
        return chapters[0]
    extra = " …" if len(sections) > 2 else ""
    return f"{chapters[0]} › {' / '.join(sections[:2])}{extra}"

def make_embed_text(group, doc_title):
    return f"Source: {doc_title}\nSection: {section_label(group)}\n\n" + \
           "\n\n".join(u["text"] for u in group)

def fit_to_model(group, doc_title):
    """Split a group at unit boundaries (then sentences) until it fits MAX_EMBED_TOKENS."""
    if count_tokens(make_embed_text(group, doc_title)) <= MAX_EMBED_TOKENS:
        return [group]
    if len(group) > 1:
        half, running, cut = total_tokens(group) / 2, 0, 1
        for j, u in enumerate(group[:-1]):
            running += u["tokens"]
            if running >= half:
                cut = j + 1
                break
        return fit_to_model(group[:cut], doc_title) + fit_to_model(group[cut:], doc_title)
    unit = group[0]
    limit = MAX_EMBED_TOKENS - count_tokens(make_embed_text([{**unit, "text": ""}], doc_title)) - 5
    pieces = (split_table(unit["text"], limit) if unit["type"] == "table"
              else split_paragraph(unit["text"], limit))
    if len(pieces) == 1:
        return [group]    # cannot be split further without breaking a sentence
    return [g for p in pieces
            for g in fit_to_model([{**unit, "text": p, "tokens": count_tokens(p)}], doc_title)]

def ends_mid_sentence(last_unit):
    """Quality check: does a chunk's last paragraph stop in the middle of a sentence?"""
    if (last_unit["type"] in ("table", "heading", "references") or is_list_item(last_unit["text"])
            or is_heading_like(last_unit["text"])      # titles/labels are not sentences
            or last_unit.get("content_type") in ("references", "front_matter")):  # citations, name lists
        return False
    text = re.sub(r"\s*\(Source:[^)]*\)$", "", last_unit["text"])
    return not ends_sentence(text) and not CAPTION.match(text)


# --- 5. The whole v4 pipeline for ONE PDF ---
def chunk_pdf(pdf_path, doc_title=None):
    """Turn one PDF into a list of chunk dictionaries. Returns (chunks, info)."""
    pdf_path = Path(pdf_path)
    source_filename = pdf_path.name
    document_id = make_document_id(source_filename)

    with pymupdf.open(pdf_path) as doc:
        num_pages = len(doc)
        pdf_title = ((doc.metadata or {}).get("title") or "").strip()

    # 5.1 PDF -> Markdown pages -> elements
    page_markdowns = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True)
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

    # 5.2 Fix headings
    for e in elements:   # figure/table captions are not section headings
        if e["type"] == "heading" and CAPTION.match(e["text"]) and not e["text"].lower().startswith("box"):
            e["type"] = "paragraph"

    # Headings numbered like siblings ("ACTION 7", "Box 1") but printed as plain text
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

    # Headings cut off by the layout ("... ACTIONS IN THE" + later "FOSSIL FUEL SECTOR")
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

    # Chapter level = the highest heading level with 2+ different headings;
    # levels above it hold the (repeated) document title.
    texts_per_level = defaultdict(set)
    for e in elements:
        if e["type"] == "heading":
            texts_per_level[e["level"]].add(e["text"])
    chapter_level = min((lvl for lvl, texts in texts_per_level.items() if len(texts) >= 2), default=1)
    title_headings = [e["text"] for e in elements if e["type"] == "heading" and e["level"] < chapter_level]
    doc_title = doc_title or pdf_title or (title_headings[0] if title_headings else pdf_path.stem)
    elements = [e for e in elements if not (e["type"] == "heading" and e["level"] < chapter_level)]

    # 5.2b The real sections after a table of contents are sometimes printed as plain
    #      (italic) text or as small headings, so they would stay inside the "Table of
    #      Contents" chapter and be typed front_matter. From a contents chapter onwards,
    #      until the next real chapter heading:
    #      - a known section name at the top of a page ("Executive summary", "Chapter 1")
    #        starts a new chapter;
    #      - inside the contents chapter itself, the first long prose paragraph ends it
    #        (a table of contents never contains prose).
    #      Runs before running-header removal, which could otherwise delete these lines.
    chapter_name, promoting, pages_seen = "", False, set()
    for i, e in enumerate(elements):
        is_first = e["page"] not in pages_seen
        pages_seen.add(e["page"])
        if e["type"] == "removed":
            continue
        if e["type"] == "heading" and e["level"] <= chapter_level:
            chapter_name, promoting = e["text"], bool(TOC_HEADING.match(e["text"]))
            continue
        if not promoting or e["type"] not in ("paragraph", "heading"):
            continue
        if is_first and KNOWN_SECTION.match(e["text"]):
            e["type"], e["level"] = "heading", chapter_level
            nxt = elements[i + 1] if i + 1 < len(elements) else None
            if (re.match(r"^chapter \d+$", e["text"], re.IGNORECASE) and nxt and nxt["page"] == e["page"]
                    and nxt["type"] in ("paragraph", "heading") and len(nxt["text"]) <= HEADING_MAX_CHARS):
                e["text"] = f"{e['text']}: {nxt['text']}"    # "Chapter 1: Unlocking clean energy investment"
                nxt["type"] = "removed"
            chapter_name = e["text"]
        elif (TOC_HEADING.match(chapter_name) and e["type"] == "paragraph"
                and len(e["text"]) >= 200 and ends_sentence(e["text"])):
            e["untitled_chapter"] = True
            chapter_name = "(untitled section)"
    elements = [e for e in elements if e["type"] != "removed"]

    # 5.3 Remove running headers/footers
    heading_keys = {normalise(e["text"]) for e in elements if e["type"] == "heading"}
    first_on_page = defaultdict(list)
    for e in elements:
        if len(first_on_page[e["page"]]) < 3:
            first_on_page[e["page"]].append(e)
    top_counts = Counter(normalise(e["text"]) for items in first_on_page.values() for e in items
                         if e["type"] == "paragraph")
    pages_with = defaultdict(set)     # repeated text -> pages it appears on
    for e in elements:
        if e["type"] != "table" and len(e["text"]) <= RUNNING_HEADER_MAX_CHARS:
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
        # Removed because it RECURS on at least a third of the pages (a page header/footer);
        # long text is only removed when it repeats like this, never for its length alone.
        if (e["type"] in ("paragraph", "heading") and len(e["text"]) <= RUNNING_HEADER_MAX_CHARS
                and len(pages_with[key]) >= max(3, num_pages // 3)):
            e["type"] = "removed"
    removed_texts = [e["text"] for e in elements if e["type"] == "removed"]
    elements = [e for e in elements if e["type"] != "removed"]

    # Mark bibliography chapters ("References", ...) and abbreviation lists, which are
    # lists of entries, not prose: they are not repaired or overlapped like paragraphs.
    in_refs = in_glossary = False
    for e in elements:
        if e["type"] == "heading" and e["level"] <= chapter_level:
            name = re.sub(r"^[\d.\s]+", "", e["text"]).strip()
            in_refs = bool(REFERENCES_HEADING.match(name))
            in_glossary = bool(GLOSSARY_HEADING.search(name))
        e["in_refs"], e["glossary"] = in_refs, in_glossary

    # 5.4 Repair paragraphs broken by page breaks, columns and figures
    for e in elements:
        e["pages"] = {e["page"]}
    for prev, e in zip(elements, elements[1:]):   # "(Source: ...)" belongs to the caption before it
        if (e["type"] == "paragraph" and e["text"].startswith("(Source") and prev["type"] == "paragraph"
                and prev["page"] == e["page"]):
            join(prev, e)
    elements = [e for e in elements if e["type"] != "removed"]

    for i, e in enumerate(elements):              # lowercase start = continuation of a sentence
        if e["type"] != "paragraph" or not e["text"][:1].islower() or e["in_refs"]:
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

    for e, nxt in zip(elements, elements[1:]):    # still unfinished: continues in the next paragraph
        if (unfinished(e) and nxt["type"] == "paragraph"
                and not is_list_item(nxt["text"]) and not is_heading_like(nxt["text"])
                and nxt["page"] - e["page"] <= 1):
            join(e, nxt)
    elements = [e for e in elements if e["type"] != "removed"]

    # 5.5 Assign chapter / section / content type
    chapter, heading_stack = "(front matter)", []
    for e in elements:
        if e.get("untitled_chapter"):     # prose found after a table of contents (see 5.3b)
            chapter, heading_stack = "(untitled section)", []
        if e["type"] == "heading":
            if e["level"] <= chapter_level:
                chapter, heading_stack = e["text"], []
            else:
                while heading_stack and heading_stack[-1][0] >= e["level"]:
                    heading_stack.pop()
                heading_stack.append((e["level"], e["text"]))
        e["chapter"] = chapter
        e["section"] = heading_stack[-1][1] if heading_stack else chapter
        if e["in_refs"]:
            e["content_type"] = "references"
        elif FRONT_MATTER.search(chapter):
            e["content_type"] = "front_matter"
        elif e["type"] == "table":
            e["content_type"] = "table"
        else:
            e["content_type"] = "content"

    footnote_chapter = {}
    for e in elements:
        for n in e["cites"]:
            footnote_chapter.setdefault(n, e["chapter"])

    # 5.6 Split only what is too long: paragraphs by sentence, tables by row
    units = []
    for e in elements:
        if e["type"] == "table":
            pieces = split_table(e["text"], MAX_BODY_TOKENS)
        elif e["type"] == "paragraph" and e["glossary"] and count_tokens(e["text"]) > MAX_BODY_TOKENS:
            pieces = split_glossary(e["text"], MAX_BODY_TOKENS)
        elif e["type"] == "paragraph" and count_tokens(e["text"]) > MAX_BODY_TOKENS:
            pieces = split_paragraph(e["text"], MAX_BODY_TOKENS)
        else:
            pieces = [e["text"]]
        for piece in pieces:
            units.append({**e, "text": piece, "tokens": count_tokens(piece)})

    remaining_in_section = [0] * len(units)   # tokens left in the section from each unit on
    running = 0
    for i in range(len(units) - 1, -1, -1):
        if i == len(units) - 1 or units[i + 1]["section"] != units[i]["section"] \
                or units[i + 1]["chapter"] != units[i]["chapter"]:
            running = 0
        running += units[i]["tokens"]
        remaining_in_section[i] = running

    # 5.7 Build chunks from whole units
    groups, current = [], []
    for i, unit in enumerate(units):
        if current and not has_content(current) and current[-1]["chapter"] != unit["chapter"]:
            current = []     # headings of a chapter with no text of its own
        if has_content(current):
            last = current[-1]
            new_chapter = unit["chapter"] != last["chapter"] or kind(unit) != kind(last)
            new_section = unit["type"] == "heading" and total_tokens(current) >= MIN_TOKENS
            table_boundary = unit["type"] == "table" or last["type"] == "table"
            too_big = total_tokens(current) + unit["tokens"] > MAX_BODY_TOKENS
            short_tail = (remaining_in_section[i] <= SECTION_TAIL_TOKENS
                          and unit["section"] == last["section"] and unit["type"] != "heading")
            inside_list = is_list_item(unit["text"]) and (is_list_item(last["text"]) or last["text"].endswith(":"))
            big_enough = total_tokens(current) >= TARGET_TOKENS and not short_tail and not inside_list

            if new_chapter or new_section or table_boundary or too_big or big_enough:
                carry = []
                if not new_chapter:
                    while (current and introduces(current[-1], unit)
                           and total_tokens(carry) + current[-1]["tokens"] + unit["tokens"] <= MAX_BODY_TOKENS):
                        carry.insert(0, current.pop())
                    if (not carry and not new_section and not table_boundary
                            and current[-1]["section"] == unit["section"]
                            and not current[-1]["in_refs"] and not current[-1]["glossary"]):
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

    i = 0                                          # merge very small chunks into a neighbour
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

    # 5.8 Reference chunks (footnotes grouped by chapter)
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

    # 5.9 Chunk dictionaries (each one checked against the model limit)
    chunks, mid_sentence = [], 0
    for group in [g for grp in groups + reference_units for g in fit_to_model(grp, doc_title)]:
        pages, cites = set(), []
        for u in group:
            pages |= u["pages"]
            cites += [n for n in u["cites"] if n not in cites]
        types = {u["content_type"] for u in group}
        embed_text = make_embed_text(group, doc_title)
        local_id = len(chunks)
        chunks.append({
            "id": f"{document_id}::{local_id:04d}",   # globally unique across all PDFs
            "chunk_id": local_id,                     # position inside this PDF
            "document_id": document_id,
            "source_filename": source_filename,
            "document_title": doc_title,
            "content_type": "table" if "table" in types else types.pop(),
            "chapter": group[0]["chapter"],
            "section": section_label(group),
            "page_numbers": sorted(pages),
            "text": "\n\n".join(u["text"] for u in group),   # clean text: show this / cite it
            "embed_text": embed_text,                        # context header + text: embed this
            "tokens": count_tokens(embed_text),
            "footnotes": cites,
            "references": [f"[{n}] {footnotes[n]['text']}" for n in cites if n in footnotes],
        })
        mid_sentence += ends_mid_sentence(group[-1])

    info = {"num_pages": num_pages, "num_footnotes": len(footnotes),
            "headers_removed": len(removed_texts), "mid_sentence": mid_sentence}
    return chunks, info


# --- 6. Find the PDFs ---
PDF_DIR.mkdir(parents=True, exist_ok=True)
CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

def list_pdfs():
    return sorted(p for p in PDF_DIR.iterdir() if p.is_file() and p.suffix.lower() == ".pdf")

pdf_paths = list_pdfs()
if not pdf_paths:
    try:
        from google.colab import files
        print(f"No PDFs in {PDF_DIR}/ - please select ALL the PDFs to upload (you can pick many at once)...")
        for name, data in files.upload().items():
            (PDF_DIR / name).write_bytes(data)
        pdf_paths = list_pdfs()
    except ImportError:
        pass
if not pdf_paths:
    raise FileNotFoundError(f"No PDF files found in {PDF_DIR}/")
print(f"Found {len(pdf_paths)} PDF(s) in {PDF_DIR}/\n")


# --- 7. Chunk every PDF (skipping unchanged ones) ---
def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

results = []          # one summary per PDF
kept_files = set()    # chunk files that belong to a PDF in the folder
seen_hashes = {}      # pdf content hash -> file name (finds the same PDF saved twice)
seen_ids = {}         # document_id -> file name

for n, pdf in enumerate(pdf_paths, 1):
    doc_id = make_document_id(pdf.name)
    out_path = CHUNKS_DIR / f"{doc_id}.json"
    sha = file_sha256(pdf)
    print(f"[{n}/{len(pdf_paths)}] {pdf.name}")

    if sha in seen_hashes:
        results.append({"file": pdf.name, "status": f"SKIPPED: same content as {seen_hashes[sha]}"})
        continue
    if doc_id in seen_ids:
        results.append({"file": pdf.name, "status": f"SKIPPED: document_id clashes with {seen_ids[doc_id]}"})
        continue
    seen_hashes[sha], seen_ids[doc_id] = pdf.name, pdf.name

    previous = None
    if out_path.exists():
        try:
            previous = json.loads(out_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            previous = None

    if (not FORCE_RECHUNK and previous and previous.get("pdf_sha256") == sha
            and previous.get("chunker_version") == CHUNKER_VERSION
            and previous.get("document_title") == DOC_TITLES.get(pdf.name, previous.get("document_title"))):
        kept_files.add(out_path.name)
        results.append({**previous["summary"], "status": "unchanged (reused)"})
        continue

    try:
        chunks, info = chunk_pdf(pdf, DOC_TITLES.get(pdf.name))
    except Exception as error:   # one bad PDF must not stop the whole batch
        if out_path.exists():
            kept_files.add(out_path.name)
        results.append({"file": pdf.name, "status": f"FAILED: {error}"})
        continue

    token_counts = [c["tokens"] for c in chunks]
    summary = {
        "file": pdf.name, "document_id": doc_id, "title": chunks[0]["document_title"],
        "pages": info["num_pages"], "chunks": len(chunks),
        "types": dict(Counter(c["content_type"] for c in chunks)),
        "tokens_min": min(token_counts), "tokens_avg": round(sum(token_counts) / len(token_counts)),
        "tokens_max": max(token_counts),
        "over_limit": sum(t > MODEL_MAX_TOKENS for t in token_counts),
        "mid_sentence": info["mid_sentence"],
        "multi_page": sum(len(c["page_numbers"]) > 1 for c in chunks),
        "footnotes": info["num_footnotes"], "headers_removed": info["headers_removed"],
    }
    out_path.write_text(json.dumps({
        "document_id": doc_id,
        "source_filename": pdf.name,
        "document_title": chunks[0]["document_title"],
        "pdf_sha256": sha,
        "chunker_version": CHUNKER_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "summary": summary,
        "chunks": chunks,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    kept_files.add(out_path.name)
    results.append({**summary, "status": "chunked"})

# Chunk files whose PDF is gone would otherwise still be embedded later
stale = sorted(p for p in CHUNKS_DIR.glob("*.json") if p.name not in kept_files)
if REMOVE_STALE_FILES:
    for p in stale:
        p.unlink()


# --- 8. Combine every document's chunks into ONE new JSON file ---
all_chunks, documents = [], []
for p in sorted(CHUNKS_DIR.glob("*.json")):
    data = json.loads(p.read_text(encoding="utf-8"))
    all_chunks.extend(data["chunks"])
    documents.append({k: data[k] for k in ("document_id", "source_filename", "document_title")}
                     | {"num_chunks": len(data["chunks"]), "chunk_file": p.name})

id_counts = Counter(c["id"] for c in all_chunks)
duplicate_ids = [i for i, n in id_counts.items() if n > 1]
COMBINED_FILE.write_text(json.dumps({
    "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "chunker_version": CHUNKER_VERSION,
    "num_documents": len(documents),
    "num_chunks": len(all_chunks),
    "documents": documents,
    "chunks": all_chunks,
}, ensure_ascii=False, indent=2), encoding="utf-8")


# --- 9. Report ---
print("\n" + "=" * 78)
print("EcoRAG BATCH CHUNKING REPORT")
print("=" * 78)
for r in results:
    print(f"\n{r['file']}  ->  {r['status']}")
    if "chunks" in r:
        print(f"   document_id: {r['document_id']}")
        print(f"   title:       {r['title']}")
        print(f"   pages {r['pages']} | chunks {r['chunks']} {r['types']}")
        print(f"   tokens min/avg/max {r['tokens_min']}/{r['tokens_avg']}/{r['tokens_max']} | "
              f"> {MODEL_MAX_TOKENS}: {r['over_limit']} | mid-sentence: {r['mid_sentence']} | "
              f"multi-page: {r['multi_page']} | footnotes: {r['footnotes']}")

ok = [r for r in results if "chunks" in r]
failed = [r for r in results if r["status"].startswith(("FAILED", "SKIPPED"))]
all_tokens = [c["tokens"] for c in all_chunks]
print("\n" + "-" * 78)
print(f"PDFs found:                 {len(pdf_paths)}")
print(f"Documents in the dataset:   {len(documents)}  "
      f"({sum(r['status'] == 'chunked' for r in ok)} chunked now, "
      f"{sum(r['status'].startswith('unchanged') for r in ok)} unchanged)")
print(f"Failed / skipped PDFs:      {len(failed)}")
print(f"Total chunks:               {len(all_chunks)}  {dict(Counter(c['content_type'] for c in all_chunks))}")
if all_tokens:
    print(f"Tokens per chunk:           min {min(all_tokens)}, "
          f"avg {sum(all_tokens) / len(all_tokens):.0f}, max {max(all_tokens)}")
print(f"Chunks > {MODEL_MAX_TOKENS} tokens:         {sum(t > MODEL_MAX_TOKENS for t in all_tokens)}")
print(f"IDs globally unique:        {'YES' if not duplicate_ids else 'NO: ' + str(duplicate_ids[:5])}")
if stale:
    print(f"Stale chunk files {'removed' if REMOVE_STALE_FILES else 'found (not removed)'}: "
          f"{[p.name for p in stale]}")
print(f"\nPer-document chunk files:   {CHUNKS_DIR}/")
print(f"Combined JSON file:         {COMBINED_FILE}")
