# Earnings Calendar Price Change Analyzer

This application analyzes stock price changes based on earnings calendar events. It fetches a list of tickers with earnings on a specific date and calculates the percentage change in their stock prices over the last year. The results are displayed in an interactive Streamlit app, categorizing tickers into "Winners" and "Losers" based on the user-defined percentage change threshold.

## Features
- Fetch tickers with earnings announcements for a specified date.
- Calculate the percentage change in stock prices over the last year.
- Display tickers with significant price changes categorized as "Winners" or "Losers".

## Installation

### Prerequisites
- Python 3.7 or higher
- pip (Python package installer)

### Steps
1. Clone the repository:
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2. Create a virtual environment (optional but recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3. Install the required packages:
    ```bash
    pip install -r requirements.txt
    ```

4. Install and configure ChromeDriver:
    - Ensure Google Chrome is installed on your system.
    - ChromeDriver will be managed automatically by `webdriver_manager`.

## Usage
1. Run the Streamlit app:
    ```bash
    streamlit run app.py
    ```

2. Open the app in your browser (usually at `http://localhost:8501`).

3. Use the interface to:
    - Select an earnings calendar date.
    - Enter a percentage change threshold.
    - Click "Analyze Tickers" to see the results.

## Code Overview

### `fetch_earnings_tickers(specific_date)`
Fetches a list of tickers with earnings announcements for the specified date using Selenium to scrape Yahoo Finance.

### `calculate_tickers_change(tickers, percent_change_threshold)`
Calculates the percentage change in stock prices for the provided tickers over the last year using the Yahoo Finance API.

### Streamlit UI
- Allows user inputs for the earnings calendar date and percentage change threshold.
- Displays the analysis results in a user-friendly interface with separate sections for "Winners" and "Losers".

## Dependencies
- `streamlit`
- `selenium`
- `webdriver_manager`
- `yfinance`
- `pandas`
- `datetime`
- `logging`

## License
This project is licensed under the MIT License.

## Contributing
Contributions are welcome! Please open an issue or submit a pull request.

## Acknowledgments
- Yahoo Finance for providing the data.
- The Selenium and Streamlit communities for their awesome tools.

---

**Note**: Replace `<repository-url>` and `<repository-directory>` with your actual repository URL and directory name.
