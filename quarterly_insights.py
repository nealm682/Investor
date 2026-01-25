import streamlit as st
import pandas as pd
import sys
import io
import re
sys.path.append('c:\\Users\\nealm\\Investor')

# Import utilities from financials.py
from financials import (
    load_company_tickers,
    get_company_cik,
    get_company_facts,
    get_company_submissions,
    rate_limit,
    get_current_stock_price,
    SEC_HEADERS,
    SEC_BASE_URL,
    openai_client
)
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import requests
import yfinance as yf

# Configure Streamlit
st.set_page_config(
    page_title="8-Quarter Trend Analyzer",
    page_icon="📊",
    layout="wide"
)

# Configuration Constants
QUARTERLY_METRICS_CONFIG = {
    # Direct XBRL extraction
    'revenue': ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet', 'RevenueFromContractWithCustomerIncludingAssessedTax'],
    'gross_profit': ['GrossProfit'],
    'operating_income': ['OperatingIncomeLoss'],
    'net_income': ['NetIncomeLoss', 'ProfitLoss', 'NetIncomeLossAvailableToCommonStockholdersBasic'],
    'operating_cash_flow': ['NetCashProvidedByUsedInOperatingActivities'],
    'capex': ['PaymentsToAcquirePropertyPlantAndEquipment', 'CapitalExpendituresIncurred'],
    'eps': ['EarningsPerShareBasic', 'EarningsPerShareDiluted'],
    'shares_outstanding': ['WeightedAverageNumberOfSharesOutstandingBasic'],
    'cost_of_revenue': ['CostOfRevenue', 'CostOfGoodsAndServicesSold'],

    # Calculated later
    'revenue_growth': 'CALCULATED',
    'gross_margin': 'CALCULATED',
    'operating_margin': 'CALCULATED',
    'net_margin': 'CALCULATED',
    'free_cash_flow': 'CALCULATED',
    'fcf_margin': 'CALCULATED'
}

# Balance sheet metrics (point-in-time, need special handling)
BALANCE_SHEET_METRICS = {
    'cash': ['CashAndCashEquivalentsAtCarryingValue', 'Cash', 'CashCashEquivalentsAndShortTermInvestments'],
    'total_debt': ['LongTermDebt', 'DebtCurrent', 'ShortTermBorrowings', 'LongTermDebtAndCapitalLeaseObligations'],
    'current_assets': ['AssetsCurrent'],
    'current_liabilities': ['LiabilitiesCurrent'],
    'stockholders_equity': ['StockholdersEquity'],

    # Calculated
    'net_cash': 'CALCULATED',
    'working_capital': 'CALCULATED',
    'current_ratio': 'CALCULATED',
    'debt_to_equity': 'CALCULATED'
}

# ============================================================================
# CORE DATA EXTRACTION FUNCTIONS
# ============================================================================

def extract_8quarter_trends(facts_data, metrics_config):
    """
    Extract 8 quarters of data for configured metrics

    Based on financials.py extract_quarterly_trends() but:
    - Extracts 8 quarters instead of 6
    - Supports 17 metrics instead of 3
    - Handles multiple data types (USD, shares, USD-per-shares)
    """
    if not facts_data or 'facts' not in facts_data:
        return None

    us_gaap = facts_data['facts'].get('us-gaap', {})
    trends = {
        'periods': [],
        'metadata': {}
    }

    # For each metric in config
    for metric_name, concepts in metrics_config.items():
        if concepts == 'CALCULATED':
            continue  # Skip calculated metrics

        best_quarterly_values = []
        best_date = ''
        best_concept = None

        # Try each concept variation (fallback pattern)
        for concept in concepts:
            if concept in us_gaap:
                units = us_gaap[concept].get('units', {})

                # Determine unit type (USD, shares, USD-per-shares)
                unit_key = None
                if 'USD' in units:
                    unit_key = 'USD'
                elif 'shares' in units:
                    unit_key = 'shares'
                elif 'USD-per-shares' in units:
                    unit_key = 'USD-per-shares'

                if not unit_key:
                    continue

                values = units[unit_key]
                quarterly_values = []

                # Filter for quarterly periods (60-120 days)
                for v in values:
                    if v.get('val') is not None and v.get('end') and v.get('start'):
                        try:
                            start = datetime.strptime(v.get('start'), '%Y-%m-%d')
                            end = datetime.strptime(v.get('end'), '%Y-%m-%d')
                            period_days = (end - start).days

                            # STRICT 60-120 day filter (avoids 9-month cumulative)
                            if 60 <= period_days <= 120:
                                quarterly_values.append(v)
                        except:
                            pass

                # Sort by end date (most recent first)
                quarterly_values.sort(key=lambda x: x.get('end', ''), reverse=True)

                # Check if this concept has more recent data
                if quarterly_values and len(quarterly_values) >= 8:
                    most_recent_date = quarterly_values[0].get('end', '')
                    if most_recent_date > best_date:
                        best_date = most_recent_date
                        best_quarterly_values = quarterly_values
                        best_concept = concept

        # Store the best quarterly values found (first 8 quarters)
        if best_quarterly_values:
            if len(best_quarterly_values) >= 8 and not trends['periods']:
                trends['periods'] = [v.get('end') for v in best_quarterly_values[:8]]
                trends['periods'].reverse()  # Oldest to newest

            trend_data = [v.get('val', 0) for v in best_quarterly_values[:8]]
            trend_data.reverse()  # Oldest to newest
            trends[metric_name] = trend_data
            trends['metadata'][metric_name] = {
                'concept': best_concept,
                'unit': unit_key if 'unit_key' in locals() else 'USD'
            }

    # Only return if we have at least revenue and 8 periods
    if len(trends['periods']) >= 8 and 'revenue' in trends:
        return trends
    return None

def extract_balance_sheet_metrics(facts_data, quarter_dates):
    """
    Extract balance sheet items (point-in-time) aligned to quarter end dates

    Args:
        facts_data: XBRL company facts
        quarter_dates: List of quarter end dates from period data ['2024-03-31', ...]

    Returns:
        Dict with metric name -> list of values aligned to quarter_dates
    """
    us_gaap = facts_data['facts'].get('us-gaap', {})
    bs_trends = {}

    for metric_name, concepts in BALANCE_SHEET_METRICS.items():
        if concepts == 'CALCULATED':
            continue

        # Find all point-in-time values for this metric
        best_values = []
        for concept in concepts:
            if concept in us_gaap:
                units = us_gaap[concept].get('units', {})
                if 'USD' in units or 'shares' in units:
                    unit_key = 'USD' if 'USD' in units else 'shares'
                    values = units[unit_key]

                    # Filter for values with only 'end' date (no 'start' = point-in-time)
                    pit_values = [v for v in values if v.get('val') is not None and v.get('end') and not v.get('start')]

                    if len(pit_values) > len(best_values):
                        best_values = pit_values

        # Align to quarter end dates (within 5 days tolerance)
        aligned_values = []
        for q_date in quarter_dates:
            q_dt = datetime.strptime(q_date, '%Y-%m-%d')
            closest_val = None
            closest_diff = 999

            for v in best_values:
                v_dt = datetime.strptime(v['end'], '%Y-%m-%d')
                diff_days = abs((v_dt - q_dt).days)

                if diff_days < closest_diff and diff_days <= 5:  # Within 5 days
                    closest_diff = diff_days
                    closest_val = v['val']

            aligned_values.append(closest_val or 0)

        bs_trends[metric_name] = aligned_values

    return bs_trends

def calculate_derived_metrics(trends):
    """
    Calculate margins, ratios, and growth rates from extracted data
    """
    # Revenue growth % (QoQ)
    if 'revenue' in trends:
        growth_rates = [0]  # First quarter has no prior comparison
        for i in range(1, len(trends['revenue'])):
            if trends['revenue'][i-1] != 0:
                growth = ((trends['revenue'][i] - trends['revenue'][i-1]) / trends['revenue'][i-1]) * 100
                growth_rates.append(growth)
            else:
                growth_rates.append(0)
        trends['revenue_growth'] = growth_rates

    # Margins (as percentages)
    if 'gross_profit' in trends and 'revenue' in trends:
        trends['gross_margin'] = [(gp / rev * 100 if rev != 0 else 0)
                                  for gp, rev in zip(trends['gross_profit'], trends['revenue'])]

    if 'operating_income' in trends and 'revenue' in trends:
        trends['operating_margin'] = [(oi / rev * 100 if rev != 0 else 0)
                                      for oi, rev in zip(trends['operating_income'], trends['revenue'])]

    if 'net_income' in trends and 'revenue' in trends:
        trends['net_margin'] = [(ni / rev * 100 if rev != 0 else 0)
                                for ni, rev in zip(trends['net_income'], trends['revenue'])]

    # Free Cash Flow
    if 'operating_cash_flow' in trends and 'capex' in trends:
        trends['free_cash_flow'] = [ocf - abs(capex) for ocf, capex in
                                    zip(trends['operating_cash_flow'], trends['capex'])]

        if 'revenue' in trends:
            trends['fcf_margin'] = [(fcf / rev * 100 if rev != 0 else 0)
                                   for fcf, rev in zip(trends['free_cash_flow'], trends['revenue'])]

    # Balance sheet ratios
    if 'cash' in trends and 'total_debt' in trends:
        trends['net_cash'] = [c - d for c, d in zip(trends['cash'], trends['total_debt'])]

    if 'current_assets' in trends and 'current_liabilities' in trends:
        trends['working_capital'] = [ca - cl for ca, cl in
                                     zip(trends['current_assets'], trends['current_liabilities'])]
        trends['current_ratio'] = [(ca / cl if cl != 0 else 0)
                                   for ca, cl in zip(trends['current_assets'], trends['current_liabilities'])]

    if 'total_debt' in trends and 'stockholders_equity' in trends:
        trends['debt_to_equity'] = [(d / e if e != 0 else 0)
                                   for d, e in zip(trends['total_debt'], trends['stockholders_equity'])]

    return trends

# ============================================================================
# MD&A EXTRACTION FUNCTIONS
# ============================================================================

def get_recent_filings_list(cik, form_types=['10-K', '10-Q'], limit=2):
    """
    Get list of recent filings with accession numbers and primary documents

    Returns:
        [{'form': '10-Q', 'date': '2024-11-15', 'accession': '...', 'primary_doc': '...'}]
    """
    submissions = get_company_submissions(cik)
    if not submissions or 'filings' not in submissions:
        return []

    recent = submissions['filings']['recent']
    filings = []

    for i, form in enumerate(recent.get('form', [])):
        if form in form_types and len(filings) < limit:
            primary_doc = recent.get('primaryDocument', [None] * len(recent['form']))[i]
            if primary_doc:  # Only add if primary document exists
                filing = {
                    'form': form,
                    'date': recent['filingDate'][i],
                    'accession': recent['accessionNumber'][i],
                    'primary_doc': primary_doc
                }
                filings.append(filing)

    return filings

def fetch_filing_html(cik, accession, primary_doc):
    """
    Download filing HTML from SEC EDGAR Archives

    URL format: /Archives/edgar/data/{CIK}/{accession_no_dashes}/{primary_doc}
    """
    # Remove dashes from accession number
    accession_plain = accession.replace('-', '')

    # Remove leading zeros from CIK for URL
    cik_num = int(cik)

    url = f"https://www.sec.gov/Archives/edgar/data/{cik_num}/{accession_plain}/{primary_doc}"

    rate_limit()
    try:
        response = requests.get(url, headers=SEC_HEADERS, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        return None

def extract_subsection(text, keywords, max_length=1000):
    """
    Find paragraphs containing keywords and extract surrounding context
    """
    text_lower = text.lower()
    matches = []

    for keyword in keywords:
        pos = text_lower.find(keyword)
        if pos != -1:
            # Extract paragraph around keyword (500 chars before, 500 after)
            start = max(0, pos - 500)
            end = min(len(text), pos + 500)
            matches.append(text[start:end])

    if matches:
        return ' ... '.join(matches[:2])[:max_length]  # First 2 matches
    return "Not found in filing"

def parse_mda_section(html, form_type):
    """
    Extract MD&A section from 10-K (Item 7) or 10-Q (Item 2)

    Returns:
        {
            'full_text': "...",
            'guidance': "...",
            'liquidity': "...",
            'risks': "..."
        }
    """
    if not html:
        return {'error': 'No HTML provided'}

    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()

    # Determine which Item to look for
    item_num = "7" if form_type == "10-K" else "2"

    # Multiple regex patterns to catch Item variations
    patterns = [
        rf'Item\s+{item_num}[\.:]\s+Management\'?s?\s+Discussion',
        rf'ITEM\s+{item_num}[\.:]\s+MANAGEMENT',
        rf'<b>Item\s+{item_num}\.?</b>.*?Management',
    ]

    # Find start of MD&A section
    mda_start = None
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            mda_start = match.start()
            break

    if not mda_start:
        return {'error': f'Could not find Item {item_num} in filing'}

    # Find end of MD&A (next Item number)
    next_item_num = str(int(item_num) + 1)
    next_item_pattern = rf'Item\s+{next_item_num}[\.:]\s'
    next_match = re.search(next_item_pattern, text[mda_start + 100:], re.IGNORECASE)

    if next_match:
        mda_end = mda_start + 100 + next_match.start()
    else:
        mda_end = mda_start + 50000  # Take next 50k chars if no boundary found

    mda_text = text[mda_start:mda_end]

    # Extract specific subsections using keyword search
    result = {
        'full_text': mda_text[:10000],  # First 10k chars
        'guidance': extract_subsection(mda_text, ['outlook', 'guidance', 'forward-looking', 'expect']),
        'liquidity': extract_subsection(mda_text, ['liquidity', 'capital resources', 'cash flow']),
        'risks': extract_subsection(mda_text, ['risk', 'uncertainty', 'challenge'])
    }

    return result

def extract_mda_insights(cik, num_filings=2):
    """
    Complete MD&A extraction pipeline
    """
    filings_list = get_recent_filings_list(cik, form_types=['10-K', '10-Q'], limit=num_filings)

    if not filings_list:
        return {'error': 'No recent filings found', 'filings': []}

    mda_data = {'filings': [], 'error': None}

    for filing in filings_list:
        html = fetch_filing_html(cik, filing['accession'], filing['primary_doc'])
        if html:
            parsed = parse_mda_section(html, filing['form'])
            filing_mda = {
                'form': filing['form'],
                'date': filing['date'],
                **parsed
            }
            mda_data['filings'].append(filing_mda)

    return mda_data

# ============================================================================
# AI ANALYSIS FUNCTIONS
# ============================================================================

def detect_trend_patterns(trends):
    """
    Detect key patterns in 8-quarter trends
    """
    patterns = []

    # 1. Margin compression/expansion
    if 'net_margin' in trends and len(trends['net_margin']) >= 2:
        margin_change = trends['net_margin'][-1] - trends['net_margin'][0]
        if margin_change < -5:
            patterns.append({
                'type': 'margin_compression',
                'severity': 'high',
                'description': f"Net margin declined {margin_change:.1f}% over 2 years"
            })
        elif margin_change > 5:
            patterns.append({
                'type': 'margin_expansion',
                'severity': 'positive',
                'description': f"Net margin expanded {margin_change:.1f}% over 2 years"
            })

    # 2. Accelerating/decelerating growth
    if 'revenue_growth' in trends and len(trends['revenue_growth']) >= 8:
        recent_avg = sum(trends['revenue_growth'][-4:]) / 4
        earlier_avg = sum(trends['revenue_growth'][:4]) / 4

        if earlier_avg != 0 and recent_avg > earlier_avg * 1.5:
            patterns.append({
                'type': 'accelerating_growth',
                'severity': 'positive',
                'description': f"Revenue growth accelerating: {recent_avg:.1f}% (recent) vs {earlier_avg:.1f}% (earlier)"
            })
        elif earlier_avg != 0 and recent_avg < earlier_avg * 0.5 and recent_avg > 0:
            patterns.append({
                'type': 'decelerating_growth',
                'severity': 'warning',
                'description': f"Revenue growth decelerating: {recent_avg:.1f}% (recent) vs {earlier_avg:.1f}% (earlier)"
            })

    # 3. Cash burn analysis (for unprofitable companies)
    if 'free_cash_flow' in trends and 'cash' in trends:
        avg_fcf = sum(trends['free_cash_flow'][-4:]) / 4
        latest_cash = trends['cash'][-1]

        if avg_fcf < 0 and latest_cash > 0:
            runway_quarters = latest_cash / abs(avg_fcf) if avg_fcf != 0 else 999
            if runway_quarters < 4:
                patterns.append({
                    'type': 'cash_burn',
                    'severity': 'critical',
                    'description': f"Cash runway critically low: ~{runway_quarters:.1f} quarters remaining"
                })

    # 4. Operating leverage
    if 'revenue' in trends and 'gross_profit' in trends and len(trends['revenue']) >= 2:
        rev_growth = ((trends['revenue'][-1] / trends['revenue'][0]) - 1) * 100 if trends['revenue'][0] != 0 else 0

        if 'cost_of_revenue' in trends:
            cost_start = trends['cost_of_revenue'][0]
            cost_end = trends['cost_of_revenue'][-1]

            if cost_start != 0:
                cost_growth = ((cost_end / cost_start) - 1) * 100
                if rev_growth > cost_growth + 5:
                    patterns.append({
                        'type': 'operating_leverage',
                        'severity': 'positive',
                        'description': f"Positive operating leverage: revenue (+{rev_growth:.1f}%) outpacing costs (+{cost_growth:.1f}%)"
                    })

    return patterns

def generate_8quarter_trend_analysis(ticker, company_name, trends, mda_data, patterns):
    """
    AI-powered trend analysis using OpenAI
    """
    if not openai_client:
        return None

    # Calculate key metrics
    rev_cagr = ((trends['revenue'][-1] / trends['revenue'][0]) ** (1/2) - 1) * 100 if trends['revenue'][0] != 0 else 0
    margin_change = trends['net_margin'][-1] - trends['net_margin'][0] if 'net_margin' in trends and len(trends['net_margin']) >= 2 else 0
    latest_fcf = trends['free_cash_flow'][-1] / 1_000_000 if 'free_cash_flow' in trends and len(trends['free_cash_flow']) > 0 else 0

    # Format trend data
    def format_trend(values):
        if not values or len(values) < 2:
            return "N/A"
        return f"[{values[0]:.0f} → {values[-1]:.0f}] (change: {((values[-1]/values[0]-1)*100):.1f}%)" if values[0] != 0 else f"[{values[0]:.0f} → {values[-1]:.0f}]"

    # Build prompt
    margin_text = f"[{trends['operating_margin'][0]:.1f}% → {trends['operating_margin'][-1]:.1f}%]" if 'operating_margin' in trends and len(trends.get('operating_margin', [])) >= 2 else 'N/A'
    fcf_text = f"${trends['free_cash_flow'][-1]/1e6:.0f}M" if 'free_cash_flow' in trends and len(trends['free_cash_flow']) > 0 else 'N/A'

    prompt = f"""Analyze 8-quarter financial trends for {company_name} ({ticker}):

TREND DATA (8 Quarters):
- Revenue: {format_trend([r/1e9 for r in trends['revenue']])} ($B)
- Net Income: {format_trend([ni/1e6 for ni in trends.get('net_income', [0]*8)])} ($M)
- Operating Margin: {margin_text}
- Free Cash Flow: {fcf_text} (latest quarter)

CALCULATED METRICS:
- 2-Year Revenue CAGR: {rev_cagr:.1f}%
- Margin trajectory: {margin_change:+.1f}%
- Latest FCF: ${latest_fcf:.0f}M

DETECTED PATTERNS:
{chr(10).join([f"- {p['description']}" for p in patterns]) if patterns else '- No significant patterns detected'}

MANAGEMENT COMMENTARY (Latest Filing):
{mda_data['filings'][0].get('guidance', 'N/A')[:500] if mda_data and mda_data.get('filings') else 'No MD&A data available'}

Provide concise analysis (300 words max):
1. TRAJECTORY: Is the business improving, stable, or deteriorating?
2. INFLECTION POINTS: Key changes in the 8-quarter trend
3. MANAGEMENT ALIGNMENT: Does commentary match actual numbers?
4. CRITICAL RISKS: What to monitor going forward
5. INVESTMENT IMPLICATION: Is the growth story intact or fading?

Use plain business language. Format numbers normally (e.g., $14.5M, not scientific notation).
"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a financial analyst providing trend analysis for retirement investors. Focus on sustainability, risks, and long-term viability."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.3
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        return None

# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================

def get_company_overview(ticker, cik):
    """
    Get company overview from SEC and yfinance

    Returns:
        Dict with description, sector, industry, employees, website, etc.
    """
    overview = {}

    # Get SEC business description
    try:
        submissions = get_company_submissions(cik)
        if submissions:
            overview['description'] = submissions.get('description', '')
            overview['fiscal_year_end'] = submissions.get('fiscalYearEnd', '')
    except Exception:
        pass

    # Get yfinance company info
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        overview['sector'] = info.get('sector', 'N/A')
        overview['industry'] = info.get('industry', 'N/A')
        overview['employees'] = info.get('fullTimeEmployees', 'N/A')
        overview['website'] = info.get('website', 'N/A')
        overview['market_cap'] = info.get('marketCap', 0)

        # Fallback to yfinance description if SEC doesn't have one
        if not overview.get('description'):
            overview['description'] = info.get('longBusinessSummary', 'No description available')
    except Exception:
        pass

    return overview

def get_price_data(ticker, period):
    """
    Fetch historical price data using yfinance

    Args:
        ticker: Stock symbol
        period: Time period ('1mo', '3mo', '6mo', '1y', '2y', '5y', 'max')

    Returns:
        DataFrame with Date and Close price
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)

        if hist.empty:
            return None

        # Reset index to make Date a column
        hist = hist.reset_index()

        # Keep only Date and Close columns
        price_data = pd.DataFrame({
            'Date': hist['Date'],
            'Close': hist['Close']
        })

        return price_data
    except Exception:
        return None

def render_company_overview(overview):
    """
    Display company overview section with key info
    """
    if not overview:
        return

    st.subheader("📋 Company Overview")

    # Key stats in columns
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        sector = overview.get('sector', 'N/A')
        st.metric("Sector", sector)

    with col2:
        industry = overview.get('industry', 'N/A')
        st.metric("Industry", industry)

    with col3:
        employees = overview.get('employees', 'N/A')
        if isinstance(employees, int):
            employees_str = f"{employees:,}"
        else:
            employees_str = employees
        st.metric("Full Time Employees", employees_str)

    with col4:
        fiscal_year = overview.get('fiscal_year_end', 'N/A')
        if fiscal_year and fiscal_year != 'N/A':
            # Format as "Month DD" (e.g., "0930" -> "September 27")
            try:
                month = fiscal_year[:2]
                day = fiscal_year[2:]
                month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                              'July', 'August', 'September', 'October', 'November', 'December']
                fiscal_display = f"{month_names[int(month)]} {int(day)}"
            except:
                fiscal_display = fiscal_year
        else:
            fiscal_display = 'N/A'
        st.metric("Fiscal Year Ends", fiscal_display)

    # Business description
    description = overview.get('description', '')
    if description and description != 'N/A':
        with st.expander("📄 Business Description", expanded=False):
            st.write(description)

    # Website link
    website = overview.get('website', '')
    if website and website != 'N/A':
        st.markdown(f"**Website:** [{website}]({website})")

    st.markdown("---")

def render_price_chart(ticker):
    """
    Display interactive price chart with multiple time frame options
    """
    st.subheader(f"📈 Price Chart - {ticker}")

    # Time period selector buttons
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

    with col1:
        if st.button("1M", key="1m"):
            st.session_state['price_period'] = '1mo'
    with col2:
        if st.button("3M", key="3m"):
            st.session_state['price_period'] = '3mo'
    with col3:
        if st.button("6M", key="6m"):
            st.session_state['price_period'] = '6mo'
    with col4:
        if st.button("1Y", key="1y"):
            st.session_state['price_period'] = '1y'
    with col5:
        if st.button("2Y", key="2y"):
            st.session_state['price_period'] = '2y'
    with col6:
        if st.button("5Y", key="5y"):
            st.session_state['price_period'] = '5y'
    with col7:
        if st.button("MAX", key="max"):
            st.session_state['price_period'] = 'max'

    # Default to 1 year if not set
    if 'price_period' not in st.session_state:
        st.session_state['price_period'] = '1y'

    period = st.session_state['price_period']

    # Fetch and display price data
    with st.spinner(f"Loading {period} price data..."):
        price_data = get_price_data(ticker, period)

    if price_data is not None and not price_data.empty:
        # Calculate price change
        start_price = price_data['Close'].iloc[0]
        end_price = price_data['Close'].iloc[-1]
        price_change = ((end_price - start_price) / start_price) * 100

        # Display metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Current Price", f"${end_price:.2f}")
        with col2:
            st.metric("Period Change", f"{price_change:+.2f}%")
        with col3:
            period_display = period.replace('mo', ' month').replace('y', ' year').upper()
            st.metric("Time Period", period_display)

        # Plot the chart
        chart_data = price_data.set_index('Date')
        st.line_chart(chart_data['Close'])
    else:
        st.warning(f"⚠️ Could not load price data for {ticker}")

    st.markdown("---")

def render_growth_charts(trends):
    """Display revenue, growth rate, and EPS charts"""
    st.subheader("📈 Growth Metrics (8 Quarters)")

    # Revenue and Growth Rate
    st.write("**Revenue & Growth Rate**")
    chart_data = pd.DataFrame({
        'Period': trends['periods'],
        'Revenue ($M)': [r / 1_000_000 for r in trends['revenue']],
        'Growth %': trends.get('revenue_growth', [0]*8)
    })
    chart_df = chart_data.set_index('Period')
    st.line_chart(chart_df)

    # Calculate 2-year CAGR
    cagr = ((trends['revenue'][-1] / trends['revenue'][0]) ** (1/2) - 1) * 100 if trends['revenue'][0] != 0 else 0
    st.metric("2-Year Revenue CAGR", f"{cagr:+.1f}%")

    # EPS Trend
    if 'eps' in trends:
        st.write("**Earnings Per Share**")
        eps_data = pd.DataFrame({
            'Period': trends['periods'],
            'EPS ($)': trends['eps']
        })
        st.line_chart(eps_data.set_index('Period'))

def render_profitability_charts(trends):
    """Display income and margin charts"""
    st.subheader("💰 Profitability Analysis (8 Quarters)")

    # Income metrics
    st.write("**Income Breakdown (in millions)**")
    income_data = pd.DataFrame({
        'Period': trends['periods'],
        'Gross Profit ($M)': [gp / 1_000_000 for gp in trends.get('gross_profit', [0]*8)],
        'Operating Income ($M)': [oi / 1_000_000 for oi in trends.get('operating_income', [0]*8)],
        'Net Income ($M)': [ni / 1_000_000 for ni in trends.get('net_income', [0]*8)]
    })
    st.line_chart(income_data.set_index('Period'))

    # Margins
    st.write("**Margin Trends (%)**")
    margin_data = pd.DataFrame({
        'Period': trends['periods'],
        'Gross Margin %': trends.get('gross_margin', [0]*8),
        'Operating Margin %': trends.get('operating_margin', [0]*8),
        'Net Margin %': trends.get('net_margin', [0]*8)
    })
    st.line_chart(margin_data.set_index('Period'))

    # Margin expansion/compression
    if 'net_margin' in trends and len(trends['net_margin']) >= 2:
        net_margin_change = trends['net_margin'][-1] - trends['net_margin'][0]
        if net_margin_change > 2:
            st.success(f"✅ Margin expansion: +{net_margin_change:.1f}% over 2 years")
        elif net_margin_change < -2:
            st.warning(f"⚠️ Margin compression: {net_margin_change:.1f}% over 2 years")

def render_cashflow_charts(trends):
    """Display OCF, CapEx, and FCF charts"""
    st.subheader("💵 Cash Flow Performance (8 Quarters)")

    # Check if we have cash flow data
    has_ocf = 'operating_cash_flow' in trends
    has_capex = 'capex' in trends

    if not has_ocf and not has_capex:
        st.warning("⚠️ Cash flow data not available for this company")
        return

    st.write("**Cash Flow Components (in millions)**")
    cf_data = pd.DataFrame({
        'Period': trends['periods'],
        'Operating CF ($M)': [ocf / 1_000_000 for ocf in trends.get('operating_cash_flow', [0]*8)],
        'CapEx ($M)': [abs(capex) / 1_000_000 for capex in trends.get('capex', [0]*8)],
        'Free CF ($M)': [fcf / 1_000_000 for fcf in trends.get('free_cash_flow', [0]*8)]
    })
    st.line_chart(cf_data.set_index('Period'))

    if 'fcf_margin' in trends:
        st.write("**FCF Margin %**")
        fcf_margin_data = pd.DataFrame({
            'Period': trends['periods'],
            'FCF Margin %': trends['fcf_margin']
        })
        st.line_chart(fcf_margin_data.set_index('Period'))
    elif has_ocf and not has_capex:
        st.info("💡 Free Cash Flow Margin not calculated (CapEx data unavailable)")

def render_balance_sheet_charts(trends):
    """Display cash, debt, and working capital charts"""
    st.subheader("🏦 Balance Sheet Health (8 Quarters)")

    st.write("**Liquidity Position (in millions)**")
    bs_data = pd.DataFrame({
        'Period': trends['periods'],
        'Cash ($M)': [c / 1_000_000 for c in trends.get('cash', [0]*8)],
        'Total Debt ($M)': [d / 1_000_000 for d in trends.get('total_debt', [0]*8)],
        'Net Cash ($M)': [nc / 1_000_000 for nc in trends.get('net_cash', [0]*8)]
    })
    st.line_chart(bs_data.set_index('Period'))

    if 'working_capital' in trends:
        st.write("**Working Capital (in millions)**")
        wc_data = pd.DataFrame({
            'Period': trends['periods'],
            'Working Capital ($M)': [wc / 1_000_000 for wc in trends['working_capital']]
        })
        st.line_chart(wc_data.set_index('Period'))

    if 'current_ratio' in trends:
        st.metric("Latest Current Ratio", f"{trends['current_ratio'][-1]:.2f}")

# ============================================================================
# MAIN ANALYSIS FUNCTION
# ============================================================================

def analyze_ticker(ticker, ticker_df, include_mda, ai_analysis):
    """
    Complete analysis pipeline for a single ticker
    """
    # Get CIK
    cik = get_company_cik(ticker, ticker_df)
    if not cik:
        return {'error': f'Ticker {ticker} not found in SEC database'}

    # Get company facts
    facts_data = get_company_facts(cik)
    if not facts_data:
        return {'error': 'Failed to fetch company financials'}

    # Extract 8-quarter trends
    trends = extract_8quarter_trends(facts_data, QUARTERLY_METRICS_CONFIG)
    if not trends:
        return {'error': 'Could not extract 8 quarters of data (company may be too new or data unavailable)'}

    # Extract balance sheet metrics
    bs_trends = extract_balance_sheet_metrics(facts_data, trends['periods'])
    trends.update(bs_trends)

    # Calculate derived metrics
    trends = calculate_derived_metrics(trends)

    # Get company name
    submissions = get_company_submissions(cik)
    company_name = submissions.get('name', 'Unknown') if submissions else 'Unknown'

    # Get company overview (description, sector, industry, etc.)
    overview = get_company_overview(ticker, cik)

    # MD&A extraction (if enabled)
    mda_data = None
    if include_mda:
        with st.spinner("Extracting MD&A from SEC filings..."):
            mda_data = extract_mda_insights(cik, num_filings=2)

    # Detect patterns
    patterns = detect_trend_patterns(trends)

    # AI analysis (if enabled)
    ai_insights = None
    if ai_analysis and openai_client:
        with st.spinner("Generating AI trend analysis..."):
            ai_insights = generate_8quarter_trend_analysis(ticker, company_name, trends, mda_data, patterns)

    return {
        'ticker': ticker,
        'company_name': company_name,
        'overview': overview,
        'trends': trends,
        'mda_data': mda_data,
        'patterns': patterns,
        'ai_insights': ai_insights,
        'error': None
    }

# ============================================================================
# UI DISPLAY FUNCTIONS
# ============================================================================

def display_overview_tab(result):
    """Display overview metrics and summary"""
    trends = result['trends']

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        latest_revenue = trends['revenue'][-1] / 1_000_000_000
        st.metric("Latest Revenue", f"${latest_revenue:.2f}B")

    with col2:
        cagr = ((trends['revenue'][-1] / trends['revenue'][0]) ** (1/2) - 1) * 100 if trends['revenue'][0] != 0 else 0
        st.metric("2Y Revenue CAGR", f"{cagr:+.1f}%")

    with col3:
        latest_margin = trends['net_margin'][-1] if 'net_margin' in trends else 0
        st.metric("Latest Net Margin", f"{latest_margin:.1f}%")

    with col4:
        latest_fcf = trends['free_cash_flow'][-1] / 1_000_000 if 'free_cash_flow' in trends else 0
        st.metric("Latest FCF", f"${latest_fcf:.0f}M")

    # Summary chart
    st.write("**Revenue & Net Income Trend**")
    summary_data = pd.DataFrame({
        'Period': trends['periods'],
        'Revenue ($M)': [r / 1_000_000 for r in trends['revenue']],
        'Net Income ($M)': [ni / 1_000_000 for ni in trends.get('net_income', [0]*8)]
    })
    st.line_chart(summary_data.set_index('Period'))

    # Detected patterns
    if result.get('patterns'):
        st.write("**Detected Trend Patterns:**")
        for pattern in result['patterns']:
            if pattern['severity'] == 'positive':
                st.success(f"✅ {pattern['description']}")
            elif pattern['severity'] == 'critical':
                st.error(f"🔴 {pattern['description']}")
            elif pattern['severity'] == 'warning':
                st.warning(f"⚠️ {pattern['description']}")
            else:
                st.info(f"ℹ️ {pattern['description']}")

def display_mda_insights(mda_data):
    """Display MD&A extracted insights"""
    st.markdown("---")
    st.subheader("📄 MD&A Highlights from SEC Filings")

    if mda_data.get('error'):
        st.warning(f"⚠️ MD&A extraction: {mda_data['error']}")
        return

    if not mda_data.get('filings'):
        st.info("No MD&A data available")
        return

    for filing in mda_data['filings']:
        with st.expander(f"{filing['form']} filed {filing['date']}", expanded=True):
            if filing.get('error'):
                st.warning(f"Could not parse: {filing['error']}")
                continue

            st.write("**Forward Guidance:**")
            st.info(filing.get('guidance', 'Not found'))

            st.write("**Liquidity & Capital Resources:**")
            st.info(filing.get('liquidity', 'Not found'))

            st.write("**Risks & Challenges:**")
            st.info(filing.get('risks', 'Not found'))

def display_analysis_results(result, export_csv):
    """Display results in tabbed interface"""
    trends = result['trends']
    company_name = result['company_name']
    ticker = result['ticker']
    overview = result.get('overview', {})

    # Header
    current_price = get_current_stock_price(ticker)
    st.header(f"📊 {ticker} - {company_name}")
    st.subheader(f"Current Price: {current_price}")

    # Company overview (displayed first)
    if overview:
        render_company_overview(overview)

    # Price chart with time frame options
    render_price_chart(ticker)

    # Quick stats in sidebar
    with st.sidebar:
        st.markdown("---")
        st.subheader("📊 Quick Stats")
        st.write(f"**Quarters Analyzed:** {len(trends['periods'])}")

        metrics_count = sum(1 for key in trends.keys() if key not in ['periods', 'metadata'])
        st.write(f"**Metrics Available:** {metrics_count}")

        if result.get('mda_data') and result['mda_data'].get('filings'):
            st.write(f"**MD&A Filings:** {len(result['mda_data']['filings'])}")

        if result.get('ai_insights'):
            st.write("**AI Analysis:** ✓ Generated")

    # Create tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Overview",
        "📈 Growth",
        "💰 Profitability",
        "💵 Cash Flow",
        "🏦 Balance Sheet",
        "🤖 AI Insights"
    ])

    with tab1:
        display_overview_tab(result)

    with tab2:
        render_growth_charts(trends)

    with tab3:
        render_profitability_charts(trends)

    with tab4:
        render_cashflow_charts(trends)

    with tab5:
        render_balance_sheet_charts(trends)

    with tab6:
        if result.get('ai_insights'):
            st.subheader("🤖 AI Trend Analysis")
            st.info(result['ai_insights'])
        else:
            st.warning("AI analysis not available. Enable OpenAI API key in .env file.")

        if result.get('mda_data'):
            display_mda_insights(result['mda_data'])

    # Export
    if export_csv:
        st.markdown("---")
        st.subheader("📥 Export Data")
        csv_data = trends_to_csv(trends, ticker)
        st.download_button(
            "📥 Download 8Q Data (CSV)",
            csv_data,
            f"{ticker}_8quarter_trends_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv"
        )

def trends_to_csv(trends, ticker):
    """Convert trends data to CSV format"""
    # Build DataFrame from trends
    data_dict = {'Period': trends['periods']}

    # Add all metrics
    for key, values in trends.items():
        if key not in ['periods', 'metadata'] and isinstance(values, list):
            data_dict[key] = values

    df = pd.DataFrame(data_dict)

    # Convert to CSV
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue()

def display_welcome_screen():
    """Display welcome screen when no analysis is running"""
    st.markdown("""
    ### Welcome to the 8-Quarter Financial Trend Analyzer! 👋

    This tool provides deep-dive analysis of companies using 8 quarters (2 years) of financial data:

    **Features:**
    - 📊 **17 Financial Metrics** - Revenue, margins, cash flow, balance sheet health
    - 📈 **8-Quarter Trends** - See how metrics evolve over 2 years
    - 📄 **MD&A Insights** - Automated extraction from SEC 10-K/10-Q filings
    - 🤖 **AI Analysis** - Pattern detection and trend interpretation
    - 💾 **Export Data** - Download all metrics to CSV

    **Metrics Analyzed:**

    **Growth:** Revenue, Revenue Growth %, EPS

    **Profitability:** Gross Profit/Margin, Operating Income/Margin, Net Income/Margin

    **Cash Flow:** Operating Cash Flow, CapEx, Free Cash Flow, FCF Margin

    **Balance Sheet:** Cash, Total Debt, Net Cash, Working Capital, Current Ratio

    **Capital Structure:** Shares Outstanding, Debt-to-Equity

    **To get started:**
    1. Enter a ticker symbol in the sidebar (e.g., AAPL, SOFI, PLTR)
    2. Configure analysis options (MD&A, AI, Export)
    3. Click "🚀 Analyze 8 Quarters"
    4. Review results across 6 tabs

    **Note:** Analysis takes 30-60 seconds due to SEC API rate limiting and MD&A extraction.
    """)

    # Sample tickers
    st.subheader("💡 Try These Tickers")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.write("**Established:**")
        st.write("• AAPL (Apple)")
        st.write("• MSFT (Microsoft)")
        st.write("• GOOGL (Alphabet)")

    with col2:
        st.write("**Growth:**")
        st.write("• SOFI (SoFi)")
        st.write("• PLTR (Palantir)")
        st.write("• TTMI (TTM Tech)")

    with col3:
        st.write("**Analysis Tips:**")
        st.write("• 8Q shows long-term trends")
        st.write("• MD&A reveals strategy")
        st.write("• AI spots inflection points")

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    st.title("📊 8-Quarter Financial Trend Analyzer")
    st.markdown("Deep-dive analysis of 17 key metrics over 2 years")

    # Load ticker database
    with st.spinner("Loading SEC company database..."):
        ticker_df = load_company_tickers()

    if ticker_df.empty:
        st.error("Could not load SEC ticker database. Please check your internet connection.")
        return

    # Sidebar
    with st.sidebar:
        st.header("🔍 Ticker Analysis")
        ticker_input = st.text_input("Enter ticker symbol", placeholder="AAPL", key="ticker_input")

        st.subheader("⚙️ Analysis Options")
        include_mda = st.checkbox("Include MD&A insights", value=True,
                                  help="Extract management commentary from SEC filings (adds 20-30 seconds)")
        ai_analysis = st.checkbox("AI trend analysis", value=True,
                                  help="Generate AI-powered insights (requires OpenAI API key)")
        export_csv = st.checkbox("Export data to CSV", value=False)

        analyze_btn = st.button("🚀 Analyze 8 Quarters", type="primary")

        if analyze_btn and ticker_input:
            st.session_state['ticker'] = ticker_input.upper()
            st.session_state['run_analysis'] = True
            st.session_state['include_mda'] = include_mda
            st.session_state['ai_analysis'] = ai_analysis
            st.session_state['export_csv'] = export_csv
            # Clear previous results when starting new analysis
            if 'result' in st.session_state:
                del st.session_state['result']
            # Reset price period to default for new ticker
            st.session_state['price_period'] = '1y'

    # Main analysis
    if st.session_state.get('run_analysis') and st.session_state.get('ticker'):
        ticker = st.session_state['ticker']
        include_mda = st.session_state.get('include_mda', True)
        ai_analysis = st.session_state.get('ai_analysis', True)
        export_csv = st.session_state.get('export_csv', False)

        # Run analysis
        with st.spinner(f"Analyzing {ticker}... This may take 30-60 seconds."):
            result = analyze_ticker(ticker, ticker_df, include_mda, ai_analysis)

        if result.get('error'):
            st.error(f"❌ Analysis failed: {result['error']}")
            st.session_state['run_analysis'] = False
            return

        # Store results in session state so they persist across button clicks
        st.session_state['result'] = result
        st.session_state['export_csv'] = export_csv
        st.session_state['run_analysis'] = False

    # Display results if they exist in session state
    if st.session_state.get('result'):
        result = st.session_state['result']
        export_csv = st.session_state.get('export_csv', False)
        display_analysis_results(result, export_csv)
    else:
        display_welcome_screen()

if __name__ == "__main__":
    main()
