# SEC EDGAR API Reference

## Overview

The SEC's EDGAR (Electronic Data Gathering, Analysis, and Retrieval) system provides public access to corporate filings through REST APIs. These APIs enable programmatic access to:

### Key Features
- **Company filings and submissions**: Search and retrieve corporate documents
- **XBRL structured data**: Extract standardized financial metrics
- **Real-time updates**: Access fresh filing data as it's published
- **Bulk downloads**: Archive files for large-scale analysis

### Important Rate Limiting
- Maximum **10 requests per second**
- Must include `User-Agent` header identifying your organization
- See [SEC.gov Privacy and Security Policy](https://www.sec.gov/developer) for compliance

---

## API Authentication & Token Management

### Overview
EDGAR Next APIs require **API tokens** for secure access. There are two types:

- **Filer API Token**: For company filing operations (1-year validity)
- **User API Token**: For individual access to submission/management APIs (30-day validity)

### 🔑 Creating a User API Token (Most Common Need)

**Required For**: EDGAR Submission API, EDGAR Filer Management API
**Not Required For**: Public data APIs (Submissions, XBRL data)

#### Step-by-Step Process:
1. **Login**: Go to [EDGAR Filer Management](https://www.sec.gov/edgar/filer-information) with Login.gov credentials
2. **Navigate**: Select **"My User API Token"** from dashboard
3. **Create**: Click **"Create User API Token"**
4. **Review**: Read the terms and click **"Create User API Token"** again
5. **Save**: Copy or download your token immediately
6. **Important**: Save securely - you cannot retrieve it later!

#### Key Details:
- ⏰ **Validity**: 30 days from creation
- 🔄 **Renewal**: Create new token before expiration
- 🚫 **Limitation**: Only one active user token per individual
- 📧 **Notification**: Email confirmation sent to Login.gov address

### 🏢 Creating a Filer API Token (For Companies)

**Required For**: Company filing operations, bulk submissions
**Who Can Create**: Technical administrators only

#### Requirements Before Creation:
- Must be a **technical administrator** for the filer
- Filer must have **at least 2 technical administrators**
- Access to EDGAR Filer Management dashboard

#### Step-by-Step Process:
1. **Login**: EDGAR Filer Management with Login.gov credentials
2. **Navigate**: Select **"My Accounts"** → Choose relevant filer
3. **Access**: Click **"Manage Filer API Token"**
4. **Create**: Select **"Create New Filer API Token"**
5. **Name**: Optionally name the token for reference
6. **Generate**: Click **"Create"**
7. **Save**: Copy or download immediately

#### Key Details:
- ⏰ **Validity**: 1 year from creation
- 🔢 **Unlimited**: Generate multiple tokens as needed
- 👥 **Overlap**: Multiple active tokens allowed simultaneously
- 📧 **Notification**: Email confirmation sent

### 🔐 Using API Tokens in Requests

#### Authentication Headers
```python
headers = {
    'User-Agent': 'YourCompany YourApp/1.0 (contact@yourcompany.com)',
    'Authorization': f'Bearer {your_api_token}',
    'Accept': 'application/json'
}
```

#### Example Python Request
```python
import requests

# For APIs requiring authentication
api_token = "your_user_or_filer_token_here"
headers = {
    'User-Agent': 'MyCompany DataAnalyzer/1.0 (analyst@mycompany.com)',
    'Authorization': f'Bearer {api_token}'
}

response = requests.get(
    'https://efts.sec.gov/api/submission-status',
    headers=headers
)
```

### ⚠️ Token Management Best Practices

#### Security
- **Never commit tokens** to version control
- **Store securely** using environment variables
- **Rotate regularly** before expiration
- **Monitor usage** for unauthorized access

#### Renewal Strategy
- **User Tokens**: Set calendar reminders for 25-day mark
- **Filer Tokens**: Plan renewal 1-2 months before expiration
- **Multiple Users**: Stagger expiration dates to avoid downtime

#### Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| "Token expired" | Generate new token through dashboard |
| "Insufficient permissions" | Verify technical admin status for filer tokens |
| "Invalid token format" | Ensure Bearer prefix and no extra characters |
| "Rate limit exceeded" | Implement delays between requests |

### 🚀 Quick Start for New Computer Setup

Since you mentioned changing computers, here's what you need:

1. **Verify Login.gov Access**: Ensure you can still access your Login.gov account
2. **Check Email Access**: Token notifications go to your Login.gov email
3. **Generate New User Token**: Follow user token creation steps above
4. **Update Your Code**: Replace old token with new one
5. **Test Connection**: Make a simple API call to verify

#### Test Your New Token:
```python
import requests

headers = {
    'User-Agent': 'Test Connection/1.0 (your-email@domain.com)',
    'Authorization': f'Bearer {new_token}'
}

# Test with a simple endpoint
test_response = requests.get(
    'https://data.sec.gov/submissions/CIK0000320193.json',
    headers=headers
)

print(f"Status Code: {test_response.status_code}")
print("✅ Token working!" if test_response.status_code == 200 else "❌ Check token")
```

---

## Company Submissions API

### Endpoint Format
```
https://data.sec.gov/submissions/CIK{10-digit-CIK}.json
```

### Description
Returns complete filing history and metadata for a specific company, including all SEC form types and submission dates.

### Example Requests
```bash
# Apple Inc. (CIK: 0000320193)
https://data.sec.gov/submissions/CIK0000320193.json

# Microsoft Corporation (CIK: 0000789019)
https://data.sec.gov/submissions/CIK0000789019.json

# Tesla Inc. (CIK: 0001318605)
https://data.sec.gov/submissions/CIK0001318605.json
```

### Key Data Fields
- **Company Information**: Name, SIC code, fiscal year end
- **Filing History**: Complete list of submissions with dates
- **Recent Filings**: Latest 10-K, 10-Q, 8-K, and other forms
- **Addresses**: Business and mailing addresses

---

## XBRL Data APIs

XBRL (eXtensible Business Reporting Language) provides structured financial data from SEC filings.

### Company Concept API

#### Endpoint Format
```
https://data.sec.gov/api/xbrl/companyconcept/CIK{10-digit-CIK}/{taxonomy}/{tag}.json
```

#### Description
Returns all XBRL disclosures for a specific company and financial concept, organized by units of measure.

#### Parameters
- **CIK**: 10-digit Central Index Key with leading zeros
- **Taxonomy**: Standard taxonomy (e.g., `us-gaap`, `ifrs-full`, `dei`)
- **Tag**: Specific financial concept (e.g., `AccountsPayableCurrent`, `Revenues`)

#### Example Requests
```bash
# Apple's Accounts Payable (Current) in US-GAAP
https://data.sec.gov/api/xbrl/companyconcept/CIK0000320193/us-gaap/AccountsPayableCurrent.json

# Microsoft's Total Revenues
https://data.sec.gov/api/xbrl/companyconcept/CIK0000789019/us-gaap/Revenues.json

# Tesla's Cash and Cash Equivalents  
https://data.sec.gov/api/xbrl/companyconcept/CIK0001318605/us-gaap/CashAndCashEquivalentsAtCarryingValue.json
```

---

### Company Facts API

#### Endpoint Format
```
https://data.sec.gov/api/xbrl/companyfacts/CIK{10-digit-CIK}.json
```

#### Description
Returns **all available XBRL concepts** for a company in a single API call - comprehensive financial data dump.

#### Example Requests
```bash
# All Apple financial concepts
https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json

# All Microsoft financial concepts
https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json
```

#### Use Cases
- **Complete financial analysis**: Get all reported financial metrics
- **Data discovery**: Find available financial concepts for a company
- **Bulk analysis**: Download comprehensive dataset for modeling

---

### Frames API - Aggregated Market Data

#### Endpoint Format
```
https://data.sec.gov/api/xbrl/frames/{taxonomy}/{tag}/{unit}/{period}.json
```

#### Description
Aggregates **one fact per company** for the most recent filing that matches the requested time period. Provides market-wide views of specific financial metrics.

#### Parameters
- **Taxonomy**: Standard taxonomy (e.g., `us-gaap`, `ifrs-full`)
- **Tag**: Financial concept (e.g., `AccountsPayableCurrent`, `Revenues`)
- **Unit**: Unit of measure (e.g., `USD`, `shares`, `USD-per-shares`)
- **Period**: Time period format (see below)

#### Period Formats
- **Annual**: `CY####` (e.g., `CY2023`) - Duration: 365 days ±30 days
- **Quarterly**: `CY####Q#` (e.g., `CY2023Q1`) - Duration: 91 days ±30 days  
- **Instantaneous**: `CY####Q#I` (e.g., `CY2023Q1I`) - Point-in-time data

#### Example Requests
```bash
# All companies' Accounts Payable for Q1 2019 (instantaneous)
https://data.sec.gov/api/xbrl/frames/us-gaap/AccountsPayableCurrent/USD/CY2019Q1I.json

# All companies' Revenue for 2023 annual
https://data.sec.gov/api/xbrl/frames/us-gaap/Revenues/USD/CY2023.json

# All companies' Earnings Per Share for Q4 2022
https://data.sec.gov/api/xbrl/frames/us-gaap/EarningsPerShareBasic/USD-per-shares/CY2022Q4.json
```

#### Important Notes
- **Date Alignment**: Company fiscal calendars vary, so frame data aligns with the closest calendar period
- **Unit Formatting**: Complex units use "-per-" separator (e.g., `USD-per-shares`)
- **Default Unit**: Pure numbers use "pure" as the unit

---

## Technical Considerations

### Cross-Origin Resource Sharing (CORS)
**Important**: `data.sec.gov` does **not** support CORS. All automated access must:
- Comply with [SEC.gov Privacy and Security Policy](https://www.sec.gov/developer)
- Use server-side requests (not browser-based JavaScript)
- Follow rate limiting guidelines

### Bulk Data Downloads

For large-scale data analysis, use these nightly-updated ZIP archives:

#### Company Facts Archive
```
https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip
```
- **Contains**: All XBRL Frame API + Company Facts API data
- **Update**: Nightly compilation
- **Use Case**: Bulk financial analysis, research datasets

#### Submissions Archive  
```
https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip
```
- **Contains**: Complete public EDGAR filing history
- **Update**: Nightly compilation
- **Use Case**: Historical analysis, compliance tracking

---

## API Performance & Updates

### Real-Time Updates
- **Submissions API**: < 1 second processing delay
- **XBRL APIs**: < 1 minute processing delay
- **Peak Times**: Delays may be longer during heavy filing periods

### Best Practices
- Use bulk archives for large datasets
- Implement proper rate limiting
- Cache responses when appropriate
- Monitor API performance during peak filing times

---

## Common Financial Concepts

### Popular XBRL Tags (US-GAAP)
- `Revenues` - Total company revenue
- `AccountsPayableCurrent` - Current accounts payable
- `CashAndCashEquivalentsAtCarryingValue` - Cash position
- `EarningsPerShareBasic` - Basic earnings per share
- `Assets` - Total assets
- `StockholdersEquity` - Total stockholder equity

### Units of Measure
- `USD` - US Dollars
- `shares` - Number of shares
- `USD-per-shares` - Dollar amount per share
- `pure` - Dimensionless numbers (ratios, percentages)

---

## Support & Feedback

**Questions or Suggestions**: Send recommendations to webmaster@sec.gov

**Technical Support**: The SEC cannot provide technical support for developing or debugging scripted downloading processes.

**Developer Resources**: See [Developer FAQs](https://www.sec.gov/developer) for compliance guidelines.