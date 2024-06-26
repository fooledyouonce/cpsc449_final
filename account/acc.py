import bcrypt
import jwt
import secrets
import redis

from celery import Celery
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, current_app
from flask_mysqldb import MySQL




# initialize Flask app
app = Flask(__name__)

# generate a random secret key with 32 bytes (256 bits)
app.secret_key = secrets.token_hex(32)

# initialize an empty set to store revoked tokens (blacklist)
revoked_tokens = set()

# Redis
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)
app.config['REDIS_CLIENT'] = redis_client

# Celery configuration
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['result_backend'] = 'redis://localhost:6379/0'

# Initialize Celery
celery1 = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery1.conf.task_routes = {'acc.*':{'queue':'a'}}
celery1.conf.update(app.config)




# MySQL configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1234'
app.config['MYSQL_DB'] = 'auth'

# Initialize MySQL
mysql = MySQL(app)

# Create Users table if not exists
with app.app_context():
    cur = mysql.connection.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL
    )
    """)
    mysql.connection.commit()






# Celery task for user registration
@celery1.task
def register_user_async(username, password):
    
    if not username and password:
        return {"error": "Username and password are required!"}, 400

    #with app.app_context():
    try:
        # hash the password
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        with app.app_context():

        # insert user information into the database
            cursor = mysql.connection.cursor()
            insert_query = "INSERT INTO Users (username, password_hash) VALUES (%s, %s)"
            cursor.execute(insert_query, (username, hashed_password))
            mysql.connection.commit()
            cursor.close()

        return {"message": "User registered successfully!"}, 201
    except Exception as err:
        return {"error": f"Failed to register user: {err}"}, 500


# endpoint for user registration
@app.route("/account/register", methods=["POST"])
def register_user():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    # send the task to Celery to execute asynchronously
    task = register_user_async.delay(username, password)
    result, status_code = task.get()  # retrieve the result and status code of the task

    # return the result with the appropriate status code
    return jsonify(result), status_code


# Celery task for user login
@celery1.task
def login_user_async(username, password):
    if not username and password:
        return {"error": "Username and password are required!"}, 400

    try:
        with app.app_context():
            
            # fetch user information from the database
            cursor = mysql.connection.cursor()
            query = "SELECT * FROM Users WHERE username = %s"
            cursor.execute(query, (username,))
            user = cursor.fetchone()
            cursor.close()

        if not user:
            return {"error": "Invalid username or password!"}, 401

        # verify password
        stored_password = user[2]  # assuming password_hash is stored at index 2
        if not bcrypt.checkpw(
            password.encode("utf-8"), stored_password.encode("utf-8")
        ):
            return {"error": "Invalid password or password!"}, 401

        # generate JWT token
        token_payload = {
            "user_id": user[0],  # assuming user_id is stored at index 0
            "exp": datetime.utcnow() + timedelta(hours=1),  # token expires in 1 hour
        }
        token = jwt.encode(token_payload, app.secret_key, algorithm="HS256")

         # Store the token in Redis
        redis_client.set(token, user[0], ex=3600)  # Expires in 1 hour

        return {"token": token}, 200
    except Exception as err:
        return {"error": f"Failed to login. Error {err}."}, 500


# endpoint for user login
@app.route("/account/login", methods=["POST"])
def login_user():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    # send the task to Celery to execute asynchronously
    task = login_user_async.delay(username, password)
    result, status_code = task.get()  # retrieve the result and status code of the task

    # return the result with the appropriate status code
    return jsonify(result), status_code


# Celery task for user logout
@celery1.task
def logout_user_async(token):
    try:
        # Cannot log out without login first
        if not redis_client.exists(token):
            return {'error': "Token not found. Must login first."}, 404
        
        # decode the JWT token to extract the payload
        payload = jwt.decode(token, app.secret_key, algorithms=["HS256"])

        # if 'jti' claim is present, add it to the revoked tokens set
        if "jti" in payload:
            revoked_tokens.add(payload["jti"])
        
        #print(token)
        redis_client.delete(token)

        return {"message": "User logged out successfully!"}, 200
    except jwt.ExpiredSignatureError:
        return {"error": "Token has expired."}, 401
    except jwt.InvalidTokenError:
        return {"error": "Invalid token."}, 401
    except Exception as err:
        return {"error": f"Failed to logout. Error {err}."}, 500


# endpoint for user logout
@app.route("/account/logout", methods=["POST"])
def logout_user():
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return {"error": "Missing Authorization header"}, 401

    token = auth_header.split(" ")[1]
    
    # send the task to Celery to execute asynchronously
    task = logout_user_async.delay(token)
    result, status_code = task.get()  # retrieve the result and status code of the task

    # return the result with the appropriate status code
    return jsonify(result), status_code



if __name__ == "__main__":
    app.run(debug=True)