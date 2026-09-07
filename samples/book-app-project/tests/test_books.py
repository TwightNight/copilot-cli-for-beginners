import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import books
from books import BookCollection


@pytest.fixture(autouse=True)
def use_temp_data_file(tmp_path, monkeypatch):
    """Use a temporary data file for each test."""
    temp_file = tmp_path / "data.json"
    temp_file.write_text("[]")
    monkeypatch.setattr(books, "DATA_FILE", str(temp_file))


class TestAddBook:
    """Tests for adding books to the collection."""

    def test_add_book_success(self):
        """Test adding a valid book."""
        collection = BookCollection()
        book = collection.add_book("1984", "George Orwell", 1949)
        
        assert len(collection.books) == 1
        assert book.title == "1984"
        assert book.author == "George Orwell"
        assert book.year == 1949
        assert book.read is False

    def test_add_book_persists_to_file(self):
        """Test that added books are saved to data.json."""
        collection = BookCollection()
        collection.add_book("Dune", "Frank Herbert", 1965)
        
        collection2 = BookCollection()
        book = collection2.find_book_by_title("Dune")
        assert book is not None
        assert book.author == "Frank Herbert"

    def test_add_multiple_books(self):
        """Test adding multiple books."""
        collection = BookCollection()
        collection.add_book("Book 1", "Author A", 2000)
        collection.add_book("Book 2", "Author B", 2001)
        collection.add_book("Book 3", "Author C", 2002)
        
        assert len(collection.books) == 3

    def test_add_book_with_zero_year(self):
        """Test adding a book with year 0 (default)."""
        collection = BookCollection()
        book = collection.add_book("Anonymous", "Unknown", 0)
        
        assert book.year == 0

    def test_add_book_with_duplicate_title(self):
        """Test that duplicate titles are allowed."""
        collection = BookCollection()
        collection.add_book("Title", "Author A", 2000)
        collection.add_book("Title", "Author B", 2001)
        
        assert len(collection.books) == 2


class TestRemoveBook:
    """Tests for removing books from the collection."""

    def test_remove_book_success(self):
        """Test removing an existing book."""
        collection = BookCollection()
        collection.add_book("The Hobbit", "J.R.R. Tolkien", 1937)
        
        result = collection.remove_book("The Hobbit")
        
        assert result is True
        assert len(collection.books) == 0
        assert collection.find_book_by_title("The Hobbit") is None

    def test_remove_book_case_insensitive(self):
        """Test that removal is case-insensitive."""
        collection = BookCollection()
        collection.add_book("The Hobbit", "J.R.R. Tolkien", 1937)
        
        result = collection.remove_book("the hobbit")
        
        assert result is True
        assert collection.find_book_by_title("The Hobbit") is None

    def test_remove_book_not_found(self):
        """Test removing a non-existent book."""
        collection = BookCollection()
        
        result = collection.remove_book("Nonexistent Book")
        
        assert result is False
        assert len(collection.books) == 0

    def test_remove_book_from_empty_collection(self):
        """Test removing from empty collection."""
        collection = BookCollection()
        
        result = collection.remove_book("Any Book")
        
        assert result is False

    def test_remove_book_persists_to_file(self):
        """Test that removal is persisted to data.json."""
        collection = BookCollection()
        collection.add_book("Book to Remove", "Author", 2000)
        collection.remove_book("Book to Remove")
        
        collection2 = BookCollection()
        assert collection2.find_book_by_title("Book to Remove") is None

    @pytest.mark.parametrize("title", ["", " ", None])
    def test_remove_book_with_empty_input(self, title):
        """Test removing with empty or None input."""
        collection = BookCollection()
        collection.add_book("Valid Book", "Author", 2000)
        
        result = collection.remove_book(title) if title is not None else collection.remove_book("")
        
        assert result is False
        assert len(collection.books) == 1


class TestFindByTitle:
    """Tests for finding books by title."""

    def test_find_book_by_title_success(self):
        """Test finding an existing book by title."""
        collection = BookCollection()
        collection.add_book("1984", "George Orwell", 1949)
        
        book = collection.find_book_by_title("1984")
        
        assert book is not None
        assert book.author == "George Orwell"
        assert book.year == 1949

    def test_find_book_by_title_case_insensitive(self):
        """Test that title search is case-insensitive."""
        collection = BookCollection()
        collection.add_book("Dune", "Frank Herbert", 1965)
        
        book = collection.find_book_by_title("dune")
        
        assert book is not None
        assert book.author == "Frank Herbert"

    def test_find_book_by_title_not_found(self):
        """Test finding a non-existent book."""
        collection = BookCollection()
        collection.add_book("Book A", "Author A", 2000)
        
        book = collection.find_book_by_title("Book B")
        
        assert book is None

    def test_find_book_by_title_from_empty_collection(self):
        """Test finding a book in empty collection."""
        collection = BookCollection()
        
        book = collection.find_book_by_title("Any Book")
        
        assert book is None

    @pytest.mark.parametrize("title", ["", " "])
    def test_find_book_by_empty_title(self, title):
        """Test finding with empty title."""
        collection = BookCollection()
        collection.add_book("Valid Book", "Author", 2000)
        
        book = collection.find_book_by_title(title)
        
        assert book is None

    def test_find_book_returns_first_match_with_duplicates(self):
        """Test behavior when multiple books have same title."""
        collection = BookCollection()
        collection.add_book("Title", "Author A", 2000)
        collection.add_book("Title", "Author B", 2001)
        
        book = collection.find_book_by_title("Title")
        
        assert book is not None
        assert book.author == "Author A"


class TestFindByAuthor:
    """Tests for finding books by author."""

    def test_find_by_author_single_book(self):
        """Test finding books by author with single match."""
        collection = BookCollection()
        collection.add_book("Book", "Stephen King", 1990)
        
        books = collection.find_by_author("Stephen King")
        
        assert len(books) == 1
        assert books[0].title == "Book"

    def test_find_by_author_multiple_books(self):
        """Test finding multiple books by same author."""
        collection = BookCollection()
        collection.add_book("Carrie", "Stephen King", 1974)
        collection.add_book("The Shining", "Stephen King", 1977)
        collection.add_book("It", "Stephen King", 1986)
        
        books = collection.find_by_author("Stephen King")
        
        assert len(books) == 3
        assert all(book.author == "Stephen King" for book in books)

    def test_find_by_author_case_insensitive(self):
        """Test that author search is case-insensitive."""
        collection = BookCollection()
        collection.add_book("Dune", "Frank Herbert", 1965)
        
        books = collection.find_by_author("frank herbert")
        
        assert len(books) == 1
        assert books[0].author == "Frank Herbert"

    def test_find_by_author_not_found(self):
        """Test finding books by non-existent author."""
        collection = BookCollection()
        collection.add_book("Book", "Author A", 2000)
        
        books = collection.find_by_author("Author B")
        
        assert books == []

    def test_find_by_author_empty_collection(self):
        """Test finding books in empty collection."""
        collection = BookCollection()
        
        books = collection.find_by_author("Any Author")
        
        assert books == []

    @pytest.mark.parametrize("author", ["", " "])
    def test_find_by_author_empty_input(self, author):
        """Test finding with empty author name."""
        collection = BookCollection()
        collection.add_book("Book", "Author", 2000)
        
        books = collection.find_by_author(author)
        
        assert books == []

    def test_find_by_author_preserves_order(self):
        """Test that results are in collection order."""
        collection = BookCollection()
        collection.add_book("Book C", "Author", 2002)
        collection.add_book("Book A", "Author", 2000)
        collection.add_book("Book B", "Author", 2001)
        
        books = collection.find_by_author("Author")
        
        assert [b.title for b in books] == ["Book C", "Book A", "Book B"]


class TestMarkAsRead:
    """Tests for marking books as read."""

    def test_mark_as_read_success(self):
        """Test marking an existing book as read."""
        collection = BookCollection()
        collection.add_book("Dune", "Frank Herbert", 1965)
        
        result = collection.mark_as_read("Dune")
        
        assert result is True
        book = collection.find_book_by_title("Dune")
        assert book.read is True

    def test_mark_as_read_persists(self):
        """Test that read status is persisted to data.json."""
        collection = BookCollection()
        collection.add_book("Dune", "Frank Herbert", 1965)
        collection.mark_as_read("Dune")
        
        collection2 = BookCollection()
        book = collection2.find_book_by_title("Dune")
        assert book.read is True

    def test_mark_as_read_case_insensitive(self):
        """Test that marking as read is case-insensitive."""
        collection = BookCollection()
        collection.add_book("Dune", "Frank Herbert", 1965)
        
        result = collection.mark_as_read("dune")
        
        assert result is True
        assert collection.find_book_by_title("Dune").read is True

    def test_mark_as_read_invalid_book(self):
        """Test marking non-existent book as read."""
        collection = BookCollection()
        
        result = collection.mark_as_read("Nonexistent Book")
        
        assert result is False

    def test_mark_as_read_empty_collection(self):
        """Test marking book as read in empty collection."""
        collection = BookCollection()
        
        result = collection.mark_as_read("Any Book")
        
        assert result is False

    def test_mark_already_read_book(self):
        """Test marking already-read book as read again."""
        collection = BookCollection()
        collection.add_book("Book", "Author", 2000)
        collection.mark_as_read("Book")
        
        result = collection.mark_as_read("Book")
        
        assert result is True
        assert collection.find_book_by_title("Book").read is True

    def test_mark_multiple_books_as_read(self):
        """Test marking multiple different books as read."""
        collection = BookCollection()
        collection.add_book("Book 1", "Author", 2000)
        collection.add_book("Book 2", "Author", 2001)
        
        collection.mark_as_read("Book 1")
        collection.mark_as_read("Book 2")
        
        assert collection.find_book_by_title("Book 1").read is True
        assert collection.find_book_by_title("Book 2").read is True


class TestEmptyCollection:
    """Tests for edge cases with empty collection."""

    def test_list_books_empty_collection(self):
        """Test listing books in empty collection."""
        collection = BookCollection()
        
        books = collection.list_books()
        
        assert books == []

    def test_find_by_title_empty_collection(self):
        """Test finding book in empty collection."""
        collection = BookCollection()
        
        book = collection.find_book_by_title("Any Book")
        
        assert book is None

    def test_find_by_author_empty_collection(self):
        """Test finding books by author in empty collection."""
        collection = BookCollection()
        
        books = collection.find_by_author("Any Author")
        
        assert books == []

    def test_remove_from_empty_collection(self):
        """Test removing book from empty collection."""
        collection = BookCollection()
        
        result = collection.remove_book("Any Book")
        
        assert result is False

    def test_mark_as_read_empty_collection(self):
        """Test marking book as read in empty collection."""
        collection = BookCollection()
        
        result = collection.mark_as_read("Any Book")
        
        assert result is False
