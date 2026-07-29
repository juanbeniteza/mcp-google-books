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

### Starting Up the Server

To begin using mcp-google-books, connect to your MCP compatible environment (such as Claude) and then run the server.

1.	Start the server by issuing the following command:
	```sh
	node mcp-google-books.js
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
mcp_Google_Books_book_search(query: str)
```

**Parameters:**
- `query`: The title of the book to search for

**Example:**
```python
# Search for a book by title
result = mcp_Google_Books_book_search(query="The Hobbit")
```

### 2. Author Search
Search for books by author using the Google Books API.

```python
mcp_Google_Books_author_search(query: str)
```

**Parameters:**
- `query`: The name of the author to search for

**Example:**
```python
# Search for books by an author
result = mcp_Google_Books_author_search(query="J.R.R. Tolkien")
```

### 3. Download Book
Downloads a public-domain book by title and saves it to disk.

```python
mcp_Google_Books_download_book(query: str, output_dir: str = ".")
```

**Parameters:**
- `query`: The title of the book to search for and download
- `output_dir`: Directory to save the downloaded file into (default: current directory)

**Example:**
```python
# Download a public-domain book by title
result = mcp_Google_Books_download_book(query="Pride and Prejudice")
```

This only downloads books that are legitimately freely available:
1. It first tries Google Books' own official PDF/EPUB download link, which
   Google only exposes when it has classified the volume as public domain.
2. If that isn't available, it falls back to a matching full-text scan on
   the Internet Archive - but **only** for titles Google Books has already
   confirmed are public domain. Archive.org's own search index mixes
   legitimate public-domain scans with unauthorized uploads of in-copyright
   books, so that confirmation from Google Books is required before it is
   trusted as a source.

It will not download in-copyright books that are only available in
snippet/preview view.

## 📝 Response Format

`book_search` and `author_search` return information about books including:
- Title
- Author(s)
- Published Date
- Description (when available)

The results are returned in a formatted text that can be easily read and processed by MCP clients.

`download_book` returns a message describing the outcome: the source and
saved file path on success, or an explanation when no legitimate download is
available.

## ⚠️ Rate Limiting

Please note that these tools use the Google Books API, which has rate limiting. Make sure to handle your requests accordingly to avoid hitting API limits.
