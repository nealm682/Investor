# Earnings Calendar Momentum Analyzer

This application analyzes stock price momentum based on earnings calendar events to identify true long-term winners. It fetches tickers with earnings announcements from Yahoo Finance and applies sophisticated filtering to find companies with sustained growth momentum - stocks that have performed well over multiple time horizons, indicating consistent investor confidence.

## Key Philosophy

**Finding True Momentum Winners**: If a stock grows year-over-year for 5 years, it must be a winner. This tool helps identify companies where investors consistently trust the business fundamentals by filtering for stocks where 5-year performance exceeds 1-year performance - indicating sustained, long-term growth rather than just recent volatility.

## Features

### 🎯 Momentum Filtering
- **Primary Filter**: User-defined percentage threshold for initial screening
- **Momentum Filter**: Advanced filter requiring 5-year performance > 1-year performance
- **True Winners**: Only companies passing both filters are highlighted as top momentum picks

### 📊 Rich Visual Analysis  
- **Interactive Cards**: Detailed company profiles for filtered winners (see screenshot below)
- **5-Year Price Charts**: Visual momentum trends for each top pick
- **Company Intelligence**: Business summaries, sector/industry classification, key metrics
- **Performance Metrics**: Clear display of 1-year vs 5-year performance comparison

![Momentum Winner Cards](2025-11-09.png)
*Example of detailed company cards showing momentum winners with 5-year charts and business intelligence*

### 📈 Data-Driven Insights
- Automatic pagination to retrieve all tickers from earnings calendar
- Real-time performance calculations across multiple time periods (1mo, 3mo, 6mo, 1y, 2y, 5y)
- Comprehensive company data: market cap, employees, sector, industry, website
- Export capabilities with CSV downloads for both filtered and all winners

### 🚀 Time-Saving Efficiency
This tool eliminates the need to manually review tickers one-by-one. Instead of spending hours researching individual stocks from earnings calendars, you get:
- Automated momentum screening across hundreds of tickers
- Pre-filtered results showing only companies with sustained growth
- Rich company context for quick investment decision making
- Visual momentum trends to spot consistent performers

## Features
- Fetch tickers with earnings announcements for a specified date from Yahoo Finance
- Automatic pagination to retrieve all tickers (not just the first page)
- Calculate 1-year percentage change using Yahoo Finance's official 52-week change metric
- Display tickers with significant price changes categorized as "Winners" or "Losers"
- Show all tickers with their price changes sorted by performance
- Real-time progress tracking during analysis

## Installation

### Prerequisites
- Python 3.7 or higher
- pip (Python package installer)
- Google Chrome browser (for web scraping)

### Steps
1. Clone the repository:
    ```bash
    git clone https://github.com/nealm682/Investor.git
    cd Investor
    ```

2. Create a virtual environment (recommended):
    ```powershell
    # Windows PowerShell
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    ```

3. Install the required packages:
    ```powershell
    pip install -r requirements.txt
    ```

4. ChromeDriver setup:
    - Ensure Google Chrome is installed on your system
    - ChromeDriver is managed automatically by `webdriver-manager`

## Usage
1. Run the enhanced momentum analyzer:
    ```powershell
    streamlit run earnings_ui_filter.py
    ```

2. Open the app in your browser (usually at `http://localhost:8501`).

3. Configure your momentum screening:
    - **Select Date**: Choose an earnings calendar date to analyze
    - **Time Period**: Pick your analysis timeframe (1mo to 5y)
    - **Threshold**: Set percentage gain threshold for initial filtering
    - **Analyze**: Click to start the momentum screening process

4. Review Results:
    - **Summary Statistics**: See how many tickers pass each filter
    - **Filtered Winners**: Download CSV of momentum winners (5Y > 1Y performance)
    - **All Winners**: Download CSV of all tickers meeting threshold
    - **Detailed Cards**: Scroll down for rich company profiles with charts and business intelligence

## How It Works

### `fetch_earnings_tickers(specific_date)`
Scrapes Yahoo Finance earnings calendar for the specified date using Selenium:
- Identifies the earnings table by checking for specific header keywords
- Extracts ticker symbols from the table's quote URLs  
- Implements pagination to retrieve all tickers (handles multiple pages)
- Returns a complete list of unique ticker symbols

### `calculate_tickers_change(tickers, percent_change_threshold, time_period)`
Advanced momentum analysis with dual filtering:
- **Primary Screening**: Filters tickers meeting initial percentage threshold over selected period
- **Momentum Analysis**: For potential winners, downloads both 1-year and 5-year historical data
- **Momentum Filter**: Applies sophisticated filter requiring 5-year performance > 1-year performance
- **Returns**: Three DataFrames - all winners, filtered momentum winners, and complete results

### `get_company_info(ticker)` & `create_ticker_card()`
Rich company intelligence gathering:
- Retrieves comprehensive company data via yfinance API
- Business summaries, sector/industry classification, financial metrics
- Creates beautiful visual cards with integrated 5-year price charts
- Handles missing data gracefully with fallback displays

### Enhanced Streamlit UI
- **Date & Period Selection**: Choose earnings date and analysis timeframe
- **Threshold Configuration**: Set percentage gain requirements
- **Progress Tracking**: Real-time updates during analysis
- **Dual Result Views**: Summary tables with CSV downloads + detailed visual cards
- **Momentum Insights**: Clear statistics showing filter effectiveness
- **Company Cards**: Rich visual profiles for each momentum winner including:
  - Interactive 5-year price charts
  - Business summaries and key metrics  
  - Sector/industry context
  - Market cap, employee count, website links

## Key Dependencies
- `streamlit>=1.50.0` - Interactive web application framework
- `selenium==4.36.0` - Web scraping automation for earnings calendar
- `webdriver-manager==4.0.2` - Automatic ChromeDriver management
- `yfinance==0.2.66` - Yahoo Finance API for stock data and company information
- `pandas==2.3.3` - Data manipulation and analysis

See `requirements.txt` for complete list of dependencies.

## Project Structure
```
Investor/
├── earnings_ui_filter.py   # Enhanced momentum analyzer (MAIN APP)
├── earnings_filter.py      # Basic filtering version  
├── earnings_app.py         # Original simple analyzer
├── requirements.txt        # Python package dependencies
├── README.md              # This file
├── 2025-11-09.png         # UI screenshot showing momentum cards
└── venv/                  # Virtual environment (not tracked in git)
```

## Investment Philosophy

This tool embodies a momentum-based investment philosophy:

**Sustained Growth Indicator**: Companies showing consistent growth over 5 years demonstrate proven business models and management execution. When 5-year performance exceeds 1-year performance, it suggests the company isn't just riding a recent trend but has fundamental strengths.

**Investor Confidence**: Year-over-year growth for 5 consecutive years indicates sustained investor confidence. The market continuously validates the company's value proposition.

**Risk Mitigation**: By filtering out stocks with only recent gains, this approach helps avoid momentum traps and temporary rallies, focusing on companies with proven track records.

**Efficiency**: Instead of manually researching hundreds of earnings-related stocks, this tool automatically identifies the handful with genuine momentum characteristics.

## Known Limitations
- Yahoo Finance may rate-limit requests for large numbers of tickers
- Some company information may be unavailable for newer/smaller companies
- International stocks may have limited English business descriptions
- Requires Google Chrome browser for web scraping functionality
- 5-year historical data may not be available for recent IPOs

## Troubleshooting

**Issue**: Virtual environment activation fails on Windows PowerShell
- **Solution**: Use `.\venv\Scripts\Activate.ps1` instead of just `activate`

**Issue**: ChromeDriver errors
- **Solution**: Ensure Chrome browser is installed and up to date. The app automatically manages ChromeDriver.

**Issue**: No filtered winners found
- **Solution**: Try lowering the percentage threshold or selecting a different date with more market activity

**Issue**: Company information missing in cards  
- **Solution**: This is normal for some tickers. The tool gracefully handles missing data and shows what's available.

## License
This project is licensed under the MIT License.

## Contributing
Contributions are welcome! Please open an issue or submit a pull request.

## Acknowledgments
- Yahoo Finance for providing earnings calendar and stock price data
- Selenium and Streamlit communities for their excellent tools
- yfinance library for simplified Yahoo Finance API access

---

**Repository**: https://github.com/nealm682/Investor
