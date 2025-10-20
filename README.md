# MCP Google Books

[![smithery badge](https://smithery.ai/badge/@juanbeniteza/mcp-google-books)](https://smithery.ai/server/@juanbeniteza/mcp-google-books)

## 🧐 What is This?

This MCP server package exposes functionality for fetching book related information from Google Books API. This implementation is designed to be used in environments that support the MCP protocol, such as Claude. 

## 📦 Usage

### Installing via Smithery

To install mcp-google-books for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@juanbeniteza/mcp-google-books):

```bash
npx -y @smithery/cli install @juanbeniteza/mcp-google-books --client claude
```

### Prerequisites

Before running the server, ensure you have:
1. Python 3.12 or higher installed
2. A Google Books API key (get one from [Google Cloud Console](https://console.cloud.google.com/))
3. A `.env` file with your API key:
   ```
   GOOGLE_API_KEY=your_api_key_here
   ```

### Starting Up the Server

To begin using mcp-google-books:

1. Install dependencies using `uv` (recommended) or `pip`:
   ```bash
   # Using uv (recommended)
   uv pip install -e .

   # Or using pip
   pip install -e .
   ```

2. Start the server:
   ```bash
   python main.py
   ```
   
## 💡 Example

Below is a detailed example of how to use the mcp-google-books server with an MCP compatible client:

1. **Initialize the Server**
 	- Start the server.
 
3. **Client Interactions**
	- With a running instance of Claude or another compatible client, the client should automatically connect and discover this server, listing its tools and resources available for use.
	- You can query books by title or author.
 
4. **Tool Listings**
	- Once the server initializes, list available tools. This would include actions that can be invoked by clients.

5. **Calling Tools**
	- Clients can now call available tools for getting book information via Google Books API.
 
## 🙏 Acknowledgements

Special thanks to Google Books API for providing the required data. 

## 🌍 License

This repository is licensed under the MIT License. See the LICENSE file for more information.

## 🛠️ Available Tools

This MCP server provides the following tools for interacting with Google Books:

### 1. Book Search
Search for books by title using the Google Books API.

```python
book_search(query: str, max_results: int = 5)
```

**Parameters:**
- `query`: The title of the book to search for (required)
- `max_results`: Maximum number of results to return (default: 5, max: 40)

**Example:**
```python
# Search for a book by title
result = book_search(query="The Hobbit")

# Get more results
result = book_search(query="Python Programming", max_results=10)
```

### 2. Author Search
Search for books by author using the Google Books API.

```python
author_search(query: str, max_results: int = 10)
```

**Parameters:**
- `query`: The name of the author to search for (required)
- `max_results`: Maximum number of results to return (default: 10, max: 40)

**Example:**
```python
# Search for books by an author
result = author_search(query="J.R.R. Tolkien")
```

### 3. ISBN Search
Search for a specific book by its ISBN (International Standard Book Number).

```python
isbn_search(isbn: str)
```

**Parameters:**
- `isbn`: ISBN-10 or ISBN-13 of the book (required)

**Example:**
```python
# Search by ISBN-13
result = isbn_search(isbn="978-0-547-92822-7")

# Search by ISBN-10
result = isbn_search(isbn="0547928227")
```

### 4. Subject Search
Search for books by subject or category.

```python
subject_search(subject: str, max_results: int = 10)
```

**Parameters:**
- `subject`: Subject or category to search for (required)
- `max_results`: Maximum number of results to return (default: 10, max: 40)

**Example:**
```python
# Search for books in a subject
result = subject_search(subject="science fiction")
result = subject_search(subject="medieval history", max_results=15)
```

## 📝 Response Format

Both tools return information about books including:
- Title
- Author(s)
- Published Date
- Description (when available)

The results are returned in a formatted text that can be easily read and processed by MCP clients.

## ⚠️ Rate Limiting

Please note that these tools use the Google Books API, which has rate limiting. Make sure to handle your requests accordingly to avoid hitting API limits.
