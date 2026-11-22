## Bookworm — Library Lending Management System

A full-stack web-based **Library Lending Management System** developed as part of the **Cardinality.ai Full Stack Developer Internship Assignment**.

Bookworm is designed to simplify and automate library operations through a centralized platform for managing books, members, borrowing requests, reservations, returns, and overdue fines.

The application supports two primary roles — **Member** and **Librarian** — with dedicated interfaces and role-based permissions.

Members can browse books, request checkouts, track active loans, reserve unavailable books, and manage fines. Librarians can maintain the book catalogue, manage book copies, and approve or reject checkout requests.

The system demonstrates full-stack development concepts, including REST API integration, relational database design, authentication, authorization, business logic, database migrations, and automated testing.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Angular 21, TypeScript, HTML, CSS |
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Database Migrations | Alembic |
| Authentication | JWT, Email OTP |
| Automated Testing | Pytest |
| Book Cover Integration | Open Library API |
| Version Control | Git and GitHub |

---

## Features

### Member Features

- Registration with email OTP verification
- Simulated ₹100 membership payment
- Secure login and password reset
- Browse and search the book catalogue
- View book details and availability
- Submit book checkout requests
- Cancel pending checkout requests
- Track active loans and borrowing history
- View due dates and return borrowed books
- Reserve unavailable books
- Monitor reservation queue positions
- View outstanding fines
- Complete simulated fine payments
- Access a dedicated member dashboard

### Librarian Features

- Role-based librarian authentication
- View and manage pending checkout requests
- Approve or reject borrowing requests
- Add new books to the catalogue
- Edit existing book information
- Add additional physical book copies
- Monitor book availability
- Manage library inventory

### Library Business Logic

The backend includes business rules for managing borrowing and reservation activities.

- Checkout restrictions based on maximum active loans
- Book availability validation
- Due-date-based loan management
- Overdue fine calculation with a maximum cap
- First-In, First-Out (FIFO) reservation allocation
- Expired reservation hold reassignment
- Prevention of concurrent checkout of the last available copy
- Validation of configurable library settings

These business rules are covered by automated tests.

---

## System Architecture

Bookworm follows a three-tier architecture consisting of an Angular frontend, a FastAPI backend, and a PostgreSQL database.

```text
             Angular 21 Frontend
       (Member and Librarian Interfaces)
                       |
                       |
                HTTP / REST API
                       |
                       v
                FastAPI Backend
       +-----------------------------+
       | Authentication & Security   |
       | Book Catalogue Management   |
       | Checkout & Loan Management  |
       | Reservation Queue           |
       | Fine Management             |
       | Library Settings            |
       +-----------------------------+
                       |
                  SQLAlchemy ORM
                       |
                       v
               PostgreSQL Database
                       |
                Alembic Migrations
```

### Frontend Layer

The frontend is developed using Angular 21 and TypeScript.

It provides interactive interfaces for members and librarians, manages user interactions, handles form submissions, and communicates with the FastAPI backend through HTTP requests.

### Backend Layer

The backend is developed using Python and FastAPI.

It provides RESTful APIs for authentication, books, checkout requests, loans, reservations, fines, payments, and library settings.

The backend follows a modular architecture consisting of:

- **Routers:** Handle API endpoints and HTTP requests.
- **Schemas:** Validate incoming and outgoing data.
- **Models:** Define database entities using SQLAlchemy.
- **Services:** Implement application business logic.
- **Core:** Contains authentication, authorization, and security utilities.
- **Database:** Manages PostgreSQL connectivity and sessions.

### Database Layer

PostgreSQL is used as the relational database for storing library records.

SQLAlchemy provides Object-Relational Mapping (ORM), allowing the backend to interact with database entities through Python objects.

Alembic manages database schema migrations and supports consistent database initialization.

---

## Database Data Model

The application uses a relational database design to manage users, books, borrowing activities, reservations, and fines.

### Main Database Entities

| Entity | Description |
|---|---|
| Users | Stores member and librarian account information |
| Books | Stores book titles, authors, and catalogue details |
| Book Copies | Tracks physical copies and their availability |
| Checkout Requests | Stores borrowing requests and approval status |
| Loans | Records borrowed books, due dates, and return information |
| Reservations | Maintains reservation records and queue information |
| Fines | Records overdue penalties |
| Fine Payments | Tracks simulated fine payments |
| Library Settings | Stores configurable lending rules |
| Email Verification | Supports registration email verification |
| Password Reset | Supports password recovery |
| Registration Payments | Tracks simulated membership payments |
| Auth Sessions | Stores authentication session information |

### Data Relationships

- A user can have multiple checkout requests.
- A user can have multiple active or historical loans.
- A user can place multiple book reservations.
- A book can have multiple physical copies.
- A loan associates a member with a borrowed book copy.
- A reservation associates a member with a requested book.
- Fine records are associated with borrowing activities.
- Library settings define configurable lending and fine rules.

The database schema is managed using SQLAlchemy models and Alembic migrations.

---

## Application Workflow

### Member Workflow

```text
Register
   |
   v
Email OTP Verification
   |
   v
Simulated Membership Payment
   |
   v
Login
   |
   v
Browse Book Catalogue
   |
   v
Submit Checkout Request
   |
   v
Librarian Approval
   |
   v
Borrow Book
   |
   v
Track Loan and Due Date
   |
   v
Return Book
   |
   v
Fine Calculation (if overdue)
```

Members can also reserve unavailable books, monitor reservation queues, and view outstanding fines.

### Librarian Workflow

```text
Librarian Login
       |
       v
Librarian Dashboard
       |
       +----> Review Checkout Requests
       |             |
       |             v
       |       Approve / Reject
       |
       +----> Manage Book Catalogue
       |             |
       |             v
       |       Add / Edit Books
       |
       +----> Manage Book Copies
       |
       +----> Monitor Availability
```

---

## Application Screenshots

### Login Page

![Login Page](screenshots/Login%20Page.png)

### Registration Page

![Registration Page](screenshots/Register%20Page.png)

### Member Book Catalogue

![Member Book Catalogue](screenshots/Members-Book%20catalogue%20Page.png)

### Member Dashboard

![Member Dashboard](screenshots/Members-Dashboard%20Page.png)

### Member Book Requests

![Member Book Requests](screenshots/Members-Book%20Request%20Page%20.png)

### Member Reservations

![Member Reservations](screenshots/Members-Reservation%20Page.png)

### Member Fines

![Member Fines](screenshots/Members-Fine%20Page.png)

### Librarian Book Catalogue

![Librarian Book Catalogue](screenshots/Librarian-Book%20Catalogue%20Page.png)

### Librarian Request Approvals

![Librarian Request Approvals](screenshots/Librarian-Request%20Approval%20Page.png)

### Librarian Manage Books

![Librarian Manage Books](screenshots/Librarian-Manage%20Books%20Page.png)

---

## Project Structure

```text
library-lending-system/
|
|-- backend/
|   |-- alembic/
|   |   |-- versions/
|   |   |-- env.py
|   |-- core/
|   |-- models/
|   |-- routers/
|   |-- schemas/
|   |-- services/
|   |-- tests/
|   |-- main.py
|   |-- database.py
|   |-- seed_data.py
|   |-- create_librarian.py
|   |-- requirements.txt
|   |-- alembic.ini
|   |-- .env.example
|
|-- frontend/
|   |-- src/
|   |   |-- app/
|   |-- public/
|   |-- package.json
|   |-- angular.json
|
|-- screenshots/
|-- .gitignore
|-- README.md
```

---

## ⚙️ Prerequisites

Before running the application, ensure the following software is installed:

- Python 3 (the project has been tested locally using Python 3.13)
- Node.js and npm compatible with Angular 21
- PostgreSQL
- Git

---

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/VinodhiniJA/library-lending-system.git
cd library-lending-system
```

### 2. Backend Setup

Navigate to the backend directory:

```bash
cd backend
```

Create a Python virtual environment:

```bash
python -m venv .venv
```

Activate the virtual environment on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install backend dependencies:

```bash
python -m pip install -r requirements.txt
```

### 3. PostgreSQL Database Configuration

Create a PostgreSQL database named:

```text
library_lending_db
```

Copy the environment configuration template:

```powershell
Copy-Item .env.example .env
```

Update the database credentials in `backend/.env` according to your local PostgreSQL configuration.

Example database configuration:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=library_lending_db
DB_USER=postgres
DB_PASSWORD=your_database_password
```

Configure any additional application secrets or email service settings required by the backend.

**Important:** Do not commit `.env` or actual credentials to GitHub.

### 4. Database Migrations

Run Alembic migrations to initialize the database schema:

```bash
alembic upgrade head
```

### 5. Seed Initial Data

Populate the database using the seed script:

```bash
python seed_data.py
```

### 6. Create a Librarian Account

Run:

```bash
python create_librarian.py
```

Follow the script's instructions, if prompted, to create the librarian account.

### 7. Start the Backend Server

```bash
uvicorn main:app --reload
```

The backend will be available at:

- **API:** http://localhost:8000
- **Swagger API Documentation:** http://localhost:8000/docs

### 8. Frontend Setup

Open a new terminal and navigate to the frontend directory from the project root:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the Angular development server:

```bash
npm start
```

The frontend will be available at:

http://localhost:4200

Ensure the backend server and PostgreSQL database are running before testing application features.

---

## Automated Testing

The backend includes automated tests implemented using Pytest.

### Test Coverage

The test suite verifies:

1. Fine calculation for early returns
2. Fine calculation for on-time returns
3. Fine calculation for overdue returns
4. Maximum fine cap
5. Successful checkout
6. Maximum active loan restrictions
7. Unavailable book handling
8. Successful book return
9. Duplicate return prevention
10. FIFO reservation queue allocation
11. Expired reservation hold reassignment
12. Concurrent checkout of the last available copy
13. Database connectivity
14. Book and copy validation
15. Database constraints
16. Library configuration validation

### Running Automated Tests

Navigate to the backend directory:

```bash
cd backend
```

Ensure the Python virtual environment is active and dependencies are installed.

Run:

```bash
python -m pytest tests/ -v
```

### Latest Local Test Results

```text
==========================
24 passed, 1 warning in 2.37s
==========================
```

All **24 collected automated tests passed** during local execution using Python 3.13.0 and Pytest 9.2.0.

The single warning was related to Starlette TestClient dependency deprecation and did not affect the test results.

### Key Business Logic Validations

- Overdue fines are calculated according to lending rules.
- Fine amounts respect the maximum fine cap.
- Members cannot exceed the maximum active loan limit.
- Reservation allocation follows FIFO ordering.
- Expired reservation holds can be reassigned.
- Concurrent checkout requests cannot both obtain the final available copy.
- Database constraints reject invalid values.

---

## Security

The application includes the following security mechanisms:

- JWT-based authentication
- Role-based access control
- Email OTP verification
- Password hashing
- Password recovery workflow
- Environment-based configuration
- Sensitive credentials excluded from version control

---

## Payment Disclaimer

Membership registration and fine payments are simulated for demonstration purposes.

The application does not process real financial transactions.

---

## Assignment Details

| Field | Details |
|---|---|
| Company | Cardinality.ai |
| Position | Full Stack Developer Internship |
| Assignment | One-Week Full Stack Project |
| Project | Library Lending with Reservation Queue and Fines |
| Frontend | Angular 21 |
| Backend | Python FastAPI |
| Database | PostgreSQL |
| Automated Tests | 24 passed |
| Version Control | Git and GitHub |

### Project Objective

The objective of this project is to develop a working full-stack Library Lending Management System that demonstrates frontend development, REST API design, relational database management, secure authentication, server-side business rules, and automated testing.

The application provides separate workflows for members and librarians while supporting core library operations such as book management, checkout approvals, reservations, returns, and fine management.

---

## Conclusion

Bookworm demonstrates the development of a full-stack web application using Angular, FastAPI, and PostgreSQL.

The project combines a user-friendly frontend with modular backend services, relational database management, authentication, borrowing workflows, reservation queues, fine calculations, and automated tests.

It provides a practical implementation of a Library Lending Management System while demonstrating essential full-stack software engineering concepts.


---

## Project Demo Video

Watch the complete demonstration of the Bookworm Library Lending Management System.

[▶ Watch Demo Video](./demo/Bookworm_Demo.mp4)
