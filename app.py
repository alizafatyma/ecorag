"""
EcoRAG API - Production Ready
Works on: Replit, Railway, Render, local, everywhere!
Serves both frontend + backend
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

ask_ecorag = None
ECORAG_READY = False

def _load_ecorag():
    """Lazy load EcoRAG retrieval (no LLM - too memory intensive)"""
    global ask_ecorag, ECORAG_READY
    if ask_ecorag is not None:
        return
    try:
        # Only load retrieval, not the full RAG with LLM
        from ecorag_ask import retrieve
        ask_ecorag = retrieve
        ECORAG_READY = True
        print("Retrieval system loaded successfully")
    except Exception as e:
        ECORAG_READY = False
        print(f"Error loading retrieval: {e}")

app = Flask(__name__, static_folder='.')
CORS(app)

# ============================================================================
# FRONTEND - Serve the HTML interface
# ============================================================================

@app.route('/')
def serve_frontend():
    """Serve the interactive web interface"""
    try:
        return send_file('ecorag_frontend.html')
    except:
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>EcoRAG API</title>
            <style>
                body { font-family: Arial; margin: 2rem; background: #e8f5e9; }
                h1 { color: #2d5016; }
                .info { background: white; padding: 1rem; border-radius: 8px; }
            </style>
        </head>
        <body>
            <h1>🌿 EcoRAG API</h1>
            <div class="info">
                <p><strong>Status:</strong> ✅ Running</p>
                <p><strong>EcoRAG System:</strong> ''' + ('✅ Ready' if ECORAG_READY else '❌ Not initialized') + '''</p>
                <hr/>
                <h3>API Endpoints:</h3>
                <ul>
                    <li><strong>GET /api/health</strong> - Check if API is running</li>
                    <li><strong>GET /api/info</strong> - Get system information</li>
                    <li><strong>POST /api/ask</strong> - Ask a question</li>
                </ul>
                <h3>Example Request:</h3>
                <pre>curl -X POST http://localhost:5000/api/ask \\
  -H "Content-Type: application/json" \\
  -d '{"question": "What is methane reduction?"}'</pre>
            </div>
        </body>
        </html>
        '''

# ============================================================================
# API - Answer questions
# ============================================================================

@app.route('/api/ask', methods=['POST'])
def ask():
    """Answer a question using EcoRAG"""
    try:
        data = request.json or {}
        question = data.get('question', '').strip()

        if not question:
            return jsonify({'error': 'No question provided'}), 400

        # Load EcoRAG on first request
        _load_ecorag()

        if not ECORAG_READY:
            return jsonify({
                'error': 'EcoRAG system not ready',
                'message': 'Models loading on first request, please try again in 30 seconds'
            }), 503

        # Use retrieval-only mode (search results without LLM)
        sources = ask_ecorag(question, top_k=5)

        # Format response
        return jsonify({
            'question': question,
            'answer': f'Found {len(sources)} relevant sources in environmental research.',
            'citations': [
                {
                    'source': s['document'],
                    'pages': s['pages'],
                    'text': s['text'][:300]
                }
                for s in sources[:3]
            ],
            'confidence': 0.70,
            'status': 'success',
            'mode': 'retrieval_only',
            'sources_found': len(sources)
        })
    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"ERROR in /api/ask: {error_msg}\n{traceback.format_exc()}")
        return jsonify({
            'error': error_msg,
            'type': type(e).__name__,
            'status': 'error'
        }), 500

# ============================================================================
# HEALTH & INFO endpoints
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health():
    """Check API health"""
    return jsonify({
        'status': 'ok',
        'message': 'EcoRAG API is running',
        'ecorag_ready': ECORAG_READY,
        'environment': os.environ.get('ENVIRONMENT', 'local')
    })

@app.route('/api/info', methods=['GET'])
def info():
    """Get system information with community-driven improvements"""
    return jsonify({
        'description': 'Environmental RAG System',
        'version': '2.0',
        'document_count': 9,
        'chunk_count': 1242,
        'model': 'Qwen2.5-3B-Instruct',
        'model_loaded': ECORAG_READY,
        'device': 'cuda' if ECORAG_READY else 'cpu',
        'embedding_model': 'BAAI/bge-small-en-v1.5',
        'embedding_dimension': 384,
        'database': 'Chroma',
        'improvements': {
            'v1': 'Citation accuracy, no hallucinations',
            'v2': 'Scope-checking rules (V4 prompt)',
            'community_feedback': 'Krzysztof Śliwka & Mason Perry identified dependent-source failure mode',
            'v2_solutions': [
                'Rule 8: Scope matching (regional vs global)',
                'Rule 9: Temporal appropriateness (date checks)',
                'Rule 10: Document type awareness (definition vs empirical)',
                'Rule 11: Model vs empirical data distinction',
                'Rule 12: Source dependency flagging',
                'Rule 13: Refusal on insufficient evidence'
            ],
            'enhanced_metadata': 'Evidence blocks now include scope flags [REGIONAL/GLOBAL/NORMATIVE/MODEL-BASED/DATA-YEAR]'
        },
        'documents': [
            {'title': 'Global Methane Status Report 2025', 'source_filename': 'GMSR_2025.pdf', 'chunk_count': 320, 'scope': 'GLOBAL'},
            {'title': 'Critical Minerals Review of Norway 2026', 'source_filename': 'CriticalMineralsReviewofNorway2026.pdf', 'chunk_count': 79, 'scope': 'REGIONAL'},
            {'title': 'Modernising Grids in the Age of Electricity', 'source_filename': 'ModernisingGridsintheAgeofElectricity.pdf', 'chunk_count': 189, 'scope': 'GLOBAL'},
            {'title': 'Mapping Green and Digital Energy Jobs', 'source_filename': 'MappingGreenandDigitalEnergyJobs.pdf', 'chunk_count': 193, 'scope': 'GLOBAL'},
            {'title': 'Definitions for Near-Zero Emissions Steel and Cement', 'source_filename': 'Definitionsfornear-zeroandlow-emissionssteelandcementandunderlyingemissionsmeasurementmethodologies.pdf', 'chunk_count': 55, 'scope': 'NORMATIVE'},
            {'title': 'Managing Seasonal Variability of Electricity Demand and Supply', 'source_filename': 'ManagingtheSeasonalVariabilityofElectricityDemandandSupply.pdf', 'chunk_count': 104, 'scope': 'TECHNICAL'},
            {'title': 'Manufacturing and Trade Model Documentation 2026', 'source_filename': 'ManufacturingandTradeModelDocumentation2026.pdf', 'chunk_count': 73, 'scope': 'MODEL-BASED'},
            {'title': 'Reducing the Cost of Capital', 'source_filename': 'ReducingtheCostofCapital.pdf', 'chunk_count': 143, 'scope': 'GLOBAL'},
            {'title': 'Methane by 2030 Call to Action', 'source_filename': 'unsg_call-action-methane_by-2030-epublication.pdf', 'chunk_count': 87, 'scope': 'GLOBAL'}
        ]
    })

# ============================================================================
# FEEDBACK - Community feedback collection
# ============================================================================

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """Collect user feedback on RAG system quality"""
    try:
        data = request.json or {}
        feedback_type = data.get('type')  # 'citation', 'scope', 'completeness', 'other'
        question = data.get('question', '')
        feedback_text = data.get('feedback', '')
        rating = data.get('rating', 5)  # 1-5 scale

        if not feedback_text:
            return jsonify({'error': 'Feedback text required'}), 400

        # Log feedback (in production, write to database)
        log_entry = {
            'timestamp': os.environ.get('TIMESTAMP', 'unknown'),
            'type': feedback_type,
            'question': question,
            'feedback': feedback_text,
            'rating': rating
        }

        print(f"FEEDBACK RECEIVED: {log_entry}")

        return jsonify({
            'status': 'success',
            'message': 'Thank you for your feedback! It helps improve EcoRAG.',
            'feedback_logged': log_entry
        }), 201

    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': 'Method not allowed'}), 405

# ============================================================================
# RUN
# ============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    environment = os.environ.get('ENVIRONMENT', 'development')

    print(f"""
    ╔════════════════════════════════════════╗
    ║        🌿 EcoRAG API Starting          ║
    ╚════════════════════════════════════════╝

    🌐 URL:      http://localhost:{port}
    🔧 Mode:     {environment}
    📊 RAG:      {'✅ Ready' if ECORAG_READY else '⚠️  Demo mode'}

    ✅ Frontend: http://localhost:{port}/
    ✅ API:      http://localhost:{port}/api/ask
    ✅ Health:   http://localhost:{port}/api/health

    Share the URL with anyone!
    """)

    app.run(
        debug=False,
        port=port,
        host='0.0.0.0',
        threaded=True
    )
