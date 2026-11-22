
# Bookworm — Library Lending Management System

A full-stack Library Lending Management System developed as part of the Cardinality.ai Full Stack Developer Internship Assignment.

Bookworm allows members to browse, borrow, reserve, and return books. Librarians can manage books and approve checkout requests.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Angular 21, TypeScript, HTML, CSS |
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Authentication | JWT, Email OTP |
| Book Covers | Open Library API |

## Features

### Member Features

- Registration with email OTP verification
- Simulated ₹100 membership payment
- Login and password reset
- Browse and search books
- View book availability
- Request book checkout
- Cancel pending checkout requests
- View active loans and borrowing history
- Return borrowed books
- Reserve unavailable books
- View reservation queue position
- View and pay fines through demo payment

### Librarian Features

- Role-based librarian login
- View pending checkout requests
- Approve or reject requests
- Add new books
- Edit book information
- Add additional book copies
- Monitor book availability


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


## Project Structure

```text
library-lending-app/
├── backend/
│   ├── alembic/
│   ├── core/
│   ├── models/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   ├── tests/
│   ├── main.py
│   ├── database.py
│   ├── seed_data.py
│   ├── create_librarian.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   ├── package.json
│   └── angular.json
├── screenshots/
├── .gitignore
└── README.md
```

## Prerequisites

- Python 3
- Node.js and npm
- PostgreSQL
- Git

## Installation and Setup

### 1. Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/library-lending-system.git
cd library-lending-system
```

### 2. Backend Setup

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a PostgreSQL database and configure the environment variables using `.env.example` as a reference.

Create a `.env` file inside the backend folder with your own database credentials and required application secrets.

Run database migrations:

```bash
alembic upgrade head
```

Populate initial book data:

```bash
python seed_data.py
```

Create a librarian account:

```bash
python create_librarian.py
```

Start the backend:

```bash
uvicorn main:app --reload
```

Backend API: http://localhost:8000

Swagger Documentation: http://localhost:8000/docs

### 3. Frontend Setup

Open another terminal:

```bash
cd frontend
npm install
npm start
```

Frontend: http://localhost:4200

## Application Workflow

### Member

Register → Verify OTP → Complete Demo Payment → Login → Browse Books → Request Checkout → Librarian Approval → Borrow → Return

Members can also reserve unavailable books and view outstanding fines.

### Librarian

Login → Review Checkout Requests → Approve/Reject → Manage Book Catalogue and Copies

## Security

- Role-based access control
- JWT-based authentication
- Email OTP verification
- Password hashing
- Environment-based database configuration
- Sensitive credentials excluded from version control

## Payment Disclaimer

Membership and fine payments are simulated for demonstration purposes.

No real financial transactions are processed.

## Testing

The backend contains automated tests for authentication, database operations, loans, reservations, fines, and business logic.

## Assignment

**Company:** Cardinality.ai

**Role:** Full Stack Developer Internship

**Project:** Library Lending Management System

**Frontend:** Angular

**Backend:** FastAPI

**Database:** PostgreSQL
j