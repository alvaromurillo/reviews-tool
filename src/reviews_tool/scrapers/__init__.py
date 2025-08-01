"""
Scrapers package for different app stores.
"""

from .android import AndroidScraper

# Import IOSScraper only if available
try:
    from .ios import IOSScraper

    __all__ = ["AndroidScraper", "IOSScraper"]
except ImportError:
    __all__ = ["AndroidScraper"]
