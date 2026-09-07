import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import books
from books import BookCollection


@pytest.fixture
def collection(tmp_path, monkeypatch):
    """Provide an empty collection backed by a temporary data file."""
    data_file = tmp_path / "data.json"
    data_file.write_text("[]")
    monkeypatch.setattr(books, "DATA_FILE", str(data_file))
    return BookCollection()


def test_remove_existing_book_returns_true_and_removes_book(collection):
    collection.add_book("Dune", "Frank Herbert", 1965)

    result = collection.remove_book("Dune")

    assert result is True
    assert collection.list_books() == []


def test_remove_book_matches_title_case_insensitively(collection):
    collection.add_book("Dune", "Frank Herbert", 1965)

    result = collection.remove_book("  dUnE  ")

    assert result is True
    assert collection.list_books() == []


def test_remove_missing_book_returns_false_and_preserves_books(collection):
    collection.add_book("Dune Messiah", "Frank Herbert", 1969)

    result = collection.remove_book("Dune")

    assert result is False
    assert [book.title for book in collection.list_books()] == ["Dune Messiah"]


def test_remove_book_from_empty_collection_returns_false(collection):
    result = collection.remove_book("Dune")

    assert result is False
    assert collection.list_books() == []
