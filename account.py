import bcrypt
import jwt
import mysql.connector
import secrets

from celery import Celery
from datetime import datetime, timedelta
from flask import Flask, request, jsonify

# generate a random secret key with 32 bytes (256 bits)
secret_key = secrets.token_hex(32)
# print(secret_key)

# initialize an empty set to store revoked tokens (blacklist)
revoked_tokens = set()

# initialize Flask app
app = Flask(__name__)

# configuration for Celery
app.config["CELERY_BROKER_URL"] = "redis://localhost:6379/0"
app.config["CELERY_RESULT_BACKEND"] = "redis://localhost:6379/0"

celery = Celery(app.name, broker=app.config["CELERY_BROKER_URL"])
celery.conf.update(app.config)


# MySQL connection

acc_db = mysql.connector.connect(
    host="localhost", user="root", password="1234", database="auth"
)


# Celery task for user registration
@celery.task
def register_user_async(username, password):
    if not username and password:
        return {"error": "Username and password are required!"}, 400

    try:
        # hash the password
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        # insert user information into the database
        cursor = acc_db.cursor()
        insert_query = "INSERT INTO Users (username, password_hash) VALUES (%s, %s)"
        cursor.execute(insert_query, (username, hashed_password))
        acc_db.commit()
        cursor.close()

        return {"message": "User registered successfully!"}, 201
    except Exception as err:
        return {"error": f"Failed to register user: {err}"}, 500


# endpoint for user registration
@app.route("/register", methods=["POST"])
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
@celery.task
def login_user_async(username, password):
    if not username and password:
        return {"error": "Username and password are required!"}, 400

    try:
        # fetch user information from the database
        cursor = acc_db.cursor()
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
        token = jwt.encode(token_payload, secret_key, algorithm="HS256")

        return {"token": token}, 200
    except Exception as err:
        return {"error": f"Failed to login. Error {err}."}, 500


# endpoint for user login
@app.route("/login", methods=["POST"])
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
@celery.task
def logout_user_async(token):
    try:
        # decode the JWT token to extract the payload
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])

        # if 'jti' claim is present, add it to the revoked tokens set
        if "jti" in payload:
            revoked_tokens.add(payload["jti"])

        return {"message": "User logged out successfully!"}, 200
    except jwt.ExpiredSignatureError:
        return {"error": "Token has expired."}, 401
    except jwt.InvalidTokenError:
        return {"error": "Invalid token."}, 401
    except Exception as err:
        return {"error": f"Failed to logout. Error {err}."}, 500


# endpoint for user logout
@app.route("/logout", methods=["POST"])
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