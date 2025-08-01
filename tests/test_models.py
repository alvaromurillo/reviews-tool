"""Unit tests for data models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from reviews_tool.models import DeveloperResponse, Review, ReviewsResponse


class TestDeveloperResponse:
    """Test suite for DeveloperResponse model."""

    def test_valid_developer_response(self):
        """Test creating a valid developer response."""
        response_date = datetime(2023, 12, 1, 14, 30)
        dev_response = DeveloperResponse(
            text="Thank you for your feedback!",
            date=response_date
        )
        
        assert dev_response.text == "Thank you for your feedback!"
        assert dev_response.date == response_date

    def test_developer_response_whitespace_stripping(self):
        """Test that whitespace is stripped from text."""
        dev_response = DeveloperResponse(
            text="  Thank you for your feedback!  ",
            date=datetime.now()
        )
        
        assert dev_response.text == "Thank you for your feedback!"

    def test_developer_response_missing_text(self):
        """Test that missing text raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            DeveloperResponse(date=datetime.now())
        
        assert "text" in str(exc_info.value)

    def test_developer_response_missing_date(self):
        """Test that missing date raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            DeveloperResponse(text="Thank you!")
        
        assert "date" in str(exc_info.value)

    def test_developer_response_empty_text(self):
        """Test that empty text raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            DeveloperResponse(text="", date=datetime.now())
        
        assert "text" in str(exc_info.value)


class TestReview:
    """Test suite for Review model."""

    def test_valid_review_minimal(self):
        """Test creating a valid review with minimal required fields."""
        review_date = datetime(2023, 12, 1, 10, 30)
        review = Review(
            id="test_review_123",
            user_name="John Doe",
            rating=5,
            text="Great app!",
            date=review_date
        )
        
        assert review.id == "test_review_123"
        assert review.user_name == "John Doe"
        assert review.rating == 5
        assert review.text == "Great app!"
        assert review.date == review_date
        assert review.title is None
        assert review.helpful_count is None
        assert review.language is None
        assert review.country is None
        assert review.version is None
        assert review.developer_response is None

    def test_valid_review_complete(self):
        """Test creating a review with all fields."""
        review_date = datetime(2023, 12, 1, 10, 30)
        dev_response_date = datetime(2023, 12, 2, 14, 15)
        
        dev_response = DeveloperResponse(
            text="Thank you for your feedback!",
            date=dev_response_date
        )
        
        review = Review(
            id="test_review_456",
            user_name="Jane Smith",
            rating=4,
            title="Good app",
            text="This app works well overall.",
            date=review_date,
            helpful_count=10,
            language="en",
            country="US",
            version="2.1.0",
            developer_response=dev_response
        )
        
        assert review.id == "test_review_456"
        assert review.user_name == "Jane Smith"
        assert review.rating == 4
        assert review.title == "Good app"
        assert review.text == "This app works well overall."
        assert review.date == review_date
        assert review.helpful_count == 10
        assert review.language == "en"
        assert review.country == "US"
        assert review.version == "2.1.0"
        assert review.developer_response == dev_response

    def test_review_rating_validation(self):
        """Test rating validation (must be 1-5)."""
        base_data = {
            "id": "test",
            "user_name": "User",
            "text": "Review",
            "date": datetime.now()
        }
        
        # Valid ratings
        for rating in [1, 2, 3, 4, 5]:
            review = Review(**base_data, rating=rating)
            assert review.rating == rating
        
        # Invalid ratings
        for invalid_rating in [0, 6, -1, 10]:
            with pytest.raises(ValidationError) as exc_info:
                Review(**base_data, rating=invalid_rating)
            assert "rating" in str(exc_info.value)

    def test_review_helpful_count_validation(self):
        """Test helpful count validation (must be non-negative)."""
        base_data = {
            "id": "test",
            "user_name": "User",
            "rating": 5,
            "text": "Review",
            "date": datetime.now()
        }
        
        # Valid helpful counts
        for count in [0, 1, 100, 1000]:
            review = Review(**base_data, helpful_count=count)
            assert review.helpful_count == count
        
        # Invalid helpful counts
        for invalid_count in [-1, -10]:
            with pytest.raises(ValidationError) as exc_info:
                Review(**base_data, helpful_count=invalid_count)
            assert "helpful_count" in str(exc_info.value)

    def test_review_whitespace_stripping(self):
        """Test that string fields have whitespace stripped."""
        review = Review(
            id="  test_id  ",
            user_name="  John Doe  ",
            rating=5,
            title="  Great App  ",
            text="  Amazing application!  ",
            date=datetime.now(),
            language="  en  ",
            country="  US  ",
            version="  1.0.0  "
        )
        
        assert review.id == "test_id"
        assert review.user_name == "John Doe"
        assert review.title == "Great App"
        assert review.text == "Amazing application!"
        assert review.language == "en"
        assert review.country == "US"
        assert review.version == "1.0.0"

    def test_review_missing_required_fields(self):
        """Test that missing required fields raise validation errors."""
        # Missing id
        with pytest.raises(ValidationError) as exc_info:
            Review(
                user_name="User",
                rating=5,
                text="Review",
                date=datetime.now()
            )
        assert "id" in str(exc_info.value)
        
        # Missing user_name
        with pytest.raises(ValidationError) as exc_info:
            Review(
                id="test",
                rating=5,
                text="Review",
                date=datetime.now()
            )
        assert "user_name" in str(exc_info.value)
        
        # Missing rating
        with pytest.raises(ValidationError) as exc_info:
            Review(
                id="test",
                user_name="User",
                text="Review",
                date=datetime.now()
            )
        assert "rating" in str(exc_info.value)
        
        # Missing text
        with pytest.raises(ValidationError) as exc_info:
            Review(
                id="test",
                user_name="User",
                rating=5,
                date=datetime.now()
            )
        assert "text" in str(exc_info.value)
        
        # Missing date
        with pytest.raises(ValidationError) as exc_info:
            Review(
                id="test",
                user_name="User",
                rating=5,
                text="Review"
            )
        assert "date" in str(exc_info.value)

    def test_review_json_serialization(self):
        """Test that review can be serialized to JSON."""
        review_date = datetime(2023, 12, 1, 10, 30, 45)
        dev_response = DeveloperResponse(
            text="Thanks!",
            date=datetime(2023, 12, 2, 14, 15, 30)
        )
        
        review = Review(
            id="test_review",
            user_name="John Doe",
            rating=5,
            title="Great",
            text="Excellent app",
            date=review_date,
            helpful_count=5,
            language="en",
            country="US",
            version="1.0.0",
            developer_response=dev_response
        )
        
        # Test JSON serialization
        json_data = review.model_dump()
        
        assert json_data["id"] == "test_review"
        assert json_data["user_name"] == "John Doe"
        assert json_data["rating"] == 5
        assert json_data["title"] == "Great"
        assert json_data["text"] == "Excellent app"
        assert json_data["helpful_count"] == 5
        assert json_data["language"] == "en"
        assert json_data["country"] == "US"
        assert json_data["version"] == "1.0.0"
        assert json_data["developer_response"]["text"] == "Thanks!"


class TestReviewsResponse:
    """Test suite for ReviewsResponse model."""

    def test_valid_reviews_response_minimal(self):
        """Test creating a valid response with minimal required fields."""
        timestamp = datetime(2023, 12, 1, 12, 0)
        response = ReviewsResponse(
            app_id="com.test.app",
            store="android",
            timestamp=timestamp
        )
        
        assert response.app_id == "com.test.app"
        assert response.store == "android"
        assert response.timestamp == timestamp
        assert response.app_name is None
        assert response.total_reviews is None
        assert response.reviews == []
        assert response.next_page_token is None
        assert response.filters_applied == {}

    def test_valid_reviews_response_complete(self):
        """Test creating a response with all fields."""
        timestamp = datetime(2023, 12, 1, 12, 0)
        
        sample_review = Review(
            id="review_1",
            user_name="User 1",
            rating=5,
            text="Great app!",
            date=datetime(2023, 11, 30)
        )
        
        response = ReviewsResponse(
            app_id="com.test.app",
            app_name="Test Application",
            store="ios",
            total_reviews=100,
            reviews=[sample_review],
            next_page_token="page_2_token",
            filters_applied={"rating": 5, "language": "en"},
            timestamp=timestamp
        )
        
        assert response.app_id == "com.test.app"
        assert response.app_name == "Test Application"
        assert response.store == "ios"
        assert response.total_reviews == 100
        assert len(response.reviews) == 1
        assert response.reviews[0] == sample_review
        assert response.next_page_token == "page_2_token"
        assert response.filters_applied == {"rating": 5, "language": "en"}
        assert response.timestamp == timestamp

    def test_reviews_response_total_reviews_validation(self):
        """Test total_reviews validation (must be non-negative)."""
        base_data = {
            "app_id": "com.test.app",
            "store": "android"
        }
        
        # Valid total_reviews
        for count in [0, 1, 100, 1000000]:
            response = ReviewsResponse(**base_data, total_reviews=count)
            assert response.total_reviews == count
        
        # Invalid total_reviews
        for invalid_count in [-1, -10]:
            with pytest.raises(ValidationError) as exc_info:
                ReviewsResponse(**base_data, total_reviews=invalid_count)
            assert "total_reviews" in str(exc_info.value)

    def test_reviews_response_whitespace_stripping(self):
        """Test that string fields have whitespace stripped."""
        response = ReviewsResponse(
            app_id="  com.test.app  ",
            app_name="  Test App  ",
            store="  android  ",
            next_page_token="  token_123  "
        )
        
        assert response.app_id == "com.test.app"
        assert response.app_name == "Test App"
        assert response.store == "android"
        assert response.next_page_token == "token_123"

    def test_reviews_response_missing_required_fields(self):
        """Test that missing required fields raise validation errors."""
        # Missing app_id
        with pytest.raises(ValidationError) as exc_info:
            ReviewsResponse(store="android")
        assert "app_id" in str(exc_info.value)
        
        # Missing store
        with pytest.raises(ValidationError) as exc_info:
            ReviewsResponse(app_id="com.test.app")
        assert "store" in str(exc_info.value)

    def test_reviews_response_default_timestamp(self):
        """Test that timestamp defaults to current time when not provided."""
        import time
        before_creation = datetime.now()
        time.sleep(0.001)  # Small delay to ensure timestamp is after
        
        response = ReviewsResponse(
            app_id="com.test.app",
            store="android"
        )
        
        time.sleep(0.001)  # Small delay to ensure timestamp is before
        after_creation = datetime.now()
        
        assert before_creation < response.timestamp < after_creation

    def test_reviews_response_json_serialization(self):
        """Test that response can be serialized to JSON."""
        timestamp = datetime(2023, 12, 1, 12, 0, 0)
        
        sample_review = Review(
            id="review_1",
            user_name="User 1",
            rating=5,
            text="Great app!",
            date=datetime(2023, 11, 30, 10, 0)
        )
        
        response = ReviewsResponse(
            app_id="com.test.app",
            app_name="Test App",
            store="android",
            total_reviews=50,
            reviews=[sample_review],
            next_page_token="token_abc",
            filters_applied={"rating": 5},
            timestamp=timestamp
        )
        
        # Test JSON serialization
        json_data = response.model_dump()
        
        assert json_data["app_id"] == "com.test.app"
        assert json_data["app_name"] == "Test App"
        assert json_data["store"] == "android"
        assert json_data["total_reviews"] == 50
        assert len(json_data["reviews"]) == 1
        assert json_data["reviews"][0]["id"] == "review_1"
        assert json_data["next_page_token"] == "token_abc"
        assert json_data["filters_applied"] == {"rating": 5}

    def test_reviews_response_with_unicode(self):
        """Test response with unicode characters."""
        sample_review = Review(
            id="unicode_review",
            user_name="用户名",
            rating=5,
            text="这是一个很好的应用程序！",
            date=datetime.now(),
            title="标题"
        )
        
        response = ReviewsResponse(
            app_id="com.chinese.app",
            app_name="中文应用",
            store="android",
            reviews=[sample_review]
        )
        
        assert response.app_name == "中文应用"
        assert response.reviews[0].user_name == "用户名"
        assert response.reviews[0].text == "这是一个很好的应用程序！"
        assert response.reviews[0].title == "标题"

    def test_reviews_response_empty_reviews_list(self):
        """Test response with empty reviews list."""
        response = ReviewsResponse(
            app_id="com.test.app",
            store="android",
            total_reviews=0
        )
        
        assert response.reviews == []
        assert len(response.reviews) == 0

    def test_reviews_response_multiple_reviews(self):
        """Test response with multiple reviews."""
        reviews = []
        for i in range(5):
            review = Review(
                id=f"review_{i}",
                user_name=f"User {i}",
                rating=5,
                text=f"Review text {i}",
                date=datetime.now()
            )
            reviews.append(review)
        
        response = ReviewsResponse(
            app_id="com.test.app",
            store="android",
            total_reviews=5,
            reviews=reviews
        )
        
        assert len(response.reviews) == 5
        assert response.total_reviews == 5
        
        # Verify all reviews are present and correct
        for i, review in enumerate(response.reviews):
            assert review.id == f"review_{i}"
            assert review.user_name == f"User {i}"
            assert review.text == f"Review text {i}"

    def test_model_config_validation_on_assignment(self):
        """Test that validation occurs on field assignment."""
        review = Review(
            id="test",
            user_name="User",
            rating=5,
            text="Review",
            date=datetime.now()
        )
        
        # This should work
        review.rating = 4
        assert review.rating == 4
        
        # This should raise validation error
        with pytest.raises(ValidationError):
            review.rating = 6