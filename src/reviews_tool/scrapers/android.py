"""Google Play Store scraper implementation using google-play-scraper library."""

import time
from datetime import datetime
from typing import Optional, Dict, Any

from google_play_scraper import app as gps_app
from google_play_scraper import reviews as gps_reviews
from google_play_scraper import Sort

from ..models import Review, DeveloperResponse, ReviewsResponse
from ..utils import validate_app_id, parse_date_flexible


class AndroidScraper:
    """Scraper for Google Play Store reviews using google-play-scraper library."""

    def __init__(self) -> None:
        """Initialize the Android scraper."""
        self.last_request_time: float = 0
        self.request_delay: int = 1  # Reduced delay since library handles rate limiting

    def _rate_limit(self) -> None:
        """Implement basic rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.request_delay:
            time.sleep(self.request_delay - time_since_last)

        self.last_request_time = time.time()

    def _convert_review_to_model(
        self,
        gps_review: Dict[str, Any],
        language: Optional[str] = None,
        country: Optional[str] = None,
    ) -> Review:
        """
        Convert google-play-scraper review to our Review model.

        Args:
            gps_review: Review dictionary from google-play-scraper
            language: Language code to set
            country: Country code to set

        Returns:
            Review object
        """
        # Extract developer response if exists
        developer_response = None
        if gps_review.get("replyContent"):
            dev_date = gps_review.get("repliedAt", datetime.now())
            if isinstance(dev_date, str):
                dev_date = parse_date_flexible(dev_date) or datetime.now()

            developer_response = DeveloperResponse(
                text=gps_review["replyContent"], date=dev_date
            )

        # Convert date
        review_date = gps_review.get("at", datetime.now())
        if isinstance(review_date, str):
            review_date = parse_date_flexible(review_date) or datetime.now()

        return Review(
            id=gps_review.get(
                "reviewId",
                f"android_{hash(gps_review.get('userName', ''))}_{int(time.time())}",
            ),
            user_name=gps_review.get("userName", "Unknown"),
            rating=int(gps_review.get("score", 5)),
            title=None,  # Google Play doesn't have review titles
            text=gps_review.get("content", ""),
            date=review_date,
            helpful_count=gps_review.get("thumbsUpCount"),
            language=language,
            country=country,
            version=gps_review.get("appVersion"),
            developer_response=developer_response,
        )

    def _get_app_info(
        self, app_id: str, language: str = "en", country: str = "us"
    ) -> Dict[str, Any]:
        """
        Get app information using google-play-scraper.

        Args:
            app_id: Application package name
            language: Language code
            country: Country code

        Returns:
            App information dictionary
        """
        try:
            self._rate_limit()
            app_info = gps_app(app_id, lang=language, country=country)
            return {
                "name": app_info.get("title"),
                "developer": app_info.get("developer"),
                "rating": app_info.get("score"),
                "total_ratings": app_info.get("reviews"),
                "installs": app_info.get("installs"),
            }
        except Exception as e:
            print(f"Error getting app info: {e}")
            return {}

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
        Search and extract reviews for an Android app using google-play-scraper.

        Args:
            app_id: Application package name (e.g., 'com.whatsapp')
            limit: Maximum number of reviews to fetch
            rating: Filter by rating (1-5)
            language: Language code (ISO 639-1)
            country: Country code (ISO 3166-1)
            has_dev_response: Filter reviews with/without developer response
            date_from: Start date for review filtering
            date_to: End date for review filtering
            page_token: Token for pagination (used internally by google-play-scraper)

        Returns:
            ReviewsResponse object with results
        """
        # Validate app ID
        if not validate_app_id(app_id, "android"):
            raise ValueError(f"Invalid Android app ID format: {app_id}")

        # Prepare parameters for google-play-scraper
        lang = language.lower() if language else "en"
        country_code = country.lower() if country else "us"

        # Prepare filters for our response
        filters: Dict[str, Any] = {}
        if language:
            filters["language"] = language.lower()
        if country:
            filters["country"] = country.upper()
        if rating:
            filters["rating"] = rating

        try:
            # Get app information
            app_info = self._get_app_info(app_id, lang, country_code)

            # Fetch reviews using google-play-scraper
            self._rate_limit()

            # Get more reviews than needed to allow for filtering
            fetch_count = min(limit * 3, 500)  # Fetch up to 3x the limit or 500 max

            raw_reviews, next_token = gps_reviews(
                app_id,
                lang=lang,
                country=country_code,
                sort=Sort.NEWEST,  # Default to newest first
                count=fetch_count,
                continuation_token=page_token,
            )

            # Convert and filter reviews
            filtered_reviews = []

            for raw_review in raw_reviews:
                review = self._convert_review_to_model(raw_review, language, country)

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

            return ReviewsResponse(
                app_id=app_id,
                app_name=app_info.get("name"),
                store="android",
                total_reviews=len(raw_reviews),
                reviews=filtered_reviews[:limit],
                next_page_token=(
                    str(next_token)
                    if next_token and len(filtered_reviews) >= limit
                    else None
                ),
                filters_applied=filters,
                timestamp=datetime.now(),
            )

        except Exception as e:
            print(f"Error fetching reviews: {e}")
            return ReviewsResponse(
                app_id=app_id,
                app_name=None,
                store="android",
                total_reviews=None,
                reviews=[],
                next_page_token=None,
                filters_applied=filters,
                timestamp=datetime.now(),
            )
