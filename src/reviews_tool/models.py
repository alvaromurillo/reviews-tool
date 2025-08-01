"""Data models for the reviews tool."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class DeveloperResponse(BaseModel):
    """Model for developer responses to reviews."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        arbitrary_types_allowed=False,
    )

    text: str = Field(..., min_length=1, description="The developer's response text")
    date: datetime = Field(..., description="When the developer responded")


class Review(BaseModel):
    """Model for a single app review."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        arbitrary_types_allowed=False,
    )

    id: str = Field(..., description="Unique review identifier")
    user_name: str = Field(..., description="Name of the reviewer")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5 stars")
    title: Optional[str] = Field(None, description="Review title (if available)")
    text: str = Field(..., description="Review content text")
    date: datetime = Field(..., description="When the review was posted")
    helpful_count: Optional[int] = Field(
        None, ge=0, description="Number of helpful votes"
    )
    language: Optional[str] = Field(
        None, description="Review language code (ISO 639-1)"
    )
    country: Optional[str] = Field(
        None, description="Reviewer country code (ISO 3166-1)"
    )
    version: Optional[str] = Field(None, description="App version being reviewed")
    developer_response: Optional[DeveloperResponse] = Field(
        None, description="Developer's response to the review"
    )


class ReviewsResponse(BaseModel):
    """Model for the complete response containing reviews and metadata."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        arbitrary_types_allowed=False,
    )

    app_id: str = Field(..., description="Application identifier")
    app_name: Optional[str] = Field(None, description="Application name")
    store: str = Field(..., description="Store type (android/ios)")
    total_reviews: Optional[int] = Field(
        None, ge=0, description="Total number of reviews available"
    )
    reviews: List[Review] = Field(default_factory=list, description="List of reviews")
    next_page_token: Optional[str] = Field(None, description="Token for pagination")
    filters_applied: Dict[str, Any] = Field(
        default_factory=dict, description="Filters that were applied"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When the data was fetched"
    )
