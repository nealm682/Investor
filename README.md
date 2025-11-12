# Earnings Calendar Momentum Analyzer & SEC EDGAR Financial Analysis Suite

This comprehensive investment analysis suite combines earnings calendar momentum screening with deep SEC EDGAR financial health analysis to identify true long-term winners. The toolkit fetches tickers with earnings announcements, applies sophisticated momentum filtering, and performs detailed financial analysis using official SEC filings.

## 🆕 Latest Enhancements

### NEW: SEC EDGAR Financial Analysis Tool
- **Real-Time SEC Data**: Direct integration with SEC EDGAR APIs for official financial data
- **Revenue & Profitability Analysis**: Automatic extraction of income statement metrics
- **Cash & Debt Analysis**: Balance sheet analysis for financial health assessment
- **Recent Filings Tracking**: Display of latest 10-K/10-Q submissions
- **Multi-Company Batch Processing**: Analyze multiple momentum stocks simultaneously
- **Export Capabilities**: CSV export of financial analysis results

### Advanced Date Filtering Options
- **Single Date Analysis**: Traditional single-day earnings analysis
- **Date Range Analysis**: Analyze earnings across multiple consecutive days
- **Multiple Specific Dates**: Cherry-pick specific dates for targeted analysis
- **Smart Date Validation**: Business day warnings and date range validation
- **Comprehensive Progress Tracking**: Real-time updates across multiple dates

## Key Philosophy

**Finding True Momentum Winners**: If a stock grows year-over-year for 5 years, it must be a winner. This suite helps identify companies where investors consistently trust the business fundamentals by:

1. **Momentum Filtering**: Finding stocks where 5-year performance exceeds 1-year performance
2. **Financial Validation**: Using SEC EDGAR data to confirm revenue generation, profitability, and financial health  
3. **Risk Assessment**: Analyzing cash position and debt levels for sustainable growth indicators

This two-stage approach eliminates momentum traps and identifies companies with both market momentum AND fundamental strength.

## Applications

### 📈 Earnings Calendar Momentum Analyzer (`earnings.py`)
Advanced momentum screening based on earnings calendar events with sophisticated filtering capabilities.

### 💰 SEC EDGAR Financial Analysis Tool (`financials.py`) 
Deep financial health analysis using official SEC filings for momentum-filtered companies.

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
- **Multi-Date Breakdown**: Visual table showing ticker counts and samples per selected date

![Multi-Date Processing](snapshot-processing-tickers.jpg)
*Enhanced multi-date processing showing breakdown by date with real-time progress tracking*

![Momentum Winner Cards](Screenshot%202025-11-09%20090533.jpg)
*Example of detailed company cards showing momentum winners with 5-year charts and business intelligence*

![SEC EDGAR Financial Analysis](financials_snapshot.jpg)
*NEW: SEC EDGAR Financial Analysis Tool showing real-time financial health assessment with revenue, profitability, and cash position analysis*

### 📈 Data-Driven Insights
- Automatic pagination to retrieve all tickers from earnings calendar
- Real-time performance calculations across multiple time periods (1mo, 3mo, 6mo, 1y, 2y, 5y)
- Comprehensive company data: market cap, employees, sector, industry, website
- Export capabilities with CSV downloads for both filtered and all winners
- **Multi-date aggregation**: Combine unique tickers across selected date ranges
- **Per-date breakdown**: Visual analysis of ticker distribution across dates

### 🚀 Time-Saving Efficiency
This tool eliminates the need to manually review tickers one-by-one. Instead of spending hours researching individual stocks from earnings calendars, you get:
- **Flexible Date Selection**: Single dates, ranges, or multiple specific dates
- Automated momentum screening across hundreds of tickers
- Pre-filtered results showing only companies with sustained growth
- Rich company context for quick investment decision making
- Visual momentum trends to spot consistent performers
- **Batch Processing**: Analyze multiple earning periods simultaneously

## Features Summary
- **Multi-Date Analysis**: Single dates, date ranges, or multiple specific dates
- **Smart Date Validation**: Business day analysis and weekend warnings
- **Enhanced Progress Tracking**: Real-time updates across multiple processing stages
- **Per-Date Breakdown**: Visual analysis of ticker distribution across selected dates
- **Momentum Filtering**: Advanced dual-filter system (threshold + 5Y > 1Y performance)
- **Rich Company Intelligence**: Business summaries, charts, and key metrics
- **Flexible Export Options**: Date-range aware CSV downloads
- **Interactive UI**: Streamlined controls with session state management
- **Batch Processing Efficiency**: Analyze hundreds of tickers across multiple dates

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

### 🚀 Quick Start - Two Application Workflow

#### Step 1: Run Earnings Momentum Analyzer
1. Open your first terminal and run the momentum analyzer:
    ```powershell
    streamlit run earnings.py
    ```
    - Open in browser at `http://localhost:8501`
    - Analyze earnings calendar data and export momentum stocks to CSV

#### Step 2: Run SEC EDGAR Financial Analyzer  
2. Open a **second terminal** and run the financial analyzer:
    ```powershell
    streamlit run financials.py --server.port 8502
    ```  
    - Open in browser at `http://localhost:8502`
    - Upload the CSV from Step 1 to analyze financial health of momentum stocks

### 📊 Earnings Calendar Momentum Analysis (`earnings.py`)

1. Open the app in your browser (usually at `http://localhost:8501`).

2. **Enhanced Date Selection** - Choose your filtering approach:
    - **Single Date**: Traditional single-day analysis for focused research
    - **Date Range**: Select start/end dates for comprehensive multi-day analysis  
    - **Multiple Specific Dates**: Add up to 10 specific dates for targeted screening

3. Configure your momentum screening:
    - **Time Period**: Pick your analysis timeframe (1mo to 5y)
    - **Threshold**: Set percentage gain threshold for initial filtering

4. **Analyze**: Click to start the momentum screening process with enhanced progress tracking

5. Review Enhanced Results:
    - **Multi-Date Summary**: See breakdown of tickers found per date
    - **Summary Statistics**: View how many tickers pass each filter across all dates
    - **Filtered Winners**: Download CSV of momentum winners (5Y > 1Y performance)
    - **All Winners**: Download CSV of all tickers meeting threshold
    - **Detailed Cards**: Scroll down for rich company profiles with charts and business intelligence

### 💰 SEC EDGAR Financial Analysis (`financials.py`)

1. Open the financial analyzer at `http://localhost:8502`

2. **Upload CSV Data**: Upload the momentum winners CSV from the earnings analyzer

3. **Configure Analysis**:
    - **Max companies to analyze**: Set limit (1-20 companies)
    - **Analysis depth options**: Include filings info, detailed metrics

4. **Start SEC Analysis**: Click "Start Analysis" to begin financial health assessment
    - ⚠️ **Note**: Analysis may take 2-5 minutes due to SEC API rate limiting (10 requests/second)

5. **Review Financial Results**:
    - **Summary Metrics**: Revenue generating, profitable, strong cash position counts
    - **Detailed Company Analysis**: Expandable cards showing:
      - Financial health indicators (✅ Revenue Generating, ✅ Profitable, 🟢 Cash Position)
      - Key metrics (Revenue, Net Income, Cash, Debt with actual dollar amounts)
      - Recent SEC filings (10-K, 10-Q with filing dates)
      - Financial summary and risk assessment
    - **Export Results**: Download comprehensive financial analysis as CSV

## How It Works

This tool scrapes the Yahoo Finance Earnings Calendar (shown below) to identify companies with earnings announcements, then applies sophisticated momentum analysis.

![Yahoo Finance Earnings Calendar](debug_screenshot.png)
*Yahoo Finance Earnings Calendar - Source of earnings announcement data*

### `fetch_earnings_tickers(specific_date)`
Enhanced earnings calendar scraper:
- Scrapes Yahoo Finance earnings calendar for the specified date using Selenium
- Identifies the earnings table by checking for specific header keywords
- Extracts ticker symbols from the table's quote URLs  
- Implements pagination to retrieve all tickers (handles multiple pages)
- **Optimized for batch processing**: Clean, efficient scraping for multiple dates
- Returns a complete list of unique ticker symbols

### Enhanced Multi-Date Processing
**Advanced Date Filtering System**:
- **Single Date Mode**: Traditional focused analysis
- **Date Range Mode**: Automatically generates all dates between start/end with business day analysis
- **Multiple Dates Mode**: Interactive date picker with session management
- **Smart Validation**: Weekend warnings and date range validation
- **Progress Tracking**: Real-time updates across multiple date processing

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
- **Advanced Date Selection**: Radio buttons for Single Date, Date Range, or Multiple Specific Dates
- **Smart Date Controls**: Business day analysis, weekend warnings, session state management
- **Enhanced Progress Tracking**: Multi-level progress bars for date processing and ticker analysis
- **Per-Date Breakdown**: Expandable table showing ticker counts and samples per date
- **Dual Result Views**: Summary tables with CSV downloads + detailed visual cards
- **Momentum Insights**: Clear statistics showing filter effectiveness across all selected dates
- **Company Cards**: Rich visual profiles for each momentum winner including:
  - Interactive 5-year price charts
  - Business summaries and key metrics  
  - Sector/industry context
  - Market cap, employee count, website links
- **Intelligent Filename Generation**: Date-range aware CSV export naming

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
├── earnings.py                       # Enhanced momentum analyzer with multi-date capabilities
├── financials.py                     # NEW: SEC EDGAR financial analysis tool
├── earnings_ui_filter.py             # Legacy single-date analyzer (maintained for compatibility)
├── sec_edgar.md                      # SEC EDGAR API documentation and authentication guide
├── requirements.txt                  # Python package dependencies
├── README.md                        # This comprehensive documentation
├── Screenshot 2025-11-09 090533.jpg # UI screenshot showing momentum cards
├── snapshot-processing-tickers.jpg  # Multi-date processing screenshot
├── financials_snapshot.jpg          # SEC EDGAR financial analysis UI screenshot
├── debug_screenshot.png             # Yahoo Finance Earnings Calendar reference
└── venv/                            # Virtual environment (not tracked in git)
```

## Investment Philosophy

This suite embodies a comprehensive momentum-based investment philosophy with financial validation:

**Sustained Growth Indicator**: Companies showing consistent growth over 5 years demonstrate proven business models and management execution. When 5-year performance exceeds 1-year performance, it suggests the company isn't just riding a recent trend but has fundamental strengths.

**Financial Health Validation**: Beyond momentum analysis, the SEC EDGAR integration provides crucial financial health verification:
- **Revenue Confirmation**: Verify that momentum is backed by actual revenue generation
- **Profitability Assessment**: Distinguish between revenue growth and actual profit generation  
- **Cash Position Analysis**: Assess financial stability through cash vs. debt ratios
- **Filing Compliance**: Recent SEC filings indicate regulatory compliance and transparency

**Investor Confidence**: Year-over-year growth for 5 consecutive years PLUS strong financials indicates sustained investor confidence with fundamental backing. The market continuously validates the company's value proposition through both price appreciation and financial performance.

**Risk Mitigation**: By combining momentum filtering with financial health analysis, this approach helps avoid:
- Momentum traps with weak fundamentals
- Revenue-less growth companies
- Debt-heavy unsustainable business models
- Companies with compliance or transparency issues

**Efficiency & Depth**: Instead of manually researching hundreds of earnings-related stocks, this suite automatically identifies companies with both momentum characteristics AND financial strength, providing a complete investment analysis workflow.

**Two-Stage Validation Process**:
1. **Stage 1**: Momentum screening identifies market-validated growth companies
2. **Stage 2**: SEC EDGAR analysis confirms financial health and sustainability

**Multi-Date Power**: The enhanced date filtering allows for sophisticated analysis strategies:
- **Earnings Clusters**: Analyze entire weeks of earnings to catch sector-wide momentum
- **Historical Comparison**: Compare different earning periods to identify consistent performers  
- **Targeted Research**: Cherry-pick specific high-impact earning days for focused analysis

## Known Limitations

### Earnings Calendar Analyzer
- Yahoo Finance may rate-limit requests for large numbers of tickers
- Some company information may be unavailable for newer/smaller companies
- International stocks may have limited English business descriptions
- Requires Google Chrome browser for web scraping functionality
- 5-year historical data may not be available for recent IPOs

### SEC EDGAR Financial Analyzer  
- **SEC API Rate Limiting**: Limited to 10 requests per second, analysis of multiple companies takes time
- **Data Availability**: Not all companies report all financial metrics in standardized XBRL format
- **Recent IPOs**: Companies with limited SEC filing history may have incomplete data
- **International Companies**: Foreign companies may have different filing requirements
- **Real-Time Data**: SEC filings are typically quarterly/annual, not real-time financial data

## Troubleshooting

### General Setup Issues
**Issue**: Virtual environment activation fails on Windows PowerShell
- **Solution**: Use `.\venv\Scripts\Activate.ps1` instead of just `activate`

### Earnings Calendar Analyzer (`earnings.py`)
**Issue**: ChromeDriver errors
- **Solution**: Ensure Chrome browser is installed and up to date. The app automatically manages ChromeDriver.

**Issue**: No filtered winners found across multiple dates
- **Solution**: Try lowering the percentage threshold or selecting dates with more market activity. Use date range mode to capture more earnings events.

**Issue**: Company information missing in cards  
- **Solution**: This is normal for some tickers. The tool gracefully handles missing data and shows what's available.

**Issue**: Date range processing takes too long
- **Solution**: Consider limiting date ranges to 5-7 business days or use specific dates mode for targeted analysis.

**Issue**: Weekend dates showing warnings
- **Solution**: This is expected - earnings calendars typically have limited activity on weekends. The tool will still process these dates but results may be minimal.

### SEC EDGAR Financial Analyzer (`financials.py`)
**Issue**: "Could not load SEC ticker database" error
- **Solution**: Check internet connection. The app downloads SEC's company ticker database on startup.

**Issue**: Financial analysis taking too long  
- **Solution**: Reduce the "Max companies to analyze" setting. SEC APIs are rate-limited to 10 requests/second.

**Issue**: "CIK Not Found" for tickers
- **Solution**: Some tickers may not be in SEC database (e.g., foreign companies, recent IPOs, delisted companies).

**Issue**: "Revenue data not available" for established companies
- **Solution**: Some companies may not report standardized XBRL data. Check recent SEC filings manually if needed.

**Issue**: Port 8502 already in use
- **Solution**: Use a different port: `streamlit run financials.py --server.port 8503`

## License
This project is licensed under the MIT License.

## Contributing
Contributions are welcome! Please open an issue or submit a pull request.

## Acknowledgments
- Yahoo Finance for providing earnings calendar and stock price data
- **SEC EDGAR** for providing comprehensive financial data through public APIs
- **SEC.gov** for maintaining transparent and accessible corporate filing systems
- Selenium and Streamlit communities for their excellent tools
- yfinance library for simplified Yahoo Finance API access

---

**Repository**: https://github.com/nealm682/Investor
