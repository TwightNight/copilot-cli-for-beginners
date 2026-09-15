import os
import sys
from datetime import date

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import book_app
from books import Book


class RecordingCollection:
    """Record add calls without writing to the real data file."""

    def __init__(self):
        self.added_books = []
        self.unread_books = []

    def add_book(self, title, author, year):
        self.added_books.append((title, author, year))

    def list_unread_books(self):
        return self.unread_books


@pytest.fixture
def recording_collection(monkeypatch):
    collection = RecordingCollection()
    monkeypatch.setattr(book_app, "collection", collection)
    return collection


def test_handle_add_accepts_valid_year(recording_collection, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: {"Title: ": "Dune", "Author: ": "Frank Herbert", "Year: ": "1965"}[_])

    book_app.handle_add()

    assert recording_collection.added_books == [("Dune", "Frank Herbert", 1965)]
    assert "Book added successfully." in capsys.readouterr().out


@pytest.mark.parametrize("year", ["", "not-a-year", "0", "-1", str(date.today().year + 1)])
def test_handle_add_rejects_invalid_year(recording_collection, monkeypatch, capsys, year):
    inputs = iter(["Dune", "Frank Herbert", year])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    book_app.handle_add()

    assert recording_collection.added_books == []
    assert "Error:" in capsys.readouterr().out


def test_handle_unread_displays_unread_books(recording_collection, capsys):
    recording_collection.unread_books = [Book("Dune", "Frank Herbert", 1965)]

    book_app.handle_unread()

    output = capsys.readouterr().out
    assert "Dune by Frank Herbert (1965)" in output


def test_handle_unread_displays_dedicated_empty_message(recording_collection, capsys):
    book_app.handle_unread()

    assert capsys.readouterr().out.strip() == "No unread books found."


def test_main_dispatches_unread_command(monkeypatch, capsys):
    monkeypatch.setattr(book_app.sys, "argv", ["book_app.py", "unread"])
    monkeypatch.setattr(book_app, "handle_unread", lambda: print("unread handler"))

    book_app.main()

    assert capsys.readouterr().out.strip() == "unread handler"
