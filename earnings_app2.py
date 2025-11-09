import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
from datetime import datetime, timedelta
import pandas as pd
import logging
import robin_stocks.robinhood as r
from src.robinhood_login import login_to_robinhood

# Suppress Selenium logging
logging.getLogger('selenium').setLevel(logging.ERROR)
logging.getLogger('webdriver_manager').setLevel(logging.ERROR)

def fetch_earnings_tickers(specific_date):
    """
    Scrapes Yahoo Finance for earnings calendar tickers.
    Note: Robinhood doesn't provide earnings calendar, so we still use Yahoo Finance.
    """
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        all_tickers = set()
        
        st.info(f"Fetching earnings for {specific_date}...")
        
        # Pagination loop
        offset = 0
        size = 100
        max_pages = 10
        page_num = 0
        
        while page_num < max_pages:
            url = f'https://finance.yahoo.com/calendar/earnings?day={specific_date}&offset={offset}&size={size}'
            st.write(f"Fetching page {page_num + 1} (offset={offset})...")
            
            driver.get(url)
            time.sleep(4)
            
            page_tickers = set()
            
            # Look ONLY in the earnings table - be very specific
            try:
                tables = driver.find_elements(By.TAG_NAME, 'table')
                
                for table_idx, table in enumerate(tables):
                    # Check if this table has the earnings columns we expect
                    try:
                        headers = table.find_elements(By.CSS_SELECTOR, 'thead th, thead td')
                        header_texts = [h.text.strip() for h in headers]
                        
                        # Look for earnings table markers
                        if any(keyword in ' '.join(header_texts).lower() for keyword in ['symbol', 'company', 'earnings', 'eps']):
                            
                            # Now extract tickers from this specific table
                            rows = table.find_elements(By.CSS_SELECTOR, 'tbody tr')
                            
                            for row in rows:
                                try:
                                    cells = row.find_elements(By.TAG_NAME, 'td')
                                    
                                    if cells:
                                        first_cell = cells[0]
                                        
                                        # Look for a link in the first cell
                                        try:
                                            link = first_cell.find_element(By.TAG_NAME, 'a')
                                            href = link.get_attribute('href')
                                            
                                            # Extract ticker from URL
                                            if href and '/quote/' in href:
                                                ticker = href.split('/quote/')[1].split('?')[0].split('/')[0]
                                                
                                                # Validate ticker format
                                                if ticker and 1 <= len(ticker) <= 10:
                                                    page_tickers.add(ticker.upper())
                                        except:
                                            pass
                                except:
                                    continue
                            
                            break  # Found the earnings table, stop looking at other tables
                            
                    except:
                        continue
                
            except Exception as e:
                st.warning(f"Error on page {page_num + 1}: {str(e)}")
            
            # Check if we found new tickers on this page
            new_tickers = page_tickers - all_tickers
            st.write(f"Page {page_num + 1}: Found {len(page_tickers)} tickers ({len(new_tickers)} new)")
            
            if not new_tickers:
                st.write("No new tickers found - pagination complete")
                break
            
            all_tickers.update(page_tickers)
            offset += size
            page_num += 1
        
        driver.quit()
        
        tickers_list = sorted(list(all_tickers))
        st.success(f"Found {len(tickers_list)} total ticker symbols from earnings calendar")
        
        return tickers_list
        
    except Exception as e:
        st.error(f"Error fetching tickers: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        if 'driver' in locals():
            driver.quit()
        return []

def calculate_tickers_change_robinhood(tickers, percent_change_threshold, time_period):
    """
    Calculate price changes using Robinhood's historical data API.
    """
    if not tickers:
        st.warning("No tickers to analyze")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    winners = []
    losers = []
    all_results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total = len(tickers)
    
    # Convert time period to Robinhood's span format
    span_mapping = {
        '1mo': 'month',
        '3mo': '3month',
        '6mo': '3month',  # Robinhood doesn't have 6mo, we'll calculate from 3month
        '1y': 'year',
        '2y': '5year',    # Use 5year and filter
        '5y': '5year'
    }
    
    # Interval mapping
    interval_mapping = {
        '1mo': 'day',
        '3mo': 'day',
        '6mo': 'day',
        '1y': 'week',
        '2y': 'week',
        '5y': 'week'
    }
    
    span = span_mapping.get(time_period, 'year')
    interval = interval_mapping.get(time_period, 'day')
    
    st.info(f"Analyzing {total} tickers ({time_period} price change using Robinhood data)...")

    for idx, ticker in enumerate(tickers):
        try:
            status_text.text(f"Processing {ticker} ({idx+1}/{total})")
            
            # Fetch historical data from Robinhood
            historical_data = r.stocks.get_stock_historicals(
                ticker,
                interval=interval,
                span=span,
                bounds='regular'
            )
            
            if historical_data and len(historical_data) >= 2:
                # Extract closing prices
                closes = []
                dates = []
                
                for item in historical_data:
                    if item.get('close_price'):
                        closes.append(float(item['close_price']))
                        dates.append(item['begins_at'])
                
                if len(closes) >= 2:
                    # Handle different time periods
                    if time_period == '6mo':
                        # Get last ~180 days from 3month data
                        cutoff_days = 180
                        # Calculate which index to start from
                        total_days = len(closes)
                        start_idx = max(0, total_days - cutoff_days)
                        first_close = closes[start_idx]
                        last_close = closes[-1]
                    elif time_period == '2y':
                        # Get last ~730 days from 5year data
                        cutoff_days = 730
                        total_days = len(closes)
                        start_idx = max(0, total_days - cutoff_days)
                        first_close = closes[start_idx]
                        last_close = closes[-1]
                    else:
                        # Standard: first to last
                        first_close = closes[0]
                        last_close = closes[-1]
                    
                    # Calculate percentage change
                    percent_change = ((last_close - first_close) / first_close) * 100
                    
                    all_results.append([ticker, round(percent_change, 2)])
                    
                    if abs(percent_change) > percent_change_threshold:
                        if percent_change > 0:
                            winners.append([ticker, round(percent_change, 2)])
                        else:
                            losers.append([ticker, round(percent_change, 2)])
                else:
                    st.warning(f"Insufficient price data for {ticker}")
            else:
                st.warning(f"No historical data available for {ticker} from Robinhood")
                
        except Exception as e:
            if len(ticker) <= 5:
                st.warning(f"Error processing {ticker}: {str(e)}")
            continue
        
        progress_bar.progress((idx + 1) / total)
    
    progress_bar.empty()
    status_text.empty()
    
    # Dynamic column name based on time period
    period_label = time_period.upper() + ' Change %'
    
    winners_df = pd.DataFrame(winners, columns=['Ticker', period_label])
    losers_df = pd.DataFrame(losers, columns=['Ticker', period_label])
    all_df = pd.DataFrame(all_results, columns=['Ticker', period_label])
    
    # Sort by percent change
    if not winners_df.empty:
        winners_df = winners_df.sort_values(period_label, ascending=False)
    if not losers_df.empty:
        losers_df = losers_df.sort_values(period_label, ascending=True)
    if not all_df.empty:
        all_df = all_df.sort_values(period_label, ascending=False)
    
    return winners_df, losers_df, all_df

# Streamlit UI
st.title('Earnings Calendar Price Change Analyzer (Robinhood Edition)')

# Sidebar for Robinhood credentials
with st.sidebar:
    st.subheader("Robinhood Credentials")
    st.markdown("**Required for fetching price data**")
    rh_username = st.text_input("Robinhood Username", "", key="rh_user")
    rh_password = st.text_input("Robinhood Password", "", type="password", key="rh_pass")
    
    if st.button("Login to Robinhood"):
        if not rh_username or not rh_password:
            st.error("Please enter both username and password")
        else:
            import os
            os.environ["ROBINHOOD_USERNAME"] = rh_username
            os.environ["ROBINHOOD_PASSWORD"] = rh_password
            
            # Attempt login
            with st.spinner("Logging in to Robinhood..."):
                login_success = login_to_robinhood()
                if login_success:
                    st.session_state["rh_logged_in"] = True
                    st.success("✅ Successfully logged in!")
                    st.rerun()
                else:
                    st.session_state["rh_logged_in"] = False
                    st.error("❌ Login failed. Check error messages above.")

# Initialize session state
if "rh_logged_in" not in st.session_state:
    st.session_state["rh_logged_in"] = False

# Check if logged in
if not st.session_state["rh_logged_in"]:
    st.warning("🔐 Please log in to Robinhood using the sidebar to continue.")
    st.info("Enter your Robinhood credentials in the sidebar and click 'Login to Robinhood'")
    st.stop()

# User inputs
specific_date = st.date_input("Select Earnings Calendar Date", datetime.today()).strftime('%Y-%m-%d')

# Time period selector
time_period = st.selectbox(
    "Select Time Period for Price Change",
    options=['1mo', '3mo', '6mo', '1y', '2y', '5y'],
    index=3,  # Default to 1y
    format_func=lambda x: {
        '1mo': '1 Month',
        '3mo': '3 Months', 
        '6mo': '6 Months',
        '1y': '1 Year',
        '2y': '2 Years',
        '5y': '5 Years'
    }[x]
)

percent_change_threshold = st.number_input("Enter Percentage Change Threshold", min_value=0, value=35)

# Button to run the analysis
if st.button('Analyze Tickers'):
    with st.spinner('Fetching tickers from Yahoo Finance earnings calendar...'):
        tickers = fetch_earnings_tickers(specific_date)
        
        if not tickers:
            st.error(f"No tickers found for {specific_date}. Please try a different date.")
        else:
            st.success(f"Found {len(tickers)} tickers for {specific_date}")
            st.write("Ticker list:", ", ".join(tickers[:20]) + ("..." if len(tickers) > 20 else ""))
            
            # Use Robinhood for price data
            winners, losers, all_results = calculate_tickers_change_robinhood(
                tickers, 
                percent_change_threshold, 
                time_period
            )
            
            st.success(f"Analysis completed using Robinhood data!")
            
            # Show summary statistics
            total_analyzed = len(tickers)
            total_extreme = len(winners) + len(losers)
            period_display = {
                '1mo': '1 month',
                '3mo': '3 months',
                '6mo': '6 months',
                '1y': '1 year',
                '2y': '2 years',
                '5y': '5 years'
            }[time_period]
            
            st.info(f"📊 {total_extreme} out of {total_analyzed} tickers ({round(total_extreme/total_analyzed*100, 1)}%) changed by more than {percent_change_threshold}% over {period_display}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Winners")
                if not winners.empty:
                    st.dataframe(winners, use_container_width=True)
                    st.metric("Total Winners", len(winners))
                else:
                    st.info(f"No winners found with >{percent_change_threshold}% threshold")
                    
            with col2:
                st.subheader("Losers")
                if not losers.empty:
                    st.dataframe(losers, use_container_width=True)
                    st.metric("Total Losers", len(losers))
                else:
                    st.info(f"No losers found with >{percent_change_threshold}% threshold")
            
            # Show all results
            st.subheader(f"📈 All Tickers - {period_display.title()} Performance")
            st.write(f"Sorted by percent change (highest to lowest)")
            st.write(f"**Data Source**: Robinhood API via robin-stocks")
            if not all_results.empty:
                st.dataframe(all_results, use_container_width=True, height=400)
