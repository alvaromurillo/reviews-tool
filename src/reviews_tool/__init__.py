"""
App Reviews Tool - A Python tool for fetching app reviews from Google Play Store and App Store.
"""

__version__ = "0.1.0"
__author__ = "Alvaro Murillo"
__email__ = "your.email@example.com"

from .models import Review, DeveloperResponse, ReviewsResponse

__all__ = ["Review", "DeveloperResponse", "ReviewsResponse"]
