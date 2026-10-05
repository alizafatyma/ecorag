"""
EcoRAG API Backend - Connect Frontend to Real System
Run this to expose your RAG system as an API
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(__file__))

# Import your EcoRAG system
from ecorag_ask import ask_ecorag

app = Flask(__name__)
CORS(app)  # Allow frontend to call this API

@app.route('/api/ask', methods=['POST'])
def ask():
    """Answer a question using EcoRAG"""
    try:
        data = request.json
        question = data.get('question', '').strip()

        if not question:
            return jsonify({'error': 'No question provided'}), 400

        # Call your actual EcoRAG system
        result = ask_ecorag(question, debug=False)

        # Format response for frontend
        response = {
            'question': question,
            'answer': result['answer'],
            'citations': [
                {
                    'source': s.get('chunk_id', 'Unknown'),
                    'text': s.get('text', '')[:200]  # First 200 chars
                }
                for s in result['sources'][:3]  # Top 3 sources
            ],
            'confidence': 0.75  # You can calculate this from your system
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Check if API is running"""
    return jsonify({'status': 'ok', 'message': 'EcoRAG API is running'})

if __name__ == '__main__':
    print("Starting EcoRAG API...")
    print("Frontend should call: http://localhost:5000/api/ask")
    app.run(debug=False, port=5000, host='0.0.0.0')
