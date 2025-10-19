# Earnings Calendar Price Change Analyzer

This application analyzes stock price changes based on earnings calendar events. It fetches a list of tickers with earnings on a specific date from Yahoo Finance and retrieves their 1-year price change percentage. The results are displayed in an interactive Streamlit app, categorizing tickers into "Winners" and "Losers" based on the user-defined percentage change threshold.

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
1. Run the Streamlit app:
    ```powershell
    streamlit run earnings_app.py
    ```

2. Open the app in your browser (usually at `http://localhost:8501`).

3. Use the interface to:
    - Select an earnings calendar date
    - Enter a percentage change threshold (default: 35%)
    - Click "Analyze Tickers" to see the results

## How It Works

### `fetch_earnings_tickers(specific_date)`
Scrapes Yahoo Finance earnings calendar for the specified date using Selenium:
- Identifies the earnings table by checking for specific header keywords
- Extracts ticker symbols from the table's quote URLs
- Implements pagination to retrieve all tickers (handles multiple pages)
- Returns a complete list of unique ticker symbols

### `calculate_tickers_change(tickers, percent_change_threshold)`
Retrieves 1-year price change data for each ticker:
- Uses Yahoo Finance API's `52WeekChange` field for accurate percentage calculation
- Filters tickers into "Winners" (positive changes above threshold) and "Losers" (negative changes below threshold)
- Returns three DataFrames: winners, losers, and all results

### Streamlit UI
- Date picker for earnings calendar selection
- Numeric input for percentage change threshold
- Progress bars and status updates during processing
- Three-section results display:
  - **Winners**: Tickers with gains exceeding the threshold
  - **Losers**: Tickers with losses exceeding the threshold
  - **All Tickers**: Complete sorted list of all analyzed stocks

## Key Dependencies
- `streamlit==1.50.0` - Interactive web application framework
- `selenium==4.36.0` - Web scraping automation
- `webdriver-manager==4.0.2` - Automatic ChromeDriver management
- `yfinance==0.2.66` - Yahoo Finance API for stock data
- `pandas==2.3.3` - Data manipulation and analysis

See `requirements.txt` for complete list of dependencies.

## Project Structure
```
Investor/
├── earnings_app.py      # Main Streamlit application
├── requirements.txt     # Python package dependencies
├── README.md           # This file
└── venv/               # Virtual environment (not tracked in git)
```

## Known Limitations
- Yahoo Finance may rate-limit requests for large numbers of tickers
- The 52-week change percentage may differ slightly from the chart UI due to timing and calculation differences
- Requires Google Chrome browser for web scraping functionality

## Troubleshooting

**Issue**: Virtual environment activation fails on Windows PowerShell
- **Solution**: Use `.\venv\Scripts\Activate.ps1` (not `venv\Scripts\activate`)

**Issue**: ChromeDriver errors
- **Solution**: Ensure Chrome browser is installed and up to date. The app automatically manages ChromeDriver.

**Issue**: No tickers found for selected date
- **Solution**: Choose a date when the stock market is open and earnings are scheduled

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
