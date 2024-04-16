import mysql.connector
import bcrypt
import secrets
import jwt

from flask import Flask, request, jsonify
from datetime import datetime, timedelta

# generate a random secret key with 32 bytes (256 bits)
secret_key = secrets.token_hex(32)
#print(secret_key)

# initialize an empty set to store revoked tokens (blacklist)
revoked_tokens = set()

app = Flask(__name__)

# MySQL connection
# MySQL connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="todo"
)


# endpoint for user registration
@app.route('/register', methods=['POST'])
def register_user():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required!'}), 400

    # hash the password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # insert user information into the database
    try:
        cursor = db.cursor()
        insert_query = "INSERT INTO Users (username, password_hash) VALUES (%s, %s)"
        cursor.execute(insert_query, (username, hashed_password))
        db.commit()
        cursor.close()
    except mysql.connector.Error as err:
        return jsonify({'error': f"Failed to register user: {err}"}), 500

    return jsonify({'message': 'User registered successfully!'}), 201


# endpoint for user login
@app.route('/login', methods=['POST'])
def login_user():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required!'}), 400

    # Fetch user information from the database
    try:
        cursor = db.cursor()
        query = "SELECT * FROM Users WHERE username = %s"
        cursor.execute(query, (username,))
        user = cursor.fetchone()
        cursor.close()
    except mysql.connector.Error as err:
        return jsonify({'error': f"Failed to fetch user information: {err}"}), 500

    if not user:
        return jsonify({'error': 'Invalid username or password!'}), 401

    # Verify password
    stored_password = user[2]  # Assuming password_hash is stored at index 2
    if not bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
        return jsonify({'error': 'Invalid username or password!'}), 401

    # Generate JWT token
    token_payload = {
        'user_id': user[0],  # Assuming user_id is stored at index 0
        'exp': datetime.utcnow() + timedelta(hours=1)  # Token expires in 1 hour
    }
    token = jwt.encode(token_payload, 'your_secret_key', algorithm='HS256')

    return jsonify({'token': token}), 200


# endpoint for user logout
@app.route('/logout', methods=['POST'])
def logout_user():
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'error': 'Missing Authorization header'}), 401

    token = auth_header.split(' ')[1]

    # decode the JWT token to extract the payload
    try:
        payload = jwt.decode(token, 'your_secret_key', algorithms=['HS256'])
    except jwt.DecodeError:
        return jsonify({'error': 'Invalid token'}), 401

    # add the token's unique identifier (e.g., jti) to the revoked tokens set (blacklist)
    revoked_tokens.add(payload['jti'])

    return jsonify({'message': 'User logged out successfully!'}), 200


@app.route('/todos', methods=['POST'])
def create_task():
    data = request.json
    title = data.get('title')
    description = data.get('description')
    due_date = data.get('due_date')

    if title and description and due_date:


        cursor = db.cursor()
        insert_query = "INSERT INTO Tasks (title, description, due_date) VALUES (%s, %s, %s)"
        cursor.execute(insert_query, (title, description, due_date))
        db.commit()
        cursor.close()

        return jsonify({"message": "Task created successfully"}), 201
        return jsonify({"message": "Task created successfully"}), 201
    else:
        return jsonify({'error': 'Missing required fields!'}), 400


@app.route('/todos', methods=['GET'])
def get_tasks():
    cursor = db.cursor()
    query = "SELECT * FROM Tasks"
    cursor.execute(query)
    tasks = cursor.fetchall()
    cursor.close()

    return jsonify(tasks)


@app.route('/todos/<int:task_id>', methods=['PATCH'])
def update_task(task_id):
    data = request.json
    title = data.get('title')
    description = data.get('description')
    due_date = data.get('due_date')
    completed = data.get('completed')

    if title or description or due_date or completed is not None:
        cursor = db.cursor()
        update_query = "UPDATE Tasks SET "
        update_values = []
        if title is not None:
            update_query += "title = %s, "
            update_values.append(title)
        if description is not None:
            update_query += "description = %s, "
            update_values.append(description)
        if due_date is not None:
            update_query += "due_date = %s, "
            update_values.append(due_date)
        if completed is not None:
            update_query += "completed = %s, "
            update_values.append(completed)
        update_query = update_query.rstrip(', ')  # remove trailing comma
        update_query += " WHERE task_id = %s"
        update_values.append(task_id)
        cursor.execute(update_query, update_values)
        if cursor.rowcount == 0:
            return jsonify({"error": "Task not found."}), 404
        db.commit()
        cursor.close()

        return jsonify({"message": "To do item updated!"})
    else:
        return jsonify({"error": "No update performed, fill in required fields."}), 400


@app.route('/todos/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    cursor = db.cursor()
    delete_query = "DELETE FROM Tasks WHERE task_id = %s"
    cursor.execute(delete_query, (task_id,))
    if cursor.rowcount == 0:
        return jsonify({"error": "Task not found."}), 404
    db.commit()
    cursor.close()

    return jsonify({"message": "Task deleted successfully"})


if __name__ == "__main__":
    app.run(debug=True)
