import redis
from celery import Celery
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
#import mysql.connector




# initialize Flask app
app = Flask(__name__)
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)



# Celery configuration
app.config["CELERY_BROKER_URL"] = "redis://localhost:6379/0"
app.config["CELERY_RESULT_BACKEND"] = "redis://localhost:6379/0"

celery = Celery(app.name, broker=app.config["CELERY_BROKER_URL"])
celery.conf.update(app.config)







# MySQL configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1234'
app.config['MYSQL_DB'] = 'todo'

# Initialize MySQL
mysql = MySQL(app)

# Create Tasks table if not exists
with app.app_context():
    cur = mysql.connection.cursor()
    cur.execute("""
        CREATE TABLE Tasks (
    task_id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    due_date DATE,
    completed BOOLEAN DEFAULT FALSE
    )
    """)
    mysql.connection.commit()
    
    
    
    
    
@app.before_request
def access_control():
    # Check if a valid session token or JWT is provided in the request headers
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Authorization token missing'}), 401

    # Query Redis to check if the token exists and is associated with a logged-in user
    if not redis_client.exists(token):
        return jsonify({'error': 'Invalid or expired token'}), 401

    # Token exists and is valid, proceed to handle the request
    # Add logic here to retrieve todos or perform other actions

    return jsonify({'message': 'Authorized to access todos'}), 200   
    
    

# Celery task for creating a task
@celery.task
def create_task_async(title, description, due_date):
    if not title or not description or not due_date:
        return {"error": "Missing required fields!"}, 400

    try:
        cursor = mysql.connection.cursor()
        insert_query = (
            "INSERT INTO Tasks (title, description, due_date) VALUES (%s, %s, %s)"
        )
        cursor.execute(insert_query, (title, description, due_date))
        mysql.connection.commit()
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
        cursor = mysql.connection.cursor()
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
        cursor = mysql.connection.cursor()
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

        mysql.connection.commit()
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
        cursor = mysql.connection.cursor()
        delete_query = "DELETE FROM Tasks WHERE task_id = %s"
        cursor.execute(delete_query, (task_id,))

        if cursor.rowcount == 0:
            return {"error": f"Task not found with an ID of {task_id}."}, 404

        mysql.connection.commit()
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