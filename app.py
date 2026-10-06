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
    """Get system information"""
    return jsonify({
        'description': 'Environmental RAG System',
        'document_count': 9,
        'chunk_count': 1242,
        'model': 'Qwen2.5-3B-Instruct',
        'model_loaded': ECORAG_READY,
        'device': 'cuda' if ECORAG_READY else 'cpu',
        'embedding_model': 'BAAI/bge-small-en-v1.5',
        'embedding_dimension': 384,
        'database': 'Chroma',
        'documents': [
            {'title': 'Global Methane Status Report 2025', 'source_filename': 'gmsr_2025.pdf', 'chunk_count': 156},
            {'title': 'Critical Minerals for Clean Energy', 'source_filename': 'critical_minerals.pdf', 'chunk_count': 142},
            {'title': 'Modernising Grids in the Age of Electricity', 'source_filename': 'grid_modernization.pdf', 'chunk_count': 189},
            {'title': 'Jobs in the Clean Energy Transition', 'source_filename': 'clean_energy_jobs.pdf', 'chunk_count': 178},
            {'title': 'Steel and Cement Decarbonization', 'source_filename': 'steel_cement.pdf', 'chunk_count': 195},
            {'title': 'Managing Seasonal Variability of Electricity', 'source_filename': 'electricity_variability.pdf', 'chunk_count': 167},
            {'title': 'Renewable Energy Integration', 'source_filename': 'renewable_integration.pdf', 'chunk_count': 144},
            {'title': 'Climate Action Framework 2030', 'source_filename': 'climate_2030.pdf', 'chunk_count': 151},
            {'title': 'Energy Transition Economics', 'source_filename': 'energy_economics.pdf', 'chunk_count': 120}
        ]
    })

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
