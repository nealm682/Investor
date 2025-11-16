import streamlit as st
import pandas as pd
import requests
import time
import json
from datetime import datetime
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
SEC_HEADERS = {
    'User-Agent': 'Individual Investor-Tools/1.0 (nealm682@gmail.com)',
    'Accept': 'application/json',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive'
}

# Rate limiting for SEC API (10 requests per second max)
last_request_time = 0

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_company_tickers():
    """Load company ticker to CIK mapping from SEC"""
    try:
        st.info("🔄 Loading SEC company database...")
        rate_limit()
        
        # Use the correct SEC endpoint with proper headers
        url = "https://www.sec.gov/files/company_tickers.json"
        response = requests.get(url, headers=SEC_HEADERS, timeout=30)
        
        if response.status_code == 200:
            tickers_data = response.json()
            
            # Convert to DataFrame for easier lookup
            ticker_list = []
            for key, company in tickers_data.items():
                ticker_list.append({
                    'ticker': str(company['ticker']).upper(),
                    'cik': str(company['cik_str']).zfill(10),  # Pad CIK to 10 digits
                    'title': company['title']
                })
                
            if ticker_list:
                df = pd.DataFrame(ticker_list)
                st.success(f"✅ Loaded {len(df):,} companies from SEC database")
                return df
        
        # If we get here, there was an error
        if response.status_code == 403:
            st.error("❌ SEC API access denied. This may be due to rate limiting or blocked access.")
            st.info("""
            **Troubleshooting Steps:**
            1. Check your internet connection
            2. Wait a few minutes and try again (rate limiting)
            3. Ensure you're not behind a corporate firewall blocking SEC.gov
            4. Try running from a different network if the issue persists
            """)
        else:
            st.error(f"SEC API returned error: {response.status_code}")
            
        response.raise_for_status()
        
    except requests.exceptions.RequestException as e:
        st.error(f"Network error loading SEC ticker database: {e}")
        st.info("Please check your internet connection and try again.")
    except Exception as e:
        st.error(f"Error loading SEC ticker database: {e}")
    
    # Fallback information for manual entry
    st.warning("⚠️ Could not load SEC ticker database automatically.")
    st.info("""
    **Manual Workaround Options:**
    
    **Wait and retry**: SEC may have temporary restrictions
    
    **Common Tickers for Testing:**
    - AAPL: CIK 0000320193 (Apple)
    - MSFT: CIK 0000789019 (Microsoft) 
    - TSLA: CIK 0001318605 (Tesla)
    - GOOGL: CIK 0001652044 (Alphabet/Google)
    - AMZN: CIK 0001018724 (Amazon)
    
    **Check connectivity**: Ensure you're not behind a corporate firewall blocking SEC.gov
    """)
    
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
        response = requests.get(url, headers=SEC_HEADERS, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            st.warning(f"SEC API access denied for CIK {cik}. Possible rate limiting.")
        else:
            st.error(f"HTTP Error fetching submissions for CIK {cik}: {e}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Network error fetching submissions for CIK {cik}: {e}")
        return None

def get_company_facts(cik):
    """Get all XBRL facts for a company"""
    if not cik:
        return None
    
    rate_limit()
    url = f"{SEC_BASE_URL}/api/xbrl/companyfacts/CIK{cik:010d}.json"
    
    try:
        response = requests.get(url, headers=SEC_HEADERS, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            st.warning(f"SEC API access denied for company facts CIK {cik}. Possible rate limiting.")
        else:
            st.error(f"HTTP Error fetching company facts for CIK {cik}: {e}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Network error fetching company facts for CIK {cik}: {e}")
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

def extract_quarterly_trends(facts_data):
    """Extract quarterly financial trends for revenue, costs, and profit"""
    if not facts_data or 'facts' not in facts_data:
        return None
    
    facts = facts_data['facts']
    us_gaap = facts.get('us-gaap', {})
    
    trends = {
        'periods': [],
        'revenues': [],
        'costs': [],
        'net_income': []
    }
    
    # Revenue concepts
    revenue_concepts = ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet', 'RevenueFromContractWithCustomerIncludingAssessedTax']
    # Cost concepts
    cost_concepts = ['CostOfRevenue', 'CostOfGoodsAndServicesSold', 'OperatingExpenses']
    # Net income concepts
    income_concepts = ['NetIncomeLoss', 'NetIncomeLossAvailableToCommonStockholdersBasic']
    
    # Extract quarterly data for each metric - check ALL concepts and pick most recent
    for concept_list, data_key in [(revenue_concepts, 'revenues'), 
                                     (cost_concepts, 'costs'), 
                                     (income_concepts, 'net_income')]:
        best_quarterly_values = []
        best_date = ''
        
        for concept in concept_list:
            if concept in us_gaap:
                units = us_gaap[concept].get('units', {})
                if 'USD' in units:
                    values = units['USD']
                    # Filter for quarterly data (STRICTLY 60-120 days only)
                    quarterly_values = []
                    for v in values:
                        if v.get('val') is not None and v.get('end') and v.get('start'):
                            try:
                                start = datetime.strptime(v.get('start'), '%Y-%m-%d')
                                end = datetime.strptime(v.get('end'), '%Y-%m-%d')
                                period_days = (end - start).days
                                # Quarterly period STRICTLY 60-120 days (excludes 9-month cumulative at ~270 days)
                                if 60 <= period_days <= 120:
                                    quarterly_values.append(v)
                            except:
                                pass
                    
                    # Sort by end date (most recent first)
                    quarterly_values.sort(key=lambda x: x.get('end', ''), reverse=True)
                    
                    # Check if this concept has more recent data than what we've found so far
                    if quarterly_values and len(quarterly_values) >= 3:
                        most_recent_date = quarterly_values[0].get('end', '')
                        if most_recent_date > best_date:
                            best_date = most_recent_date
                            best_quarterly_values = quarterly_values
        
        # Use the best (most recent) quarterly values found across all concepts
        if best_quarterly_values:
            if len(best_quarterly_values) >= 3 and not trends['periods']:
                # Store periods (only once, from the first metric with data)
                trends['periods'] = [v.get('end') for v in best_quarterly_values[:3]]
                trends['periods'].reverse()  # Oldest to newest for chart
            
            # Store values for this metric
            trend_data = [v.get('val', 0) for v in best_quarterly_values[:3]]
            trend_data.reverse()  # Oldest to newest
            trends[data_key] = trend_data
    
    # Only return if we have at least revenue data and 3 periods
    if len(trends['periods']) >= 3 and trends['revenues']:
        return trends
    return None

def extract_key_financials(facts_data):
    """Extract key financial metrics from company facts - prioritizing most recent data"""
    if not facts_data or 'facts' not in facts_data:
        return {}
    
    facts = facts_data['facts']
    key_metrics = {}
    
    # Common financial concepts to look for with improved concept mapping
    concepts_to_find = {
        'Revenues': ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet', 'RevenueFromContractWithCustomerIncludingAssessedTax'],
        'NetIncome': ['NetIncomeLoss', 'ProfitLoss', 'NetIncomeLossAvailableToCommonStockholdersBasic', 'NetIncomeLossAttributableToParent'],
        'TotalAssets': ['Assets', 'AssetsCurrent', 'AssetsNoncurrent'],
        'TotalLiabilities': ['Liabilities', 'LiabilitiesAndStockholdersEquity', 'LiabilitiesCurrent'],
        'Cash': ['CashAndCashEquivalentsAtCarryingValue', 'Cash', 'CashCashEquivalentsAndShortTermInvestments', 'CashAndCashEquivalentsFairValueDisclosure'],
        'Debt': ['LongTermDebt', 'LongTermDebtCurrent', 'LongTermDebtNoncurrent', 'LongTermDebtAndCapitalLeaseObligations', 'DebtCurrent', 'ShortTermBorrowings'],
        'TotalDebt': ['DebtAndCapitalLeaseObligations', 'DebtLongtermAndShorttermCombinedAmount', 'LongTermDebt']  # Removed Liabilities fallback
    }
    
    # Look in us-gaap taxonomy
    us_gaap = facts.get('us-gaap', {})
    
    for metric_name, concept_list in concepts_to_find.items():
        best_metric = None
        best_date = ''
        
        # Check ALL concepts for this metric and find the one with most recent data
        for concept in concept_list:
            if concept in us_gaap:
                units = us_gaap[concept].get('units', {})
                if 'USD' in units:
                    values = units['USD']
                    
                    # Strategy: Get most recent data regardless of form type, but prefer more recent filings
                    # Filter out invalid/null values and sort by end date
                    valid_values = [v for v in values if v.get('val') is not None and v.get('end')]
                    
                    if valid_values:
                        # Sort by end date (most recent first)
                        valid_values.sort(key=lambda x: x.get('end', ''), reverse=True)
                        
                        # For point-in-time data (Cash, Debt, TotalDebt, Assets, Liabilities), use most recent
                        if metric_name in ['Cash', 'Debt', 'TotalDebt', 'TotalAssets', 'TotalLiabilities']:
                            # Get the most recent point-in-time value
                            most_recent = valid_values[0]
                            candidate_date = most_recent.get('end', '')
                            
                            # Only update if this concept has more recent data
                            if candidate_date > best_date:
                                best_date = candidate_date
                                best_metric = {
                                    'value': most_recent.get('val'),
                                    'date': most_recent.get('end'),
                                    'form': most_recent.get('form'),
                                    'filed': most_recent.get('filed'),
                                    'period_type': 'Point-in-Time',
                                    'concept': concept
                                }
                        else:
                            # For period data (Revenues, NetIncome), get most recent period regardless of type
                            # Sort all valid values by end date to get the absolute most recent
                            annual_values = []
                            quarterly_values = []
                            
                            for v in valid_values:
                                form = v.get('form', '')
                                start_date = v.get('start', '')
                                end_date = v.get('end', '')
                                
                                # Calculate period length if we have start and end dates
                                period_days = 0
                                if start_date and end_date:
                                    try:
                                        from datetime import datetime
                                        start = datetime.strptime(start_date, '%Y-%m-%d')
                                        end = datetime.strptime(end_date, '%Y-%m-%d')
                                        period_days = (end - start).days
                                    except:
                                        pass
                                
                                # Categorize STRICTLY by period length (ignore form type to avoid 9-month confusion)
                                if period_days >= 300:  # Annual = 300+ days
                                    annual_values.append(v)
                                elif 60 <= period_days <= 120:  # Quarterly = 60-120 days only (single quarter)
                                    quarterly_values.append(v)
                            
                            # Sort both arrays by end date (most recent first)
                            annual_values.sort(key=lambda x: x.get('end', ''), reverse=True)
                            quarterly_values.sort(key=lambda x: x.get('end', ''), reverse=True)
                            
                            # PRIORITY: Use the most recent data by date, whether annual or quarterly
                            # Compare dates if we have both types
                            selected_value = None
                            period_type = ''
                            
                            if annual_values and quarterly_values:
                                # Compare dates - use whichever is more recent
                                annual_date = annual_values[0].get('end', '')
                                quarterly_date = quarterly_values[0].get('end', '')
                                
                                if quarterly_date > annual_date:
                                    selected_value = quarterly_values[0]
                                    period_type = 'Quarterly'
                                else:
                                    selected_value = annual_values[0]
                                    period_type = 'Annual'
                            elif annual_values:
                                selected_value = annual_values[0]
                                period_type = 'Annual'
                            elif quarterly_values:
                                selected_value = quarterly_values[0]
                                period_type = 'Quarterly'
                            elif valid_values:
                                selected_value = valid_values[0]  # Fallback to most recent
                                period_type = 'Unknown Period'
                            
                            if selected_value:
                                candidate_date = selected_value.get('end', '')
                                
                                # Only update if this concept has more recent data
                                if candidate_date > best_date:
                                    best_date = candidate_date
                                    best_metric = {
                                        'value': selected_value.get('val'),
                                        'date': selected_value.get('end'),
                                        'form': selected_value.get('form'),
                                        'filed': selected_value.get('filed'),
                                        'period_type': period_type,
                                        'start_date': selected_value.get('start'),
                                        'concept': concept
                                    }
        
        # After checking all concepts for this metric, save the best one found
        if best_metric:
            key_metrics[metric_name] = best_metric
    
    return key_metrics

def analyze_financial_health(metrics):
    """Analyze financial health based on key metrics with enhanced period tracking"""
    analysis = {
        'revenue_generating': False,
        'profitable': False,
        'debt_concerns': False,
        'cash_position': 'Unknown',
        'summary': '',
        'details': {},
        'periods': {}  # Track data periods for debugging
    }
    
    # Check revenue generation
    if 'Revenues' in metrics and metrics['Revenues']['value']:
        revenue = metrics['Revenues']['value']
        revenue_data = metrics['Revenues']
        analysis['periods']['revenue'] = f"{revenue_data.get('period_type', 'Unknown')} ending {revenue_data.get('date', 'Unknown')}"
        
        if revenue > 0:
            analysis['revenue_generating'] = True
            # Format revenue with period info
            period_info = f" ({revenue_data.get('period_type', 'Unknown')} ending {revenue_data.get('date', 'Unknown')})"
            analysis['details']['revenue'] = f"${revenue:,.0f}{period_info}"
        else:
            analysis['details']['revenue'] = "No revenue reported"
    else:
        analysis['details']['revenue'] = "Revenue data not available"
    
    # Check profitability
    if 'NetIncome' in metrics and metrics['NetIncome']['value']:
        net_income = metrics['NetIncome']['value']
        net_income_data = metrics['NetIncome']
        analysis['periods']['net_income'] = f"{net_income_data.get('period_type', 'Unknown')} ending {net_income_data.get('date', 'Unknown')}"
        
        if net_income > 0:
            analysis['profitable'] = True
            period_info = f" ({net_income_data.get('period_type', 'Unknown')} ending {net_income_data.get('date', 'Unknown')})"
            analysis['details']['net_income'] = f"${net_income:,.0f} (Profit){period_info}"
        else:
            period_info = f" ({net_income_data.get('period_type', 'Unknown')} ending {net_income_data.get('date', 'Unknown')})"
            analysis['details']['net_income'] = f"${net_income:,.0f} (Loss){period_info}"
    else:
        analysis['details']['net_income'] = "Net income data not available"
    
    # Analyze debt vs cash (point-in-time data)
    cash = metrics.get('Cash', {}).get('value', 0) or 0
    debt = metrics.get('Debt', {}).get('value', 0) or 0
    total_debt = metrics.get('TotalDebt', {}).get('value', 0) or 0
    
    # Use specific debt if available, otherwise use total debt/liabilities
    effective_debt = debt if debt > 0 else total_debt
    debt_label = "Debt" if debt > 0 else "Total Liabilities"
    
    # Track cash data period
    if 'Cash' in metrics:
        cash_data = metrics['Cash']
        analysis['periods']['cash'] = f"As of {cash_data.get('date', 'Unknown')}"
        period_info = f" (As of {cash_data.get('date', 'Unknown')})"
        analysis['details']['cash'] = f"${cash:,.0f}{period_info}" if cash else f"Cash data not available"
    else:
        analysis['details']['cash'] = "Cash data not available"
    
    # Track debt data period
    if 'Debt' in metrics:
        debt_data = metrics['Debt']
        analysis['periods']['debt'] = f"As of {debt_data.get('date', 'Unknown')}"
        period_info = f" (As of {debt_data.get('date', 'Unknown')})"
        analysis['details']['debt'] = f"${debt:,.0f}{period_info}"
    elif 'TotalDebt' in metrics:
        debt_data = metrics['TotalDebt']
        analysis['periods']['debt'] = f"As of {debt_data.get('date', 'Unknown')}"
        period_info = f" (As of {debt_data.get('date', 'Unknown')})"
        analysis['details']['debt'] = f"${total_debt:,.0f} ({debt_label}){period_info}"
    else:
        # If no debt metrics found, company likely has no debt
        analysis['details']['debt'] = "$0 (No traditional debt reported)"
        if 'Cash' in metrics:
            analysis['periods']['debt'] = f"As of {metrics['Cash'].get('date', 'Unknown')}"
    
    # Cash position analysis using effective debt
    if cash > 0 and effective_debt > 0:
        cash_to_debt_ratio = cash / effective_debt
        if cash_to_debt_ratio > 2:
            analysis['cash_position'] = 'Strong'
        elif cash_to_debt_ratio > 1:
            analysis['cash_position'] = 'Adequate'
        elif effective_debt > cash * 2:
            analysis['cash_position'] = 'Concerning'
            analysis['debt_concerns'] = True
        else:
            analysis['cash_position'] = 'Moderate'
        
        analysis['details']['cash_debt_ratio'] = f"{cash_to_debt_ratio:.2f}x"
    elif cash > 0 and effective_debt == 0:
        analysis['cash_position'] = 'Excellent (No Debt)'
    elif cash == 0 and effective_debt > 0:
        analysis['cash_position'] = 'Concerning (No Cash, Has Debt)'
    else:
        analysis['cash_position'] = 'Unknown'
    
    # Generate summary with period awareness
    revenue_status = "generating revenue" if analysis['revenue_generating'] else "not generating significant revenue"
    profit_status = "profitable" if analysis['profitable'] else "unprofitable"
    
    # Add period information to summary
    latest_date = 'Unknown'
    if 'Cash' in metrics and metrics['Cash'].get('date'):
        latest_date = metrics['Cash']['date']
    elif 'NetIncome' in metrics and metrics['NetIncome'].get('date'):
        latest_date = metrics['NetIncome']['date']
    
    analysis['summary'] = f"Company is {revenue_status} and {profit_status}. Cash position: {analysis['cash_position'].lower()}. Data as of: {latest_date}"
    
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
        
        # Extract quarterly trends
        quarterly_trends = extract_quarterly_trends(facts_data)
        
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
            'key_metrics': key_metrics,
            'quarterly_trends': quarterly_trends
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
        st.error("⚠️ Could not load SEC ticker database. The tool can still work with manual ticker entry.")
        
        # Show manual entry option when database fails to load
        with st.expander("🔧 Manual Ticker Entry (Alternative)", expanded=True):
            st.markdown("""
            **You can still analyze specific companies by entering ticker and CIK manually:**
            
            1. Find the company's CIK at [SEC Company Search](https://www.sec.gov/edgar/searchedgar/companysearch.html)
            2. Use the format: TICKER,CIK (e.g., AAPL,0000320193)
            3. Upload a CSV with these columns: Ticker, CIK, Company Name
            """)
            
            # Sample data for testing
            sample_data = pd.DataFrame([
                {'Ticker': 'AAPL', 'CIK': '0000320193', 'Company Name': 'Apple Inc'},
                {'Ticker': 'MSFT', 'CIK': '0000789019', 'Company Name': 'Microsoft Corporation'},
                {'Ticker': 'TSLA', 'CIK': '0001318605', 'Company Name': 'Tesla Inc'},
                {'Ticker': 'GOOGL', 'CIK': '0001652044', 'Company Name': 'Alphabet Inc'},
                {'Ticker': 'AMZN', 'CIK': '0001018724', 'Company Name': 'Amazon.com Inc'},
                {'Ticker': 'TTMI', 'CIK': '0000755111', 'Company Name': 'TTM Technologies Inc'}
            ])
            
            st.markdown("**Sample companies you can use for testing:**")
            st.dataframe(sample_data, hide_index=True, width='stretch')
            
            # Download sample CSV
            csv_sample = sample_data.to_csv(index=False)
            st.download_button(
                label="📥 Download Sample CSV",
                data=csv_sample,
                file_name="sample_tickers_with_cik.csv",
                mime="text/csv",
                help="Use this as a template for manual ticker entry"
            )
        
        return
    
   
    # Sidebar for file upload and testing
    with st.sidebar:
        st.header("🧪 Quick Testing")
        
        # Single ticker test
        test_ticker = st.text_input("Test single ticker (e.g., TTMI, AAPL)", placeholder="Enter ticker symbol")
        if st.button("🔍 Test Ticker") and test_ticker:
            if test_ticker.upper() in ticker_df['ticker'].values:
                st.info(f"Testing {test_ticker.upper()}...")
                result = process_ticker_analysis(test_ticker.upper(), ticker_df)
                
                if result['status'] == 'Success':
                    st.success("✅ Analysis completed!")
                    
                    # Show basic results
                    st.write(f"**Company:** {result['company_name']}")
                    st.write(f"**Revenue Generating:** {'✅' if result['revenue_generating'] else '❌'}")
                    st.write(f"**Profitable:** {'✅' if result['profitable'] else '❌'}")
                    st.write(f"**Cash Position:** {result['cash_position']}")
                    
                    # Show raw metrics for debugging
                    if 'key_metrics' in result and result['key_metrics']:
                        with st.expander("Debug: Raw Data", expanded=False):
                            for metric, data in result['key_metrics'].items():
                                st.write(f"**{metric}:** ${data.get('value', 0):,.0f}")
                                st.write(f"  - Date: {data.get('date', 'Unknown')}")
                                st.write(f"  - Period: {data.get('period_type', 'Unknown')}")
                                st.write(f"  - Form: {data.get('form', 'Unknown')}")
                                st.write("---")
                else:
                    st.error(f"❌ {result['status']}: {result.get('error', 'Unknown error')}")
            else:
                st.warning(f"Ticker {test_ticker.upper()} not found in SEC database")
        
        st.markdown("---")
        
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
        
        # Dynamic max companies based on available momentum stocks
        if uploaded_file is not None:
            try:
                temp_df = pd.read_csv(uploaded_file)
                uploaded_file.seek(0)  # Reset file pointer for later reading
                if 'Momentum Filter ✓' in temp_df.columns:
                    momentum_count = len(temp_df[temp_df['Momentum Filter ✓'] == True])
                    max_limit = momentum_count if analyze_all and momentum_count > 0 else min(20, momentum_count) if momentum_count > 0 else 20
                    default_val = momentum_count if analyze_all else min(5, momentum_count) if momentum_count > 0 else 5
                    max_companies = st.slider("Max companies to analyze", 1, max(max_limit, 1), default_val)
                else:
                    max_companies = st.slider("Max companies to analyze", 1, 20, 5)
            except:
                max_companies = st.slider("Max companies to analyze", 1, 20, 5)
        else:
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
        # Reset file pointer in case it was read in sidebar
        try:
            uploaded_file.seek(0)
        except:
            pass  # Some file types don't support seek
            
        try:
            df = pd.read_csv(uploaded_file)
            
            if df.empty or len(df.columns) == 0:
                st.error("❌ The uploaded CSV file is empty. Please upload a valid CSV file with data.")
                return
                
        except pd.errors.EmptyDataError:
            st.error("❌ The uploaded CSV file is empty or has no columns. Please upload a valid CSV file.")
            return
        except Exception as e:
            st.error(f"❌ Error reading CSV file: {e}")
            return
        
        st.subheader("📋 Uploaded Data Preview")
        st.dataframe(df.head(10), width='stretch')
        
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
                        width='stretch',
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
                                                    if 'cash_debt_ratio' in details:
                                                        st.write(f"📊 **Cash/Debt Ratio:** {details.get('cash_debt_ratio', 'N/A')}")
                                                
                                                with metric_col2:
                                                    st.write(f"📈 **Net Income:** {details.get('net_income', 'N/A')}")
                                                    st.write(f"💳 **Debt:** {details.get('debt', 'N/A')}")
                                                
                                                # Add debugging information for period tracking
                                                if 'key_metrics' in result and result['key_metrics']:
                                                    with st.expander("🔍 Data Sources & Periods (Debug)", expanded=False):
                                                        debug_data = []
                                                        for metric_name, metric_data in result['key_metrics'].items():
                                                            debug_data.append({
                                                                'Metric': metric_name,
                                                                'Value': f"${metric_data.get('value', 0):,.0f}" if metric_data.get('value') else 'N/A',
                                                                'Period': metric_data.get('period_type', 'Unknown'),
                                                                'Date': metric_data.get('date', 'Unknown'),
                                                                'Form': metric_data.get('form', 'Unknown'),
                                                                'XBRL Concept': metric_data.get('concept', 'Unknown')
                                                            })
                                                        
                                                        if debug_data:
                                                            debug_df = pd.DataFrame(debug_data)
                                                            st.dataframe(debug_df, hide_index=True, width='stretch')
                                        
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
                                            elif 'Concerning' in cash_pos:
                                                cash_icon = "🔴"
                                            elif 'Excellent' in cash_pos:
                                                cash_icon = "💚"
                                            else:
                                                cash_icon = "⚪"
                                            
                                            st.write(f"{cash_icon} Cash Position: {cash_pos}")
                                        
                                        # Quarterly Trend Analysis
                                        if result.get('quarterly_trends'):
                                            st.markdown("---")
                                            with st.expander("📈 Quarterly Financial Trends (Last 3 Quarters)", expanded=False):
                                                trends = result['quarterly_trends']
                                                
                                                # Create chart data - ensure all arrays match periods length
                                                num_periods = len(trends['periods'])
                                                
                                                # Pad or truncate arrays to match periods length
                                                revenues = trends['revenues'][:num_periods] if trends['revenues'] else []
                                                revenues = revenues + [0] * (num_periods - len(revenues))  # Pad if needed
                                                
                                                costs = trends['costs'][:num_periods] if trends['costs'] else []
                                                costs = costs + [0] * (num_periods - len(costs))
                                                
                                                net_income = trends['net_income'][:num_periods] if trends['net_income'] else []
                                                net_income = net_income + [0] * (num_periods - len(net_income))
                                                
                                                chart_data = pd.DataFrame({
                                                    'Period': trends['periods'],
                                                    'Revenue': revenues,
                                                    'Costs': costs,
                                                    'Net Income': net_income
                                                })
                                                
                                                # Convert to millions for readability
                                                for col in ['Revenue', 'Costs', 'Net Income']:
                                                    if col in chart_data.columns:
                                                        chart_data[f'{col} ($M)'] = chart_data[col] / 1_000_000
                                                
                                                # Display bar chart
                                                st.write("**Financial Performance Trend (in millions):**")
                                                chart_df = chart_data[['Period', 'Revenue ($M)', 'Costs ($M)', 'Net Income ($M)']].set_index('Period')
                                                st.bar_chart(chart_df)
                                                
                                                # Calculate and display trends
                                                if len(trends['revenues']) >= 2:
                                                    rev_growth = ((trends['revenues'][-1] - trends['revenues'][0]) / trends['revenues'][0] * 100) if trends['revenues'][0] != 0 else 0
                                                    cost_growth = ((trends['costs'][-1] - trends['costs'][0]) / trends['costs'][0] * 100) if trends['costs'] and trends['costs'][0] != 0 else 0
                                                    income_growth = ((trends['net_income'][-1] - trends['net_income'][0]) / trends['net_income'][0] * 100) if trends['net_income'] and trends['net_income'][0] != 0 else 0
                                                    
                                                    trend_col1, trend_col2, trend_col3 = st.columns(3)
                                                    with trend_col1:
                                                        st.metric("Revenue Growth", f"{rev_growth:+.1f}%", 
                                                                 delta=f"${(trends['revenues'][-1] - trends['revenues'][0])/1_000_000:.1f}M")
                                                    with trend_col2:
                                                        if trends['costs']:
                                                            st.metric("Cost Growth", f"{cost_growth:+.1f}%",
                                                                     delta=f"${(trends['costs'][-1] - trends['costs'][0])/1_000_000:.1f}M")
                                                    with trend_col3:
                                                        if trends['net_income']:
                                                            st.metric("Profit Growth", f"{income_growth:+.1f}%",
                                                                     delta=f"${(trends['net_income'][-1] - trends['net_income'][0])/1_000_000:.1f}M")
                                                    
                                                    # Analysis insights
                                                    if trends['revenues'] and trends['costs'] and rev_growth > 0:
                                                        if rev_growth > cost_growth:
                                                            st.success("✅ **Positive Trend**: Revenue growing faster than costs - improving margins")
                                                        elif cost_growth > rev_growth:
                                                            st.warning("⚠️ **Watch**: Costs growing faster than revenue - margin compression")
                                                        else:
                                                            st.info("ℹ️ **Stable**: Revenue and costs growing at similar rates")
                                        
                                        if include_filings and result.get('recent_filings'):
                                            st.write("**Recent SEC Filings:**")
                                            filings_df = pd.DataFrame(result['recent_filings'])
                                            st.dataframe(filings_df, hide_index=True, width='stretch')
                                
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
                                st.dataframe(failed_df, hide_index=True, width='stretch')
                    
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
                width='stretch'
            )

if __name__ == "__main__":
    main()
