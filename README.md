# Bookworm — Library Lending Management System

**Bookworm** is a full-stack web-based Library Lending Management System developed using **Angular 21, TypeScript, Python, FastAPI, PostgreSQL, SQLAlchemy, and Alembic** as part of the **Cardinality.ai Full Stack Developer Internship Assignment**.

The application is designed to simplify and automate library operations by providing a centralized digital platform for managing books, library members, borrowing requests, reservations, returns, and overdue fines. It replaces manual library management processes with an organized, secure, and user-friendly system that improves efficiency for both library members and librarians.

The system supports two primary user roles: **Member and Librarian**, each with dedicated functionality and role-based access permissions.

## Member Management and Authentication

Bookworm provides a structured registration and authentication workflow. New members can create accounts, verify their email addresses using a One-Time Password (OTP), and complete a simulated ₹100 registration payment to activate their membership.

The authentication system uses JWT-based security mechanisms and role-based access control to protect application resources. Members can securely log in, manage their borrowing activities, and reset forgotten passwords through an OTP-based password recovery process.

## Book Catalogue and Availability Management

The application features an interactive book catalogue where members can browse available books, search by title or author, and view the number of available copies.

Book cover images are retrieved through the Open Library API to improve the visual browsing experience. When an actual cover is unavailable, the application generates a custom illustrated cover displaying the book title and author.

Librarians can add new books, update existing book information, and increase the number of physical copies available in the library.

## Book Checkout and Approval Workflow

Members can submit checkout requests for available books through the application.

Instead of automatically issuing books, the system follows a librarian-controlled approval workflow. Librarians can review pending requests and approve or reject them based on availability and library rules.

Members can monitor their checkout request status and cancel requests that are still pending.

Approved borrowing activities are recorded in the system, allowing members to view their active loans and borrowing history.

## Book Reservations and Queue Management

When a book is unavailable, members can place a reservation to join the waiting queue.

The reservation system allows members to monitor their queue positions, view the number of members ahead of them, and cancel reservations when necessary.

This provides an organized approach to handling demand for books with limited available copies.

## Book Returns and Fine Management

Members can track borrowed books through their dashboard and initiate the return process.

The application supports overdue fine management, allowing members to view outstanding fines associated with their borrowing activities.

A simulated payment feature is provided to demonstrate the fine settlement workflow without processing actual financial transactions.

## Librarian Administration

The librarian interface provides tools for managing essential library operations, including reviewing checkout requests, approving or rejecting borrowing requests, maintaining the book catalogue, updating book details, and managing physical book inventory.

These administrative features help librarians maintain accurate book availability records and manage member borrowing activities efficiently.

## Backend Architecture and Database Management

The backend is developed using FastAPI, providing RESTful API endpoints for authentication, books, checkout requests, loans, reservations, fines, and membership payments.

PostgreSQL is used as the relational database, with SQLAlchemy handling database interactions through object-relational mapping.

Alembic manages database schema migrations, helping maintain database structure as the application evolves.

The backend follows a modular structure with separate routers, models, schemas, services, and security components to improve maintainability and separation of concerns.

## Frontend Development

The frontend is developed using Angular 21 and TypeScript, with HTML and CSS for the user interface.

It provides separate member and librarian experiences, including catalogue browsing, member dashboards, checkout request management, reservations, fine tracking, and book administration.

The frontend communicates with the FastAPI backend through HTTP requests, enabling dynamic data retrieval and updates.

## Technologies Used

- **Frontend:** Angular 21, TypeScript, HTML, CSS
- **Backend:** Python, FastAPI, REST APIs
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Database Migrations:** Alembic
- **Authentication:** JWT, Email OTP, Role-Based Access Control
- **External Integration:** Open Library API
- **Version Control:** Git and GitHub

## Project Objective

The primary objective of Bookworm is to develop a functional, maintainable, and user-friendly library management application that demonstrates full-stack development concepts, relational database design, REST API integration, secure authentication, role-based authorization, and real-world library lending workflows.

The project showcases the integration of a modern Angular frontend with a Python FastAPI backend and PostgreSQL database to deliver a complete library lending solution.
