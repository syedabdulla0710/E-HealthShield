"""
Symmetric Searchable Encryption (SSE)
======================================
Allows keyword search over encrypted EHR files without decryption.

Workflow:
    Upload  -> extract_keywords(file) -> generate_tags(sse_key, keywords) -> store tags
    Search  -> generate_trapdoor(sse_key, keyword) -> match_trapdoor(trapdoor, tags)

All tags and trapdoors are HMAC-SHA256(sse_key, keyword), so a match
proves the keyword exists without revealing file contents.
"""

import hmac
import hashlib
import os
import re


# -- Key Management -----------------------------------------------------------

def generate_sse_key() -> bytes:
    """
    Generate a 32-byte SSE master key.

    In this prototype a single global key is used for all users.
    Store this in the backend .env file (base64-encoded).

    Returns:
        32 cryptographically-secure random bytes.
    """
    return os.urandom(32)


# -- Keyword Extraction -------------------------------------------------------

# Common English stop-words to skip (keeps tags meaningful)
_STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "is", "are", "was", "were",
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "as",
    "it", "its", "be", "been", "being", "have", "has", "had", "do",
    "does", "did", "will", "would", "shall", "should", "may", "might",
    "can", "could", "not", "no", "nor", "so", "if", "then", "than",
    "that", "this", "these", "those", "he", "she", "they", "we", "you",
    "i", "me", "my", "his", "her", "our", "your", "their", "up", "out",
    "about", "into", "over", "after", "before", "between", "under",
    "again", "each", "all", "any", "both", "few", "more", "most",
    "other", "some", "such", "only", "own", "same", "too", "very",
})

# Minimum keyword length to keep
_MIN_KEYWORD_LENGTH = 3


def extract_keywords(file_bytes: bytes, filename: str) -> list[str]:
    """
    Auto-extract meaningful keywords from a file.

    Supported formats:
        .txt, .csv  -- decoded as UTF-8 text
        .pdf        -- basic text extraction (requires PyPDF2, optional)

    Falls back to filename-based keywords if content parsing fails.

    Args:
        file_bytes: Raw bytes of the uploaded file.
        filename:   Original filename (used for extension detection + fallback).

    Returns:
        Sorted, deduplicated list of lowercase keyword strings.
    """
    text = ""
    ext = _get_extension(filename)

    if ext in (".txt", ".csv", ".json", ".xml", ".html"):
        text = _decode_text(file_bytes)
    elif ext == ".pdf":
        text = _extract_pdf_text(file_bytes)
    else:
        # Fallback: try decoding as text anyway
        text = _decode_text(file_bytes)

    # Always include keywords derived from the filename
    name_part = filename.rsplit(".", 1)[0] if "." in filename else filename
    text += " " + name_part

    keywords = _tokenize(text)
    return keywords


def _get_extension(filename: str) -> str:
    """Return the lowercase file extension including the dot."""
    if "." in filename:
        return "." + filename.rsplit(".", 1)[1].lower()
    return ""


def _decode_text(data: bytes) -> str:
    """Best-effort UTF-8 decode."""
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _extract_pdf_text(data: bytes) -> str:
    """
    Extract text from a PDF file.

    Uses PyPDF2 if available; otherwise returns empty string
    (the filename will still contribute keywords).
    """
    try:
        import io
        from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(data))
        pages_text = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                pages_text.append(page_text)
        return " ".join(pages_text)
    except ImportError:
        # PyPDF2 not installed -- degrade gracefully
        return ""
    except Exception:
        return ""


def _tokenize(text: str) -> list[str]:
    """
    Tokenize text into a clean, sorted list of unique keywords.

    * Lowercased
    * Punctuation stripped
    * Stop-words removed
    * Short tokens (< 3 chars) removed
    """
    # Replace non-alphanumeric chars with spaces
    cleaned = re.sub(r"[^a-zA-Z0-9]", " ", text.lower())
    tokens = cleaned.split()

    unique = sorted({
        t for t in tokens
        if len(t) >= _MIN_KEYWORD_LENGTH and t not in _STOP_WORDS
    })
    return unique


# -- Tag Generation -----------------------------------------------------------

def generate_tags(sse_key: bytes, keywords: list[str]) -> list[str]:
    """
    Generate SSE tags for a list of keywords.

    Each tag = HMAC-SHA256(sse_key, keyword).hex()

    Args:
        sse_key:  32-byte SSE master key.
        keywords: List of lowercase keyword strings.

    Returns:
        List of hex-encoded tag strings (same order as keywords).
    """
    return [
        hmac.new(sse_key, kw.encode("utf-8"), hashlib.sha256).hexdigest()
        for kw in keywords
    ]


# -- Trapdoor & Matching -----------------------------------------------------

def generate_trapdoor(sse_key: bytes, keyword: str) -> str:
    """
    Generate a search trapdoor for a single keyword.

    The trapdoor is identical to a tag: HMAC-SHA256(sse_key, keyword).
    This is by design -- a match proves the keyword exists.

    Args:
        sse_key: 32-byte SSE master key.
        keyword: The search term (will be lowercased).

    Returns:
        Hex-encoded trapdoor string.
    """
    return hmac.new(
        sse_key, keyword.lower().encode("utf-8"), hashlib.sha256
    ).hexdigest()


def match_trapdoor(trapdoor: str, tags: list[str]) -> bool:
    """
    Check whether a trapdoor matches any tag in the list.

    Uses constant-time comparison (hmac.compare_digest) to prevent
    timing side-channel attacks.

    Args:
        trapdoor: Hex-encoded trapdoor from generate_trapdoor().
        tags:     List of hex-encoded SSE tags from generate_tags().

    Returns:
        True if the trapdoor matches at least one tag.
    """
    for tag in tags:
        if hmac.compare_digest(trapdoor, tag):
            return True
    return False
