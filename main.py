import httpx
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import os
from typing import Optional

load_dotenv(override=True)


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_API_BASE_URL = 'https://www.googleapis.com/books/v1'

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY must be set in .env file")


mcp = FastMCP("Google Books MCP")

# Shared client instance for better performance
_client: Optional[httpx.AsyncClient] = None

async def get_api_client() -> httpx.AsyncClient:
    """Get or create a shared API client for better performance"""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=GOOGLE_API_BASE_URL,
            headers={
                "Accept": "application/json"
            },
            timeout=30.0
        )
    return _client


def format_book_info(volume_info: dict, max_description_length: int = 500) -> str:
    """Format book information into a readable string.

    Args:
        volume_info: The volumeInfo dictionary from Google Books API
        max_description_length: Maximum length for description (default: 500)

    Returns:
        Formatted book information string
    """
    title = volume_info.get('title', 'N/A')
    authors = ', '.join(volume_info.get('authors', ['N/A']))
    published_date = volume_info.get('publishedDate', 'N/A')
    description = volume_info.get('description', 'No description available')

    # Truncate long descriptions
    if len(description) > max_description_length:
        description = description[:max_description_length] + '...'

    return (
        f"Title: {title}\n"
        f"Authors: {authors}\n"
        f"Published Date: {published_date}\n"
        f"Description: {description}\n"
    )


async def search_books(search_param: str, query: str, max_results: int = 5) -> str:
    """Generic function to search books using Google Books API.

    Args:
        search_param: The search parameter (e.g., 'intitle', 'inauthor', 'isbn')
        query: The search query
        max_results: Maximum number of results to return (default: 5)

    Returns:
        Formatted search results or error message
    """
    if not query or not query.strip():
        return "Error: Query cannot be empty"

    try:
        params = {
            "q": f"{search_param}:{query.strip()}",
            "projection": "lite",
            "printType": "books",
            "maxResults": min(max_results, 40),  # Google Books API max is 40
            "key": GOOGLE_API_KEY
        }

        client = await get_api_client()
        response = await client.get("/volumes", params=params)
        response.raise_for_status()
        data = response.json()

        if "items" not in data or len(data["items"]) == 0:
            return f"No results found for '{query}'"

        results = []
        for item in data["items"]:
            volume_info = item.get('volumeInfo', {})
            results.append(format_book_info(volume_info))

        return "\n\n".join(results)

    except httpx.HTTPStatusError as e:
        return f"HTTP error from Google Books API: {e.response.status_code} - {e.response.text}"
    except httpx.RequestError as e:
        return f"Network error communicating with Google Books API: {str(e)}"
    except Exception as e:
        return f"Unexpected error during search: {str(e)}"


@mcp.tool()
async def book_search(query: str, max_results: int = 5) -> str:
    """Search for books on Google Books by their title.

    Args:
        query: Title of the book to search for (required)
        max_results: Maximum number of results to return (default: 5, max: 40)

    Returns:
        Formatted list of books matching the query, or an error message
    """
    return await search_books("intitle", query, max_results)


@mcp.tool()
async def author_search(query: str, max_results: int = 10) -> str:
    """Search for books on Google Books by their author.

    Args:
        query: Name of the author to search for (required)
        max_results: Maximum number of results to return (default: 10, max: 40)

    Returns:
        Formatted list of books by the author, or an error message
    """
    return await search_books("inauthor", query, max_results)


@mcp.tool()
async def isbn_search(isbn: str) -> str:
    """Search for a book on Google Books by its ISBN.

    Args:
        isbn: ISBN-10 or ISBN-13 of the book (required)

    Returns:
        Book information if found, or an error message
    """
    # Remove any hyphens or spaces from ISBN
    clean_isbn = isbn.replace("-", "").replace(" ", "").strip()

    # Validate ISBN format (basic check)
    if not clean_isbn.isdigit() or len(clean_isbn) not in [10, 13]:
        return "Error: ISBN must be a 10 or 13 digit number"

    return await search_books("isbn", clean_isbn, max_results=1)


@mcp.tool()
async def subject_search(subject: str, max_results: int = 10) -> str:
    """Search for books on Google Books by subject/category.

    Args:
        subject: Subject or category to search for (e.g., 'science fiction', 'history')
        max_results: Maximum number of results to return (default: 10, max: 40)

    Returns:
        Formatted list of books in the subject category, or an error message
    """
    return await search_books("subject", subject, max_results)


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')