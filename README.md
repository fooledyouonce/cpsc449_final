# WIP



**Please Install Required Packages:**

Celery (asynchronous processing)<br>
Redis (message broker)<br>
Nginx (API Gateway)<br>
MySQL (database)<br>
Flask (web application)<br>
Eventlet (using Celery with Windows)<br>
Bycrypt, JWT, Secrets (Security/Authorization)<br>
Postman (testing)<br>
<br>


**Run the following services:**

Redis server<br>
Nginx server in same folder as application<br>
MySQL database servers, 1 for account, 1 for application<br>
Set the correct database configuration in both acc.py and todo.py files<br>
Account server (acc.py)<br>
Celery worker 1 ('celery -A acc.celery1 worker -Q a -l info -P eventlet')<br>
Application server (todo.py)<br>
Celery worker 2 ('celery -A todo.celery2 worker -Q b -l info -P eventlet')<br>
<br>


**Usage:**

Use 127.0.0.1:80 for all request.<br>
Register a user.<br>
Login using the same credential in order to use application APIs.<br>
An authorization token will be returned when logged in.<br>
In Postman, in the Authorization tab, choose Bearer Token and fill in the Key form with the token provided whenever making a request to the Application APIs or when logging out.<br>
<br>


*Note*
All testings and commands were performed in Windows 10<br>

