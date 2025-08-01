"""Unit tests for Android scraper."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from google_play_scraper import Sort

from reviews_tool.scrapers.android import AndroidScraper
from reviews_tool.models import Review, DeveloperResponse, ReviewsResponse


class TestAndroidScraper:
    """Test suite for AndroidScraper class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.scraper = AndroidScraper()
        self.sample_app_id = "com.whatsapp"
        
        # Sample raw review data from google-play-scraper
        self.sample_raw_review = {
            "reviewId": "test_review_123",
            "userName": "John Doe",
            "score": 4,
            "content": "Great app! Very useful.",
            "at": datetime(2023, 12, 1, 10, 30),
            "thumbsUpCount": 5,
            "appVersion": "2.23.1",
            "replyContent": "Thank you for your feedback!",
            "repliedAt": datetime(2023, 12, 2, 14, 15)
        }
        
        self.sample_raw_review_no_reply = {
            "reviewId": "test_review_456",
            "userName": "Jane Smith",
            "score": 5,
            "content": "Excellent service",
            "at": datetime(2023, 11, 15, 9, 0),
            "thumbsUpCount": 3,
            "appVersion": "2.22.5"
        }

    def test_init(self):
        """Test scraper initialization."""
        scraper = AndroidScraper()
        assert scraper.last_request_time == 0
        assert scraper.request_delay == 1

    def test_rate_limit(self):
        """Test rate limiting mechanism."""
        import time
        start_time = time.time()
        
        # First call should not delay
        self.scraper._rate_limit()
        first_call_time = time.time() - start_time
        assert first_call_time < 0.1  # Should be almost instant
        
        # Second call should delay
        start_time = time.time()
        self.scraper._rate_limit()
        second_call_time = time.time() - start_time
        assert second_call_time >= self.scraper.request_delay * 0.9  # Allow small margin

    def test_convert_review_to_model_with_developer_response(self):
        """Test converting raw review with developer response to model."""
        review = self.scraper._convert_review_to_model(
            self.sample_raw_review, 
            language="en", 
            country="US"
        )
        
        assert isinstance(review, Review)
        assert review.id == "test_review_123"
        assert review.user_name == "John Doe"
        assert review.rating == 4
        assert review.title is None  # Google Play doesn't have titles
        assert review.text == "Great app! Very useful."
        assert review.date == datetime(2023, 12, 1, 10, 30)
        assert review.helpful_count == 5
        assert review.language == "en"
        assert review.country == "US"
        assert review.version == "2.23.1"
        
        # Check developer response
        assert review.developer_response is not None
        assert isinstance(review.developer_response, DeveloperResponse)
        assert review.developer_response.text == "Thank you for your feedback!"
        assert review.developer_response.date == datetime(2023, 12, 2, 14, 15)

    def test_convert_review_to_model_without_developer_response(self):
        """Test converting raw review without developer response to model."""
        review = self.scraper._convert_review_to_model(
            self.sample_raw_review_no_reply,
            language="es",
            country="ES"
        )
        
        assert isinstance(review, Review)
        assert review.id == "test_review_456"
        assert review.user_name == "Jane Smith"
        assert review.rating == 5
        assert review.text == "Excellent service"
        assert review.date == datetime(2023, 11, 15, 9, 0)
        assert review.helpful_count == 3
        assert review.language == "es"
        assert review.country == "ES"
        assert review.version == "2.22.5"
        assert review.developer_response is None

    def test_convert_review_to_model_missing_fields(self):
        """Test converting raw review with missing fields."""
        minimal_review = {
            "content": "Basic review",
            "score": 3
        }
        
        review = self.scraper._convert_review_to_model(minimal_review)
        
        assert isinstance(review, Review)
        assert review.user_name == "Unknown"
        assert review.rating == 3
        assert review.text == "Basic review"
        assert isinstance(review.date, datetime)
        assert review.helpful_count is None
        assert review.version is None
        assert review.developer_response is None

    @patch('reviews_tool.scrapers.android.gps_app')
    def test_get_app_info_success(self, mock_gps_app):
        """Test successful app info retrieval."""
        mock_app_data = {
            "title": "WhatsApp Messenger",
            "developer": "WhatsApp Inc.",
            "score": 4.5,
            "reviews": 1000000,
            "installs": "5,000,000,000+"
        }
        mock_gps_app.return_value = mock_app_data
        
        app_info = self.scraper._get_app_info("com.whatsapp", "en", "us")
        
        mock_gps_app.assert_called_once_with("com.whatsapp", lang="en", country="us")
        assert app_info["name"] == "WhatsApp Messenger"
        assert app_info["developer"] == "WhatsApp Inc."
        assert app_info["rating"] == 4.5
        assert app_info["total_ratings"] == 1000000
        assert app_info["installs"] == "5,000,000,000+"

    @patch('reviews_tool.scrapers.android.gps_app')
    def test_get_app_info_error(self, mock_gps_app):
        """Test app info retrieval with error."""
        mock_gps_app.side_effect = Exception("Network error")
        
        app_info = self.scraper._get_app_info("invalid.app", "en", "us")
        
        assert app_info == {}

    @patch('reviews_tool.scrapers.android.validate_app_id')
    def test_search_reviews_invalid_app_id(self, mock_validate):
        """Test search with invalid app ID."""
        mock_validate.return_value = False
        
        with pytest.raises(ValueError, match="Invalid Android app ID format"):
            self.scraper.search_reviews("invalid_id")

    @patch('reviews_tool.scrapers.android.gps_reviews')
    @patch('reviews_tool.scrapers.android.validate_app_id')
    @patch.object(AndroidScraper, '_get_app_info')
    def test_search_reviews_success(self, mock_get_app_info, mock_validate, mock_gps_reviews):
        """Test successful review search."""
        # Setup mocks
        mock_validate.return_value = True
        mock_get_app_info.return_value = {
            "name": "WhatsApp Messenger"
        }
        
        mock_gps_reviews.return_value = (
            [self.sample_raw_review, self.sample_raw_review_no_reply],
            "next_token_123"
        )
        
        # Execute search
        result = self.scraper.search_reviews(
            app_id="com.whatsapp",
            limit=2,
            language="en",
            country="US"
        )
        
        # Verify result
        assert isinstance(result, ReviewsResponse)
        assert result.app_id == "com.whatsapp"
        assert result.app_name == "WhatsApp Messenger"
        assert result.store == "android"
        assert result.total_reviews == 2
        assert len(result.reviews) == 2
        assert result.next_page_token == "next_token_123"
        assert result.filters_applied == {"language": "en", "country": "US"}
        
        # Verify google-play-scraper was called correctly
        mock_gps_reviews.assert_called_once_with(
            "com.whatsapp",
            lang="en",
            country="us",
            sort=Sort.NEWEST,
            count=6,  # limit * 3
            continuation_token=None
        )

    @patch('reviews_tool.scrapers.android.gps_reviews')
    @patch('reviews_tool.scrapers.android.validate_app_id')
    @patch.object(AndroidScraper, '_get_app_info')
    def test_search_reviews_with_rating_filter(self, mock_get_app_info, mock_validate, mock_gps_reviews):
        """Test review search with rating filter."""
        mock_validate.return_value = True
        mock_get_app_info.return_value = {"name": "Test App"}
        
        # Create reviews with different ratings
        review_4_star = dict(self.sample_raw_review, score=4)
        review_5_star = dict(self.sample_raw_review_no_reply, score=5)
        
        mock_gps_reviews.return_value = ([review_4_star, review_5_star], None)
        
        # Search for only 5-star reviews
        result = self.scraper.search_reviews(
            app_id="com.test",
            limit=10,
            rating=5
        )
        
        assert len(result.reviews) == 1
        assert result.reviews[0].rating == 5
        assert result.filters_applied == {"rating": 5}

    @patch('reviews_tool.scrapers.android.gps_reviews')
    @patch('reviews_tool.scrapers.android.validate_app_id')
    @patch.object(AndroidScraper, '_get_app_info')
    def test_search_reviews_with_date_filter(self, mock_get_app_info, mock_validate, mock_gps_reviews):
        """Test review search with date filters."""
        mock_validate.return_value = True
        mock_get_app_info.return_value = {"name": "Test App"}
        
        # Create reviews with different dates
        old_review = dict(self.sample_raw_review, at=datetime(2023, 10, 1))
        new_review = dict(self.sample_raw_review_no_reply, at=datetime(2023, 12, 1))
        
        mock_gps_reviews.return_value = ([old_review, new_review], None)
        
        # Search for reviews after November 1
        result = self.scraper.search_reviews(
            app_id="com.test",
            limit=10,
            date_from=datetime(2023, 11, 1)
        )
        
        assert len(result.reviews) == 1
        assert result.reviews[0].date == datetime(2023, 12, 1)

    @patch('reviews_tool.scrapers.android.gps_reviews')
    @patch('reviews_tool.scrapers.android.validate_app_id')
    @patch.object(AndroidScraper, '_get_app_info')
    def test_search_reviews_with_dev_response_filter(self, mock_get_app_info, mock_validate, mock_gps_reviews):
        """Test review search with developer response filter."""
        mock_validate.return_value = True
        mock_get_app_info.return_value = {"name": "Test App"}
        
        mock_gps_reviews.return_value = (
            [self.sample_raw_review, self.sample_raw_review_no_reply], 
            None
        )
        
        # Search for reviews WITH developer response
        result_with_response = self.scraper.search_reviews(
            app_id="com.test",
            limit=10,
            has_dev_response=True
        )
        
        assert len(result_with_response.reviews) == 1
        assert result_with_response.reviews[0].developer_response is not None
        
        # Search for reviews WITHOUT developer response
        result_without_response = self.scraper.search_reviews(
            app_id="com.test",
            limit=10,
            has_dev_response=False
        )
        
        assert len(result_without_response.reviews) == 1
        assert result_without_response.reviews[0].developer_response is None

    @patch('reviews_tool.scrapers.android.gps_reviews')
    @patch('reviews_tool.scrapers.android.validate_app_id')
    @patch.object(AndroidScraper, '_get_app_info')
    def test_search_reviews_pagination(self, mock_get_app_info, mock_validate, mock_gps_reviews):
        """Test review search with pagination."""
        mock_validate.return_value = True
        mock_get_app_info.return_value = {"name": "Test App"}
        
        mock_gps_reviews.return_value = (
            [self.sample_raw_review, self.sample_raw_review_no_reply], 
            "next_token_456"
        )
        
        result = self.scraper.search_reviews(
            app_id="com.test",
            limit=1,  # Limit to 1 to test pagination
            page_token="existing_token"
        )
        
        assert len(result.reviews) == 1
        assert result.next_page_token == "next_token_456"
        
        # Verify the existing token was passed to gps_reviews
        mock_gps_reviews.assert_called_once_with(
            "com.test",
            lang="en",
            country="us",
            sort=Sort.NEWEST,
            count=3,
            continuation_token="existing_token"
        )

    @patch('reviews_tool.scrapers.android.gps_reviews')
    @patch('reviews_tool.scrapers.android.validate_app_id')
    @patch.object(AndroidScraper, '_get_app_info')
    def test_search_reviews_error_handling(self, mock_get_app_info, mock_validate, mock_gps_reviews):
        """Test review search error handling."""
        mock_validate.return_value = True
        mock_get_app_info.return_value = {"name": "Test App"}
        mock_gps_reviews.side_effect = Exception("Network error")
        
        result = self.scraper.search_reviews("com.test")
        
        assert isinstance(result, ReviewsResponse)
        assert result.app_id == "com.test"
        assert result.store == "android"
        assert result.reviews == []
        assert result.total_reviews is None

    def test_search_reviews_limit_enforcement(self):
        """Test that the limit is properly enforced."""
        with patch('reviews_tool.scrapers.android.validate_app_id', return_value=True), \
             patch.object(self.scraper, '_get_app_info', return_value={}), \
             patch('reviews_tool.scrapers.android.gps_reviews') as mock_gps_reviews:
            
            # Create more reviews than the limit
            many_reviews = [dict(self.sample_raw_review, reviewId=f"review_{i}") for i in range(10)]
            mock_gps_reviews.return_value = (many_reviews, None)
            
            result = self.scraper.search_reviews("com.test", limit=3)
            
            # Should only return 3 reviews despite having 10 available
            assert len(result.reviews) == 3
            assert result.total_reviews == 10

    @patch('reviews_tool.scrapers.android.time.sleep')
    def test_rate_limiting_sleep_called(self, mock_sleep):
        """Test that rate limiting actually calls sleep when needed."""
        # Make two rapid calls
        self.scraper._rate_limit()
        self.scraper._rate_limit()
        
        # Sleep should be called on the second call
        mock_sleep.assert_called()