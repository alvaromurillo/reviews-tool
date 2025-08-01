# Development Roadmap - App Reviews Tool

This document contains all pending tasks to complete the development of the app reviews tool. Use it to track progress and resume work in future sessions.

## Project Status

**✅ Completed:**
- [x] Create GitHub repository: https://github.com/alvaromurillo/reviews-tool
- [x] Initial documentation (README.md and CLAUDE.md)
- [x] Technical specifications defined

**🚧 In Progress:**
- [ ] Python project structure

**📋 Pending:**
- [ ] Full implementation

---

## 📋 Pending Tasks

### Phase 1: Project Setup
- [ ] **1.1** Create directory structure according to README.md design
- [ ] **1.2** Configure requirements.txt with dependencies
- [ ] **1.3** Create setup.py for package installation
- [ ] **1.4** Configure pytest for testing
- [ ] **1.5** Configure linting (flake8, black, mypy)

### Phase 2: Data Models
- [ ] **2.1** Implement Pydantic models in `src/reviews_tool/models.py`
  - [ ] Review model
  - [ ] DeveloperResponse model  
  - [ ] ReviewsResponse model
- [ ] **2.2** Create common utilities in `src/reviews_tool/utils.py`

### Phase 3: Scrapers
- [ ] **3.1** Implement Google Play Store scraper (`src/reviews_tool/scrapers/android.py`)
  - [ ] Search by app ID
  - [ ] Extract reviews with all fields
  - [ ] Handle pagination
  - [ ] Implement filters (rating, date, language, country, dev response)
  - [ ] Rate limiting and error handling
- [ ] **3.2** Implement App Store scraper (`src/reviews_tool/scrapers/ios.py`)
  - [ ] Search by app ID
  - [ ] Extract reviews with all fields
  - [ ] Handle pagination
  - [ ] Implement filters (rating, date, language, country, dev response)
  - [ ] Rate limiting and error handling

### Phase 4: CLI Interface
- [ ] **4.1** Implement CLI with Click (`src/reviews_tool/cli.py`)
  - [ ] `search` command with all arguments
  - [ ] Argument validation
  - [ ] Formatted JSON output
  - [ ] Save to file option
  - [ ] Error handling and informative messages
- [ ] **4.2** Create entry script in setup.py

### Phase 5: MCP Server
- [ ] **5.1** Implement MCP server (`src/reviews_tool/mcp_server.py`)
  - [ ] Server configuration
  - [ ] Expose tools for AI integration
  - [ ] Asynchronous request handling
  - [ ] `serve` command in CLI

### Phase 6: Testing
- [ ] **6.1** Unit tests for scrapers
  - [ ] HTTP response mocks
  - [ ] Filter tests
  - [ ] Error handling tests
- [ ] **6.2** Integration tests with real APIs (rate-limited)
- [ ] **6.3** CLI tests
- [ ] **6.4** MCP server tests

### Phase 7: Documentation and CI/CD
- [ ] **7.1** Configure GitHub Actions for CI
  - [ ] Automated tests
  - [ ] Linting
  - [ ] Type checking
- [ ] **7.2** Configure release automation
- [ ] **7.3** Update documentation with real examples

---

## 📝 Task Management Instructions

### How to Mark Tasks as In Progress
When starting work on a task, change `- [ ]` to `- [🚧]` and move it to the "In Progress" section at the top:

```markdown
**🚧 In Progress:**
- [🚧] **1.1** Create directory structure according to README.md design
```

### How to Mark Tasks as Completed
When finishing a task, change `- [🚧]` to `- [x]` and move it to the "Completed" section:

```markdown
**✅ Completed:**
- [x] **1.1** Create directory structure according to README.md design
```

### Commit Message Convention
When completing tasks, use this commit message format:
```
feat: complete task X.Y - brief description

- Detailed description of what was implemented
- Any important notes or decisions made

Closes #X.Y
```

---

## 🔧 Technical Details

### Required Dependencies
```
requests>=2.31.0
beautifulsoup4>=4.12.0
click>=8.1.0
pydantic>=2.0.0
pytest>=7.0.0
flake8>=6.0.0
black>=23.0.0
mypy>=1.0.0
mcp>=0.1.0  # For MCP server
```

### File Structure to Create
```
src/
├── reviews_tool/
│   ├── __init__.py
│   ├── cli.py              # CLI interface
│   ├── mcp_server.py       # MCP server
│   ├── models.py           # Pydantic models
│   ├── utils.py            # Common utilities
│   └── scrapers/
│       ├── __init__.py
│       ├── android.py      # Google Play scraper
│       └── ios.py          # App Store scraper
tests/
├── __init__.py
├── test_cli.py
├── test_models.py
├── test_scrapers_android.py
├── test_scrapers_ios.py
└── test_mcp_server.py
setup.py
requirements.txt
pytest.ini
.github/
└── workflows/
    └── ci.yml
```

### Implementation Considerations

**Rate Limiting:**
- Google Play: ~100 requests/hour
- App Store: ~50 requests/hour
- Implement exponential backoff

**User Agents:**
- Rotate realistic user agents
- Avoid bot detection

**Error Handling:**
- Graceful degradation
- Informative logging
- Automatic retries

---

## 🎯 Priority Use Cases

1. **Marketing:** Find positive reviews for landing pages
2. **Customer Support:** Identify reviews without developer response
3. **Analysis:** Sentiment analysis and competitor monitoring

---

## 📝 Session Notes

**Last updated:** 2025-08-01
**Current status:** Repository created, initial documentation complete
**Next step:** Create Python project structure (Phase 1)

### Development Commands (for future sessions)
```bash
# Clone and enter project
git clone https://github.com/alvaromurillo/reviews-tool.git
cd reviews-tool

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Tests
pytest

# Linting
flake8 src/
black src/ --check
mypy src/

# Run tool
reviews-tool search com.whatsapp --store android --limit 10
```

### Working Directory
The actual repository is located at:
```
/Volumes/Developer/reviews-tool/reviews-tool/
```

Make sure to work from this directory in future sessions.