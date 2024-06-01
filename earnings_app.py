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
    options.add_argument("--headless")  # Runs Chrome in headless mode.
    options.add_experimental_option('excludeSwitches', ['enable-logging'])  # Suppresses logging
    # Specify the version of Chrome driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install('91.0.4472.19')), options=options)
    tickers_list = []
    offset = 0
    size = 100

    while True:
        url = f'https://finance.yahoo.com/calendar/earnings?day={specific_date}&offset={offset}&size={size}'
        driver.get(url)
        time.sleep(5)
        tickers = driver.find_elements(By.CSS_SELECTOR, 'a[data-test="quoteLink"]')
        if not tickers:
            break
        tickers_list.extend([ticker.text for ticker in tickers])
        offset += size
    driver.quit()
    return tickers_list

def calculate_tickers_change(tickers, percent_change_threshold):
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')
    winners = []
    losers = []
    counter = 0

    for ticker in tickers:
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        counter += 1
        if not data.empty:
            start_close = data.iloc[0]['Close']
            end_close = data.iloc[-1]['Close']
            percent_change = ((end_close - start_close) / start_close) * 100
            if abs(percent_change) > percent_change_threshold:
                if percent_change > 0:
                    winners.append([ticker, percent_change])
                else:
                    losers.append([ticker, percent_change])
    winners_df = pd.DataFrame(winners, columns=['Ticker', 'Percent Change'])
    losers_df = pd.DataFrame(losers, columns=['Ticker', 'Percent Change'])
    return winners_df, losers_df

# Streamlit UI
st.title('Earnings Calendar Price Change Analyzer')

# User inputs
specific_date = st.date_input("Select Earnings Calendar Date", datetime.today()).strftime('%Y-%m-%d')
percent_change_threshold = st.number_input("Enter Percentage Change Threshold", min_value=0, value=35)

# Button to run the analysis
if st.button('Analyze Tickers'):
    with st.spinner('Fetching tickers...'):
        tickers = fetch_earnings_tickers(specific_date)
        if tickers:
            winners, losers = calculate_tickers_change(tickers, percent_change_threshold)
            st.success(f"Analysis completed for {specific_date}")
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Winners")
                st.dataframe(winners)
            with col2:
                st.subheader("Losers")
                st.dataframe(losers)
        else:
            st.error("No tickers found for the selected date.")


'''
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
    options.add_argument("--headless")  # Runs Chrome in headless mode.
    options.add_experimental_option('excludeSwitches', ['enable-logging'])  # Suppresses logging
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    tickers_list = []
    offset = 0
    size = 100

    while True:
        url = f'https://finance.yahoo.com/calendar/earnings?day={specific_date}&offset={offset}&size={size}'
        driver.get(url)
        time.sleep(5)
        tickers = driver.find_elements(By.CSS_SELECTOR, 'a[data-test="quoteLink"]')
        if not tickers:
            break
        tickers_list.extend([ticker.text for ticker in tickers])
        offset += size
    driver.quit()
    return tickers_list

def calculate_tickers_change(tickers, percent_change_threshold):
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')
    winners = []
    losers = []
    counter = 0

    for ticker in tickers:
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        counter += 1
        if not data.empty:
            start_close = data.iloc[0]['Close']
            end_close = data.iloc[-1]['Close']
            percent_change = ((end_close - start_close) / start_close) * 100
            if abs(percent_change) > percent_change_threshold:
                if percent_change > 0:
                    winners.append([ticker, percent_change])
                else:
                    losers.append([ticker, percent_change])
    winners_df = pd.DataFrame(winners, columns=['Ticker', 'Percent Change'])
    losers_df = pd.DataFrame(losers, columns=['Ticker', 'Percent Change'])
    return winners_df, losers_df

# Streamlit UI
st.title('Earnings Calendar Price Change Analyzer')

# User inputs
specific_date = st.date_input("Select Earnings Calendar Date", datetime.today()).strftime('%Y-%m-%d')
percent_change_threshold = st.number_input("Enter Percentage Change Threshold", min_value=0, value=35)

# Button to run the analysis
if st.button('Analyze Tickers'):
    with st.spinner('Fetching tickers...'):
        tickers = fetch_earnings_tickers(specific_date)
        if tickers:
            winners, losers = calculate_tickers_change(tickers, percent_change_threshold)
            st.success(f"Analysis completed for {specific_date}")
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Winners")
                st.dataframe(winners)
            with col2:
                st.subheader("Losers")
                st.dataframe(losers)
        else:
            st.error("No tickers found for the selected date.")
'''
