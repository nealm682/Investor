# Copilot Instructions: Earnings Calendar Momentum & SEC Financial Analysis Suite

## Project Architecture & Philosophy

This is a **two-stage investment analysis pipeline** combining earnings calendar momentum screening with SEC EDGAR financial validation:

1. **Stage 1** (`earnings.py`): Momentum screening using Yahoo Finance earnings calendar + yfinance
2. **Stage 2** (`financials.py`): Financial health validation using SEC EDGAR APIs

**Core Investment Philosophy**: Find companies where 5-year performance > 1-year performance (avoiding momentum traps) AND strong financial fundamentals (revenue generating, profitable, strong cash position).

## Key Application Structure

### Primary Applications (Run Simultaneously)
- **`earnings.py`** - Streamlit app on port 8501: Multi-date earnings calendar analysis
- **`financials.py`** - Streamlit app on port 8502: SEC EDGAR financial analysis

### Workflow Integration
```bash
# Terminal 1: Momentum Analysis
streamlit run earnings.py

# Terminal 2: Financial Analysis  
streamlit run financials.py --server.port 8502
```

Expected CSV flow: earnings.py exports → financials.py imports for analysis

## Critical Dependencies & Constraints

### Selenium Web Scraping (earnings.py)
- **Requires**: Chrome browser + automatic ChromeDriver management via `webdriver-manager`
- **Target**: Yahoo Finance earnings calendar with pagination
- **Parsing Strategy**: Look for tables with earnings-specific headers (`symbol`, `company`, `earnings`, `eps`)
- **Rate Limiting**: Built-in delays between page requests

### SEC EDGAR API Integration (financials.py)
- **Critical**: Must use proper User-Agent: `'Individual Investor-Tools/1.0 (email@domain.com)'`
- **Rate Limit**: 10 requests/second maximum (enforced via `rate_limit()` function)
- **Key Endpoints**:
  - Company tickers: `https://www.sec.gov/files/company_tickers.json`
  - Company facts: `https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json`
  - Submissions: `https://data.sec.gov/submissions/CIK{cik:010d}.json`

## Data Processing Patterns

### Momentum Filter Implementation
```python
# Core logic: 5Y performance must exceed 1Y performance
if one_year_change is not None and five_year_change is not None:
    passes_momentum_filter = five_year_change > one_year_change
```

### Multi-Date Processing (earnings.py)
- **Three modes**: Single Date, Date Range, Multiple Specific Dates
- **Session state management**: `st.session_state.earnings_dates` for multi-date picker
- **Aggregation**: Combine unique tickers across all selected dates
- **Business day validation**: Warn about weekends (low earnings activity)

### SEC Financial Analysis (financials.py)
- **Financial Health Indicators**: Revenue generating, profitable, strong cash position
- **XBRL Parsing**: Extract from `us-gaap` taxonomy, prefer 10-K annual data
- **Fallback Strategy**: Manual ticker entry when SEC database fails

## Development Workflows

### Local Development Setup
```bash
# Virtual environment setup
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -r requirements.txt
```

### Testing & Debugging
- **Sample Tickers**: AAPL (0000320193), MSFT (0000789019), TSLA (0001318605)
- **Debug Mode**: Remove `--headless` from Selenium options to see browser actions
- **SEC API Testing**: Use company facts API for quick connectivity verification

### Common Error Scenarios
1. **SEC 403 Forbidden**: Check User-Agent header format
2. **Selenium TimeoutException**: Yahoo Finance page structure changed
3. **yfinance Data Missing**: Handle MultiIndex columns from price data
4. **Empty Momentum Results**: Lower percentage thresholds or check date selection

## File Organization Conventions

### CSV Export Naming
- **Pattern**: `{type}_{date_range}.csv`
- **Examples**: `filtered_winners_2024-11-14.csv`, `all_winners_2024-11-10_to_2024-11-15.csv`

### Streamlit Session State
- **earnings.py**: `st.session_state.earnings_dates` for multi-date picker
- **financials.py**: `st.session_state['start_analysis']` for analysis trigger

### Configuration Constants
- **SEC_HEADERS**: Must include proper User-Agent for EDGAR compliance
- **Rate limiting**: Global `last_request_time` for SEC API calls
- **Caching**: `@st.cache_data(ttl=3600)` for SEC ticker database

## Integration Points

### CSV Data Flow
- **From earnings.py**: Columns include 'Ticker', 'Momentum Filter ✓', '1Y Performance %'
- **To financials.py**: Filters for `df['Momentum Filter ✓'] == True`
- **Key Requirement**: CSV must contain momentum-filtered results

### API Dependencies
- **Yahoo Finance**: Via yfinance library (can be unreliable, handle exceptions)
- **SEC EDGAR**: Official APIs with strict rate limiting and User-Agent requirements
- **ChromeDriver**: Managed automatically by webdriver-manager

## Common Pitfalls & Solutions

### SEC API Access Issues
- **Problem**: 403 Forbidden errors
- **Solution**: Verify User-Agent format includes organization and contact info
- **Fallback**: Manual ticker entry with sample CIK data

### Memory & Performance
- **Large Date Ranges**: Can generate thousands of tickers, implement progress bars
- **Chart Generation**: Limit to top 10 for detailed company cards
- **Rate Limiting**: Essential for SEC compliance (built into `rate_limit()` function)

### Data Quality
- **yfinance Reliability**: Always check for empty DataFrames and MultiIndex columns
- **SEC Data Gaps**: Not all companies report standardized XBRL data
- **Date Validation**: Business days only for earnings calendar meaningful results

## Code Style Conventions

### Error Handling Pattern
```python
try:
    # API call
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 403:
        # Specific handling for SEC 403 errors
    else:
        # Generic HTTP error handling
except Exception as e:
    # Fallback error handling
```

### Progress Tracking Pattern
```python
progress_bar = st.progress(0)
status_text = st.empty()
for i, item in enumerate(items):
    status_text.text(f"Processing {item}... ({i+1}/{len(items)})")
    # Process item
    progress_bar.progress((i + 1) / len(items))
progress_bar.empty()
status_text.empty()
```