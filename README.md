# App Reviews Tool

A Python tool for fetching app reviews from Google Play Store (Android) and App Store (iOS). Available as both a CLI tool and MCP (Model Context Protocol) server for AI integration.

## Features

- Fetch reviews by app ID from Google Play Store and App Store
- Multiple filtering options (rating, date, language, country, developer response status)
- JSON output format
- Dual interface: CLI and MCP server
- No maximum limit on number of reviews

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### CLI Interface

```bash
# Basic usage
reviews-tool search com.whatsapp --store android

# With filters
reviews-tool search com.whatsapp --store android --limit 50 --min-rating 4
reviews-tool search com.instagram.android --store android --since 2024-01-01 --language es
reviews-tool search 310633997 --store ios --developer-response no --country US

# Output to file
reviews-tool search com.example.app --store android --output reviews.json
```

### MCP Server

Start the MCP server for AI tool integration:

```bash
reviews-tool serve --port 8000
```

## Command Line Options

### Required Arguments
- `app_id`: The application ID (e.g., `com.whatsapp` for Android, `310633997` for iOS)
- `--store {android,ios}`: Target store (required)

### Optional Filters
- `--limit N`: Number of reviews to fetch (default: 20, no maximum)
- `--min-rating {1,2,3,4,5}`: Minimum rating filter
- `--max-rating {1,2,3,4,5}`: Maximum rating filter  
- `--since YYYY-MM-DD`: Reviews from this date onwards
- `--until YYYY-MM-DD`: Reviews until this date
- `--language CODE`: Language code (e.g., es, en, fr)
- `--country CODE`: Country code (e.g., ES, US, FR)
- `--developer-response {any,yes,no}`: Filter by developer response status
  - `any`: all reviews (default)
  - `yes`: only reviews WITH developer response
  - `no`: only reviews WITHOUT developer response
- `--output FILE`: Save output to JSON file

## Output Format

The tool returns a JSON array with the following structure:

```json
{
  "app_id": "com.example.app",
  "store": "android",
  "total_reviews": 45,
  "reviews": [
    {
      "rating": 5,
      "text": "Great app! Love the new features.",
      "date": "2024-01-15T10:30:00Z",
      "user": "john_doe",
      "app_version": "2.1.0",
      "developer_response": null,
      "store": "android"
    },
    {
      "rating": 4,
      "text": "Good app but could use improvements in UI.",
      "date": "2024-01-14T15:45:00Z", 
      "user": "jane_smith",
      "app_version": "2.1.0",
      "developer_response": {
        "text": "Thank you for the feedback! We're working on UI improvements.",
        "date": "2024-01-15T09:00:00Z"
      },
      "store": "android"
    }
  ]
}
```

## Use Cases

- **Sentiment Analysis**: Analyze user sentiment and satisfaction
- **Competitive Monitoring**: Track competitor app reviews and ratings
- **Marketing Content**: Find positive reviews for landing pages and marketing materials
- **Customer Support**: Identify unanswered reviews for AI-generated responses
- **Product Improvement**: Extract feedback for feature development

## Project Structure

```
reviews-tool/
├── src/
│   ├── reviews_tool/
│   │   ├── __init__.py
│   │   ├── cli.py              # CLI interface
│   │   ├── mcp_server.py       # MCP server implementation
│   │   ├── scrapers/
│   │   │   ├── __init__.py
│   │   │   ├── android.py      # Google Play Store scraper
│   │   │   └── ios.py          # App Store scraper
│   │   ├── models.py           # Data models
│   │   └── utils.py            # Common utilities
├── tests/
├── requirements.txt
├── setup.py
├── CLAUDE.md                   # AI assistant guidance
└── README.md
```

## Development

### Requirements
- Python 3.8+
- Dependencies listed in `requirements.txt`

### Common Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Run linting
flake8 src/
black src/

# Type checking
mypy src/

# Install in development mode
pip install -e .
```

## App ID Examples

### Android (Google Play Store)
- WhatsApp: `com.whatsapp`
- Instagram: `com.instagram.android`
- Spotify: `com.spotify.music`

### iOS (App Store)
- WhatsApp: `310633997`
- Instagram: `389801252`
- Spotify: `324684580`

## API Rate Limits

Be mindful of store rate limits:
- Google Play Store: ~100 requests/hour recommended
- App Store: ~50 requests/hour recommended

The tool includes automatic rate limiting and retry mechanisms.

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run linting and tests
6. Submit a pull request