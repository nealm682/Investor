
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
    """Fetch earnings tickers for a specific date"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        all_tickers = set()
        
        # Pagination loop
        offset = 0
        size = 100
        max_pages = 10
        page_num = 0
        
        while page_num < max_pages:
            url = f'https://finance.yahoo.com/calendar/earnings?day={specific_date}&offset={offset}&size={size}'
            
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
                st.warning(f"Error on page {page_num + 1} for {specific_date}: {str(e)}")
            
            # Check if we found new tickers on this page
            new_tickers = page_tickers - all_tickers
            
            if not new_tickers:
                break
            
            all_tickers.update(page_tickers)
            offset += size
            page_num += 1
        
        driver.quit()
        
        return sorted(list(all_tickers))
        
    except Exception as e:
        st.error(f"Error fetching tickers for {specific_date}: {str(e)}")
        if 'driver' in locals():
            driver.quit()
        return []

def calculate_tickers_change(tickers, percent_change_threshold, time_period):
    if not tickers:
        st.warning("No tickers to analyze")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    winners = []
    all_results = []
    filtered_winners = []  # Winners that pass the momentum filter
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total = len(tickers)
    st.info(f"Analyzing {total} tickers ({time_period} price change)...")

    for idx, ticker in enumerate(tickers):
        try:
            status_text.text(f"Processing {ticker} ({idx+1}/{total})")
            
            # Download historical data for the specified period
            hist = yf.download(ticker, period=time_period, progress=False, auto_adjust=True)
            
            if not hist.empty and len(hist) >= 2:
                # Handle multi-level columns if present
                if isinstance(hist.columns, pd.MultiIndex):
                    hist.columns = hist.columns.get_level_values(0)
                
                # Get first and last closing prices for selected period
                first_close = float(hist['Close'].iloc[0])
                last_close = float(hist['Close'].iloc[-1])
                
                # Calculate percentage change for selected period
                percent_change = ((last_close - first_close) / first_close) * 100
                
                # Add to all results (simplified, just the main period data)
                all_results.append([ticker, round(percent_change, 2)])
                
                # Get 1-year and 5-year data for momentum check (only for potential winners)
                one_year_change = None
                five_year_change = None
                passes_momentum_filter = False
                
                if percent_change > percent_change_threshold:
                    try:
                        # Get 1-year data
                        hist_1y = yf.download(ticker, period='1y', progress=False, auto_adjust=True)
                        if not hist_1y.empty and len(hist_1y) >= 2:
                            if isinstance(hist_1y.columns, pd.MultiIndex):
                                hist_1y.columns = hist_1y.columns.get_level_values(0)
                            one_year_change = ((float(hist_1y['Close'].iloc[-1]) - float(hist_1y['Close'].iloc[0])) / float(hist_1y['Close'].iloc[0])) * 100
                        
                        # Get 5-year data
                        hist_5y = yf.download(ticker, period='5y', progress=False, auto_adjust=True)
                        if not hist_5y.empty and len(hist_5y) >= 2:
                            if isinstance(hist_5y.columns, pd.MultiIndex):
                                hist_5y.columns = hist_5y.columns.get_level_values(0)
                            five_year_change = ((float(hist_5y['Close'].iloc[-1]) - float(hist_5y['Close'].iloc[0])) / float(hist_5y['Close'].iloc[0])) * 100
                        
                        # Apply momentum filter: 5-year change should be greater than 1-year change
                        if one_year_change is not None and five_year_change is not None:
                            passes_momentum_filter = five_year_change > one_year_change
                        
                    except Exception as momentum_error:
                        st.warning(f"Could not get momentum data for {ticker}: {str(momentum_error)}")
                    
                    # Create winner row with momentum data
                    winner_row = [ticker, round(percent_change, 2)]
                    if one_year_change is not None:
                        winner_row.append(round(one_year_change, 2))
                    else:
                        winner_row.append(None)
                    if five_year_change is not None:
                        winner_row.append(round(five_year_change, 2))
                    else:
                        winner_row.append(None)
                    winner_row.append(passes_momentum_filter)
                    
                    winners.append(winner_row)
                    
                    # Add to filtered winners if it passes momentum filter
                    if passes_momentum_filter:
                        filtered_winners.append(winner_row)
            else:
                st.warning(f"Insufficient data for {ticker}")
                # Still add to all_results with None value
                all_results.append([ticker, None])
                
        except Exception as e:
            if len(ticker) <= 5:
                st.warning(f"Error processing {ticker}: {str(e)}")
            # Add to all_results with None value for failed tickers
            all_results.append([ticker, None])
            continue
        
        progress_bar.progress((idx + 1) / total)
    
    progress_bar.empty()
    status_text.empty()
    
    # Dynamic column name based on time period
    period_label = time_period.upper() + ' Performance %'
    
    # Create DataFrames with momentum columns for winners
    winner_columns = [
        'Ticker', 
        period_label, 
        '1Y Change %', 
        '5Y Change %', 
        'Momentum Filter ✓'
    ]
    
    winners_df = pd.DataFrame(winners, columns=winner_columns) if winners else pd.DataFrame()
    filtered_winners_df = pd.DataFrame(filtered_winners, columns=winner_columns) if filtered_winners else pd.DataFrame()
    
    # All results simplified (just ticker and main period performance)
    all_df = pd.DataFrame(all_results, columns=['Ticker', period_label]) if all_results else pd.DataFrame()
    
    # Sort by percent change (handle empty DataFrames)
    if not winners_df.empty:
        winners_df = winners_df.sort_values(period_label, ascending=False)
    if not filtered_winners_df.empty:
        filtered_winners_df = filtered_winners_df.sort_values(period_label, ascending=False)
    if not all_df.empty and period_label in all_df.columns:
        # Only sort non-null values
        all_df = all_df.sort_values(period_label, ascending=False, na_position='last')
    
    return winners_df, filtered_winners_df, all_df

def get_company_info(ticker):
    """Get company business summary and other key info"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        return {
            'business_summary': info.get('businessSummary', 'Business summary not available'),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'market_cap': info.get('marketCap', 'N/A'),
            'employees': info.get('fullTimeEmployees', 'N/A'),
            'website': info.get('website', 'N/A'),
            'company_name': info.get('longName', ticker)
        }
    except Exception as e:
        return {
            'business_summary': f'Could not retrieve company information: {str(e)}',
            'sector': 'N/A',
            'industry': 'N/A', 
            'market_cap': 'N/A',
            'employees': 'N/A',
            'website': 'N/A',
            'company_name': ticker
        }

def create_ticker_card(ticker_data, company_info):
    """Create a card display for a ticker with chart and company info"""
    ticker = ticker_data[0]
    performance = ticker_data[1]
    one_year = ticker_data[2]
    five_year = ticker_data[3]
    
    with st.container():
        st.markdown(f"""
        <div style="
            border: 2px solid #1f77b4;
            border-radius: 10px;
            padding: 20px;
            margin: 10px 0;
            background-color: #f8f9fa;
        ">
        """, unsafe_allow_html=True)
        
        # Header with ticker and company name
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown(f"### 📈 {ticker}")
            st.markdown(f"**5Y:** +{five_year:.1f}%")
            st.markdown(f"**1Y:** +{one_year:.1f}%")
        
        with col2:
            st.markdown(f"#### {company_info['company_name']}")
            st.markdown(f"**Sector:** {company_info['sector']}")
            st.markdown(f"**Industry:** {company_info['industry']}")
        
        # Get and display 5-year chart
        try:
            hist_5y = yf.download(ticker, period='5y', progress=False, auto_adjust=True)
            if not hist_5y.empty:
                # Handle multi-level columns
                if isinstance(hist_5y.columns, pd.MultiIndex):
                    hist_5y.columns = hist_5y.columns.get_level_values(0)
                
                st.markdown("**5-Year Price Chart:**")
                st.line_chart(hist_5y['Close'])
            else:
                st.warning("Chart data not available")
        except Exception as e:
            st.warning(f"Could not load chart: {str(e)}")
        
        # Business summary
        st.markdown("**Business Summary:**")
        summary = company_info['business_summary']
        if len(summary) > 500:
            summary = summary[:500] + "..."
        st.write(summary)
        
        # Additional info in columns
        info_col1, info_col2, info_col3 = st.columns(3)
        with info_col1:
            if company_info['market_cap'] != 'N/A':
                st.metric("Market Cap", f"${company_info['market_cap']:,}" if isinstance(company_info['market_cap'], int) else str(company_info['market_cap']))
        with info_col2:
            if company_info['employees'] != 'N/A':
                st.metric("Employees", f"{company_info['employees']:,}" if isinstance(company_info['employees'], int) else str(company_info['employees']))
        with info_col3:
            if company_info['website'] != 'N/A':
                st.markdown(f"[Company Website]({company_info['website']})")
        
        st.markdown("</div>", unsafe_allow_html=True)

# Streamlit UI
st.title('Earnings Calendar Price Change Analyzer')

# Enhanced date filtering options
st.subheader("📅 Date Selection Options")

# Radio button for filtering mode
filter_mode = st.radio(
    "Choose your date filtering approach:",
    ["Single Date", "Date Range", "Multiple Specific Dates"],
    horizontal=True
)

# Date inputs based on selected mode
selected_dates = []

if filter_mode == "Single Date":
    single_date = st.date_input("Select Earnings Calendar Date", datetime.today())
    selected_dates = [single_date.strftime('%Y-%m-%d')]
    st.info(f"Selected: {single_date.strftime('%B %d, %Y')}")

elif filter_mode == "Date Range":
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", datetime.today() - timedelta(days=7))
    with col2:
        end_date = st.date_input("End Date", datetime.today())
    
    if start_date <= end_date:
        # Check for weekend/holiday warnings
        current_date = start_date
        business_days = 0
        weekend_days = 0
        
        while current_date <= end_date:
            if current_date.weekday() < 5:  # Monday = 0, Friday = 4
                business_days += 1
            else:
                weekend_days += 1
            current_date += timedelta(days=1)
        
        total_days = (end_date - start_date).days + 1
        
        # Generate all dates in the range
        current_date = start_date
        while current_date <= end_date:
            selected_dates.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)
        
        st.info(f"📅 **Date range:** {start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}")
        st.info(f"📊 **Total:** {total_days} days • **Business days:** {business_days} • **Weekends:** {weekend_days}")
        
        if weekend_days > 0:
            st.warning(f"⚠️ Note: {weekend_days} weekend days included. Earnings calendars typically have limited activity on weekends.")
    else:
        st.error("❌ Start date must be before or equal to end date!")

elif filter_mode == "Multiple Specific Dates":
    st.write("Add up to 10 specific dates:")
    
    # Initialize session state for multiple dates if not exists
    if 'earnings_dates' not in st.session_state:
        st.session_state.earnings_dates = []
    
    # Add new date
    col1, col2 = st.columns([3, 1])
    with col1:
        new_date = st.date_input("Select a date to add", datetime.today(), key="new_date_input")
    with col2:
        if st.button("➕ Add Date", key="add_date"):
            date_str = new_date.strftime('%Y-%m-%d')
            if date_str not in st.session_state.earnings_dates and len(st.session_state.earnings_dates) < 10:
                st.session_state.earnings_dates.append(date_str)
                st.rerun()
    
    # Display current dates
    if st.session_state.earnings_dates:
        st.write("**Selected dates:**")
        for i, date_str in enumerate(st.session_state.earnings_dates):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"{i+1}. {datetime.strptime(date_str, '%Y-%m-%d').strftime('%B %d, %Y')}")
            with col2:
                if st.button("🗑️", key=f"remove_{i}", help="Remove this date"):
                    st.session_state.earnings_dates.pop(i)
                    st.rerun()
        
        # Clear all button
        if st.button("🗑️ Clear All Dates"):
            st.session_state.earnings_dates = []
            st.rerun()
        
        selected_dates = st.session_state.earnings_dates.copy()
        st.info(f"Total selected: {len(selected_dates)} dates")
    else:
        st.info("No dates selected yet. Add dates using the controls above.")

# Analysis options
st.subheader("⚙️ Analysis Settings")

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

percent_change_threshold = st.number_input("Enter Percentage Change Threshold (%)", min_value=0, value=70)

# Button to run the analysis
if st.button('🚀 Analyze Tickers'):
    if not selected_dates:
        st.error("Please select at least one date before running the analysis!")
    else:
        # Combine all tickers from selected dates
        all_tickers = set()
        date_results = {}  # Track results per date
        
        # Create progress tracking
        total_dates = len(selected_dates)
        date_progress = st.progress(0)
        date_status = st.empty()
        
        with st.spinner('Fetching tickers from selected dates...'):
            for i, date in enumerate(selected_dates):
                date_status.text(f"Processing date {i+1}/{total_dates}: {datetime.strptime(date, '%Y-%m-%d').strftime('%B %d, %Y')}")
                
                tickers_for_date = fetch_earnings_tickers(date)
                date_results[date] = tickers_for_date
                
                if tickers_for_date:
                    all_tickers.update(tickers_for_date)
                    st.success(f"✅ {date}: Found {len(tickers_for_date)} tickers")
                else:
                    st.warning(f"⚠️ {date}: No tickers found")
                
                # Update progress
                date_progress.progress((i + 1) / total_dates)
        
        # Clear progress indicators
        date_progress.empty()
        date_status.empty()
        
        # Convert to sorted list
        final_tickers = sorted(list(all_tickers))
        
        if not final_tickers:
            st.error("No tickers found for any of the selected dates. Please try different dates.")
        else:
            # Display summary
            date_summary = ""
            if len(selected_dates) == 1:
                date_summary = f"earnings date {selected_dates[0]}"
            else:
                date_summary = f"{len(selected_dates)} selected dates"
            
            st.success(f"🎯 Found {len(final_tickers)} unique tickers across {date_summary}")
            
            # Show breakdown per date if multiple dates
            if len(selected_dates) > 1:
                with st.expander("📊 Breakdown by Date", expanded=False):
                    breakdown_data = []
                    for date in selected_dates:
                        count = len(date_results.get(date, []))
                        breakdown_data.append({
                            'Date': datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d (%a)'),
                            'Tickers Found': count,
                            'Sample Tickers': ', '.join(date_results.get(date, [])[:5]) + ('...' if count > 5 else '')
                        })
                    
                    breakdown_df = pd.DataFrame(breakdown_data)
                    st.dataframe(breakdown_df, use_container_width=True)
            
            # Show sample of tickers
            if len(final_tickers) > 20:
                st.write("**Sample tickers:**", ", ".join(final_tickers[:20]) + f"... (and {len(final_tickers)-20} more)")
            else:
                st.write("**All tickers:**", ", ".join(final_tickers))
            
            # Run the analysis
            winners, filtered_winners, all_results = calculate_tickers_change(final_tickers, percent_change_threshold, time_period)
            
            st.success(f"✅ Analysis completed!")
            
            # Show summary statistics
            total_analyzed = len(final_tickers)
            total_winners = len(winners)
            period_display = {
                '1mo': '1 month',
                '3mo': '3 months',
                '6mo': '6 months',
                '1y': '1 year',
                '2y': '2 years',
                '5y': '5 years'
            }[time_period]
            
            st.info(f"📊 {total_winners} out of {total_analyzed} tickers ({round(total_winners/total_analyzed*100, 1)}%) gained more than {percent_change_threshold}% over {period_display}")
            
            # Add momentum filter summary
            if not winners.empty:
                momentum_pass_count = len(filtered_winners)
                st.info(f"🚀 {momentum_pass_count} out of {len(winners)} winners ({round(momentum_pass_count/len(winners)*100, 1)}%) pass the momentum filter (5Y > 1Y performance)")
            
            # Create filename suffix based on date selection
            if len(selected_dates) == 1:
                filename_suffix = selected_dates[0]
            else:
                filename_suffix = f"{selected_dates[0]}_to_{selected_dates[-1]}" if len(selected_dates) > 1 else "multiple_dates"
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🏆 Filtered Winners")
                st.caption("Winners that pass momentum filter (5Y > 1Y)")
                if not filtered_winners.empty:
                    st.dataframe(filtered_winners, use_container_width=True)
                    st.metric("Filtered Winners", len(filtered_winners))
                    
                    # Download button for filtered winners
                    csv = filtered_winners.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Filtered Winners CSV",
                        data=csv,
                        file_name=f"filtered_winners_{filename_suffix}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info(f"No winners pass the momentum filter")
                    
            with col2:
                st.subheader("All Winners")
                if not winners.empty:
                    st.dataframe(winners, use_container_width=True)
                    st.metric("Total Winners", len(winners))
                    
                    # Download button for all winners
                    csv = winners.to_csv(index=False)
                    st.download_button(
                        label="📥 Download All Winners CSV",
                        data=csv,
                        file_name=f"all_winners_{filename_suffix}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info(f"No winners found with >{percent_change_threshold}% threshold")
            
            # Show detailed cards for filtered winners
            if not filtered_winners.empty:
                st.markdown("---")
                st.subheader("🎯 Detailed Analysis - Top Momentum Winners")
                st.caption("Companies with 5-year performance exceeding 1-year performance")
                
                # Limit to top 10 for performance
                top_filtered = filtered_winners.head(10)
                if len(filtered_winners) > 10:
                    st.info(f"Showing top 10 out of {len(filtered_winners)} filtered winners")
                
                # Create cards for each filtered winner
                for idx, row in top_filtered.iterrows():
                    with st.spinner(f"Loading details for {row['Ticker']}..."):
                        company_info = get_company_info(row['Ticker'])
                        create_ticker_card(row.values, company_info)
            else:
                st.info("No filtered winners to display detailed cards for.")

