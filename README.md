<readme>
mcp-google-books
================
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
</readme>
