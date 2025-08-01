# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python tool for fetching app reviews from Google Play Store (Android) and App Store (iOS). It provides both a CLI interface and an MCP (Model Context Protocol) server for AI integration. The tool scrapes reviews with various filtering options and outputs structured JSON data.

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .

# Run tests
pytest

# Run linting
flake8 src/
black src/ --check

# Format code
black src/

# Type checking
mypy src/

# Run the CLI tool (after installation)
reviews-tool search com.whatsapp --store android --limit 10

# Start MCP server
reviews-tool serve --port 8000
```

## Architecture

### Core Components

1. **CLI Interface** (`src/reviews_tool/cli.py`)
   - Built with Click framework
   - Handles argument parsing and validation
   - Main entry point for command-line usage

2. **MCP Server** (`src/reviews_tool/mcp_server.py`)
   - Model Context Protocol server implementation
   - Exposes tool functionality to AI assistants
   - Uses asyncio for concurrent operations

3. **Scrapers** (`src/reviews_tool/scrapers/`)
   - `android.py`: Google Play Store scraper using requests/BeautifulSoup
   - `ios.py`: App Store scraper using iTunes Search API and web scraping
   - Each scraper handles rate limiting and error recovery

4. **Data Models** (`src/reviews_tool/models.py`)
   - Pydantic models for type safety
   - Review, DeveloperResponse, and ReviewsResponse classes
   - JSON serialization/deserialization

### Key Design Patterns

- **Strategy Pattern**: Different scrapers for different stores
- **Builder Pattern**: Filter configuration and query building
- **Factory Pattern**: Scraper instantiation based on store type

### Critical Implementation Notes

- **Rate Limiting**: Both stores have strict rate limits. Implement exponential backoff and respect robots.txt
- **User-Agent Rotation**: Use realistic browser user agents to avoid detection
- **Error Handling**: Graceful degradation when reviews are unavailable
- **Date Parsing**: Handle different date formats from each store
- **Language/Country Codes**: Validate ISO codes for language and country filters

### Store-Specific Considerations

**Google Play Store:**
- Uses web scraping of store pages
- Reviews are paginated, requires handling continuation tokens
- Some reviews may be truncated, need to handle "read more" expansion
- Developer responses are nested in review elements

**App Store:**
- Uses iTunes Search API for app metadata
- Reviews available through RSS feeds and web scraping
- Different URL patterns for different countries
- Rate limiting is more restrictive than Google Play

### Testing Strategy

- Unit tests for each scraper with mocked responses
- Integration tests with real (but rate-limited) API calls
- CLI tests using Click's testing utilities
- MCP server tests with mock clients

### Common Pitfalls to Avoid

1. **Don't** make parallel requests to the same store without rate limiting
2. **Don't** assume review text is always available (some may be empty)
3. **Don't** hardcode user agents or request headers
4. **Always** validate app IDs before making requests
5. **Always** handle network timeouts and retries gracefully

### Development Workflow

1. When adding new features, update both CLI and MCP interfaces
2. Add corresponding tests for any new functionality
3. Update README.md examples if CLI interface changes
4. Run full test suite and linting before commits
5. Consider rate limiting impact when testing with real stores