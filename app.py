from flask import Flask, request, jsonify  
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import mysql.connector
import os
from dotenv import load_dotenv
from flask_cors import CORS

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

bcrypt = Bcrypt(app)
app.config['JWT_SECRET_KEY'] = os.getenv("JWT_SECRET_KEY", "your_secret_key")
jwt = JWTManager(app)

# Database Connection Function
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "concisely"),
            auth_plugin='mysql_native_password'
        )
        return conn
    except mysql.connector.Error as err:
        print(f"❌ Database Connection Error: {err}")
        return None

# User Registration
@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username, email, password = data.get('username'), data.get('email'), data.get('password')
    
    if not username or not email or not password:
        return jsonify({"error": "Missing fields"}), 400
    
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                       (username, email, hashed_password))
        conn.commit()
        return jsonify({"message": "User registered successfully!"}), 201
    except mysql.connector.IntegrityError:
        return jsonify({"error": "Username or email already exists"}), 400
    finally:
        cursor.close()
        conn.close()

# User Login
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username, password = data.get('username'), data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user and bcrypt.check_password_hash(user['password_hash'], password):
        access_token = create_access_token(identity=user['user_id'])
        return jsonify({"message": "Login successful!", "token": access_token})
    return jsonify({"error": "Invalid credentials"}), 401

# Get User Profile
@app.route('/profile', methods=['GET'])
@jwt_required()
def profile():
    user_id = get_jwt_identity()
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT username, email FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    return jsonify(user) if user else jsonify({"error": "User not found"}), 404

# Save Text Summary
@app.route('/save-text-summary', methods=['POST'])
@jwt_required()
def save_text_summary():
    user_id = get_jwt_identity()
    data = request.get_json()
    summary = data.get('summary')
    
    if not summary:
        return jsonify({"error": "Summary is required"}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor()
    cursor.execute("INSERT INTO text_summaries (user_id, summary) VALUES (%s, %s)", (user_id, summary))
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({"message": "Text summary saved successfully!"}), 201

# Get Text Summary History
@app.route('/get-text-history', methods=['GET'])
@jwt_required()
def get_text_history():
    user_id = get_jwt_identity()
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, summary, created_at FROM text_summaries WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
    summaries = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify(summaries)

# Save Video Summary
@app.route('/save-video-summary', methods=['POST'])
@jwt_required()
def save_video_summary():
    user_id = get_jwt_identity()
    data = request.get_json()
    video_summary = data.get('video_summary')
    
    if not video_summary:
        return jsonify({"error": "Video summary is required"}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor()
    cursor.execute("INSERT INTO video_summaries (user_id, video_summary) VALUES (%s, %s)", (user_id, video_summary))
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({"message": "Video summary saved successfully!"}), 201

# Get Video Summary History
@app.route('/get-video-history', methods=['GET'])
@jwt_required()
def get_video_history():
    user_id = get_jwt_identity()
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, video_summary, created_at FROM video_summaries WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
    video_summaries = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify(video_summaries)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
