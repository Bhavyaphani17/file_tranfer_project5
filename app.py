from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for, flash
import os
from werkzeug.utils import secure_filename
import mysql.connector
from mysql.connector import Error
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Replace with a secure key in production

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'zip', 'rar'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB max upload size

# Initialize Bcrypt
bcrypt = Bcrypt(app)

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'file_transfer_project'
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_database_and_table():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password=''
        )
        cursor = connection.cursor()
        
        # Create database if not exists
        cursor.execute("CREATE DATABASE IF NOT EXISTS file_transfer_project")
        cursor.execute("USE file_transfer_project")
        
        # Create users table if not exists with name column
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) NOT NULL UNIQUE,
                name VARCHAR(255) NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create file table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file (
                id INT AUTO_INCREMENT PRIMARY KEY,
                receiver_id VARCHAR(255) NOT NULL,
                sender_id VARCHAR(255) NOT NULL,
                filename VARCHAR(255) NOT NULL,
                filepath VARCHAR(255) NOT NULL,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert test users with usernames, names, and hashed passwords
        test_users = [
            ('alice', 'Alice Johnson', 'password123'),
            ('amy', 'Amy Smith', 'pass111'),
            ('andrew', 'Andrew Brown', 'pass112'),
            ('anna', 'Anna Davis', 'pass113'),
            ('aaron', 'Aaron Wilson', 'pass114'),
            ('bob', 'Bob Miller', 'password456'),
            ('ben', 'Ben Taylor', 'pass123'),
            ('bella', 'Bella Anderson', 'pass456'),
            ('brian', 'Brian Harris', 'pass789'),
            ('beth', 'Beth Clark', 'pass101'),
            ('bradley', 'Bradley Lewis', 'pass202'),
            ('charlie', 'Charlie Moore', 'password789'),
            ('chloe', 'Chloe Walker', 'pass115'),
            ('chris', 'Chris Evans', 'pass116'),
            ('claire', 'Claire White', 'pass117'),
            ('cathy', 'Cathy Lee', 'pass118'),
            ('david', 'David King', 'pass303'),
            ('diana', 'Diana Scott', 'pass404'),
            ('daniel', 'Daniel Green', 'pass505'),
            ('daisy', 'Daisy Adams', 'pass119'),
            ('derek', 'Derek Young', 'pass120'),
            ('emma', 'Emma Hall', 'pass606'),
            ('ethan', 'Ethan Wright', 'pass707'),
            ('ella', 'Ella Turner', 'pass121'),
            ('evan', 'Evan Mitchell', 'pass122'),
            ('erin', 'Erin Baker', 'pass123'),
            ('frank', 'Frank Carter', 'pass124'),
            ('fiona', 'Fiona Parker', 'pass125'),
            ('fred', 'Fred Collins', 'pass126'),
            ('faith', 'Faith Brooks', 'pass127'),
            ('felix', 'Felix Morgan', 'pass128'),
            ('grace', 'Grace Phillips', 'pass129'),
            ('george', 'George Edwards', 'pass130'),
            ('gina', 'Gina Campbell', 'pass131'),
            ('greg', 'Greg Stewart', 'pass132'),
            ('gwen', 'Gwen Kelly', 'pass133'),
            ('bhavyaphani17', 'Bhavya Phani Sri', 'pass134')
        ]
        
        for username, name, password in test_users:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if not cursor.fetchone():
                hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
                cursor.execute(
                    "INSERT INTO users (username, name, password) VALUES (%s, %s, %s)",
                    (username, name, hashed_password)
                )
                print(f"Inserted user: {username}, {name}, {hashed_password}")
        
        connection.commit()
    except Error as e:
        print(f"Error: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# Middleware to check if user is logged in
def login_required(f):
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('upload'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('upload'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('login.html')
        
        try:
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("SELECT id, username, password FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            
            if not user or not bcrypt.check_password_hash(user['password'], password):
                flash('Invalid username or password.', 'error')
                return render_template('login.html')
            
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Login successful!', 'success')
            return redirect(url_for('upload'))
            
        except Error as e:
            flash(f'Database error: {str(e)}', 'error')
            return render_template('login.html')
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        return upload_file()
    return render_template('upload.html')

@app.route('/download')
@login_required
def download():
    return render_template('download.html')

@app.route('/view_sent')
@login_required
def view_sent():
    return render_template('view_sent.html')

@app.route('/get_current_user', methods=['GET'])
@login_required
def get_current_user():
    return jsonify({'username': session['username']}), 200

@app.route('/get_users', methods=['GET'])
@login_required
def get_users():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({'users': []}), 200
    
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        
        # Search by username OR name (case-insensitive), excluding the current user
        cursor.execute(
            """
            SELECT username, name 
            FROM users 
            WHERE (LOWER(username) LIKE %s OR LOWER(name) LIKE %s) 
            AND username != %s 
            LIMIT 5
            """,
            (f'{query.lower()}%', f'{query.lower()}%', session['username'])
        )
        users = cursor.fetchall()
        
        # Format the response to include both username and name
        users_list = [{'username': user['username'], 'name': user['name']} for user in users]
        
        return jsonify({'users': users_list}), 200
    
    except Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/get_files', methods=['POST'])
@login_required
def get_files():
    # Use the logged-in user's username as the receiver_id
    receiver_id = session['username']
    
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        
        # Case-insensitive match for receiver_id
        cursor.execute(
            """
            SELECT id, filename, upload_time 
            FROM file 
            WHERE LOWER(receiver_id) = %s
            """,
            (receiver_id.lower(),)
        )
        files = cursor.fetchall()
        
        return jsonify({'files': files}), 200
    
    except Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/get_sent_files', methods=['POST'])
@login_required
def get_sent_files():
    sender_id = session['username']  # Use the logged-in user's username as sender_id
    
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        
        # Case-insensitive match for sender_id and join with users to get receiver's name
        cursor.execute(
            """
            SELECT f.id, f.receiver_id, f.filename, f.upload_time, u.name AS receiver_name
            FROM file f
            LEFT JOIN users u ON LOWER(u.username) = LOWER(f.receiver_id)
            WHERE LOWER(f.sender_id) = %s
            """,
            (sender_id.lower(),)
        )
        files = cursor.fetchall()
        
        print(f"Fetched files for sender_id '{sender_id}': {files}")  # Debugging output
        
        return jsonify({'files': files}), 200
    
    except Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/download_file/<int:file_id>')
@login_required
def download_file(file_id):
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("SELECT filename, filepath FROM file WHERE id = %s", (file_id,))
        file = cursor.fetchone()
        
        if not file:
            return jsonify({'error': 'File not found in database'}), 404
        
        # Check if the file exists on the server
        if not os.path.exists(file['filepath']):
            return jsonify({'error': f'File not found on server: {file["filepath"]}'}), 404
        
        return send_file(file['filepath'], download_name=file['filename'], as_attachment=True)
    
    except Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/view_file/<int:file_id>')
@login_required
def view_file(file_id):
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("SELECT filename, filepath FROM file WHERE id = %s", (file_id,))
        file = cursor.fetchone()
        
        if not file:
            return jsonify({'error': 'File not found in database'}), 404
        
        # Check if the file exists on the server
        if not os.path.exists(file['filepath']):
            return jsonify({'error': f'File not found on server: {file["filepath"]}'}), 404
        
        return send_file(file['filepath'], download_name=file['filename'], as_attachment=False)
    
    except Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'files' not in request.files or 'receiver_ids' not in request.form:
        return jsonify({'error': 'No files or receiver IDs provided'}), 400
    
    receiver_ids_input = request.form['receiver_ids'].strip()
    receiver_ids = [rid.strip() for rid in receiver_ids_input.split(',') if rid.strip()]
    sender_id = session['username']  # Use the logged-in user's username as sender_id
    files = request.files.getlist('files')
    
    if not receiver_ids:
        return jsonify({'error': 'At least one Receiver ID is required'}), 400
    
    # Ensure the uploads folder exists
    try:
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    except Exception as e:
        return jsonify({'error': f'Failed to create uploads directory: {str(e)}'}), 500
    
    uploaded_files = []
    
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                try:
                    file.save(filepath)
                except Exception as e:
                    return jsonify({'error': f'Failed to save file: {str(e)}'}), 500
                
                # Insert a separate database entry for each receiver_id
                for receiver_id in receiver_ids:
                    cursor.execute(
                        "INSERT INTO file (receiver_id, sender_id, filename, filepath) VALUES (%s, %s, %s, %s)",
                        (receiver_id, sender_id, filename, filepath)
                    )
                uploaded_files.append(filename)
        
        connection.commit()
        return jsonify({'message': f'{len(uploaded_files)} file(s) uploaded successfully to {len(receiver_ids)} receiver(s)'}), 200
    
    except Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == '__main__':
    create_database_and_table()
    app.run(debug=True)
