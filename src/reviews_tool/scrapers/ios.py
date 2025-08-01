"""App Store (iOS) scraper implementation using iTunes Search API and web scraping."""

import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from ..models import Review, ReviewsResponse
from ..utils import (
    validate_app_id,
    parse_date_flexible,
    build_request_headers,
    exponential_backoff,
    clean_text,
)


class IOSScraper:
    """Scraper for App Store reviews using iTunes Search API and web scraping."""

    def __init__(self) -> None:
        """Initialize the iOS scraper."""
        self.last_request_time: float = 0
        self.request_delay: int = 2  # More conservative delay for App Store
        self.session = requests.Session()

        # iTunes Search API base URL
        self.itunes_api_base = "https://itunes.apple.com/search"
        self.app_lookup_base = "https://itunes.apple.com/lookup"

        # Customer reviews RSS feed pattern
        self.reviews_rss_pattern = "https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/xml"

        # App Store web page pattern for additional scraping
        self.app_store_pattern = "https://apps.apple.com/{country}/app/id{app_id}"

    def _rate_limit(self) -> None:
        """Implement rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.request_delay:
            time.sleep(self.request_delay - time_since_last)

        self.last_request_time = time.time()

    def _make_request(
        self, url: str, headers: Optional[Dict[str, str]] = None, retries: int = 3
    ) -> Optional[requests.Response]:
        """
        Make HTTP request with error handling and retries.

        Args:
            url: URL to request
            headers: Optional HTTP headers
            retries: Number of retries on failure

        Returns:
            Response object or None if failed
        """
        if headers is None:
            headers = build_request_headers()

        for attempt in range(retries):
            try:
                self._rate_limit()
                response = self.session.get(url, headers=headers, timeout=30)

                if response.status_code == 200:
                    return response
                elif response.status_code == 429:  # Rate limited
                    exponential_backoff(attempt, base_delay=5.0)
                    continue
                else:
                    print(f"HTTP {response.status_code} for {url}")

            except requests.RequestException as e:
                print(f"Request error (attempt {attempt + 1}): {e}")
                if attempt < retries - 1:
                    exponential_backoff(attempt)

        return None

    def _get_app_info_by_id(self, app_id: str, country: str = "us") -> Dict[str, Any]:
        """
        Get app information by app ID using iTunes API.

        Args:
            app_id: Numeric app ID
            country: Country code

        Returns:
            App information dictionary
        """
        url = f"{self.app_lookup_base}?id={app_id}&country={country}"
        response = self._make_request(url)

        if not response:
            return {}

        try:
            data = response.json()
            if data.get("results"):
                app = data["results"][0]
                return {
                    "name": app.get("trackName"),
                    "developer": app.get("artistName"),
                    "rating": app.get("averageUserRating"),
                    "total_ratings": app.get("userRatingCount"),
                    "version": app.get("version"),
                    "bundle_id": app.get("bundleId"),
                    "release_date": app.get("releaseDate"),
                    "description": app.get("description"),
                }
        except Exception as e:
            print(f"Error parsing app info: {e}")

        return {}

    def _search_app_by_bundle_id(
        self, bundle_id: str, country: str = "us"
    ) -> Optional[str]:
        """
        Search for app ID using bundle identifier.

        Args:
            bundle_id: App bundle identifier (e.g., com.whatsapp.WhatsApp)
            country: Country code

        Returns:
            Numeric app ID or None if not found
        """
        url = f"{self.itunes_api_base}?term={quote(bundle_id)}&country={country}&entity=software&limit=50"
        response = self._make_request(url)

        if not response:
            return None

        try:
            data = response.json()
            for result in data.get("results", []):
                if result.get("bundleId") == bundle_id:
                    return str(result.get("trackId"))
        except Exception as e:
            print(f"Error searching for app: {e}")

        return None

    def _parse_rss_reviews(
        self,
        rss_content: str,
        language: Optional[str] = None,
        country: Optional[str] = None,
    ) -> List[Review]:
        """
        Parse reviews from iTunes RSS feed.

        Args:
            rss_content: RSS XML content
            language: Language code to set
            country: Country code to set

        Returns:
            List of Review objects
        """
        reviews = []

        try:
            soup = BeautifulSoup(rss_content, "xml")
            entries = soup.find_all("entry")

            for entry in entries:
                # Skip the first entry which is usually app info
                if entry.find("im:name"):
                    continue

                try:
                    # Extract review data
                    title_elem = entry.find("title")
                    title = clean_text(title_elem.text) if title_elem else ""

                    content_elem = entry.find("content")
                    text = clean_text(content_elem.text) if content_elem else ""

                    # Rating from im:rating
                    rating_elem = entry.find("im:rating")
                    rating = int(rating_elem.text) if rating_elem else 5

                    # Author
                    author_elem = entry.find("author")
                    if author_elem:
                        name_elem = author_elem.find("name")
                        user_name = (
                            clean_text(name_elem.text) if name_elem else "Anonymous"
                        )
                    else:
                        user_name = "Anonymous"

                    # Date
                    updated_elem = entry.find("updated")
                    if updated_elem:
                        date = parse_date_flexible(updated_elem.text) or datetime.now()
                    else:
                        date = datetime.now()

                    # Version from im:version
                    version_elem = entry.find("im:version")
                    version = clean_text(version_elem.text) if version_elem else None

                    # Create review ID
                    review_id = f"ios_{hash(user_name + title + str(date.timestamp()))}_{int(time.time())}"

                    review = Review(
                        id=review_id,
                        user_name=user_name,
                        rating=rating,
                        title=title if title else None,
                        text=text,
                        date=date,
                        helpful_count=None,  # Not available in RSS feed
                        language=language,
                        country=country,
                        version=version,
                        developer_response=None,  # Would need additional scraping
                    )

                    reviews.append(review)

                except Exception as e:
                    print(f"Error parsing review entry: {e}")
                    continue

        except Exception as e:
            print(f"Error parsing RSS feed: {e}")

        return reviews

    def _get_reviews_from_rss(
        self, app_id: str, country: str = "us", page: int = 1
    ) -> List[Review]:
        """
        Get reviews from iTunes RSS feed.

        Args:
            app_id: Numeric app ID
            country: Country code
            page: Page number (1-10, RSS limit)

        Returns:
            List of Review objects
        """
        url = self.reviews_rss_pattern.format(
            country=country.lower(), page=page, app_id=app_id
        )

        response = self._make_request(url)
        if not response:
            return []

        return self._parse_rss_reviews(response.text, country=country.upper())

    def search_reviews(
        self,
        app_id: str,
        limit: int = 50,
        rating: Optional[int] = None,
        language: Optional[str] = None,
        country: Optional[str] = None,
        has_dev_response: Optional[bool] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page_token: Optional[str] = None,
    ) -> ReviewsResponse:
        """
        Search and extract reviews for an iOS app.

        Args:
            app_id: Application ID (numeric) or bundle ID (com.company.app)
            limit: Maximum number of reviews to fetch
            rating: Filter by rating (1-5)
            language: Language code (ISO 639-1) - affects country selection
            country: Country code (ISO 3166-1)
            has_dev_response: Filter reviews with/without developer response
            date_from: Start date for review filtering
            date_to: End date for review filtering
            page_token: Token for pagination (page number as string)

        Returns:
            ReviewsResponse object with results
        """
        # Default country
        country_code = (country or "us").lower()

        # Determine if app_id is numeric or bundle ID
        numeric_app_id: str
        if app_id.isdigit():
            numeric_app_id = app_id
        else:
            # Validate bundle ID format
            if not validate_app_id(app_id, "ios"):
                # Try to search by bundle ID
                found_app_id = self._search_app_by_bundle_id(app_id, country_code)
                if not found_app_id:
                    raise ValueError(
                        f"Invalid iOS app ID format or app not found: {app_id}"
                    )
                numeric_app_id = found_app_id
            else:
                # This is already validated as a numeric ID
                numeric_app_id = app_id

        # Prepare filters for response
        filters = {}
        if language:
            filters["language"] = language.lower()
        if country:
            filters["country"] = country.upper()
        if rating:
            filters["rating"] = rating

        try:
            # Get app information
            app_info = self._get_app_info_by_id(numeric_app_id, country_code)

            # Determine starting page
            current_page = 1
            if page_token:
                try:
                    current_page = int(page_token)
                except ValueError:
                    current_page = 1

            # Collect reviews from multiple pages
            all_reviews = []
            max_pages = min(
                10, (limit // 50) + 2
            )  # RSS has max 10 pages, ~50 reviews per page

            for page in range(current_page, current_page + max_pages):
                page_reviews = self._get_reviews_from_rss(
                    numeric_app_id, country_code, page
                )

                if not page_reviews:
                    break  # No more reviews

                all_reviews.extend(page_reviews)

                # Stop if we have enough reviews
                if len(all_reviews) >= limit * 2:  # Get extra for filtering
                    break

            # Apply filters
            filtered_reviews = []

            for review in all_reviews:
                # Apply rating filter
                if rating and review.rating != rating:
                    continue

                # Apply date filters
                if date_from and review.date < date_from:
                    continue
                if date_to and review.date > date_to:
                    continue

                # Apply developer response filter
                if has_dev_response is not None:
                    has_response = review.developer_response is not None
                    if has_dev_response != has_response:
                        continue

                filtered_reviews.append(review)

                # Stop when we have enough reviews
                if len(filtered_reviews) >= limit:
                    break

            # Determine next page token
            next_token = None
            if len(filtered_reviews) >= limit and current_page < 10:
                next_token = str(current_page + max_pages)

            return ReviewsResponse(
                app_id=app_id,
                app_name=app_info.get("name"),
                store="ios",
                total_reviews=len(all_reviews),
                reviews=filtered_reviews[:limit],
                next_page_token=next_token,
                filters_applied=filters,
                timestamp=datetime.now(),
            )

        except Exception as e:
            print(f"Error fetching iOS reviews: {e}")
            return ReviewsResponse(
                app_id=app_id,
                app_name=None,
                store="ios",
                total_reviews=None,
                reviews=[],
                next_page_token=None,
                filters_applied=filters,
                timestamp=datetime.now(),
            )
