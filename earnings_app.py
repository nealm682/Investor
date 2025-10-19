
import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import logging

# Suppress Selenium logging
logging.getLogger('selenium').setLevel(logging.ERROR)
logging.getLogger('webdriver_manager').setLevel(logging.ERROR)

def fetch_earnings_tickers(specific_date):
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

def calculate_tickers_change(tickers, percent_change_threshold):
    if not tickers:
        st.warning("No tickers to analyze")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    winners = []
    losers = []
    all_results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total = len(tickers)
    st.info(f"Analyzing {total} tickers (using Yahoo Finance 52-week change data)...")

    for idx, ticker in enumerate(tickers):
        try:
            status_text.text(f"Processing {ticker} ({idx+1}/{total})")
            
            # Use Yahoo Finance's official 52-week change field
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info
            
            # Get the 52WeekChange field - this is Yahoo's official metric
            week_change = info.get('52WeekChange')
            
            if week_change is not None:
                percent_change = week_change * 100  # Convert decimal to percentage
                
                all_results.append([ticker, round(percent_change, 2)])
                
                if abs(percent_change) > percent_change_threshold:
                    if percent_change > 0:
                        winners.append([ticker, round(percent_change, 2)])
                    else:
                        losers.append([ticker, round(percent_change, 2)])
            else:
                st.warning(f"No 52-week data available for {ticker}")
                
        except Exception as e:
            if len(ticker) <= 5:
                st.warning(f"Error processing {ticker}: {str(e)}")
            continue
        
        progress_bar.progress((idx + 1) / total)
    
    progress_bar.empty()
    status_text.empty()
    
    winners_df = pd.DataFrame(winners, columns=['Ticker', '1Y Change %'])
    losers_df = pd.DataFrame(losers, columns=['Ticker', '1Y Change %'])
    all_df = pd.DataFrame(all_results, columns=['Ticker', '1Y Change %'])
    
    # Sort by percent change
    if not winners_df.empty:
        winners_df = winners_df.sort_values('1Y Change %', ascending=False)
    if not losers_df.empty:
        losers_df = losers_df.sort_values('1Y Change %', ascending=True)
    if not all_df.empty:
        all_df = all_df.sort_values('1Y Change %', ascending=False)
    
    return winners_df, losers_df, all_df

# Streamlit UI
st.title('Earnings Calendar Price Change Analyzer')

# User inputs
specific_date = st.date_input("Select Earnings Calendar Date", datetime.today()).strftime('%Y-%m-%d')
percent_change_threshold = st.number_input("Enter Percentage Change Threshold", min_value=0, value=35)

# Button to run the analysis
if st.button('Analyze Tickers'):
    with st.spinner('Fetching tickers...'):
        tickers = fetch_earnings_tickers(specific_date)
        
        if not tickers:
            st.error(f"No tickers found for {specific_date}. Please try a different date.")
        else:
            st.success(f"Found {len(tickers)} tickers for {specific_date}")
            st.write("Ticker list:", ", ".join(tickers[:20]) + ("..." if len(tickers) > 20 else ""))
            
            winners, losers, all_results = calculate_tickers_change(tickers, percent_change_threshold)
            
            st.success(f"Analysis completed!")
            
            # Show summary statistics
            total_analyzed = len(tickers)
            total_extreme = len(winners) + len(losers)
            st.info(f"📊 {total_extreme} out of {total_analyzed} tickers ({round(total_extreme/total_analyzed*100, 1)}%) changed by more than {percent_change_threshold}%")
            
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
            st.subheader("📈 All Tickers - 1 Year Performance")
            st.write(f"Sorted by percent change (highest to lowest)")
            if not all_results.empty:
                st.dataframe(all_results, use_container_width=True, height=400)

