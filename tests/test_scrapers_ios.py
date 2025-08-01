"""Unit tests for iOS scraper."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import requests

from reviews_tool.scrapers.ios import IOSScraper
from reviews_tool.models import Review, ReviewsResponse


class TestIOSScraper:
    """Test suite for IOSScraper class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.scraper = IOSScraper()
        self.sample_app_id = "310633997"  # WhatsApp iOS app ID
        self.sample_bundle_id = "net.whatsapp.WhatsApp"
        
        # Sample RSS review XML
        self.sample_rss_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns:im="http://itunes.apple.com/rss" xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <im:name>WhatsApp Messenger</im:name>
            </entry>
            <entry>
                <updated>2023-12-01T10:30:00-07:00</updated>
                <id>123456789</id>
                <title>Great app!</title>
                <content type="text">This app is amazing and very useful.</content>
                <im:rating>5</im:rating>
                <im:version>23.24.1</im:version>
                <author>
                    <name>John Doe</name>
                </author>
            </entry>
            <entry>
                <updated>2023-11-15T09:00:00-07:00</updated>
                <id>987654321</id>
                <title>Good service</title>
                <content type="text">Pretty good overall.</content>
                <im:rating>4</im:rating>
                <im:version>23.23.5</im:version>
                <author>
                    <name>Jane Smith</name>
                </author>
            </entry>
        </feed>'''
        
        # Sample iTunes API response
        self.sample_itunes_response = {
            "results": [{
                "trackId": 310633997,
                "trackName": "WhatsApp Messenger",
                "artistName": "WhatsApp Inc.",
                "averageUserRating": 4.5,
                "userRatingCount": 1000000,
                "version": "23.24.1",
                "bundleId": "net.whatsapp.WhatsApp",
                "releaseDate": "2009-05-03T07:00:00Z",
                "description": "WhatsApp Messenger is a messaging app"
            }]
        }

    def test_init(self):
        """Test scraper initialization."""
        scraper = IOSScraper()
        assert scraper.last_request_time == 0
        assert scraper.request_delay == 2
        assert isinstance(scraper.session, requests.Session)
        assert "itunes.apple.com" in scraper.itunes_api_base
        assert "customerreviews" in scraper.reviews_rss_pattern

    def test_rate_limit(self):
        """Test rate limiting mechanism."""
        import time
        start_time = time.time()
        
        # First call should not delay significantly
        self.scraper._rate_limit()
        first_call_time = time.time() - start_time
        assert first_call_time < 0.1
        
        # Second call should delay
        start_time = time.time()
        self.scraper._rate_limit()
        second_call_time = time.time() - start_time
        assert second_call_time >= self.scraper.request_delay * 0.9

    def test_make_request_success(self):
        """Test successful HTTP request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "success"
        
        with patch.object(self.scraper.session, 'get', return_value=mock_response):
            result = self.scraper._make_request("https://example.com")
            
            assert result == mock_response
            self.scraper.session.get.assert_called_once()

    def test_make_request_rate_limited(self):
        """Test request with rate limiting (429 status)."""
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        
        with patch.object(self.scraper.session, 'get', side_effect=[mock_response_429, mock_response_200]), \
             patch('reviews_tool.scrapers.ios.exponential_backoff'):
            
            result = self.scraper._make_request("https://example.com")
            
            assert result == mock_response_200
            assert self.scraper.session.get.call_count == 2

    def test_make_request_failure(self):
        """Test request failure after retries."""
        with patch.object(self.scraper.session, 'get', side_effect=requests.RequestException("Network error")):
            result = self.scraper._make_request("https://example.com", retries=2)
            
            assert result is None
            assert self.scraper.session.get.call_count == 2

    def test_get_app_info_by_id_success(self):
        """Test successful app info retrieval by ID."""
        mock_response = Mock()
        mock_response.json.return_value = self.sample_itunes_response
        
        with patch.object(self.scraper, '_make_request', return_value=mock_response):
            app_info = self.scraper._get_app_info_by_id("310633997", "us")
            
            assert app_info["name"] == "WhatsApp Messenger"
            assert app_info["developer"] == "WhatsApp Inc."
            assert app_info["rating"] == 4.5
            assert app_info["total_ratings"] == 1000000
            assert app_info["version"] == "23.24.1"
            assert app_info["bundle_id"] == "net.whatsapp.WhatsApp"

    def test_get_app_info_by_id_not_found(self):
        """Test app info retrieval when app not found."""
        mock_response = Mock()
        mock_response.json.return_value = {"results": []}
        
        with patch.object(self.scraper, '_make_request', return_value=mock_response):
            app_info = self.scraper._get_app_info_by_id("999999999", "us")
            
            assert app_info == {}

    def test_get_app_info_by_id_request_failed(self):
        """Test app info retrieval when request fails."""
        with patch.object(self.scraper, '_make_request', return_value=None):
            app_info = self.scraper._get_app_info_by_id("310633997", "us")
            
            assert app_info == {}

    def test_search_app_by_bundle_id_success(self):
        """Test successful app search by bundle ID."""
        search_response = {
            "results": [
                {"bundleId": "net.whatsapp.WhatsApp", "trackId": 310633997},
                {"bundleId": "com.other.app", "trackId": 123456789}
            ]
        }
        
        mock_response = Mock()
        mock_response.json.return_value = search_response
        
        with patch.object(self.scraper, '_make_request', return_value=mock_response):
            app_id = self.scraper._search_app_by_bundle_id("net.whatsapp.WhatsApp", "us")
            
            assert app_id == "310633997"

    def test_search_app_by_bundle_id_not_found(self):
        """Test app search when bundle ID not found."""
        search_response = {
            "results": [
                {"bundleId": "com.other.app", "trackId": 123456789}
            ]
        }
        
        mock_response = Mock()
        mock_response.json.return_value = search_response
        
        with patch.object(self.scraper, '_make_request', return_value=mock_response):
            app_id = self.scraper._search_app_by_bundle_id("net.whatsapp.WhatsApp", "us")
            
            assert app_id is None

    def test_parse_rss_reviews_success(self):
        """Test successful RSS review parsing."""
        reviews = self.scraper._parse_rss_reviews(self.sample_rss_xml, "en", "US")
        
        assert len(reviews) == 2  # Should skip the first entry (app info)
        
        # Check first review
        review1 = reviews[0]
        assert isinstance(review1, Review)
        assert review1.user_name == "John Doe"
        assert review1.rating == 5
        assert review1.title == "Great app!"
        assert review1.text == "This app is amazing and very useful."
        assert review1.version == "23.24.1"
        assert review1.language == "en"
        assert review1.country == "US"
        assert review1.helpful_count is None  # Not available in RSS
        assert review1.developer_response is None  # Would need additional scraping
        
        # Check second review
        review2 = reviews[1]
        assert review2.user_name == "Jane Smith"
        assert review2.rating == 4
        assert review2.title == "Good service"
        assert review2.text == "Pretty good overall."
        assert review2.version == "23.23.5"

    def test_parse_rss_reviews_malformed_xml(self):
        """Test RSS parsing with malformed XML."""
        malformed_xml = "not valid xml"
        
        reviews = self.scraper._parse_rss_reviews(malformed_xml)
        
        assert reviews == []

    def test_parse_rss_reviews_missing_fields(self):
        """Test RSS parsing with missing fields."""
        minimal_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns:im="http://itunes.apple.com/rss" xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <im:name>App Name</im:name>
            </entry>
            <entry>
                <content type="text">Basic review text</content>
            </entry>
        </feed>'''
        
        reviews = self.scraper._parse_rss_reviews(minimal_xml)
        
        assert len(reviews) == 1
        review = reviews[0]
        assert review.user_name == "Anonymous"  # Default when missing
        assert review.rating == 5  # Default when missing
        assert review.title is None
        assert review.text == "Basic review text"
        assert isinstance(review.date, datetime)

    def test_get_reviews_from_rss_success(self):
        """Test successful RSS review fetching."""
        mock_response = Mock()
        mock_response.text = self.sample_rss_xml
        
        with patch.object(self.scraper, '_make_request', return_value=mock_response):
            reviews = self.scraper._get_reviews_from_rss("310633997", "us", 1)
            
            assert len(reviews) == 2
            assert all(isinstance(review, Review) for review in reviews)

    def test_get_reviews_from_rss_failed_request(self):
        """Test RSS review fetching when request fails."""
        with patch.object(self.scraper, '_make_request', return_value=None):
            reviews = self.scraper._get_reviews_from_rss("310633997", "us", 1)
            
            assert reviews == []

    @patch('reviews_tool.scrapers.ios.validate_app_id')
    def test_search_reviews_invalid_bundle_id(self, mock_validate):
        """Test search with invalid bundle ID that can't be found."""
        mock_validate.return_value = False
        
        with patch.object(self.scraper, '_search_app_by_bundle_id', return_value=None):
            with pytest.raises(ValueError, match="Invalid iOS app ID format or app not found"):
                self.scraper.search_reviews("invalid.bundle.id")

    @patch.object(IOSScraper, '_get_app_info_by_id')
    @patch.object(IOSScraper, '_get_reviews_from_rss')
    def test_search_reviews_numeric_id_success(self, mock_get_reviews, mock_get_app_info):
        """Test successful review search with numeric app ID."""
        # Setup mocks
        mock_get_app_info.return_value = {"name": "WhatsApp Messenger"}
        
        sample_reviews = [
            Review(
                id="review1", user_name="User1", rating=5, text="Great!", 
                date=datetime(2023, 12, 1), title="Excellent"
            ),
            Review(
                id="review2", user_name="User2", rating=4, text="Good", 
                date=datetime(2023, 11, 15), title="Nice"
            )
        ]
        mock_get_reviews.side_effect = [sample_reviews, []]
        
        # Execute search
        result = self.scraper.search_reviews(
            app_id="310633997",
            limit=2,
            language="en",
            country="US"
        )
        
        # Verify result
        assert isinstance(result, ReviewsResponse)
        assert result.app_id == "310633997"
        assert result.app_name == "WhatsApp Messenger"
        assert result.store == "ios"
        assert result.total_reviews == 2
        assert len(result.reviews) == 2
        assert result.filters_applied == {"language": "en", "country": "US"}
        
        # Verify methods were called
        mock_get_app_info.assert_called_once_with("310633997", "us")
        mock_get_reviews.assert_called()

    @patch('reviews_tool.scrapers.ios.validate_app_id')
    @patch.object(IOSScraper, '_search_app_by_bundle_id')
    @patch.object(IOSScraper, '_get_app_info_by_id')
    @patch.object(IOSScraper, '_get_reviews_from_rss')
    def test_search_reviews_bundle_id_success(self, mock_get_reviews, mock_get_app_info, 
                                              mock_search_bundle, mock_validate):
        """Test successful review search with bundle ID."""
        # Setup mocks
        mock_validate.return_value = True
        mock_search_bundle.return_value = None  # This shouldn't be called for valid bundle ID
        mock_get_app_info.return_value = {"name": "WhatsApp Messenger"}
        mock_get_reviews.return_value = []
        
        # Execute search with bundle ID format
        result = self.scraper.search_reviews("net.whatsapp.WhatsApp")
        
        assert result.app_id == "net.whatsapp.WhatsApp"
        assert result.store == "ios"

    @patch.object(IOSScraper, '_get_app_info_by_id')
    @patch.object(IOSScraper, '_get_reviews_from_rss')
    def test_search_reviews_with_rating_filter(self, mock_get_reviews, mock_get_app_info):
        """Test review search with rating filter."""
        mock_get_app_info.return_value = {"name": "Test App"}
        
        # Create reviews with different ratings
        all_reviews = [
            Review(id="1", user_name="U1", rating=4, text="Good", date=datetime.now()),
            Review(id="2", user_name="U2", rating=5, text="Great", date=datetime.now()),
            Review(id="3", user_name="U3", rating=4, text="Nice", date=datetime.now())
        ]
        mock_get_reviews.side_effect = [all_reviews, []]
        
        # Search for only 5-star reviews
        result = self.scraper.search_reviews("123456", rating=5, limit=10)
        
        assert len(result.reviews) == 1
        assert result.reviews[0].rating == 5
        assert result.filters_applied == {"rating": 5}

    @patch.object(IOSScraper, '_get_app_info_by_id')
    @patch.object(IOSScraper, '_get_reviews_from_rss')
    def test_search_reviews_with_date_filter(self, mock_get_reviews, mock_get_app_info):
        """Test review search with date filters."""
        mock_get_app_info.return_value = {"name": "Test App"}
        
        # Create reviews with different dates
        all_reviews = [
            Review(id="1", user_name="U1", rating=5, text="Old", date=datetime(2023, 10, 1)),
            Review(id="2", user_name="U2", rating=5, text="New", date=datetime(2023, 12, 1))
        ]
        mock_get_reviews.side_effect = [all_reviews, []]
        
        # Search for reviews after November 1
        result = self.scraper.search_reviews(
            "123456", 
            date_from=datetime(2023, 11, 1),
            limit=10
        )
        
        assert len(result.reviews) == 1
        assert result.reviews[0].text == "New"

    @patch.object(IOSScraper, '_get_app_info_by_id')
    @patch.object(IOSScraper, '_get_reviews_from_rss')
    def test_search_reviews_pagination(self, mock_get_reviews, mock_get_app_info):
        """Test review search with pagination."""
        mock_get_app_info.return_value = {"name": "Test App"}
        
        # Mock returns different reviews for different pages
        def mock_reviews_side_effect(app_id, country, page):
            if page == 1:
                return [Review(id="1", user_name="U1", rating=5, text="Page1", date=datetime.now())]
            elif page == 2:
                return [Review(id="2", user_name="U2", rating=5, text="Page2", date=datetime.now())]
            else:
                return []
        
        mock_get_reviews.side_effect = mock_reviews_side_effect
        
        # Test with page token
        result = self.scraper.search_reviews("123456", limit=1, page_token="2")
        
        assert len(result.reviews) == 1
        assert result.reviews[0].text == "Page2"
        
        # Verify _get_reviews_from_rss was called with correct page numbers
        calls = mock_get_reviews.call_args_list
        pages_called = [call[0][2] for call in calls]  # Third argument is page number
        assert 2 in pages_called

    @patch.object(IOSScraper, '_get_app_info_by_id')
    @patch.object(IOSScraper, '_get_reviews_from_rss')
    def test_search_reviews_limit_enforcement(self, mock_get_reviews, mock_get_app_info):
        """Test that the limit is properly enforced."""
        mock_get_app_info.return_value = {"name": "Test App"}
        
        # Create more reviews than the limit
        many_reviews = [
            Review(id=f"review_{i}", user_name=f"User{i}", rating=5, 
                  text=f"Review {i}", date=datetime.now())
            for i in range(10)
        ]
        mock_get_reviews.return_value = many_reviews
        
        result = self.scraper.search_reviews("123456", limit=3)
        
        # Should only return 3 reviews despite having 10 available
        assert len(result.reviews) == 3
        assert result.total_reviews == 10

    @patch.object(IOSScraper, '_get_app_info_by_id')
    @patch.object(IOSScraper, '_get_reviews_from_rss')
    def test_search_reviews_error_handling(self, mock_get_reviews, mock_get_app_info):
        """Test review search error handling."""
        mock_get_app_info.side_effect = Exception("Network error")
        
        result = self.scraper.search_reviews("123456")
        
        assert isinstance(result, ReviewsResponse)
        assert result.app_id == "123456"
        assert result.store == "ios"
        assert result.reviews == []
        assert result.total_reviews is None

    @patch('reviews_tool.scrapers.ios.time.sleep')
    def test_rate_limiting_sleep_called(self, mock_sleep):
        """Test that rate limiting actually calls sleep when needed."""
        # Make two rapid calls
        self.scraper._rate_limit()
        self.scraper._rate_limit()
        
        # Sleep should be called on the second call
        mock_sleep.assert_called()

    def test_search_reviews_next_page_token_generation(self):
        """Test next page token generation logic."""
        with patch.object(self.scraper, '_get_app_info_by_id', return_value={}), \
             patch.object(self.scraper, '_get_reviews_from_rss') as mock_get_reviews:
            
            # Create enough reviews to trigger next page token
            many_reviews = [
                Review(id=f"review_{i}", user_name=f"User{i}", rating=5, 
                      text=f"Review {i}", date=datetime.now())
                for i in range(50)
            ]
            mock_get_reviews.return_value = many_reviews
            
            result = self.scraper.search_reviews("123456", limit=25)
            
            # Should have next page token since we have more reviews than limit
            assert result.next_page_token is not None
            assert int(result.next_page_token) > 1  # Should be page number > 1