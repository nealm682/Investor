import streamlit as st
import pandas as pd
import requests
import time
import json
from datetime import datetime, timedelta
import re
import io

# Configure Streamlit page
st.set_page_config(
    page_title="Financial Analysis Tool",
    page_icon="📊",
    layout="wide"
)

# SEC API Configuration
SEC_BASE_URL = "https://data.sec.gov"
HEADERS = {
    'User-Agent': 'InvestmentAnalyzer/1.0 (github.com/nealm682/Investor)',
    'Accept': 'application/json'
}

# Rate limiting for SEC API (10 requests per second max)
last_request_time = 0

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_company_tickers():
    """Load company ticker to CIK mapping from SEC"""
    try:
        url = "https://www.sec.gov/files/company_tickers.json"
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        
        tickers_data = response.json()
        
        # Convert to DataFrame for easier lookup
        ticker_list = []
        for key, company in tickers_data.items():
            ticker_list.append({
                'ticker': company['ticker'],
                'cik': company['cik_str'],
                'title': company['title']
            })
        
        return pd.DataFrame(ticker_list)
    except Exception as e:
        st.error(f"Error loading company tickers: {e}")
        return pd.DataFrame()

def rate_limit():
    """Enforce SEC API rate limiting"""
    global last_request_time
    current_time = time.time()
    time_since_last = current_time - last_request_time
    if time_since_last < 0.1:  # 100ms between requests
        time.sleep(0.1 - time_since_last)
    last_request_time = time.time()

def get_company_cik(ticker, ticker_df):
    """Get company CIK from ticker symbol"""
    if ticker_df.empty:
        return None
    
    # Look up ticker in the DataFrame
    match = ticker_df[ticker_df['ticker'].str.upper() == ticker.upper()]
    if not match.empty:
        return int(match.iloc[0]['cik'])
    
    return None

def get_company_submissions(cik):
    """Get company submissions from SEC API"""
    if not cik:
        return None
    
    rate_limit()
    url = f"{SEC_BASE_URL}/submissions/CIK{cik:010d}.json"
    
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching submissions for CIK {cik}: {e}")
        return None

def get_company_facts(cik):
    """Get all XBRL facts for a company"""
    if not cik:
        return None
    
    rate_limit()
    url = f"{SEC_BASE_URL}/api/xbrl/companyfacts/CIK{cik:010d}.json"
    
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching company facts for CIK {cik}: {e}")
        return None

def find_recent_filings(submissions_data, form_types=['10-K', '10-Q']):
    """Find most recent 10-K and 10-Q filings"""
    if not submissions_data or 'filings' not in submissions_data:
        return []
    
    recent = submissions_data['filings']['recent']
    filings = []
    
    for i, form in enumerate(recent.get('form', [])):
        if form in form_types:
            filing = {
                'form': form,
                'filingDate': recent['filingDate'][i],
                'accessionNumber': recent['accessionNumber'][i],
                'reportDate': recent.get('reportDate', [None] * len(recent['form']))[i]
            }
            filings.append(filing)
    
    # Sort by filing date (most recent first)
    filings.sort(key=lambda x: x['filingDate'], reverse=True)
    return filings[:5]  # Return top 5 most recent

def extract_key_financials(facts_data):
    """Extract key financial metrics from company facts"""
    if not facts_data or 'facts' not in facts_data:
        return {}
    
    facts = facts_data['facts']
    key_metrics = {}
    
    # Common financial concepts to look for
    concepts_to_find = {
        'Revenues': ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet'],
        'NetIncome': ['NetIncomeLoss', 'ProfitLoss', 'NetIncomeLossAvailableToCommonStockholdersBasic'],
        'TotalAssets': ['Assets', 'AssetsCurrent'],
        'TotalLiabilities': ['Liabilities', 'LiabilitiesAndStockholdersEquity'],
        'Cash': ['CashAndCashEquivalentsAtCarryingValue', 'Cash', 'CashCashEquivalentsAndShortTermInvestments'],
        'Debt': ['DebtCurrent', 'LongTermDebt', 'DebtAndCapitalLeaseObligations']
    }
    
    # Look in us-gaap taxonomy
    us_gaap = facts.get('us-gaap', {})
    
    for metric_name, concept_list in concepts_to_find.items():
        for concept in concept_list:
            if concept in us_gaap:
                # Get the most recent annual value
                units = us_gaap[concept].get('units', {})
                if 'USD' in units:
                    values = units['USD']
                    # Filter for annual data (form 10-K) and most recent
                    annual_values = [v for v in values if v.get('form') == '10-K']
                    if annual_values:
                        # Sort by end date and get most recent
                        annual_values.sort(key=lambda x: x.get('end', ''), reverse=True)
                        key_metrics[metric_name] = {
                            'value': annual_values[0].get('val'),
                            'date': annual_values[0].get('end'),
                            'form': annual_values[0].get('form'),
                            'concept': concept
                        }
                        break
    
    return key_metrics

def analyze_financial_health(metrics):
    """Analyze financial health based on key metrics"""
    analysis = {
        'revenue_generating': False,
        'profitable': False,
        'debt_concerns': False,
        'cash_position': 'Unknown',
        'summary': '',
        'details': {}
    }
    
    # Check revenue generation
    if 'Revenues' in metrics and metrics['Revenues']['value']:
        revenue = metrics['Revenues']['value']
        if revenue > 0:
            analysis['revenue_generating'] = True
            analysis['details']['revenue'] = f"${revenue:,.0f}"
        else:
            analysis['details']['revenue'] = "No revenue reported"
    else:
        analysis['details']['revenue'] = "Revenue data not available"
    
    # Check profitability
    if 'NetIncome' in metrics and metrics['NetIncome']['value']:
        net_income = metrics['NetIncome']['value']
        if net_income > 0:
            analysis['profitable'] = True
            analysis['details']['net_income'] = f"${net_income:,.0f} (Profit)"
        else:
            analysis['details']['net_income'] = f"${net_income:,.0f} (Loss)"
    else:
        analysis['details']['net_income'] = "Net income data not available"
    
    # Analyze debt vs cash
    cash = metrics.get('Cash', {}).get('value', 0) or 0
    debt = metrics.get('Debt', {}).get('value', 0) or 0
    
    analysis['details']['cash'] = f"${cash:,.0f}" if cash else "Cash data not available"
    analysis['details']['debt'] = f"${debt:,.0f}" if debt else "Debt data not available"
    
    if cash > 0 and debt > 0:
        if cash > debt * 2:
            analysis['cash_position'] = 'Strong'
        elif cash > debt:
            analysis['cash_position'] = 'Adequate'
        elif debt > cash * 2:
            analysis['cash_position'] = 'Concerning'
            analysis['debt_concerns'] = True
        else:
            analysis['cash_position'] = 'Moderate'
    else:
        analysis['cash_position'] = 'Unknown'
    
    # Generate summary
    revenue_status = "generating revenue" if analysis['revenue_generating'] else "not generating significant revenue"
    profit_status = "profitable" if analysis['profitable'] else "unprofitable"
    
    analysis['summary'] = f"Company is {revenue_status} and {profit_status}. Cash position: {analysis['cash_position'].lower()}."
    
    return analysis

def process_ticker_analysis(ticker, ticker_df):
    """Process financial analysis for a single ticker"""
    try:
        # Get CIK
        cik = get_company_cik(ticker, ticker_df)
        if not cik:
            return {
                'ticker': ticker,
                'status': 'CIK Not Found',
                'error': f'Ticker {ticker} not found in SEC database'
            }
        
        # Get company submissions
        submissions_data = get_company_submissions(cik)
        if not submissions_data:
            return {
                'ticker': ticker,
                'status': 'Submissions Error',
                'error': 'Failed to fetch company submissions'
            }
        
        # Get company facts
        facts_data = get_company_facts(cik)
        if not facts_data:
            return {
                'ticker': ticker,
                'status': 'Facts Error',
                'error': 'Failed to fetch company financial facts'
            }
        
        # Find recent filings
        recent_filings = find_recent_filings(submissions_data)
        
        # Extract key financials
        key_metrics = extract_key_financials(facts_data)
        
        # Analyze financial health
        analysis = analyze_financial_health(key_metrics)
        
        result = {
            'ticker': ticker,
            'cik': cik,
            'company_name': submissions_data.get('name', 'Unknown'),
            'status': 'Success',
            'recent_filings': recent_filings[:3],  # Top 3 recent filings
            'revenue_generating': analysis['revenue_generating'],
            'profitable': analysis['profitable'],
            'cash_position': analysis['cash_position'],
            'debt_concerns': analysis['debt_concerns'],
            'summary': analysis['summary'],
            'financial_details': analysis['details'],
            'key_metrics': key_metrics
        }
        
        return result
        
    except Exception as e:
        return {
            'ticker': ticker,
            'status': 'Error',
            'error': str(e)
        }

# Streamlit UI
def main():
    st.title("📊 Financial Analysis Tool")
    st.markdown("Analyze financial health of companies from momentum filter results using SEC EDGAR data")
    
    # Load ticker mapping data
    with st.spinner("Loading SEC company ticker database..."):
        ticker_df = load_company_tickers()
    
    if ticker_df.empty:
        st.error("⚠️ Could not load SEC ticker database. Please check your internet connection and try again.")
        return
    
    st.success(f"✅ Loaded {len(ticker_df):,} companies from SEC database")
    
    # Sidebar for file upload
    with st.sidebar:
        st.header("📁 Data Input")
        
        # File upload
        uploaded_file = st.file_uploader(
            "Upload CSV file",
            type=['csv'],
            help="Upload your CSV file with ticker data and momentum filter column"
        )
        
        # Analysis options
        st.header("⚙️ Analysis Options")
        analyze_all = st.checkbox("Analyze all momentum stocks", value=False)
        max_companies = st.slider("Max companies to analyze", 1, 20, 5)
        
        # SEC API Options
        st.header("🔍 Analysis Depth")
        include_filings = st.checkbox("Include recent filings info", value=True)
        detailed_metrics = st.checkbox("Show detailed financial metrics", value=True)
        
        if st.button("🚀 Start Analysis", type="primary"):
            if uploaded_file is not None:
                st.session_state['start_analysis'] = True
            else:
                st.error("Please upload a CSV file first!")
    
    # Main content area
    if uploaded_file is not None:
        # Load and display CSV data
        df = pd.read_csv(uploaded_file)
        
        st.subheader("📋 Uploaded Data Preview")
        st.dataframe(df.head(10), use_container_width=True)
        
        # Filter for momentum stocks
        if 'Momentum Filter ✓' in df.columns:
            momentum_stocks = df[df['Momentum Filter ✓'] == True].copy()
            
            st.subheader(f"🎯 Momentum Stocks Found: {len(momentum_stocks)}")
            
            if len(momentum_stocks) > 0:
                col1, col2, col3 = st.columns([1, 1, 2])
                
                with col1:
                    st.metric("Total Momentum Stocks", len(momentum_stocks))
                
                with col2:
                    avg_performance = momentum_stocks['1Y Performance %'].mean() if '1Y Performance %' in momentum_stocks.columns else 0
                    st.metric("Avg 1Y Performance", f"{avg_performance:.1f}%")
                
                with col3:
                    st.dataframe(
                        momentum_stocks[['Ticker', '1Y Performance %', 'Momentum Filter ✓']].head(5),
                        use_container_width=True,
                        hide_index=True
                    )
                
                # Analysis section
                if st.session_state.get('start_analysis', False):
                    st.subheader("🔍 SEC EDGAR Financial Analysis")
                    
                    # Select tickers to analyze
                    tickers_to_analyze = momentum_stocks['Ticker'].head(max_companies).tolist()
                    
                    if tickers_to_analyze:
                        st.info(f"🔄 Starting SEC EDGAR analysis of {len(tickers_to_analyze)} companies...")
                        st.warning("⚠️ This may take a few minutes due to SEC API rate limiting (10 requests/second)")
                        
                        # Progress tracking
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        results_container = st.container()
                        
                        analysis_results = []
                        
                        for i, ticker in enumerate(tickers_to_analyze):
                            status_text.text(f"🔍 Analyzing {ticker}... ({i+1}/{len(tickers_to_analyze)})")
                            
                            # Actual SEC API analysis
                            result = process_ticker_analysis(ticker, ticker_df)
                            analysis_results.append(result)
                            
                            progress_bar.progress((i + 1) / len(tickers_to_analyze))
                            
                        # Display results
                        status_text.text("✅ Analysis complete!")
                        
                        with results_container:
                            st.subheader("📊 Analysis Results")
                            
                            # Separate successful and failed analyses
                            successful_results = [r for r in analysis_results if r['status'] == 'Success']
                            failed_results = [r for r in analysis_results if r['status'] != 'Success']
                            
                            # Summary metrics
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.metric("Analyzed", len(successful_results))
                            
                            with col2:
                                revenue_gen = sum(1 for r in successful_results if r.get('revenue_generating', False))
                                st.metric("Revenue Generating", f"{revenue_gen}/{len(successful_results)}")
                            
                            with col3:
                                profitable = sum(1 for r in successful_results if r.get('profitable', False))
                                st.metric("Profitable", f"{profitable}/{len(successful_results)}")
                            
                            with col4:
                                strong_cash = sum(1 for r in successful_results if r.get('cash_position') == 'Strong')
                                st.metric("Strong Cash Position", f"{strong_cash}/{len(successful_results)}")
                            
                            # Detailed results
                            if successful_results:
                                st.subheader("💰 Financial Health Analysis")
                                
                                for result in successful_results:
                                    with st.expander(f"🏢 {result['ticker']} - {result['company_name']}", expanded=False):
                                        col1, col2 = st.columns([2, 1])
                                        
                                        with col1:
                                            st.write("**Financial Summary:**")
                                            st.write(result['summary'])
                                            
                                            if detailed_metrics and 'financial_details' in result:
                                                st.write("**Key Metrics:**")
                                                details = result['financial_details']
                                                
                                                metric_col1, metric_col2 = st.columns(2)
                                                with metric_col1:
                                                    st.write(f"💰 **Revenue:** {details.get('revenue', 'N/A')}")
                                                    st.write(f"💵 **Cash:** {details.get('cash', 'N/A')}")
                                                
                                                with metric_col2:
                                                    st.write(f"📊 **Net Income:** {details.get('net_income', 'N/A')}")
                                                    st.write(f"💳 **Debt:** {details.get('debt', 'N/A')}")
                                        
                                        with col2:
                                            # Status indicators
                                            st.write("**Health Indicators:**")
                                            
                                            revenue_icon = "✅" if result.get('revenue_generating') else "❌"
                                            st.write(f"{revenue_icon} Revenue Generating")
                                            
                                            profit_icon = "✅" if result.get('profitable') else "❌"
                                            st.write(f"{profit_icon} Profitable")
                                            
                                            cash_pos = result.get('cash_position', 'Unknown')
                                            if cash_pos == 'Strong':
                                                cash_icon = "🟢"
                                            elif cash_pos == 'Adequate':
                                                cash_icon = "🟡"
                                            elif cash_pos == 'Concerning':
                                                cash_icon = "�"
                                            else:
                                                cash_icon = "⚪"
                                            
                                            st.write(f"{cash_icon} Cash Position: {cash_pos}")
                                        
                                        if include_filings and result.get('recent_filings'):
                                            st.write("**Recent SEC Filings:**")
                                            filings_df = pd.DataFrame(result['recent_filings'])
                                            st.dataframe(filings_df, hide_index=True, use_container_width=True)
                                
                                # Export functionality
                                st.subheader("📥 Export Results")
                                
                                # Create summary DataFrame
                                summary_data = []
                                for result in successful_results:
                                    summary_data.append({
                                        'Ticker': result['ticker'],
                                        'Company': result['company_name'],
                                        'Revenue Generating': result.get('revenue_generating', False),
                                        'Profitable': result.get('profitable', False),
                                        'Cash Position': result.get('cash_position', 'Unknown'),
                                        'Summary': result['summary']
                                    })
                                
                                summary_df = pd.DataFrame(summary_data)
                                csv_buffer = io.StringIO()
                                summary_df.to_csv(csv_buffer, index=False)
                                
                                st.download_button(
                                    label="� Download Analysis Results (CSV)",
                                    data=csv_buffer.getvalue(),
                                    file_name=f"financial_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                    mime="text/csv"
                                )
                            
                            # Show failed analyses if any
                            if failed_results:
                                st.subheader("⚠️ Analysis Issues")
                                st.warning(f"{len(failed_results)} companies could not be analyzed:")
                                
                                failed_df = pd.DataFrame([
                                    {'Ticker': r['ticker'], 'Status': r['status'], 'Error': r.get('error', 'Unknown error')}
                                    for r in failed_results
                                ])
                                st.dataframe(failed_df, hide_index=True, use_container_width=True)
                    
                    # Reset analysis flag
                    st.session_state['start_analysis'] = False
            else:
                st.warning("No stocks found with Momentum Filter ✓ = True")
        else:
            st.error("CSV file must contain 'Momentum Filter ✓' column")
    else:
        # Welcome screen
        st.markdown("""
        ### Welcome to the SEC EDGAR Financial Analysis Tool! 👋
        
        This tool analyzes the financial health of momentum stocks using official SEC EDGAR data:
        
        1. **📁 Loading your CSV data** with momentum filter results
        2. **🎯 Filtering for momentum stocks** (where Momentum Filter ✓ = True)
        3. **🔍 Fetching SEC financial data** using official EDGAR APIs
        4. **📊 Analyzing key metrics** like revenue, profitability, cash, and debt
        5. **📈 Providing financial insights** with detailed health analysis
        
        **🆕 Real SEC Data Integration:**
        - Direct access to SEC EDGAR database
        - Real-time company financials from 10-K/10-Q filings
        - Revenue, net income, cash, and debt analysis
        - Recent filing information
        - Export capabilities for further analysis
        
        **To get started:**
        - Upload your CSV file using the sidebar
        - Configure analysis options (number of companies to analyze)
        - Click "Start Analysis" to begin SEC data retrieval
        
        **Rate Limiting Notice:** SEC APIs are limited to 10 requests per second, so analysis may take a few minutes for multiple companies.
        """)
        
        # Show sample of available companies
        if not ticker_df.empty:
            st.subheader("📈 Sample Companies in SEC Database")
            sample_companies = ticker_df.sample(min(10, len(ticker_df)))
            st.dataframe(
                sample_companies[['ticker', 'title']].rename(columns={'ticker': 'Ticker', 'title': 'Company Name'}),
                hide_index=True,
                use_container_width=True
            )

if __name__ == "__main__":
    main()
