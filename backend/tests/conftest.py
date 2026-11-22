
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, URL
from sqlalchemy.orm import sessionmaker

from main import app
from database import get_db, settings
from models.base import Base

# Import all models to register their tables.
from models.user import User
from models.book import Book
from models.book_copy import BookCopy
from models.loan import Loan
from models.reservation import Reservation
from models.fine import Fine
from models.fine_payment import FinePayment
from models.library_setting import LibrarySetting


# --------------------------------------------------
# 1. TEST DATABASE CONFIGURATION
# --------------------------------------------------

TEST_DB_NAME = "library_lending_test_db"

if settings.DB_NAME == TEST_DB_NAME:
    raise RuntimeError(
        "Application database must be different from test database."
    )

test_database_url = URL.create(
    drivername="postgresql+psycopg",
    username=settings.DB_USER,
    password=settings.DB_PASSWORD,
    host=settings.DB_HOST,
    port=settings.DB_PORT,
    database=TEST_DB_NAME,
)

test_engine = create_engine(
    test_database_url,
    pool_pre_ping=True
)

TestSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    autocommit=False
)


# --------------------------------------------------
# 2. CREATE AND CLEAN UP TEST DATABASE TABLES
# --------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():

    if test_engine.url.database != TEST_DB_NAME:
        raise RuntimeError(
            "Unsafe test database configuration."
        )

    # Create tables only in the test database.
    Base.metadata.create_all(bind=test_engine)

    yield

    # Remove tables after all tests finish.
    Base.metadata.drop_all(bind=test_engine)

    test_engine.dispose()


# --------------------------------------------------
# 3. DATABASE SESSION WITH TRANSACTION ROLLBACK
# --------------------------------------------------

@pytest.fixture
def db():

    connection = test_engine.connect()

    # Begin an outer transaction.
    transaction = connection.begin()

    # Create a session with SAVEPOINT support.
    session = TestSessionLocal(
        bind=connection,
        join_transaction_mode="create_savepoint"
    )

    try:
        yield session

    finally:
        # Close the session.
        session.close()

        # Roll back all changes made during the test,
        # including changes from session.commit().
        transaction.rollback()

        # Release the database connection.
        connection.close()


# --------------------------------------------------
# 4. FASTAPI TEST CLIENT
# --------------------------------------------------

@pytest.fixture
def client(db):

    # Override the production database dependency.
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client

    finally:
        # Restore original FastAPI dependencies.
        app.dependency_overrides.clear()
