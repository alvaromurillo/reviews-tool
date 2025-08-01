"""CLI interface for the reviews tool."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Union, Dict, Any

import click

from .models import ReviewsResponse
from .scrapers.android import AndroidScraper
from .scrapers.ios import IOSScraper
from .utils import validate_app_id, validate_language_code, validate_country_code


@click.group()
@click.version_option(version="0.1.0", prog_name="reviews-tool")
def cli() -> None:
    """App Reviews Tool - Fetch app reviews from Google Play Store and App Store."""
    pass


@cli.command()
@click.argument("app_id", type=str)
@click.option(
    "--store",
    "-s",
    type=click.Choice(["android", "ios"], case_sensitive=False),
    required=True,
    help="Store to search in (android/ios)",
)
@click.option(
    "--limit",
    "-l",
    type=int,
    default=10,
    help="Maximum number of reviews to fetch (default: 10)",
)
@click.option(
    "--rating", "-r", type=click.IntRange(1, 5), help="Filter by rating (1-5 stars)"
)
@click.option(
    "--language",
    "--lang",
    type=str,
    help="Filter by language (ISO 639-1 code, e.g., 'en', 'es')",
)
@click.option(
    "--country",
    "-c",
    type=str,
    help="Filter by country (ISO 3166-1 code, e.g., 'US', 'ES')",
)
@click.option(
    "--date-from",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Filter reviews from this date (YYYY-MM-DD)",
)
@click.option(
    "--date-to",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Filter reviews up to this date (YYYY-MM-DD)",
)
@click.option(
    "--has-dev-response/--no-dev-response",
    default=None,
    help="Filter by presence of developer response",
)
@click.option(
    "--output", "-o", type=click.Path(), help="Save output to file (JSON format)"
)
@click.option(
    "--sort",
    type=click.Choice(
        ["newest", "oldest", "rating_high", "rating_low", "helpful"],
        case_sensitive=False,
    ),
    default="newest",
    help="Sort order for results (default: newest)",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def search(
    app_id: str,
    store: str,
    limit: int,
    rating: Optional[int],
    language: Optional[str],
    country: Optional[str],
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    has_dev_response: Optional[bool],
    output: Optional[str],
    sort: str,
    verbose: bool,
) -> None:
    """
    Search for app reviews by APP_ID.

    APP_ID can be:
    - Android: Package name (com.whatsapp)
    - iOS: App Store ID (310633997) or bundle ID (com.whatsapp.WhatsApp)

    Examples:
    \b
    reviews-tool search com.whatsapp --store android --limit 10
    reviews-tool search 310633997 --store ios --rating 5 --language en
    reviews-tool search com.spotify.music --store android --has-dev-response --output reviews.json
    """
    store = store.lower()

    if verbose:
        click.echo(f"Searching for reviews of {app_id} on {store.upper()}...", err=True)

    # Validate app ID format
    if not validate_app_id(app_id, store):
        click.echo(f"Error: Invalid app ID format for {store.upper()} store", err=True)
        if store == "android":
            click.echo(
                "Android app IDs should be package names (e.g., com.whatsapp)", err=True
            )
        else:
            click.echo(
                "iOS app IDs should be numeric IDs (e.g., 310633997) or bundle IDs (e.g., com.whatsapp.WhatsApp)",
                err=True,
            )
        sys.exit(1)

    # Validate language code if provided
    if language and not validate_language_code(language):
        click.echo(
            f"Error: Invalid language code '{language}'. Use ISO 639-1 codes (e.g., 'en', 'es')",
            err=True,
        )
        sys.exit(1)

    # Validate country code if provided
    if country and not validate_country_code(country):
        click.echo(
            f"Error: Invalid country code '{country}'. Use ISO 3166-1 codes (e.g., 'US', 'ES')",
            err=True,
        )
        sys.exit(1)

    # Validate date range
    if date_from and date_to and date_from > date_to:
        click.echo("Error: --date-from cannot be later than --date-to", err=True)
        sys.exit(1)

    # Dates are already parsed by Click, just use them directly
    parsed_date_from: Optional[datetime] = date_from
    parsed_date_to: Optional[datetime] = date_to

    # Build filters dictionary for display
    filters: Dict[str, Any] = {}
    if rating:
        filters["rating"] = rating
    if language:
        filters["language"] = language
    if country:
        filters["country"] = country
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to
    if has_dev_response is not None:
        filters["has_dev_response"] = has_dev_response
    if sort != "newest":
        filters["sort"] = sort

    try:
        # Initialize appropriate scraper
        scraper: Union[AndroidScraper, IOSScraper]
        if store == "android":
            scraper = AndroidScraper()
        else:
            scraper = IOSScraper()

        if verbose:
            click.echo(
                f"Fetching up to {limit} reviews with filters: {filters}", err=True
            )

        # Fetch reviews
        response: ReviewsResponse = scraper.search_reviews(
            app_id=app_id,
            limit=limit,
            rating=rating,
            language=language,
            country=country,
            has_dev_response=has_dev_response,
            date_from=parsed_date_from,
            date_to=parsed_date_to,
        )

        if verbose:
            click.echo(f"Found {len(response.reviews)} reviews", err=True)
            if response.app_name:
                click.echo(f"App: {response.app_name}", err=True)

        # Prepare output data
        output_data: Dict[str, Any] = {
            "app_id": response.app_id,
            "app_name": response.app_name,
            "store": response.store,
            "total_reviews": response.total_reviews,
            "reviews_fetched": len(response.reviews),
            "next_page_token": response.next_page_token,
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

        # Output results
        json_output = json.dumps(output_data, indent=2, ensure_ascii=False)

        if output:
            # Save to file
            output_path = Path(output)
            output_path.write_text(json_output, encoding="utf-8")
            if verbose:
                click.echo(f"Results saved to {output_path.absolute()}", err=True)
            else:
                click.echo(f"Saved {len(response.reviews)} reviews to {output}")
        else:
            # Print to stdout
            click.echo(json_output)

    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        if verbose:
            import traceback

            click.echo(traceback.format_exc(), err=True)
        sys.exit(1)


def validate_port(ctx: Any, param: Any, value: int) -> int:
    if not (1 <= value <= 65535):
        raise click.BadParameter("Port must be between 1 and 65535")
    return value


@cli.command()
@click.option(
    "--port",
    "-p",
    type=int,
    default=8000,
    help="Port to run the MCP server on (default: 8000)",
    callback=validate_port,
)
@click.option(
    "--host",
    type=str,
    default="localhost",
    help="Host to bind the MCP server to (default: localhost)",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def serve(port: int, host: str, verbose: bool) -> None:
    """
    Start the MCP (Model Context Protocol) server for AI integration.

    This command starts a server that exposes the reviews tool functionality
    as tools that can be used by AI assistants and other MCP clients.
    """
    try:
        from .mcp_server import start_server

        click.echo(f"Starting MCP server on {host}:{port}...")
        if verbose:
            click.echo("Verbose logging enabled")
        start_server(host=host, port=port, verbose=verbose)
    except ImportError:
        click.echo("Error: MCP server dependencies not installed", err=True)
        click.echo("Install with: pip install 'reviews-tool[mcp]'", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error starting server: {str(e)}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
