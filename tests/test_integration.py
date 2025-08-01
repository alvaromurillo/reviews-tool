"""Integration tests with real APIs (rate-limited)."""

import pytest
import time
from datetime import datetime, timedelta

from reviews_tool.scrapers.android import AndroidScraper
from reviews_tool.scrapers.ios import IOSScraper
from reviews_tool.models import ReviewsResponse


class TestIntegrationAndroid:
    """Integration tests for Android scraper with real Google Play Store API."""

    def setup_method(self):
        """Set up test fixtures."""
        self.scraper = AndroidScraper()
        # Use a well-known app that should always be available
        self.test_app_id = "com.whatsapp"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_android_search_basic(self):
        """Test basic Android search with real API (rate-limited)."""
        # Rate limit to avoid overwhelming the API
        time.sleep(2)
        
        result = self.scraper.search_reviews(
            app_id=self.test_app_id,
            limit=5  # Small limit to reduce API calls
        )
        
        assert isinstance(result, ReviewsResponse)
        assert result.app_id == self.test_app_id
        assert result.store == "android"
        assert result.app_name is not None
        assert len(result.reviews) <= 5
        
        # Verify review structure
        if result.reviews:
            review = result.reviews[0]
            assert review.id is not None
            assert review.user_name is not None
            assert 1 <= review.rating <= 5
            assert review.text is not None
            assert isinstance(review.date, datetime)

    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_android_search_with_rating_filter(self):
        """Test Android search with rating filter."""
        time.sleep(2)
        
        result = self.scraper.search_reviews(
            app_id=self.test_app_id,
            limit=3,
            rating=5  # Only 5-star reviews
        )
        
        assert isinstance(result, ReviewsResponse)
        assert result.filters_applied.get("rating") == 5
        
        # All returned reviews should be 5-star
        for review in result.reviews:
            assert review.rating == 5

    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_android_search_with_language_filter(self):
        """Test Android search with language filter."""
        time.sleep(2)
        
        result = self.scraper.search_reviews(
            app_id=self.test_app_id,
            limit=3,
            language="en",
            country="US"
        )
        
        assert isinstance(result, ReviewsResponse)
        assert result.filters_applied.get("language") == "en"
        assert result.filters_applied.get("country") == "US"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_android_search_invalid_app_id(self):
        """Test Android search with invalid app ID."""
        time.sleep(1)
        
        result = self.scraper.search_reviews(
            app_id="com.nonexistent.invalid.app.that.should.not.exist",
            limit=1
        )
        
        # Should return empty results, not crash
        assert isinstance(result, ReviewsResponse)
        assert len(result.reviews) == 0

    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_android_pagination(self):
        """Test Android pagination with real API."""
        time.sleep(2)
        
        # Get first page
        result1 = self.scraper.search_reviews(
            app_id=self.test_app_id,
            limit=3
        )
        
        assert isinstance(result1, ReviewsResponse)
        
        # If we got a next page token, test pagination
        if result1.next_page_token:
            time.sleep(2)  # Rate limit
            
            result2 = self.scraper.search_reviews(
                app_id=self.test_app_id,
                limit=3,
                page_token=result1.next_page_token
            )
            
            assert isinstance(result2, ReviewsResponse)
            # Pages should have different reviews (assuming enough reviews exist)
            if result1.reviews and result2.reviews:
                assert result1.reviews[0].id != result2.reviews[0].id


class TestIntegrationIOS:
    """Integration tests for iOS scraper with real App Store API."""

    def setup_method(self):
        """Set up test fixtures."""
        self.scraper = IOSScraper()
        # Use WhatsApp iOS app ID
        self.test_app_id = "310633997"
        self.test_bundle_id = "net.whatsapp.WhatsApp"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_ios_search_basic_numeric_id(self):
        """Test basic iOS search with numeric app ID."""
        time.sleep(3)  # iOS API is more rate-limited
        
        result = self.scraper.search_reviews(
            app_id=self.test_app_id,
            limit=3
        )
        
        assert isinstance(result, ReviewsResponse)
        assert result.app_id == self.test_app_id
        assert result.store == "ios"
        assert result.app_name is not None
        assert len(result.reviews) <= 3
        
        # Verify review structure
        if result.reviews:
            review = result.reviews[0]
            assert review.id is not None
            assert review.user_name is not None
            assert 1 <= review.rating <= 5
            assert review.text is not None
            assert isinstance(review.date, datetime)

    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_ios_app_info_lookup(self):
        """Test iOS app info lookup."""
        time.sleep(2)
        
        app_info = self.scraper._get_app_info_by_id(self.test_app_id, "us")
        
        assert isinstance(app_info, dict)
        assert app_info.get("name") is not None
        assert app_info.get("developer") is not None
        assert app_info.get("bundle_id") is not None

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.xfail(reason="App Store API may have changed")
    def test_real_ios_bundle_id_search(self):
        """Test iOS bundle ID search."""
        time.sleep(2)
        
        # Search for numeric ID by bundle ID
        numeric_id = self.scraper._search_app_by_bundle_id(self.test_bundle_id, "us")
        
        assert numeric_id is not None
        assert numeric_id.isdigit()
        assert numeric_id == self.test_app_id

    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_ios_rss_feed_parsing(self):
        """Test iOS RSS feed parsing."""
        time.sleep(3)
        
        reviews = self.scraper._get_reviews_from_rss(self.test_app_id, "us", 1)
        
        assert isinstance(reviews, list)
        # RSS feed should contain some reviews
        if reviews:
            review = reviews[0]
            assert hasattr(review, 'id')
            assert hasattr(review, 'user_name')
            assert hasattr(review, 'rating')
            assert hasattr(review, 'text')
            assert hasattr(review, 'date')

    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_ios_search_with_country_filter(self):
        """Test iOS search with country filter."""
        time.sleep(3)
        
        result = self.scraper.search_reviews(
            app_id=self.test_app_id,
            limit=2,
            country="US"
        )
        
        assert isinstance(result, ReviewsResponse)
        assert result.filters_applied.get("country") == "US"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_ios_search_invalid_app_id(self):
        """Test iOS search with invalid app ID."""
        time.sleep(2)
        
        result = self.scraper.search_reviews(
            app_id="999999999999",  # Very unlikely to exist
            limit=1
        )
        
        # Should return empty results, not crash
        assert isinstance(result, ReviewsResponse)
        assert len(result.reviews) == 0

    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_ios_pagination(self):
        """Test iOS pagination with RSS pages."""
        time.sleep(3)
        
        # Get first page
        result1 = self.scraper.search_reviews(
            app_id=self.test_app_id,
            limit=2
        )
        
        assert isinstance(result1, ReviewsResponse)
        
        # If we got a next page token, test pagination
        if result1.next_page_token:
            time.sleep(3)  # Rate limit
            
            result2 = self.scraper.search_reviews(
                app_id=self.test_app_id,
                limit=2,
                page_token=result1.next_page_token
            )
            
            assert isinstance(result2, ReviewsResponse)


class TestIntegrationCLI:
    """Integration tests for CLI with real APIs."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_cli_integration_android(self):
        """Test CLI with real Android API."""
        from click.testing import CliRunner
        from reviews_tool.cli import cli
        
        runner = CliRunner()
        
        # Rate limit
        time.sleep(2)
        
        result = runner.invoke(cli, [
            'search', 'com.whatsapp',
            '--store', 'android',
            '--limit', '2'
        ])
        
        # Should succeed (exit code 0)
        assert result.exit_code == 0
        
        # Should return valid JSON
        try:
            import json
            output_data = json.loads(result.output)
            assert output_data['app_id'] == 'com.whatsapp'
            assert output_data['store'] == 'android'
        except json.JSONDecodeError:
            pytest.fail("CLI output is not valid JSON")

    @pytest.mark.integration
    @pytest.mark.slow
    def test_cli_integration_ios(self):
        """Test CLI with real iOS API."""
        from click.testing import CliRunner
        from reviews_tool.cli import cli
        
        runner = CliRunner()
        
        # Rate limit
        time.sleep(3)
        
        result = runner.invoke(cli, [
            'search', '310633997',
            '--store', 'ios',
            '--limit', '1'
        ])
        
        # Should succeed
        assert result.exit_code == 0
        
        # Should return valid JSON
        try:
            import json
            output_data = json.loads(result.output)
            assert output_data['app_id'] == '310633997'
            assert output_data['store'] == 'ios'
        except json.JSONDecodeError:
            pytest.fail("CLI output is not valid JSON")


class TestIntegrationMCP:
    """Integration tests for MCP server with real APIs."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_mcp_integration_android(self):
        """Test MCP server with real Android API."""
        from reviews_tool.mcp_server import ReviewsToolMCPServer
        
        server = ReviewsToolMCPServer(verbose=True)
        
        # Rate limit
        time.sleep(2)
        
        arguments = {
            "app_id": "com.whatsapp",
            "store": "android",
            "limit": 2
        }
        
        result = await server._search_reviews(arguments)
        
        assert len(result.content) == 1
        content = result.content[0]
        assert content.type == "text"
        
        # Should be valid JSON
        import json
        response_data = json.loads(content.text)
        assert response_data["app_id"] == "com.whatsapp"
        assert response_data["store"] == "android"

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_mcp_integration_ios(self):
        """Test MCP server with real iOS API."""
        from reviews_tool.mcp_server import ReviewsToolMCPServer
        
        server = ReviewsToolMCPServer(verbose=True)
        
        # Rate limit
        time.sleep(3)
        
        arguments = {
            "app_id": "310633997",
            "store": "ios",
            "limit": 1
        }
        
        result = await server._search_reviews(arguments)
        
        assert len(result.content) == 1
        content = result.content[0]
        
        # Should be valid JSON
        import json
        response_data = json.loads(content.text)
        assert response_data["app_id"] == "310633997"
        assert response_data["store"] == "ios"


# Pytest configuration for integration tests
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (may be slow)"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )


# Skip integration tests by default (run with: pytest -m integration)
pytestmark = pytest.mark.integration