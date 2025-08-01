"""Unit tests for CLI interface."""

import pytest
import json
import tempfile
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from reviews_tool.cli import cli, search, serve
from reviews_tool.models import Review, ReviewsResponse


class TestCLI:
    """Test suite for CLI interface."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        
        # Sample response for mocking
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

    def test_cli_main_help(self):
        """Test main CLI help command."""
        result = self.runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "search" in result.output
        assert "serve" in result.output

    def test_search_help(self):
        """Test search command help."""
        result = self.runner.invoke(cli, ['search', '--help'])
        
        assert result.exit_code == 0
        assert "APP_ID" in result.output
        assert "--store" in result.output
        assert "--limit" in result.output
        assert "--rating" in result.output

    def test_serve_help(self):
        """Test serve command help."""
        result = self.runner.invoke(cli, ['serve', '--help'])
        
        assert result.exit_code == 0
        assert "--port" in result.output

    @patch('src.reviews_tool.cli.AndroidScraper')
    def test_search_android_basic(self, mock_android_class):
        """Test basic Android search command."""
        # Setup mock
        mock_scraper = Mock()
        mock_scraper.search_reviews.return_value = self.sample_response
        mock_android_class.return_value = mock_scraper
        
        # Execute command
        result = self.runner.invoke(cli, [
            'search', 'com.test.app',
            '--store', 'android'
        ])
        
        # Verify result
        assert result.exit_code == 0
        
        # Parse output as JSON
        output_data = json.loads(result.output)
        assert output_data['app_id'] == 'com.test.app'
        assert output_data['store'] == 'android'
        assert len(output_data['reviews']) == 1
        assert output_data['reviews'][0]['user_name'] == 'John Doe'
        
        # Verify scraper was called correctly
        mock_scraper.search_reviews.assert_called_once_with(
            app_id='com.test.app',
            limit=10,  # default
            rating=None,
            language=None,
            country=None,
            has_dev_response=None,
            date_from=None,
            date_to=None
        )

    @patch('src.reviews_tool.cli.IOSScraper')
    def test_search_ios_basic(self, mock_ios_class):
        """Test basic iOS search command."""
        # Setup mock
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
        
        # Execute command
        result = self.runner.invoke(cli, [
            'search', '123456789',
            '--store', 'ios'
        ])
        
        # Verify result
        assert result.exit_code == 0
        
        output_data = json.loads(result.output)
        assert output_data['app_id'] == '123456789'
        assert output_data['store'] == 'ios'

    @patch('src.reviews_tool.cli.AndroidScraper')
    def test_search_with_all_filters(self, mock_android_class):
        """Test search command with all filter options."""
        mock_scraper = Mock()
        mock_scraper.search_reviews.return_value = self.sample_response
        mock_android_class.return_value = mock_scraper
        
        result = self.runner.invoke(cli, [
            'search', 'com.test.app',
            '--store', 'android',
            '--limit', '25',
            '--rating', '5',
            '--language', 'es',
            '--country', 'ES',
            '--has-dev-response',
            '--date-from', '2023-01-01',
            '--date-to', '2023-12-31'
        ])
        
        assert result.exit_code == 0
        
        # Verify scraper was called with all parameters
        expected_call = mock_scraper.search_reviews.call_args
        assert expected_call.kwargs['app_id'] == 'com.test.app'
        assert expected_call.kwargs['limit'] == 25
        assert expected_call.kwargs['rating'] == 5
        assert expected_call.kwargs['language'] == 'es' 
        assert expected_call.kwargs['country'] == 'ES'
        assert expected_call.kwargs['date_from'] == datetime(2023, 1, 1, 0, 0)
        assert expected_call.kwargs['date_to'] == datetime(2023, 12, 31, 0, 0)
        assert expected_call.kwargs['has_dev_response'] == True

    @patch('src.reviews_tool.cli.AndroidScraper')
    def test_search_no_dev_response_filter(self, mock_android_class):
        """Test search command with --no-dev-response flag."""
        mock_scraper = Mock()
        mock_scraper.search_reviews.return_value = self.sample_response
        mock_android_class.return_value = mock_scraper
        
        result = self.runner.invoke(cli, [
            'search', 'com.test.app',
            '--store', 'android',
            '--no-dev-response'
        ])
        
        assert result.exit_code == 0
        
        # Verify has_dev_response was set to False
        call_args = mock_scraper.search_reviews.call_args
        assert call_args[1]['has_dev_response'] is False

    def test_search_invalid_store(self):
        """Test search command with invalid store option."""
        result = self.runner.invoke(cli, [
            'search', 'com.test.app',
            '--store', 'invalid'
        ])
        
        assert result.exit_code != 0
        assert "Invalid value for '--store'" in result.output

    def test_search_invalid_rating(self):
        """Test search command with invalid rating."""
        result = self.runner.invoke(cli, [
            'search', 'com.test.app',
            '--store', 'android',
            '--rating', '6'
        ])
        
        assert result.exit_code != 0
        assert "Invalid value for '--rating'" in result.output

    def test_search_invalid_date_format(self):
        """Test search command with invalid date format."""
        result = self.runner.invoke(cli, [
            'search', 'com.test.app',
            '--store', 'android',
            '--date-from', 'invalid-date'
        ])
        
        assert result.exit_code != 0
        assert "Invalid value for '--date-from': 'invalid-date' does not match the format" in result.output

    @patch('src.reviews_tool.cli.AndroidScraper')
    def test_search_with_output_file(self, mock_android_class):
        """Test search command with output file option."""
        mock_scraper = Mock()
        mock_scraper.search_reviews.return_value = self.sample_response
        mock_android_class.return_value = mock_scraper
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp_file:
            tmp_filename = tmp_file.name
        
        try:
            result = self.runner.invoke(cli, [
                'search', 'com.test.app',
                '--store', 'android',
                '--output', tmp_filename
            ])
            
            assert result.exit_code == 0
            assert f"Saved 1 reviews to {tmp_filename}" in result.output
            
            # Verify file was created and contains correct data
            assert os.path.exists(tmp_filename)
            
            with open(tmp_filename, 'r') as f:
                file_data = json.load(f)
                assert file_data['app_id'] == 'com.test.app'
                assert file_data['store'] == 'android'
                
        finally:
            # Clean up
            if os.path.exists(tmp_filename):
                os.unlink(tmp_filename)

    @patch('src.reviews_tool.cli.AndroidScraper')
    def test_search_scraper_exception(self, mock_android_class):
        """Test search command when scraper raises exception."""
        mock_scraper = Mock()
        mock_scraper.search_reviews.side_effect = ValueError("Invalid app ID")
        mock_android_class.return_value = mock_scraper
        
        result = self.runner.invoke(cli, [
            'search', 'invalid.app.id',
            '--store', 'android'
        ])
        
        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "Invalid app ID" in result.output

    @patch('src.reviews_tool.cli.AndroidScraper')
    def test_search_empty_results(self, mock_android_class):
        """Test search command with empty results."""
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
        
        result = self.runner.invoke(cli, [
            'search', 'com.test.app',
            '--store', 'android'
        ])
        
        assert result.exit_code == 0
        
        output_data = json.loads(result.output)
        assert output_data['app_id'] == 'com.test.app'
        assert len(output_data['reviews']) == 0

    def test_search_missing_app_id(self):
        """Test search command without required app-id argument."""
        result = self.runner.invoke(cli, ['search'])
        
        assert result.exit_code != 0
        assert "Missing argument" in result.output

    @patch('src.reviews_tool.cli.AndroidScraper')
    def test_search_date_range_validation(self, mock_android_class):
        """Test search command with date range where from > to."""
        mock_scraper = Mock()
        mock_scraper.search_reviews.return_value = self.sample_response
        mock_android_class.return_value = mock_scraper
        
        result = self.runner.invoke(cli, [
            'search', 'com.test.app',
            '--store', 'android',
            '--date-from', '2023-12-31',
            '--date-to', '2023-01-01'
        ])
        
        assert result.exit_code != 0
        assert "Error: --date-from cannot be later than --date-to" in result.output

    @patch('src.reviews_tool.cli.AndroidScraper')
    def test_search_pretty_print_format(self, mock_android_class):
        """Test that JSON output is properly formatted."""
        mock_scraper = Mock()
        mock_scraper.search_reviews.return_value = self.sample_response
        mock_android_class.return_value = mock_scraper
        
        result = self.runner.invoke(cli, [
            'search', 'com.test.app',
            '--store', 'android'
        ])
        
        assert result.exit_code == 0
        
        # Verify JSON is properly indented (pretty printed)
        lines = result.output.strip().split('\n')
        assert len(lines) > 1  # Should be multiple lines if indented
        
        # Should be valid JSON
        json.loads(result.output)

    @patch('src.reviews_tool.mcp_server.start_server')
    def test_serve_command_default_port(self, mock_start_server):
        """Test serve command with default port."""
        result = self.runner.invoke(cli, ['serve'])
        
        assert result.exit_code == 0
        mock_start_server.assert_called_once_with(host='localhost', port=8000, verbose=False)

    @patch('src.reviews_tool.mcp_server.start_server')
    def test_serve_command_custom_port(self, mock_start_server):
        """Test serve command with custom port."""
        result = self.runner.invoke(cli, ['serve', '--port', '8080', '--host', '0.0.0.0', '-v'])
        
        assert result.exit_code == 0
        mock_start_server.assert_called_once_with(host='0.0.0.0', port=8080, verbose=True)

    def test_serve_invalid_port(self):
        """Test serve command with invalid port number."""
        result = self.runner.invoke(cli, ['serve', '--port', '99999'])
        
        assert result.exit_code != 0

    @patch('src.reviews_tool.cli.IOSScraper')
    def test_search_ios_bundle_id(self, mock_ios_class):
        """Test iOS search with bundle ID format."""
        mock_scraper = Mock()
        mock_scraper.search_reviews.return_value = self.sample_response
        mock_ios_class.return_value = mock_scraper
        
        result = self.runner.invoke(cli, [
            'search', 'com.company.AppName',
            '--store', 'ios'
        ])
        
        assert result.exit_code == 0
        
        # Verify scraper was called with bundle ID
        call_args = mock_scraper.search_reviews.call_args
        assert call_args[1]['app_id'] == 'com.company.AppName'

    @patch('src.reviews_tool.cli.AndroidScraper')
    def test_search_output_file_write_error(self, mock_android_class):
        """Test search command when output file cannot be written."""
        mock_scraper = Mock()
        mock_scraper.search_reviews.return_value = self.sample_response
        mock_android_class.return_value = mock_scraper
        
        # Try to write to a directory that doesn't exist
        invalid_path = '/nonexistent/directory/output.json'
        
        result = self.runner.invoke(cli, [
            'search', 'com.test.app',
            '--store', 'android',
            '--output', invalid_path
        ])
        
        assert result.exit_code == 1
        assert "No such file or directory" in result.output

    @patch('src.reviews_tool.cli.AndroidScraper')
    def test_search_concurrent_requests_safety(self, mock_android_class):
        """Test that search command handles scraper rate limiting."""
        mock_scraper = Mock()
        
        # Simulate rate limiting delay in scraper
        def slow_search(*args, **kwargs):
            import time
            time.sleep(0.1)  # Small delay to simulate rate limiting
            return self.sample_response
        
        mock_scraper.search_reviews.side_effect = slow_search
        mock_android_class.return_value = mock_scraper
        
        result = self.runner.invoke(cli, [
            'search', 'com.test.app',
            '--store', 'android'
        ])
        
        assert result.exit_code == 0
        # Should still return valid JSON despite delay
        json.loads(result.output)

    @patch('src.reviews_tool.cli.AndroidScraper')
    def test_search_response_serialization(self, mock_android_class):
        """Test that all response fields are properly serialized to JSON."""
        mock_scraper = Mock()
        
        # Create response with all possible fields
        complex_response = ReviewsResponse(
            app_id="com.test.app",
            app_name="Test App with Special Chars: é, ñ, 中文",
            store="android",
            total_reviews=100,
            reviews=[
                Review(
                    id="review_with_unicode_💫",
                    user_name="User with émojis 🎉",
                    rating=5,
                    title="Title with special chars: àáâã",
                    text="Review text with unicode: 你好世界",
                    date=datetime(2023, 12, 1, 10, 30, 45),
                    helpful_count=42,
                    language="zh",
                    country="CN",
                    version="1.2.3",
                    developer_response=None
                )
            ],
            next_page_token="token_with_special_chars_🔗",
            filters_applied={"rating": 5, "language": "zh"},
            timestamp=datetime(2023, 12, 1, 12, 0, 0)
        )
        
        mock_scraper.search_reviews.return_value = complex_response
        mock_android_class.return_value = mock_scraper
        
        result = self.runner.invoke(cli, [
            'search', 'com.test.app',
            '--store', 'android'
        ])
        
        assert result.exit_code == 0
        
        # Verify all fields are properly serialized
        output_data = json.loads(result.output)
        assert output_data['app_name'] == "Test App with Special Chars: é, ñ, 中文"
        assert output_data['reviews'][0]['user_name'] == "User with émojis 🎉"
        assert output_data['reviews'][0]['text'] == "Review text with unicode: 你好世界"
        assert output_data['next_page_token'] == "token_with_special_chars_🔗"