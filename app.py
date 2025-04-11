from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import mysql.connector
import os
from dotenv import load_dotenv
from flask_cors import CORS
import re
import pytube
from youtube_transcript_api import YouTubeTranscriptApi
from transformers import pipeline
import pdfplumber
import docx
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, redirect, url_for, session, render_template
from text_summarizer import TextSummarizer
from youtube_summarizer import YouTubeVideoSummarizer

# Load environment variables
load_dotenv()

# Create a single Flask app instance
app = Flask(__name__)
app.secret_key = "your_secret_key"
# CORS Configuration
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})

# Initialize extensions
bcrypt = Bcrypt(app)
app.config['JWT_SECRET_KEY'] = os.getenv("JWT_SECRET_KEY", "your_secret_key")
jwt = JWTManager(app)

# App Configurations
app.config['UPLOAD_FOLDER'] = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'docx'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database Connection
def get_db_connection():
    return mysql.connector.connect(
        host="127.0.0.1", 
        port=3306,
        user="root", 
        password="root", 
        database="concisely"
    )

# Helper Functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_file(file_path, file_type):
    text = ""
    try:
        if file_type == 'pdf':
            with pdfplumber.open(file_path) as pdf:
                text = "\n".join([page.extract_text() or "" for page in pdf.pages])
        elif file_type == 'docx':
            doc = docx.Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
        elif file_type == 'txt':
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        return text
    except Exception as e:
        print(f"Error extracting text: {e}")
        return ""

# User Routes
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({"error": "Missing fields"}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                       (username, email, hashed_password))
        conn.commit()
        return jsonify({"message": "User registered successfully!"}), 201
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 400
    finally:
        cursor.close()
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user and bcrypt.check_password_hash(user['password_hash'], password):
            access_token = create_access_token(identity=user['user_id'])
            return jsonify({
                "message": "Login successful!", 
                "token": access_token,
                "user_id": user['user_id']
            })
        else:
            return jsonify({"error": "Invalid credentials"}), 401
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/summarize', methods=['POST'])
def summarize():  # Removed @jwt_required()
    # No need to fetch user_id from JWT
    # user_id = get_jwt_identity()  ❌ Remove this line

    if request.is_json:
        data = request.json
        text = data.get("text", "").strip()
        
        if text:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()

                # Insert file record without user_id
                cursor.execute("""
                    INSERT INTO files 
                    (user_id,file_name, file_type, file_path, file_status) 
                    VALUES (%s, %s, %s, %s,%s)
                """, (
                    None,
                    'text_input', 
                    'text', 
                    text[:255],  # truncate for file_path 
                    'completed'
                ))
                conn.commit()
                file_id = cursor.lastrowid

                # Generate summary
                summarizer = TextSummarizer()
                summary = summarizer.generate_summary(text, ratio=0.3, min_sentences=2)

                # Save summary
                cursor.execute("""
                    INSERT INTO summaries 
                    (file_id, summary_text, summary_type) 
                    VALUES (%s, %s, %s)
                """, (file_id, summary, 'text'))
                conn.commit()

                return jsonify({
                    "file_id": file_id,
                    "original_text": text,
                    "summary": summary
                })
            except mysql.connector.Error as db_err:
                return jsonify({"error": f"Database error: {str(db_err)}"}), 500
            finally:
                cursor.close()
                conn.close()

    return jsonify({"error": "Invalid request. Provide text."}), 400

@app.route('/summarize_youtube', methods=['POST'])
def summarize_video():
    data = request.get_json()
    youtube_url = data.get("youtube_url")

    if not youtube_url:
        return jsonify({"error": "YouTube URL is required"}), 400

    summarizer = YouTubeVideoSummarizer()
    result = summarizer.process_video(youtube_url)

    if isinstance(result, str):  
        result = {"summary": result}
    elif not isinstance(result, dict):  
        return jsonify({"error": "Invalid response format from summarizer"}), 500

    # Logging to both terminal and potential log file
    app.logger.info(f"Summarization Result: {result}")

    return jsonify(result)

@app.route('/save_summary', methods=['POST'])
@jwt_required()
def save_summary():
    """Save a generated summary and trigger download"""
    user_id = get_jwt_identity()
    data = request.json

    # Validate input
    if not data or not data.get('summary') or not data.get('source'):
        return jsonify({"error": "Invalid summary data"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Generate a unique filename
        import uuid
        unique_filename = f"{uuid.uuid4()}_{data.get('source')[:50]}"

        # Insert file record
        cursor.execute("""
            INSERT INTO files 
            (user_id, file_name, file_type, file_path, file_status) 
            VALUES (%s, %s, %s, %s, %s)
        """, (
            user_id, 
            unique_filename,
            data.get('type', 'video'),
            data.get('source', ''),
            'completed'
        ))
        conn.commit()
        file_id = cursor.lastrowid

        # Save summary
        cursor.execute("""
            INSERT INTO summaries 
            (file_id, summary_text, summary_type) 
            VALUES (%s, %s, %s)
        """, (
            file_id, 
            data['summary'], 
            data.get('type', 'video')
        ))
        conn.commit()

        # Log action
        cursor.execute("""
            INSERT INTO login 
            (user_id, file_id, action) 
            VALUES (%s, %s, %s)
        """, (user_id, file_id, 'Summary Saved'))
        conn.commit()

        return jsonify({
            "message": "Summary saved successfully",
            "file_id": file_id,
            "summary": data['summary']
        })

    except mysql.connector.Error as db_err:
        return jsonify({"error": f"Database error: {str(db_err)}"}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/history', methods=['GET'])
@jwt_required()
def get_user_summaries():
    """Retrieve all summaries for the logged-in user"""
    user_id = get_jwt_identity()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Query to get all summaries with file details
        query = """
        SELECT 
            f.file_id, 
            f.file_name, 
            f.file_path, 
            f.file_type, 
            s.summary_text, 
            f.upload_timestamp
        FROM files f
        JOIN summaries s ON f.file_id = s.file_id
        WHERE f.user_id = %s
        ORDER BY f.upload_timestamp DESC
        """
        
        cursor.execute(query, (user_id,))
        summaries = cursor.fetchall()
        
        return jsonify(summaries)

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/download_summary/<int:file_id>', methods=['GET'])
@jwt_required()
def download_summary(file_id):
    """Download a saved summary"""
    user_id = get_jwt_identity()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Fetch summary, ensuring user ownership
        cursor.execute("""
            SELECT 
                f.file_name, 
                s.summary_text, 
                f.file_type
            FROM files f
            JOIN summaries s ON f.file_id = s.file_id
            WHERE f.file_id = %s AND f.user_id = %s
        """, (file_id, user_id))
        
        summary = cursor.fetchone()
        
        if not summary:
            return jsonify({"error": "Summary not found or access denied"}), 404

        # Prepare file for download
        from flask import send_file
        from io import BytesIO

        # Create a text file with the summary
        summary_buffer = BytesIO()
        summary_buffer.write(summary['summary_text'].encode('utf-8'))
        summary_buffer.seek(0)

        return send_file(
            summary_buffer, 
            mimetype='text/plain',
            as_attachment=True,
            download_name=f"{summary['file_name']}_summary.txt"
        )

    except Exception as err:
        return jsonify({"error": str(err)}), 500
    finally:
        cursor.close()
        conn.close()
# Health check route
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy", 
        "message": "API is up and running"
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)