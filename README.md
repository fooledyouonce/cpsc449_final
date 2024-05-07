# WIP



Please Install Required Packages:

Celery (asynchronous processing)
Redis (message broker)
Nginx (API Gateway)
MySQL (database)
Flask (web application)
Eventlet (using Celery with Windows)
Bycrypt, JWT, Secrets (Security/Authorization)
Postman (testing)



Run the following services:

Redis server
Nginx
MySQL database server
Account server (acc.py)
Celery worker 1 ('celery -A acc.celery1 worker -Q a -l info -P eventlet')
Application server (todo.py)
Celery worker 2 ('celery -A todo.celery2 worker -Q b -l info -P eventlet')



Usage:
Login is required in order to use application APIs.
An authorization token will be returned when logged in.
In Postman, in the Authorization tab, choose Bearer Token and fill in the Key form with the token provided whenever a request is made to the Application APIs.

