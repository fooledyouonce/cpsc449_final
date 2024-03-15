from flask import Flask, request, jsonify
import mysql.connector

app = Flask(__name__)

# MySQL configuration
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="todo"
)

@app.route('/todolist', methods=['POST'])
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

        return jsonify({"message": "To do item added!"}), 201
    else:
        return jsonify({'error': 'Missing required fields!'}), 400

@app.route('/todolist', methods=['GET'])
def get_tasks():
    cursor = db.cursor()
    query = "SELECT * FROM Tasks"
    cursor.execute(query)
    tasks = cursor.fetchall()
    cursor.close()

    return jsonify(tasks)

@app.route('/todolist/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    data = request.json
    title = data.get('title')
    description = data.get('description')
    due_date = data.get('due_date')
    completed = data.get('completed')

    if title or description or due_date or completed:
        cursor = db.cursor()
        update_query = "UPDATE Tasks SET title = %s, description = %s, due_date = %s, completed = %s WHERE task_id = %s"
        cursor.execute(update_query, (title, description, due_date, completed, task_id))
        db.commit()
        cursor.close()

        return jsonify({"message": "To do item updated!"})
    else:
        return jsonify({"error": "No update performed, fill in required fields."})

@app.route('/todolist/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    cursor = db.cursor()
    delete_query = "DELETE FROM Tasks WHERE task_id = %s"
    cursor.execute(delete_query, (task_id,))
    db.commit()
    cursor.close()

    return jsonify({"message": "Task deleted successfully"})

if __name__ == "__main__":
    app.run(debug=True)
