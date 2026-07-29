import httpx
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import datetime
import os
import re
from urllib.parse import quote

load_dotenv(override=True)


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_API_BASE_URL = 'https://www.googleapis.com/books/v1'
ARCHIVE_ORG_BASE_URL = 'https://archive.org'
DOWNLOAD_USER_AGENT = 'Mozilla/5.0 (compatible; mcp-google-books)'

# Fixed-term US public domain cutoff: works published this many years ago or
# earlier are conclusively public domain regardless of any other rights
# metadata. A single Archive.org item collection can mix genuinely old
# public-domain scans with more recent in-copyright critical editions of the
# same classical work (seen in practice: a 1946 Desclée critical edition
# turned up alongside 1885 and 1669 editions of the same title, all under
# the same author/title search) - this is a belt-and-suspenders check on top
# of the access-restricted-item flag and the Google Books confirmation gate.
PUBLIC_DOMAIN_YEAR_CUTOFF = datetime.date.today().year - 96

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


def _sanitize_filename(name: str) -> str:
    """Turn a book title into a safe filename stem."""
    name = re.sub(r"[^\w\s-]", "", name).strip()
    name = re.sub(r"\s+", "_", name)
    return name[:150] or "book"


def _archive_item_year(meta: dict) -> int | None:
    """Best-effort parse of an Archive.org item's publication year from its
    metadata (the 'date' field is usually an ISO date or a bare year)."""
    raw = meta.get("metadata", {}).get("date") or meta.get("metadata", {}).get("year")
    if not raw:
        return None
    match = re.search(r"(\d{4})", str(raw))
    return int(match.group(1)) if match else None


def _archive_item_is_safely_public_domain(meta: dict) -> bool:
    """Only accept Archive.org items old enough to be conclusively public
    domain by publication date alone. See PUBLIC_DOMAIN_YEAR_CUTOFF for why
    this check exists independently of the access-restricted-item flag and
    the Google Books confirmation gate.
    """
    year = _archive_item_year(meta)
    return year is not None and year <= PUBLIC_DOMAIN_YEAR_CUTOFF


_FILE_SIGNATURES = {
    "pdf": b"%PDF",
    "epub": b"PK\x03\x04",
}


def _has_valid_signature(filepath: str, fmt: str) -> bool:
    """Check the magic bytes match the expected format.

    Google Books occasionally serves an HTML CAPTCHA/interstitial page
    instead of the file when it rate-limits automated requests; this catches
    that (and any other non-file response) before treating the download as
    a success.
    """
    signature = _FILE_SIGNATURES.get(fmt)
    if not signature:
        return True
    try:
        with open(filepath, "rb") as f:
            return f.read(len(signature)) == signature
    except OSError:
        return False


async def _stream_download(url: str, filepath: str, headers: dict | None = None) -> int:
    """Stream a URL to disk, returning the number of bytes written."""
    total = 0
    async with httpx.AsyncClient(follow_redirects=True, timeout=120.0, headers=headers) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            with open(filepath, "wb") as f:
                async for chunk in response.aiter_bytes():
                    f.write(chunk)
                    total += len(chunk)
    return total


async def _search_google_books_volumes(query: str, author: str | None = None) -> dict:
    """Run a Google Books title (optionally + author) search and return the raw response JSON."""
    q = f"intitle:{query}"
    if author:
        q += f"+inauthor:{author}"

    params = {
        "q": q,
        "printType": "books",
        "maxResults": 10,
        "key": GOOGLE_API_KEY,
    }

    async with await get_api_client() as client:
        response = await client.get("/volumes", params=params)
        response.raise_for_status()
        return response.json()


def _is_confirmed_public_domain(volumes_data: dict) -> bool:
    """True if Google Books' own classification marks at least one matching
    volume as public domain.

    This is used to gate the Internet Archive fallback: Archive.org's search
    index mixes legitimate public-domain scans with unmoderated uploads of
    in-copyright books (its "not access-restricted" flag is not a reliable
    signal on its own - it does not catch these). Google's publicDomain
    classification is a real, jurisdiction-aware legal determination, so
    only titles it already confirms are public domain are allowed to fall
    back to an Archive.org download.
    """
    return any(
        item.get("accessInfo", {}).get("publicDomain")
        for item in volumes_data.get("items", [])
    )


async def _download_from_google_books(volumes_data: dict, output_dir: str) -> str | None:
    """Try to download a book directly via Google Books' own public-domain
    PDF/EPUB download link. Only ever returns a link when Google Books marks
    the volume as accessInfo.publicDomain == true, so this can't be used to
    pull full text of in-copyright, preview-only books.
    """
    for item in volumes_data.get("items", []):
        access = item.get("accessInfo", {})
        if not access.get("publicDomain"):
            continue

        for fmt in ("pdf", "epub"):
            fmt_info = access.get(fmt, {})
            download_link = fmt_info.get("downloadLink")
            if not (fmt_info.get("isAvailable") and download_link):
                continue

            title = item["volumeInfo"].get("title", "book")
            filepath = os.path.join(output_dir, f"{_sanitize_filename(title)}.{fmt}")

            try:
                size = await _stream_download(
                    download_link, filepath, headers={"User-Agent": DOWNLOAD_USER_AGENT}
                )
            except httpx.HTTPError:
                if os.path.exists(filepath):
                    os.remove(filepath)
                continue

            if not _has_valid_signature(filepath, fmt):
                # Google served an HTML interstitial/CAPTCHA instead of the
                # file (happens under rate limiting) - don't report success.
                os.remove(filepath)
                continue

            return (
                f"Downloaded '{title}' from Google Books ({fmt.upper()}, public domain) "
                f"to {filepath} ({size:,} bytes)"
            )

    return None


async def _download_all_from_google_books(volumes_data: dict, output_dir: str) -> list[str]:
    """Like _download_from_google_books, but downloads every distinct
    public-domain volume in the search results instead of stopping at the
    first one - used for multi-volume/multi-tome works.
    """
    results = []
    seen_ids = set()

    for item in volumes_data.get("items", []):
        access = item.get("accessInfo", {})
        if not access.get("publicDomain"):
            continue

        volume_id = item.get("id")
        if not volume_id or volume_id in seen_ids:
            continue

        for fmt in ("pdf", "epub"):
            fmt_info = access.get(fmt, {})
            download_link = fmt_info.get("downloadLink")
            if not (fmt_info.get("isAvailable") and download_link):
                continue

            title = item["volumeInfo"].get("title", "book")
            filepath = os.path.join(output_dir, f"{_sanitize_filename(title)}_{volume_id}.{fmt}")

            try:
                size = await _stream_download(
                    download_link, filepath, headers={"User-Agent": DOWNLOAD_USER_AGENT}
                )
            except httpx.HTTPError:
                if os.path.exists(filepath):
                    os.remove(filepath)
                continue

            if not _has_valid_signature(filepath, fmt):
                os.remove(filepath)
                continue

            results.append(
                f"Downloaded '{title}' from Google Books ({fmt.upper()}, public domain) "
                f"to {filepath} ({size:,} bytes)"
            )
            seen_ids.add(volume_id)
            break

    return results


async def _download_from_archive_org(query: str, output_dir: str, author: str | None = None) -> str | None:
    """Fall back to the Internet Archive's full-text scans when Google Books
    itself has no public-domain download available for the title.

    Classical/scholastic titles are often reused by multiple different
    authors (e.g. "Cursus Theologicus" was used by John of St. Thomas,
    Billuart, Tournely, and others) - passing `author` narrows the search to
    that creator so the wrong author's book isn't downloaded instead.
    """
    search_query = f"title:({query})"
    if author:
        search_query += f" AND creator:({author})"
    search_query += " AND mediatype:texts"

    search_params = {
        "q": search_query,
        "fl[]": ["identifier", "title"],
        "rows": 10,
        "output": "json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        search_response = await client.get(
            f"{ARCHIVE_ORG_BASE_URL}/advancedsearch.php", params=search_params
        )
        search_response.raise_for_status()
        docs = search_response.json().get("response", {}).get("docs", [])

        for doc in docs:
            identifier = doc.get("identifier")
            if not identifier:
                continue

            meta_response = await client.get(f"{ARCHIVE_ORG_BASE_URL}/metadata/{identifier}")
            meta_response.raise_for_status()
            meta = meta_response.json()

            # Lending-library items require a borrower session and can't be
            # downloaded directly; only freely downloadable items qualify.
            if str(meta.get("metadata", {}).get("access-restricted-item", "false")).lower() == "true":
                continue

            if not _archive_item_is_safely_public_domain(meta):
                continue

            pdf_file = next(
                (
                    f for f in meta.get("files", [])
                    if f["name"].lower().endswith(".pdf")
                    and "_text" not in f["name"]
                    and "ocr" not in f["name"].lower()
                ),
                None,
            )
            if not pdf_file:
                continue

            download_url = f"{ARCHIVE_ORG_BASE_URL}/download/{identifier}/{quote(pdf_file['name'])}"
            title = doc.get("title", identifier)
            filepath = os.path.join(output_dir, f"{_sanitize_filename(title)}.pdf")

            try:
                size = await _stream_download(download_url, filepath)
            except httpx.HTTPError:
                if os.path.exists(filepath):
                    os.remove(filepath)
                continue

            if not _has_valid_signature(filepath, "pdf"):
                os.remove(filepath)
                continue

            return (
                f"Downloaded '{title}' from the Internet Archive to "
                f"{filepath} ({size:,} bytes)"
            )

    return None


async def _download_all_from_archive_org(query: str, output_dir: str, author: str | None = None) -> list[str]:
    """Like _download_from_archive_org, but downloads every qualifying
    full-scan PDF across every matching, non-restricted item instead of
    stopping at the first one. A single Internet Archive item can legitimately
    bundle several distinct volume/tome files (e.g. one item per multi-tome
    classical work, with one file per tome), which the single-file version
    can't reach beyond the first file it finds.
    """
    search_query = f"title:({query})"
    if author:
        search_query += f" AND creator:({author})"
    search_query += " AND mediatype:texts"

    search_params = {
        "q": search_query,
        "fl[]": ["identifier", "title"],
        "rows": 10,
        "output": "json",
    }

    results = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        search_response = await client.get(
            f"{ARCHIVE_ORG_BASE_URL}/advancedsearch.php", params=search_params
        )
        search_response.raise_for_status()
        docs = search_response.json().get("response", {}).get("docs", [])

        for doc in docs:
            identifier = doc.get("identifier")
            if not identifier:
                continue

            meta_response = await client.get(f"{ARCHIVE_ORG_BASE_URL}/metadata/{identifier}")
            meta_response.raise_for_status()
            meta = meta_response.json()

            if str(meta.get("metadata", {}).get("access-restricted-item", "false")).lower() == "true":
                continue

            if not _archive_item_is_safely_public_domain(meta):
                continue

            pdf_files = [
                f for f in meta.get("files", [])
                if f["name"].lower().endswith(".pdf")
                and "_text" not in f["name"]
                and "ocr" not in f["name"].lower()
            ]

            for pdf_file in pdf_files:
                download_url = f"{ARCHIVE_ORG_BASE_URL}/download/{identifier}/{quote(pdf_file['name'])}"
                stem = os.path.splitext(pdf_file["name"])[0]
                filepath = os.path.join(output_dir, f"{_sanitize_filename(stem)}.pdf")

                try:
                    size = await _stream_download(download_url, filepath)
                except httpx.HTTPError:
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    continue

                if not _has_valid_signature(filepath, "pdf"):
                    os.remove(filepath)
                    continue

                results.append(
                    f"Downloaded '{pdf_file['name']}' from the Internet Archive "
                    f"(item: {identifier}) to {filepath} ({size:,} bytes)"
                )

    return results


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


@mcp.tool()
async def download_book(query: str, author: str = "", output_dir: str = ".", all_volumes: bool = False):
    """Downloads a public-domain book by title and saves it to disk.

    Only works for books that are legitimately freely downloadable: it first
    tries Google Books' own official download link (available only when
    Google marks the volume as public domain), then - only if Google Books
    itself confirms some matching edition of the title is public domain -
    falls back to a matching full-text scan on the Internet Archive. It will
    not fetch in-copyright books that are only available in snippet/preview
    view, and it will not fall back to the Internet Archive for titles
    Google Books does not confirm as public domain (Archive.org hosts some
    unauthorized uploads of in-copyright books alongside legitimate public
    domain scans, so that confirmation is required first).

    Passing `author` is strongly recommended for classical/scholastic
    titles, since many were reused by multiple authors (e.g. "Cursus
    Theologicus" was written by several different theologians) - without it,
    the Internet Archive fallback can only match on title text and may
    return the wrong author's book.

    Set `all_volumes=True` for multi-volume/multi-tome works to download
    every distinct public-domain volume found (across both Google Books and
    the Internet Archive) instead of stopping at the first match found.

    Args:
        query: Title of the book to search for and download (required)
        author: Author name, to disambiguate titles reused by multiple authors (optional)
        output_dir: Directory to save the downloaded file into (default: current directory)
        all_volumes: Download every distinct volume/tome found instead of just the first (default: False)
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
        author = author or None

        volumes_data = await _search_google_books_volumes(query, author)

        if all_volumes:
            results = await _download_all_from_google_books(volumes_data, output_dir)

            if _is_confirmed_public_domain(volumes_data):
                results += await _download_all_from_archive_org(query, output_dir, author)

            if not results:
                return (
                    f"No public-domain downloads found for '{query}' via Google Books or "
                    "the Internet Archive. The book may still be under copyright, or "
                    "only available in limited preview."
                )

            return f"Downloaded {len(results)} file(s):\n\n" + "\n".join(results)

        result = await _download_from_google_books(volumes_data, output_dir)
        if result:
            return result

        if _is_confirmed_public_domain(volumes_data):
            result = await _download_from_archive_org(query, output_dir, author)
            if result:
                return result

        return (
            f"No public-domain download found for '{query}' via Google Books or "
            "the Internet Archive. The book may still be under copyright, or "
            "only available in limited preview."
        )

    except httpx.HTTPError as e:
        return f"Error communicating with Google Books API or Internet Archive: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')