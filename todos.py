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
db = mysql.connector.connect(
    host="localhost", user="root", password="1234", database="todo"
)

# Celery task for creating a task
@celery.task
def create_task_async(title, description, due_date):
    if not title or not description or not due_date:
        return {"error": "Missing required fields!"}, 400

    try:
        cursor = db.cursor()
        insert_query = (
            "INSERT INTO Tasks (title, description, due_date) VALUES (%s, %s, %s)"
        )
        cursor.execute(insert_query, (title, description, due_date))
        db.commit()
        cursor.close()

        return {"message": "Task created successfully!"}, 201
    except Exception as err:
        return {"error": f"Failed to create task. Error {err}."}, 500


# endpoint for creating a task
@app.route("/todos", methods=["POST"])
def create_task():
    data = request.json
    title = data.get("title")
    description = data.get("description")
    due_date = data.get("due_date")

    # send the task to Celery to execute asynchronously
    task = create_task_async.delay(title, description, due_date)
    result, status_code = task.get()  # retrieve the result and status code of the task

    # return the result with the appropriate status code
    return jsonify(result), status_code


# Celery task for retrieving tasks
@celery.task
def get_tasks_async():
    try:
        cursor = db.cursor()
        query = "SELECT * FROM Tasks"
        cursor.execute(query)
        tasks = cursor.fetchall()
        cursor.close()

        if not tasks:
            return {"error": "Empty table, no tasks found."}, 200

        return {"tasks": tasks, "message": "Tasks retrieved successfully!"}, 200
    except Exception as err:
        return {"error": f"Failed to retrieve tasks. Error {err}."}, 500


# endpoint for retrieving tasks
@app.route("/todos", methods=["GET"])
def get_tasks():
    # send the task to Celery to execute asynchronously
    task = get_tasks_async.delay()
    result, status_code = task.get()  # retrieve the result and status code of the task

    # return the result with the appropriate status code
    return jsonify(result), status_code


# Celery task for updating a task
@celery.task
def update_task_async(task_id, title, description, due_date, completed):
    try:
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

        update_query = update_query.rstrip(", ")  # remove trailing comma
        update_query += " WHERE task_id = %s"
        update_values.append(task_id)
        cursor.execute(update_query, update_values)

        if cursor.rowcount == 0:
            return {"error": f"Task not found with an ID of {task_id}."}, 404

        db.commit()
        cursor.close()

        return {"message": "Task updated successfully!"}, 200
    except Exception as err:
        return {"error": f"Failed to update task. Error {err}."}, 500


# endpoint for updating a task
@app.route("/todos/<int:task_id>", methods=["PATCH"])
def update_task(task_id):
    data = request.json
    title = data.get("title")
    description = data.get("description")
    due_date = data.get("due_date")
    completed = data.get("completed")

    # send the task to Celery to execute asynchronously
    task = update_task_async.delay(task_id, title, description, due_date, completed)
    result, status_code = task.get()  # retrieve the result and status code of the task

    # return the result with the appropriate status code
    return jsonify(result), status_code


# Celery task for deleting a task
@celery.task
def delete_task_async(task_id):
    try:
        cursor = db.cursor()
        delete_query = "DELETE FROM Tasks WHERE task_id = %s"
        cursor.execute(delete_query, (task_id,))

        if cursor.rowcount == 0:
            return {"error": f"Task not found with an ID of {task_id}."}, 404

        db.commit()
        cursor.close()

        return {"message": "Task deleted successfully!"}, 200
    except Exception as err:
        return {"error": f"Failed to delete task. Error {err}."}, 500


# endpoint for deleting a task
@app.route("/todos/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    # send the task to Celery to execute asynchronously
    task = delete_task_async.delay(task_id)
    result, status_code = task.get()  # retrieve the result and status code of the task

    # return the result with the appropriate status code
    return jsonify(result), status_code


if __name__ == "__main__":
    app.run(debug=True)