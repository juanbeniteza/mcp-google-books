import httpx
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import os

load_dotenv(override=True)


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_API_BASE_URL = 'https://www.googleapis.com/books/v1'

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY must be set in .env file")


mcp = FastMCP("Google Books MCP")

async def get_api_client() -> httpx.AsyncClient:
    """Create an API client"""
    return httpx.AsyncClient(
        base_url=GOOGLE_API_BASE_URL,
        headers={
            "Accept": "application/json"
        },
        timeout=30.0
    )


@mcp.tool()
async def book_search(query: str):
    """Performs a search for books on Google Books by their title based on a query.

    Args:
        query: Title of the book (required)
    """

    try:
        params = {
            "q": f"intitle:{query}",
            "projection": "lite",
            "printType": "books",
            "maxResults": 5,
            "key": GOOGLE_API_KEY
        }

        async with await get_api_client() as client:
            response = await client.get("/volumes", params=params)

            response.raise_for_status()
            data = response.json()

            if "items" not in data:
                return "No results found."

            results = []
            for result in data["items"]:
                results.append(
                    f"Title: {result['volumeInfo'].get('title')}\n"
                    f"Authors: {', '.join(result['volumeInfo'].get('authors', []))}\n"
                    f"Published Date: {result['volumeInfo'].get('publishedDate')}\n"
                    f"Description: {result['volumeInfo'].get('description')}\n"
                )

            return "\n\n".join(results)

    except httpx.HTTPError as e:
        return f"Error communicating with Google Books API: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"
    

@mcp.tool()
async def author_search(query: str):
    """Performs a search for books on Google Books by their author based on a query.

    Args:
        query: Author name (required)
    """

    try:
        params = {
            "q": f"inauthor:{query}",
            "projection": "lite",
            "printType": "books",
            "maxResults": 10,
            "key": GOOGLE_API_KEY
        }

        async with await get_api_client() as client:
            response = await client.get("/volumes", params=params)

            response.raise_for_status()
            data = response.json()

            if "items" not in data:
                return "No results found."

            results = []
            for result in data["items"]:
                results.append(
                    f"Title: {result['volumeInfo'].get('title')}\n"
                    f"Authors: {', '.join(result['volumeInfo'].get('authors', []))}\n"
                    f"Published Date: {result['volumeInfo'].get('publishedDate')}\n"
                    f"Description: {result['volumeInfo'].get('description')}\n"
                )

            return "\n\n".join(results)

    except httpx.HTTPError as e:
        return f"Error communicating with Google Books API: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')