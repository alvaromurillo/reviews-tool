"""MCP (Model Context Protocol) server for the reviews tool."""

import asyncio
import json
import logging
from typing import Any, Dict, Optional, Union

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    ListToolsResult,
    Tool,
    TextContent,
)
from pydantic import BaseModel, Field

from .models import ReviewsResponse
from .scrapers.android import AndroidScraper
from .scrapers.ios import IOSScraper
from .utils import validate_app_id, validate_language_code, validate_country_code


# Configure logging
logger = logging.getLogger(__name__)


class SearchReviewsArgs(BaseModel):
    """Arguments for the search_reviews tool."""

    app_id: str = Field(
        description="App ID (package name for Android, numeric ID or bundle ID for iOS)"
    )
    store: str = Field(description="Store to search in ('android' or 'ios')")
    limit: int = Field(
        default=10, description="Maximum number of reviews to fetch (default: 10)"
    )
    rating: Optional[int] = Field(
        default=None, description="Filter by rating (1-5 stars)"
    )
    language: Optional[str] = Field(
        default=None, description="Filter by language (ISO 639-1 code)"
    )
    country: Optional[str] = Field(
        default=None, description="Filter by country (ISO 3166-1 code)"
    )
    has_dev_response: Optional[bool] = Field(
        default=None, description="Filter by presence of developer response"
    )
    sort: str = Field(
        default="newest",
        description="Sort order: newest, oldest, rating_high, rating_low, helpful",
    )


class ReviewsToolMCPServer:
    """MCP server for the reviews tool."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.server = Server("reviews-tool")
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Set up MCP server handlers."""

        @self.server.list_tools()  # type: ignore[no-untyped-call]
        async def handle_list_tools() -> ListToolsResult:
            """List available tools."""
            return ListToolsResult(
                tools=[
                    Tool(
                        name="search_reviews",
                        description=(
                            "Search for app reviews from Google Play Store (Android) or App Store (iOS). "
                            "Fetches reviews with various filtering options including rating, language, "
                            "country, developer response presence, and sorting."
                        ),
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "app_id": {
                                    "type": "string",
                                    "description": "App ID (package name for Android like 'com.whatsapp', numeric ID for iOS like '310633997', or bundle ID for iOS like 'com.whatsapp.WhatsApp')",
                                },
                                "store": {
                                    "type": "string",
                                    "enum": ["android", "ios"],
                                    "description": "Store to search in ('android' for Google Play Store or 'ios' for App Store)",
                                },
                                "limit": {
                                    "type": "integer",
                                    "default": 10,
                                    "minimum": 1,
                                    "maximum": 1000,
                                    "description": "Maximum number of reviews to fetch (default: 10, max: 1000)",
                                },
                                "rating": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 5,
                                    "description": "Filter by rating (1-5 stars)",
                                },
                                "language": {
                                    "type": "string",
                                    "description": "Filter by language using ISO 639-1 code (e.g., 'en' for English, 'es' for Spanish)",
                                },
                                "country": {
                                    "type": "string",
                                    "description": "Filter by country using ISO 3166-1 code (e.g., 'US' for United States, 'ES' for Spain)",
                                },
                                "has_dev_response": {
                                    "type": "boolean",
                                    "description": "Filter by presence of developer response (true to show only reviews with developer responses, false for reviews without)",
                                },
                                "sort": {
                                    "type": "string",
                                    "enum": [
                                        "newest",
                                        "oldest",
                                        "rating_high",
                                        "rating_low",
                                        "helpful",
                                    ],
                                    "default": "newest",
                                    "description": "Sort order for results (default: newest)",
                                },
                            },
                            "required": ["app_id", "store"],
                        },
                    )
                ]
            )

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Dict[str, Any] | None
        ) -> CallToolResult:
            """Handle tool calls."""
            if name == "search_reviews":
                return await self._search_reviews(arguments or {})
            else:
                raise ValueError(f"Unknown tool: {name}")

    async def _search_reviews(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Search for app reviews."""
        try:
            # Parse and validate arguments
            args = SearchReviewsArgs(**arguments)

            if self.verbose:
                logger.info(f"Searching for reviews: {args.app_id} on {args.store}")

            # Validate app ID format
            if not validate_app_id(args.app_id, args.store):
                error_msg = f"Invalid app ID format for {args.store.upper()} store"
                if args.store == "android":
                    error_msg += (
                        ". Android app IDs should be package names (e.g., com.whatsapp)"
                    )
                else:
                    error_msg += ". iOS app IDs should be numeric IDs (e.g., 310633997) or bundle IDs (e.g., com.whatsapp.WhatsApp)"

                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {error_msg}")]
                )

            # Validate language code if provided
            if args.language and not validate_language_code(args.language):
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"Error: Invalid language code '{args.language}'. Use ISO 639-1 codes (e.g., 'en', 'es')",
                        )
                    ]
                )

            # Validate country code if provided
            if args.country and not validate_country_code(args.country):
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"Error: Invalid country code '{args.country}'. Use ISO 3166-1 codes (e.g., 'US', 'ES')",
                        )
                    ]
                )

            # Build filters dictionary for display
            filters: Dict[str, Any] = {}
            if args.rating:
                filters["rating"] = args.rating
            if args.language:
                filters["language"] = args.language
            if args.country:
                filters["country"] = args.country
            if args.has_dev_response is not None:
                filters["has_dev_response"] = args.has_dev_response
            if args.sort != "newest":
                filters["sort"] = args.sort

            # Initialize appropriate scraper and run in thread pool
            loop = asyncio.get_event_loop()

            def scrape_reviews() -> ReviewsResponse:
                scraper: Union[AndroidScraper, IOSScraper]
                if args.store == "android":
                    scraper = AndroidScraper()
                else:
                    scraper = IOSScraper()

                return scraper.search_reviews(
                    app_id=args.app_id,
                    limit=args.limit,
                    rating=args.rating,
                    language=args.language,
                    country=args.country,
                    has_dev_response=args.has_dev_response,
                    date_from=None,
                    date_to=None,
                )

            # Run the synchronous scraper in a thread pool
            response: ReviewsResponse = await loop.run_in_executor(None, scrape_reviews)

            if self.verbose:
                logger.info(
                    f"Found {len(response.reviews)} reviews for {response.app_name or args.app_id}"
                )

            # Prepare output data
            output_data: Dict[str, Any] = {
                "app_id": response.app_id,
                "app_name": response.app_name,
                "store": response.store,
                "total_reviews": response.total_reviews,
                "reviews_fetched": len(response.reviews),
                "filters_applied": response.filters_applied,
                "timestamp": response.timestamp.isoformat(),
                "reviews": [],
            }

            # Convert reviews to dict format for JSON serialization
            for review in response.reviews:
                review_dict = {
                    "id": review.id,
                    "user_name": review.user_name,
                    "rating": review.rating,
                    "title": review.title,
                    "text": review.text,
                    "date": review.date.isoformat(),
                    "helpful_count": review.helpful_count,
                    "language": review.language,
                    "country": review.country,
                    "version": review.version,
                }

                if review.developer_response:
                    review_dict["developer_response"] = {
                        "text": review.developer_response.text,
                        "date": review.developer_response.date.isoformat(),
                    }
                else:
                    review_dict["developer_response"] = None

                output_data["reviews"].append(review_dict)

            # Return formatted JSON response
            json_output = json.dumps(output_data, indent=2, ensure_ascii=False)

            return CallToolResult(content=[TextContent(type="text", text=json_output)])

        except Exception as e:
            error_msg = f"Error searching reviews: {str(e)}"
            if self.verbose:
                import traceback

                error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
                logger.error(error_msg)

            return CallToolResult(content=[TextContent(type="text", text=error_msg)])


async def main_server(verbose: bool = False) -> None:
    """Main server function for MCP."""
    if verbose:
        logging.basicConfig(level=logging.INFO)
        logger.info("Starting Reviews Tool MCP Server with verbose logging")

    server_instance = ReviewsToolMCPServer(verbose=verbose)

    # Run the server using stdio transport
    async with stdio_server() as (read_stream, write_stream):
        await server_instance.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="reviews-tool",
                server_version="0.1.0",
                capabilities=server_instance.server.get_capabilities(
                    notification_options=None,  # type: ignore[arg-type]
                    experimental_capabilities={},
                ),
            ),
        )


def start_server(
    host: str = "localhost", port: int = 8000, verbose: bool = False
) -> None:
    """
    Start the MCP server.

    Note: This function starts a stdio-based MCP server, not an HTTP server.
    The host and port parameters are included for CLI compatibility but are not used.
    MCP servers typically use stdio for communication with clients.
    """
    if verbose:
        print("Starting Reviews Tool MCP Server...")
        print("Note: MCP server uses stdio communication, not HTTP")
        print("Connect your MCP client to this process via stdin/stdout")

    try:
        asyncio.run(main_server(verbose=verbose))
    except KeyboardInterrupt:
        if verbose:
            print("\nMCP server stopped by user")
    except Exception as e:
        print(f"Error running MCP server: {e}")
        if verbose:
            import traceback

            print(traceback.format_exc())


if __name__ == "__main__":
    # For testing purposes
    start_server(verbose=True)
