# To-Do Application

Alexis Vu

- Incorporated Celery along with Redis for enabling asynchronous task execution. Defined Celery tasks for essential functionalities including user registration, login, task management (creation, retrieval, updating, and deletion). 

Mike Thai

- Transform the application into a Microservices Architecture, namely: Creating monorepo, API gateway using Nginx, message broker using Redis for granting access with authorization key, modifying Celery configuration, separated account services and application services with their own databases.

Emily Crowl

- Created RESTful API endpoints for CRUD and user registration and login/logout. Created database and linked it to application. Helped support choosing scaling strategies and testing. 

## Required Packages

Please install the following packages:

- Celery (asynchronous processing)

- Redis (message broker)

- Nginx (API Gateway)

- MySQL (database)

- Flask (web application)

- Eventlet (using Celery with Windows)

- Bycrypt, JWT, Secrets (Security/Authorization)

- Postman (testing)

## Services to Run

- Redis server
  
- Nginx server in same folder as application
    - Repalce the files in the conf folder with the files attached
  
- MySQL database servers
    - Two servers: one for account, one for application

- Set the correct database configuration in both `acc.py` and `todo.py` files
    - Account server (`acc.py`)
      - Celery worker 1 -- `celery -A acc.celery1 worker -Q a -l info -P eventlet`
        
    - Application server (`todo.py`)
        - Celery worker 2 -- `celery -A todo.celery2 worker -Q b -l info -P eventlet`

## Usage

Use `127.0.0.1:80` for all requests.

- Register a user.
  
- Login using the same credential in order to use application APIs.
  
- An authorization token will be returned when logged in.
  
- In Postman, in the Authorization tab, choose Bearer Token and fill in the Key form with the token provided whenever making a request to the Application APIs or when logging out.

##

##### *Note:*
- *All testing and commands were performed on the Windows 10 OS*
- *Omit '-P eventlet' when running on Mac OS*
