"""Common utilities for the reviews tool."""

import re
import time
import random
from datetime import datetime
from typing import Optional, Dict, Any
from urllib.parse import urlparse


# User agents for web scraping to avoid bot detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def get_random_user_agent() -> str:
    """Get a random user agent string to avoid bot detection."""
    return random.choice(USER_AGENTS)


def validate_app_id(app_id: str, store: str) -> bool:
    """
    Validate app ID format for the specified store.

    Args:
        app_id: The application identifier
        store: Store type ('android' or 'ios')

    Returns:
        True if the app ID format is valid
    """
    if store == "android":
        # Android package names: com.company.app
        return bool(
            re.match(r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)+$", app_id)
        )
    elif store == "ios":
        # iOS app IDs can be numeric or bundle IDs
        if app_id.isdigit() and len(app_id) >= 8:
            return True
        # Also accept bundle ID format like com.company.app
        return bool(
            re.match(r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)+$", app_id)
        )
    return False


def validate_language_code(lang_code: str) -> bool:
    """
    Validate ISO 639-1 language code format.

    Args:
        lang_code: Two-letter language code

    Returns:
        True if the format is valid
    """
    return bool(re.match(r"^[a-z]{2}$", lang_code.lower()))


def validate_country_code(country_code: str) -> bool:
    """
    Validate ISO 3166-1 alpha-2 country code format.

    Args:
        country_code: Two-letter country code

    Returns:
        True if the format is valid
    """
    return bool(re.match(r"^[A-Z]{2}$", country_code.upper()))


def parse_date_flexible(date_str: str) -> Optional[datetime]:
    """
    Parse date strings from various formats used by app stores.

    Args:
        date_str: Date string in various formats

    Returns:
        Parsed datetime object or None if parsing fails
    """
    # Common date formats used by app stores
    formats = [
        "%Y-%m-%d",  # 2023-12-01
        "%Y-%m-%dT%H:%M:%S",  # 2023-12-01T10:30:00
        "%Y-%m-%dT%H:%M:%SZ",  # 2023-12-01T10:30:00Z
        "%Y-%m-%dT%H:%M:%S.%fZ",  # 2023-12-01T10:30:00.123Z
        "%B %d, %Y",  # December 1, 2023
        "%d/%m/%Y",  # 01/12/2023
        "%m/%d/%Y",  # 12/01/2023
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue

    return None


def exponential_backoff(
    attempt: int, base_delay: float = 1.0, max_delay: float = 60.0
) -> None:
    """
    Implement exponential backoff for rate limiting.

    Args:
        attempt: Current attempt number (0-based)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
    """
    delay = min(base_delay * (2**attempt) + random.uniform(0, 1), max_delay)
    time.sleep(delay)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a string to be safe for use as a filename.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip(". ")
    # Limit length
    return sanitized[:255] if len(sanitized) > 255 else sanitized


def build_request_headers(referer: Optional[str] = None) -> Dict[str, str]:
    """
    Build HTTP headers for requests to avoid bot detection.

    Args:
        referer: Optional referer URL

    Returns:
        Dictionary of HTTP headers
    """
    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    if referer:
        headers["Referer"] = referer

    return headers


def extract_domain(url: str) -> Optional[str]:
    """
    Extract domain from URL.

    Args:
        url: Full URL

    Returns:
        Domain name or None if invalid
    """
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except Exception:
        return None


def clean_text(text: str) -> str:
    """
    Clean and normalize text content.

    Args:
        text: Raw text content

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text.strip())

    # Remove common HTML entities if they slipped through
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")

    return text.strip()


def format_json_output(data: Any, indent: int = 2) -> str:
    """
    Format data as JSON with proper indentation.

    Args:
        data: Data to serialize
        indent: Number of spaces for indentation

    Returns:
        Formatted JSON string
    """
    import json
    from datetime import datetime

    def json_serializer(obj: Any) -> str:
        """JSON serializer for objects not serializable by default json code."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    return json.dumps(data, indent=indent, default=json_serializer, ensure_ascii=False)
