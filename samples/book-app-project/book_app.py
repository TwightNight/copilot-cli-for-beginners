import sys
from books import BookCollection
from utils import print_books


# Global collection instance
collection = BookCollection()


def handle_list() -> None:
    """Display all books in the collection."""
    books = collection.list_books()
    print_books(books)


def handle_add() -> None:
    """Prompt user to add a new book to the collection."""
    print("\nAdd a New Book\n")

    title = input("Title: ").strip()
    author = input("Author: ").strip()
    year_str = input("Year: ").strip()

    if not title or not author:
        print("\nError: Title and author cannot be empty.\n")
        return

    try:
        year = int(year_str) if year_str else 0
        collection.add_book(title, author, year)
        print("\nBook added successfully.\n")
    except ValueError:
        print("\nError: Year must be a valid number.\n")


def handle_remove() -> None:
    """Prompt user to remove a book from the collection by title."""
    print("\nRemove a Book\n")

    title = input("Enter the title of the book to remove: ").strip()

    if not title:
        print("\nError: Title cannot be empty.\n")
        return

    if collection.remove_book(title):
        print("\nBook removed successfully.\n")
    else:
        print("\nBook not found.\n")


def handle_find() -> None:
    """Prompt user to find books by author."""
    print("\nFind Books by Author\n")

    author = input("Author name: ").strip()

    if not author:
        print("\nError: Author name cannot be empty.\n")
        return

    books = collection.find_by_author(author)
    print_books(books)


def show_help() -> None:
    """Display help message with available commands."""
    print("""
Book Collection Helper

Commands:
  list     - Show all books
  add      - Add a new book
  remove   - Remove a book by title
  find     - Find books by author
  help     - Show this help message
""")


def main() -> None:
    """Parse command-line arguments and dispatch to appropriate handler."""
    if len(sys.argv) < 2:
        show_help()
        return

    command = sys.argv[1].lower()

    commands: dict[str, callable] = {
        "list": handle_list,
        "add": handle_add,
        "remove": handle_remove,
        "find": handle_find,
        "help": show_help,
    }

    handler = commands.get(command)

    if handler:
        handler()
    else:
        print("Unknown command.\n")
        show_help()


if __name__ == "__main__":
    main()
