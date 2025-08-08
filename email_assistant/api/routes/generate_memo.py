from flask import Blueprint, request, jsonify, send_file
import os
import sys
from werkzeug.utils import secure_filename

# Add the project root to the Python path
# This file already has the project root in the path, so no changes are needed.

from core.pipeline import run_memo_pipeline

memo_bp = Blueprint('memo_bp', __name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@memo_bp.route('/generate-memo', methods=['POST'])
def generate_memo():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)

        try:
            result_path = run_memo_pipeline(file_path)
            if result_path:
                # Return the generated file for download
                return send_file(result_path, as_attachment=True, download_name=os.path.basename(result_path))
            else:
                return jsonify({'error': 'Failed to generate memo'}), 500
        except Exception as e:
            # It's good practice to log the exception
            print(f"Error generating memo: {e}")
            return jsonify({'error': str(e)}), 500
