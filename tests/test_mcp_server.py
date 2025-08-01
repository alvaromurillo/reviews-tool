"""Unit tests for MCP server."""

import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from reviews_tool.mcp_server import ReviewsToolMCPServer, main_server, SearchReviewsArgs
from reviews_tool.models import Review, ReviewsResponse


class TestReviewsToolMCPServer:
    """Test suite for ReviewsToolMCPServer class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.server = ReviewsToolMCPServer()
        
        # Sample data for mocking
        self.sample_review = Review(
            id="test_review_123",
            user_name="John Doe",
            rating=5,
            text="Great app!",
            date=datetime(2023, 12, 1, 10, 30),
            language="en",
            country="US",
            version="1.0.0"
        )
        
        self.sample_response = ReviewsResponse(
            app_id="com.test.app",
            app_name="Test App",
            store="android",
            total_reviews=1,
            reviews=[self.sample_review],
            filters_applied={"language": "en"},
            timestamp=datetime(2023, 12, 1, 12, 0)
        )

    def test_server_initialization(self):
        """Test server initialization."""
        server = ReviewsToolMCPServer()
        assert hasattr(server, 'server')
        assert hasattr(server, 'verbose')
        assert server.verbose is False
        
        # Test with verbose mode
        verbose_server = ReviewsToolMCPServer(verbose=True)
        assert verbose_server.verbose is True

    @pytest.mark.asyncio
    async def test_search_reviews_args_validation(self):
        """Test SearchReviewsArgs model validation."""
        # Valid args
        args = SearchReviewsArgs(
            app_id="com.test.app",
            store="android",
            limit=10,
            rating=5
        )
        assert args.app_id == "com.test.app"
        assert args.store == "android"
        assert args.limit == 10
        assert args.rating == 5
        
        # Test defaults
        minimal_args = SearchReviewsArgs(
            app_id="com.test.app",
            store="android"
        )
        assert minimal_args.limit == 10  # default
        assert minimal_args.rating is None
        assert minimal_args.sort == "newest"

    @pytest.mark.asyncio
    @patch('src.reviews_tool.mcp_server.AndroidScraper')
    @patch('src.reviews_tool.mcp_server.validate_app_id')
    async def test_search_reviews_android_success(self, mock_validate, mock_android_class):
        """Test successful Android review search."""
        # Setup mocks
        mock_validate.return_value = True
        mock_scraper = Mock()
        mock_scraper.search_reviews.return_value = self.sample_response
        mock_android_class.return_value = mock_scraper
        
        # Test the internal search method
        arguments = {
            "app_id": "com.test.app",
            "store": "android",
            "limit": 10
        }
        
        result = await self.server._search_reviews(arguments)
        
        # Verify result structure
        assert len(result.content) == 1
        content = result.content[0]
        assert content.type == "text"
        
        # Parse JSON response
        response_data = json.loads(content.text)
        assert response_data["app_id"] == "com.test.app"
        assert response_data["store"] == "android"
        assert response_data["app_name"] == "Test App"
        assert len(response_data["reviews"]) == 1
        assert response_data["reviews"][0]["user_name"] == "John Doe"
        assert response_data["reviews"][0]["rating"] == 5

    @pytest.mark.asyncio
    @patch('src.reviews_tool.mcp_server.IOSScraper')
    @patch('src.reviews_tool.mcp_server.validate_app_id')
    async def test_search_reviews_ios_success(self, mock_validate, mock_ios_class):
        """Test successful iOS review search."""
        # Setup mocks
        mock_validate.return_value = True
        mock_scraper = Mock()
        ios_response = ReviewsResponse(
            app_id="123456789",
            app_name="iOS Test App",
            store="ios", 
            total_reviews=1,
            reviews=[self.sample_review],
            filters_applied={},
            timestamp=datetime.now()
        )
        mock_scraper.search_reviews.return_value = ios_response
        mock_ios_class.return_value = mock_scraper
        
        arguments = {
            "app_id": "123456789",
            "store": "ios",
            "limit": 5,
            "rating": 5
        }
        
        result = await self.server._search_reviews(arguments)
        
        content = result.content[0]
        response_data = json.loads(content.text)
        assert response_data["app_id"] == "123456789"
        assert response_data["store"] == "ios"
        assert response_data["app_name"] == "iOS Test App"

    @pytest.mark.asyncio
    @patch('src.reviews_tool.mcp_server.validate_app_id')
    async def test_search_reviews_invalid_app_id(self, mock_validate):
        """Test search with invalid app ID."""
        mock_validate.return_value = False
        
        arguments = {
            "app_id": "invalid_id",
            "store": "android"
        }
        
        result = await self.server._search_reviews(arguments)
        
        content = result.content[0]
        assert "Error: Invalid app ID format" in content.text

    @pytest.mark.asyncio
    @patch('src.reviews_tool.mcp_server.validate_language_code')
    @patch('src.reviews_tool.mcp_server.validate_app_id')
    async def test_search_reviews_invalid_language(self, mock_validate_app, mock_validate_lang):
        """Test search with invalid language code."""
        mock_validate_app.return_value = True
        mock_validate_lang.return_value = False
        
        arguments = {
            "app_id": "com.test.app",
            "store": "android",
            "language": "invalid_lang"
        }
        
        result = await self.server._search_reviews(arguments)
        
        content = result.content[0]
        assert "Error: Invalid language code" in content.text

    @pytest.mark.asyncio
    @patch('src.reviews_tool.mcp_server.validate_country_code')
    @patch('src.reviews_tool.mcp_server.validate_language_code')
    @patch('src.reviews_tool.mcp_server.validate_app_id')
    async def test_search_reviews_invalid_country(self, mock_validate_app, mock_validate_lang, mock_validate_country):
        """Test search with invalid country code."""
        mock_validate_app.return_value = True
        mock_validate_lang.return_value = True
        mock_validate_country.return_value = False
        
        arguments = {
            "app_id": "com.test.app",
            "store": "android",
            "language": "en",
            "country": "INVALID"
        }
        
        result = await self.server._search_reviews(arguments)
        
        content = result.content[0]
        assert "Error: Invalid country code" in content.text

    @pytest.mark.asyncio
    async def test_search_reviews_invalid_arguments(self):
        """Test search with invalid arguments that cause validation error."""
        # Missing required arguments
        arguments = {
            "store": "android"  # Missing app_id
        }
        
        result = await self.server._search_reviews(arguments)
        
        content = result.content[0]
        assert "Error searching reviews:" in content.text

    @pytest.mark.asyncio
    @patch('src.reviews_tool.mcp_server.AndroidScraper')
    @patch('src.reviews_tool.mcp_server.validate_app_id')
    async def test_search_reviews_scraper_exception(self, mock_validate, mock_android_class):
        """Test search when scraper raises exception."""
        mock_validate.return_value = True
        mock_scraper = Mock()
        mock_scraper.search_reviews.side_effect = ValueError("Invalid app ID")
        mock_android_class.return_value = mock_scraper
        
        arguments = {
            "app_id": "com.test.app",
            "store": "android"
        }
        
        result = await self.server._search_reviews(arguments)
        
        content = result.content[0]
        assert "Error searching reviews:" in content.text
        assert "Invalid app ID" in content.text

    @pytest.mark.asyncio
    @patch('src.reviews_tool.mcp_server.AndroidScraper')
    @patch('src.reviews_tool.mcp_server.validate_app_id')
    async def test_search_reviews_with_all_filters(self, mock_validate, mock_android_class):
        """Test search with all available filters."""
        mock_validate.return_value = True
        mock_scraper = Mock()
        mock_scraper.search_reviews.return_value = self.sample_response
        mock_android_class.return_value = mock_scraper
        
        arguments = {
            "app_id": "com.test.app",
            "store": "android",
            "limit": 25,
            "rating": 4,
            "language": "es",
            "country": "ES",
            "has_dev_response": True,
            "sort": "rating_high"
        }
        
        # Mock all validation functions
        with patch('src.reviews_tool.mcp_server.validate_language_code', return_value=True), \
             patch('src.reviews_tool.mcp_server.validate_country_code', return_value=True):
            
            result = await self.server._search_reviews(arguments)
            
            # Verify scraper was called with filters
            call_args = mock_scraper.search_reviews.call_args
            assert call_args[1]['app_id'] == 'com.test.app'
            assert call_args[1]['limit'] == 25
            assert call_args[1]['rating'] == 4
            assert call_args[1]['language'] == 'es'
            assert call_args[1]['country'] == 'ES'
            assert call_args[1]['has_dev_response'] is True
            # Note: sort parameter is not currently passed to scrapers

    @pytest.mark.asyncio
    @patch('src.reviews_tool.mcp_server.AndroidScraper')
    @patch('src.reviews_tool.mcp_server.validate_app_id')
    async def test_search_reviews_empty_results(self, mock_validate, mock_android_class):
        """Test search that returns empty results."""
        mock_validate.return_value = True
        mock_scraper = Mock()
        empty_response = ReviewsResponse(
            app_id="com.test.app",
            store="android",
            reviews=[],
            filters_applied={},
            timestamp=datetime.now()
        )
        mock_scraper.search_reviews.return_value = empty_response
        mock_android_class.return_value = mock_scraper
        
        arguments = {
            "app_id": "com.test.app",
            "store": "android"
        }
        
        result = await self.server._search_reviews(arguments)
        
        content = result.content[0]
        response_data = json.loads(content.text)
        assert response_data["app_id"] == "com.test.app"
        assert len(response_data["reviews"]) == 0
        assert response_data["reviews_fetched"] == 0

    @pytest.mark.asyncio
    @patch('src.reviews_tool.mcp_server.AndroidScraper') 
    @patch('src.reviews_tool.mcp_server.validate_app_id')
    async def test_search_reviews_with_developer_response(self, mock_validate, mock_android_class):
        """Test search with review that has developer response."""
        mock_validate.return_value = True
        
        # Create review with developer response
        from reviews_tool.models import DeveloperResponse
        dev_response = DeveloperResponse(
            text="Thank you for your feedback!",
            date=datetime(2023, 12, 2, 14, 15)
        )
        
        review_with_response = Review(
            id="review_with_dev_response",
            user_name="Happy User",
            rating=5,
            text="Great app with good support!",
            date=datetime(2023, 12, 1),
            developer_response=dev_response
        )
        
        response_with_dev = ReviewsResponse(
            app_id="com.test.app",
            store="android",
            reviews=[review_with_response],
            filters_applied={},
            timestamp=datetime.now()
        )
        
        mock_scraper = Mock()
        mock_scraper.search_reviews.return_value = response_with_dev
        mock_android_class.return_value = mock_scraper
        
        arguments = {
            "app_id": "com.test.app",
            "store": "android"
        }
        
        result = await self.server._search_reviews(arguments)
        
        content = result.content[0]
        response_data = json.loads(content.text)
        
        review = response_data["reviews"][0]
        assert review["developer_response"] is not None
        assert review["developer_response"]["text"] == "Thank you for your feedback!"
        assert "2023-12-02T14:15:00" in review["developer_response"]["date"]

    @pytest.mark.asyncio
    async def test_search_reviews_verbose_logging(self):
        """Test search with verbose logging enabled."""
        verbose_server = ReviewsToolMCPServer(verbose=True)
        
        # Test with invalid arguments to trigger error logging
        arguments = {"invalid": "args"}
        
        result = await verbose_server._search_reviews(arguments)
        
        content = result.content[0]
        assert "Error searching reviews:" in content.text

    @pytest.mark.asyncio
    @patch('src.reviews_tool.mcp_server.stdio_server')
    async def test_main_server_function(self, mock_stdio_server):
        """Test main server function."""
        # Create mock streams
        mock_read_stream = AsyncMock()
        mock_write_stream = AsyncMock()
        mock_stdio_server.return_value.__aenter__.return_value = (mock_read_stream, mock_write_stream)
        
        # Mock the server run method
        with patch.object(ReviewsToolMCPServer, '__init__', return_value=None) as mock_init:
            mock_server_instance = Mock()
            mock_server_instance.server = Mock()
            mock_server_instance.server.run = AsyncMock()
            mock_server_instance.server.get_capabilities = Mock(return_value={})
            
            with patch('src.reviews_tool.mcp_server.ReviewsToolMCPServer', return_value=mock_server_instance):
                # This would normally run forever, so we'll just test initialization
                try:
                    # Set a short timeout to avoid hanging
                    await asyncio.wait_for(main_server(verbose=True), timeout=0.1)
                except asyncio.TimeoutError:
                    pass  # Expected since server runs indefinitely
                
                # Verify server was initialized
                mock_stdio_server.assert_called_once()


class TestSearchReviewsArgs:
    """Test suite for SearchReviewsArgs model."""

    def test_valid_args_minimal(self):
        """Test creating args with minimal required fields."""
        args = SearchReviewsArgs(
            app_id="com.test.app",
            store="android"
        )
        
        assert args.app_id == "com.test.app"
        assert args.store == "android"
        assert args.limit == 10  # default
        assert args.rating is None
        assert args.sort == "newest"

    def test_valid_args_complete(self):
        """Test creating args with all fields."""
        args = SearchReviewsArgs(
            app_id="com.test.app",
            store="ios",
            limit=50,
            rating=4,
            language="es",
            country="ES",
            has_dev_response=True,
            sort="rating_high"
        )
        
        assert args.app_id == "com.test.app"
        assert args.store == "ios"
        assert args.limit == 50
        assert args.rating == 4
        assert args.language == "es"
        assert args.country == "ES"
        assert args.has_dev_response is True
        assert args.sort == "rating_high"

    def test_args_validation_error(self):
        """Test args validation with missing required fields."""
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            SearchReviewsArgs(store="android")  # Missing app_id
        
        with pytest.raises(ValidationError):
            SearchReviewsArgs(app_id="com.test.app")  # Missing store