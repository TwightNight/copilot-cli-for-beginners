from books import Book
from utils import print_books


def test_print_books_with_no_books(capsys):
    print_books([])

    assert capsys.readouterr().out == "No books found.\n"


def test_print_books_displays_book_status(capsys):
    print_books([Book("Dune", "Frank Herbert", 1965, read=True)])

    assert "1. [x] Dune by Frank Herbert (1965)" in capsys.readouterr().out
