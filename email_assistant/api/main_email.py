from flask import Flask, jsonify
from dotenv import load_dotenv
import sys
from pathlib import Path

# Add project root to the Python path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from email_assistant.api.routes.generate_memo import memo_bp
from email_assistant.api.routes.analyze_report import analyze_bp

# Load environment variables
load_dotenv()

app = Flask(__name__)

app.register_blueprint(memo_bp)
app.register_blueprint(analyze_bp)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)