from flask import Flask, jsonify
from dotenv import load_dotenv
from email_assistant.api.routes.generate_memo import memo_bp

# Load environment variables
load_dotenv()

app = Flask(__name__)

app.register_blueprint(memo_bp)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)