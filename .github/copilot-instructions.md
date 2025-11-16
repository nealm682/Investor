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
- **XBRL Parsing**: Extract from `us-gaap` taxonomy with multiple concept fallbacks
- **Period Selection**: Prioritizes most recent data by date - compares quarterly vs annual and selects whichever is newer
- **Point-in-Time vs Period Data**: Distinguishes balance sheet (Cash, Debt as of date) from income statement (Revenue, Net Income for period)
- **Critical XBRL Pattern**: MUST check ALL concept variations for each metric and select most recent by date (never break after first concept)
- **Period Classification**: STRICT day-count only (60-120 days = Quarterly, 300+ = Annual) - never rely on form types (10-Q can contain 9-month cumulative)
- **Debt vs Liabilities**: Traditional debt (borrowings) ≠ Operating leases or deferred revenue - use specific debt concepts only
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

### XBRL Data Accuracy (CRITICAL PATTERNS)

#### Bug Pattern: Old Data Selection
**Problem**: Companies showing data from 2018-2022 instead of current 2025 quarters
**Root Cause**: Code breaks after first matching XBRL concept, which may contain outdated data
**Example**: MP Materials showed 2022-06-30 revenue instead of 2025-09-30, LEU showed 2018 quarterly data
**Solution**: Check ALL concept variations, compare end dates, select most recent
```python
# WRONG - Stops at first concept
for concept in concept_list:
    if concept in us_gaap:
        # Extract data
        break  # ❌ BUG: May have old data

# CORRECT - Checks all concepts
best_date = ''
best_metric = None
for concept in concept_list:
    if concept in us_gaap:
        # Extract data and get end date
        if candidate_date > best_date:
            best_date = candidate_date
            best_metric = data
# Use best_metric after checking all
```

#### Bug Pattern: Period Misclassification
**Problem**: 9-month cumulative revenue ($986M) displayed as quarterly revenue instead of single quarter ($376M)
**Root Cause**: Using form type (10-Q) to classify periods, but 10-Q can contain year-to-date cumulative data
**Example**: SOFI Q3 showing 9-month cumulative instead of 3-month quarter
**Solution**: Calculate period length from start/end dates, use strict day ranges
```python
# WRONG - Form-based classification
if '10-Q' in form or (60 <= period_days <= 120):
    quarterly_values.append(v)  # ❌ BUG: Includes 9-month periods

# CORRECT - Strict day-count only
if 60 <= period_days <= 120:  # Single quarter only
    quarterly_values.append(v)
elif period_days >= 300:  # Annual only
    annual_values.append(v)
```

#### Bug Pattern: Debt vs Liabilities Confusion
**Problem**: Companies showing $1.4B debt when they have $0 traditional borrowings
**Root Cause**: Including 'Liabilities' as fallback in debt concepts captures operating leases, deferred revenue
**Example**: PLTR showing total liabilities as debt instead of $0 (debt-free company)
**Solution**: Use specific debt concepts only, handle $0 debt explicitly
```python
# WRONG - Includes all liabilities
'TotalDebt': ['DebtAndCapitalLeaseObligations', 'Liabilities']  # ❌ Too broad

# CORRECT - Specific debt concepts
'TotalDebt': ['DebtAndCapitalLeaseObligations', 
              'DebtLongtermAndShorttermCombinedAmount', 
              'LongTermDebt']  # ✅ Traditional borrowings only

# Handle debt-free companies
if no_debt_found:
    return "$0 (No traditional debt reported)"
```

#### Bug Pattern: File Pointer Exhaustion
**Problem**: CSV upload fails with "empty or has no columns" error
**Root Cause**: Reading uploaded file twice (sidebar dynamic slider + main area) exhausts file pointer
**Solution**: Add `uploaded_file.seek(0)` after each read to reset pointer

#### Validated Companies (Real-World Testing)
- **SOFI**: Fixed 9-month vs quarterly classification (Q3 $376M not 9-month $986M)
- **MP Materials**: Fixed old data selection (2025-09-30 not 2022-06-30)
- **PLTR**: Fixed debt classification ($0 debt, not $1.4B liabilities)
- **LEU**: Fixed quarterly trends date selection (2025 quarters not 2018)
- **ASTR**: Currently under audit - investigating conflicting debt values ($334M vs $183M)
- **XBRL Concept Variations**: Same financial metric has multiple XBRL concept names (e.g., Revenue = 'Revenues' OR 'RevenueFromContractWithCustomerExcludingAssessedTax' OR 'SalesRevenueNet' OR 'RevenueFromContractWithCustomerIncludingAssessedTax')
- **Old Data Trap**: First matching XBRL concept may contain old data (2018) while later concepts have current data (2025) - MUST check all concepts and compare dates
- **Period Misclassification**: 10-Q forms can contain 9-month cumulative data, not just quarterly - use period length (days between start/end), never form type alone

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

### XBRL Data Extraction Pattern (CRITICAL)
```python
def extract_financial_metric(us_gaap, concept_list, metric_type='period'):
    """
    Extract financial metric from XBRL data - MUST check ALL concepts
    
    Args:
        us_gaap: us-gaap taxonomy dictionary
        concept_list: List of XBRL concept names to check (e.g., ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax'])
        metric_type: 'period' for income statement (Revenue, Net Income) or 'point-in-time' for balance sheet (Cash, Debt)
    
    Returns:
        Dictionary with value, date, period info, or None
    """
    best_metric = None
    best_date = ''
    
    # CRITICAL: Check ALL concepts, never break early
    for concept in concept_list:
        if concept not in us_gaap:
            continue
            
        units = us_gaap[concept].get('units', {})
        if 'USD' not in units:
            continue
            
        values = units['USD']
        valid_values = [v for v in values if v.get('val') is not None and v.get('end')]
        
        if not valid_values:
            continue
            
        # Sort by end date (most recent first)
        valid_values.sort(key=lambda x: x.get('end', ''), reverse=True)
        
        if metric_type == 'point-in-time':
            # Balance sheet items - use most recent point
            candidate = valid_values[0]
            candidate_date = candidate.get('end', '')
            
        else:  # metric_type == 'period'
            # Income statement items - classify by period length
            quarterly_values = []
            annual_values = []
            
            for v in valid_values:
                start_date = v.get('start', '')
                end_date = v.get('end', '')
                
                if start_date and end_date:
                    from datetime import datetime
                    start = datetime.strptime(start_date, '%Y-%m-%d')
                    end = datetime.strptime(end_date, '%Y-%m-%d')
                    period_days = (end - start).days
                    
                    # STRICT classification - no form type checks
                    if 60 <= period_days <= 120:
                        quarterly_values.append(v)
                    elif period_days >= 300:
                        annual_values.append(v)
            
            quarterly_values.sort(key=lambda x: x.get('end', ''), reverse=True)
            annual_values.sort(key=lambda x: x.get('end', ''), reverse=True)
            
            # Use most recent by date (quarterly or annual)
            candidate = None
            if quarterly_values and annual_values:
                candidate = quarterly_values[0] if quarterly_values[0]['end'] > annual_values[0]['end'] else annual_values[0]
            elif quarterly_values:
                candidate = quarterly_values[0]
            elif annual_values:
                candidate = annual_values[0]
            else:
                continue
            
            candidate_date = candidate.get('end', '')
        
        # Only update if this concept has more recent data
        if candidate_date > best_date:
            best_date = candidate_date
            best_metric = {
                'value': candidate.get('val'),
                'date': candidate.get('end'),
                'form': candidate.get('form'),
                'concept': concept,
                # ... other fields
            }
    
    return best_metric
```