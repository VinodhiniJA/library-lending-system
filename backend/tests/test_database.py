from sqlalchemy import select

from models.book import Book


def test_database_connection(db):
    result = db.scalars(select(Book)).all()
    assert result == []