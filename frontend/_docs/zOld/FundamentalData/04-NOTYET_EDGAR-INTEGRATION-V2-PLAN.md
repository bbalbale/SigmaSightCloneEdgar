# EDGAR Integration Plan v2: Replace Yahoo for Actuals + Non-GAAP

**Date**: November 2, 2025
**Status**: Ready for Implementation
**Architecture Decision**: EDGAR for actuals, Yahoo for estimates only

---

## Executive Summary

**Strategic Direction**:
- ✅ **EDGAR** → All historical actuals (official SEC filings)
- ✅ **Yahoo/yfinance** → Analyst estimates only (forward-looking data)
- ✅ **8-K Press Releases** → Non-GAAP reconciliations (the key value-add!)

### Why This Approach?

| Data Type | Best Source | Reason |
|-----------|-------------|--------|
| Historical Financials | EDGAR | Official SEC filings, legally required to be accurate |
| Analyst Estimates | Yahoo/yfinance | Not available in SEC filings (forward-looking) |
| Non-GAAP Adjustments | 8-K Exhibit 99.1 | Companies publish reconciliations in earnings press releases |

### What We're Building

```
Current Flow:
Yahoo Finance → All Data (actuals + estimates)

New Flow:
EDGAR XBRL APIs → Income Statement, Balance Sheet, Cash Flow (GAAP)
     ↓
8-K Exhibit 99.1 → Earnings Press Release → Non-GAAP Reconciliations
     ↓
yfinance → Analyst Estimates (future quarters/years)
```

---

## Phase 1: EDGAR Core Infrastructure

### Step 1.1: Understanding the SEC APIs

**Three Main APIs We'll Use**:

1. **Submissions API** - Filing metadata and history
   - URL: `https://data.sec.gov/submissions/CIK{cik}.json`
   - Returns: All filings for a company (10-K, 10-Q, 8-K, etc.)
   - Example Response:
   ```json
   {
     "cik": "0000320193",
     "name": "Apple Inc.",
     "filings": {
       "recent": {
         "accessionNumber": ["0000320193-23-000077", ...],
         "form": ["10-K", "8-K", "10-Q", ...],
         "filingDate": ["2023-11-03", "2023-10-27", ...],
         "primaryDocument": ["aapl-20230930.htm", ...]
       }
     }
   }
   ```

2. **Company Facts API** - All XBRL financial data
   - URL: `https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json`
   - Returns: Every XBRL fact ever filed (revenue, expenses, etc.)
   - Example Response:
   ```json
   {
     "facts": {
       "us-gaap": {
         "Revenues": {
           "units": {
             "USD": [
               {"end": "2023-09-30", "val": 383285000000, "form": "10-K", "fy": 2023, "fp": "FY"},
               {"end": "2023-06-30", "val": 81797000000, "form": "10-Q", "fy": 2023, "fp": "Q3"}
             ]
           }
         }
       }
     }
   }
   ```

3. **Direct File Download** - For 8-K press releases
   - URL: `https://www.sec.gov/Archives/edgar/data/{cik}/{accessionNo}/{filename}`
   - Returns: HTML file of the press release
   - We'll parse this to extract non-GAAP tables

### Step 1.2: Create EdgarService Class

```python
# backend/app/services/edgar_service.py

import httpx
import asyncio
from typing import Dict, List, Optional, Any
from datetime import date, datetime
import json
from bs4 import BeautifulSoup
import re

class EdgarService:
    """
    Service for interacting with SEC EDGAR APIs.
    
    Handles:
    - CIK lookups (ticker → CIK)
    - Company Facts retrieval (XBRL data)
    - Submissions metadata (filing history)
    - 8-K press release downloads
    - HTML table parsing for non-GAAP reconciliations
    """
    
    BASE_URL = "https://data.sec.gov"
    ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"
    
    # REQUIRED by SEC - they track and may block generic user agents
    USER_AGENT = "SigmaSight/1.0 (ben@sigmasight.com)"
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={"User-Agent": self.USER_AGENT},
            timeout=30.0,
            follow_redirects=True
        )
        self.rate_limiter = RateLimiter(max_requests=9, period=1.0)
        self._cik_cache = {}  # Ticker → CIK mapping cache
    
    async def load_cik_mapping(self) -> Dict[str, str]:
        """
        Download SEC's official ticker-to-CIK mapping.
        
        SEC provides this file: https://www.sec.gov/files/company_tickers.json
        Format: {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}, ...}
        
        Returns:
            Dict mapping ticker → CIK (with leading zeros)
        """
        await self.rate_limiter.acquire()
        
        url = "https://www.sec.gov/files/company_tickers.json"
        response = await self.client.get(url)
        response.raise_for_status()
        
        data = response.json()
        
        # Convert to ticker → CIK mapping
        mapping = {}
        for item in data.values():
            ticker = item['ticker']
            cik = str(item['cik_str']).zfill(10)  # Pad to 10 digits
            mapping[ticker] = cik
        
        self._cik_cache = mapping
        return mapping
    
    async def get_cik(self, ticker: str) -> Optional[str]:
        """Get CIK for a ticker symbol."""
        if not self._cik_cache:
            await self.load_cik_mapping()
        
        return self._cik_cache.get(ticker.upper())
    
    async def get_submissions(self, cik: str) -> Dict[str, Any]:
        """
        Get all filing metadata for a company.
        
        Returns recent filings plus pagination info for historical filings.
        """
        await self.rate_limiter.acquire()
        
        url = f"{self.BASE_URL}/submissions/CIK{cik}.json"
        response = await self.client.get(url)
        response.raise_for_status()
        
        return response.json()
    
    async def get_company_facts(self, cik: str) -> Dict[str, Any]:
        """
        Get all XBRL facts for a company.
        
        This is the gold mine - contains ALL financial data from 10-K/10-Q filings.
        """
        await self.rate_limiter.acquire()
        
        url = f"{self.BASE_URL}/api/xbrl/companyfacts/CIK{cik}.json"
        response = await self.client.get(url)
        response.raise_for_status()
        
        return response.json()
    
    async def get_8k_filing(self, cik: str, accession_number: str) -> str:
        """
        Download an 8-K filing HTML.
        
        Args:
            cik: Company CIK (no leading zeros for URL)
            accession_number: Like "0000320193-23-000077"
        
        Returns:
            HTML content of the 8-K filing
        """
        await self.rate_limiter.acquire()
        
        # Remove leading zeros from CIK for URL
        cik_no_zeros = str(int(cik))
        
        # Remove dashes from accession number for URL path
        accession_path = accession_number.replace('-', '')
        
        # Typical 8-K URL structure
        url = f"{self.ARCHIVES_URL}/{cik_no_zeros}/{accession_path}/{accession_number}.txt"
        
        response = await self.client.get(url)
        response.raise_for_status()
        
        return response.text
    
    async def find_exhibit_99_url(self, cik: str, accession_number: str) -> Optional[str]:
        """
        Find the Exhibit 99.1 (press release) URL from an 8-K filing.
        
        Process:
        1. Get filing metadata from submissions
        2. Look for document with type "EX-99.1"
        3. Return full URL to that exhibit
        
        Returns:
            URL to Exhibit 99.1 HTML file, or None if not found
        """
        submissions = await self.get_submissions(cik)
        
        # Find the filing in recent filings
        recent = submissions.get('filings', {}).get('recent', {})
        accession_numbers = recent.get('accessionNumber', [])
        
        try:
            filing_index = accession_numbers.index(accession_number)
        except ValueError:
            return None
        
        # Get primary document for this filing
        primary_doc = recent.get('primaryDocument', [])[filing_index]
        
        # Exhibit 99.1 is typically named like "exhibit991.htm" or "ex99_1.htm"
        # We'll need to download the filing index to find exact filename
        
        cik_no_zeros = str(int(cik))
        accession_path = accession_number.replace('-', '')
        
        # Download filing index page
        index_url = f"{self.ARCHIVES_URL}/{cik_no_zeros}/{accession_path}/{accession_number}-index.htm"
        
        await self.rate_limiter.acquire()
        response = await self.client.get(index_url)
        
        if response.status_code != 200:
            return None
        
        # Parse HTML to find EX-99.1 link
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for link with "EX-99.1" or "Exhibit 99.1" text
        for link in soup.find_all('a'):
            link_text = link.get_text().strip().upper()
            if 'EX-99' in link_text or 'EXHIBIT 99' in link_text:
                href = link.get('href')
                if href:
                    # Construct full URL
                    return f"{self.ARCHIVES_URL}/{cik_no_zeros}/{accession_path}/{href}"
        
        return None
    
    async def download_exhibit_99(self, url: str) -> str:
        """
        Download Exhibit 99.1 HTML content.
        
        This is the earnings press release with non-GAAP reconciliation tables.
        """
        await self.rate_limiter.acquire()
        
        response = await self.client.get(url)
        response.raise_for_status()
        
        return response.text
```

### Step 1.3: Rate Limiter (Critical!)

```python
# backend/app/services/rate_limiter.py

import asyncio
import time
from collections import deque

class RateLimiter:
    """
    Token bucket rate limiter for SEC API.
    
    SEC limit: 10 requests/second HARD LIMIT (they will block your IP)
    We use 9 req/sec to be safe.
    """
    
    def __init__(self, max_requests: int = 9, period: float = 1.0):
        self.max_requests = max_requests
        self.period = period
        self.requests = deque()
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Wait until a request slot is available."""
        async with self.lock:
            now = time.time()
            
            # Remove requests older than period
            while self.requests and self.requests[0] <= now - self.period:
                self.requests.popleft()
            
            # If at capacity, wait
            if len(self.requests) >= self.max_requests:
                sleep_time = self.period - (now - self.requests[0])
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    return await self.acquire()  # Recursive retry
            
            # Record this request
            self.requests.append(now)
```

---

## Phase 2: XBRL Data Extraction

### Step 2.1: Parse Company Facts into Financial Statements

```python
# backend/app/services/edgar_parser.py

from typing import Dict, List, Optional, Any
from datetime import datetime

class EdgarXBRLParser:
    """
    Parse XBRL Company Facts JSON into structured financial statements.
    
    Challenge: Companies use different XBRL concepts for the same metric
    Solution: Try multiple concept names with fallback logic
    """
    
    # XBRL concept mappings with fallbacks
    REVENUE_CONCEPTS = [
        'Revenues',
        'RevenueFromContractWithCustomerExcludingAssessedTax',
        'SalesRevenueNet',
        'RevenueFromContractWithCustomerIncludingAssessedTax'
    ]
    
    COST_OF_REVENUE_CONCEPTS = [
        'CostOfRevenue',
        'CostOfGoodsAndServicesSold',
        'CostOfGoodsSold'
    ]
    
    GROSS_PROFIT_CONCEPTS = [
        'GrossProfit'
    ]
    
    RD_EXPENSE_CONCEPTS = [
        'ResearchAndDevelopmentExpense',
        'ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost'
    ]
    
    SGA_EXPENSE_CONCEPTS = [
        'SellingGeneralAndAdministrativeExpense'
    ]
    
    # Can break down SG&A further:
    SELLING_MARKETING_CONCEPTS = [
        'SellingAndMarketingExpense',
        'MarketingExpense'
    ]
    
    GENERAL_ADMIN_CONCEPTS = [
        'GeneralAndAdministrativeExpense'
    ]
    
    OPERATING_INCOME_CONCEPTS = [
        'OperatingIncomeLoss',
        'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest'
    ]
    
    NET_INCOME_CONCEPTS = [
        'NetIncomeLoss',
        'ProfitLoss'
    ]
    
    EPS_DILUTED_CONCEPTS = [
        'EarningsPerShareDiluted'
    ]
    
    # Non-GAAP adjustment concepts
    STOCK_BASED_COMP_CONCEPTS = [
        'ShareBasedCompensation',
        'AllocatedShareBasedCompensationExpense',
        'ShareBasedCompensationArrangementByShareBasedPaymentAwardOptionsGrantsInPeriodGross'
    ]
    
    RESTRUCTURING_CONCEPTS = [
        'RestructuringCharges',
        'RestructuringAndRelatedCost'
    ]
    
    IMPAIRMENT_CONCEPTS = [
        'AssetImpairmentCharges',
        'GoodwillImpairmentLoss',
        'ImpairmentOfIntangibleAssetsExcludingGoodwill'
    ]
    
    def __init__(self, company_facts: Dict[str, Any]):
        """
        Initialize parser with company facts JSON.
        
        Args:
            company_facts: Response from get_company_facts()
        """
        self.facts = company_facts
        self.us_gaap = company_facts.get('facts', {}).get('us-gaap', {})
    
    def _get_concept_value(
        self,
        concept_names: List[str],
        period_end: str,
        form_type: str = None
    ) -> Optional[float]:
        """
        Try to get a value from multiple concept names.
        
        Args:
            concept_names: List of XBRL concept names to try
            period_end: Date like "2023-09-30"
            form_type: Filter by form (10-K, 10-Q) or None for any
        
        Returns:
            First matching value found, or None
        """
        for concept_name in concept_names:
            concept_data = self.us_gaap.get(concept_name, {})
            units = concept_data.get('units', {}).get('USD', [])
            
            for fact in units:
                if fact.get('end') == period_end:
                    if form_type and fact.get('form') != form_type:
                        continue
                    return fact.get('val')
        
        return None
    
    def get_all_periods(self) -> List[Dict[str, Any]]:
        """
        Get all unique reporting periods from the facts.
        
        Returns:
            List of dicts like:
            [
                {'period_end': '2023-09-30', 'fy': 2023, 'fp': 'FY', 'form': '10-K'},
                {'period_end': '2023-06-30', 'fy': 2023, 'fp': 'Q3', 'form': '10-Q'},
                ...
            ]
        """
        periods = set()
        
        # Get periods from Revenue (should be in every filing)
        for concept in self.REVENUE_CONCEPTS:
            if concept in self.us_gaap:
                units = self.us_gaap[concept].get('units', {}).get('USD', [])
                for fact in units:
                    period_data = (
                        fact.get('end'),
                        fact.get('fy'),
                        fact.get('fp'),
                        fact.get('form'),
                        fact.get('filed')  # Filing date
                    )
                    periods.add(period_data)
        
        # Convert to list of dicts and sort by date descending
        result = [
            {
                'period_end': p[0],
                'fiscal_year': p[1],
                'fiscal_period': p[2],
                'form': p[3],
                'filed_date': p[4]
            }
            for p in periods if p[0]  # Filter out None dates
        ]
        
        result.sort(key=lambda x: x['period_end'], reverse=True)
        return result
    
    def extract_income_statement(
        self,
        period_end: str,
        form_type: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extract income statement for a specific period.
        
        Args:
            period_end: Date like "2023-09-30"
            form_type: "10-K" or "10-Q" (None = any)
        
        Returns:
            Dict of financial metrics, or None if period not found
        """
        return {
            # Revenue & Gross Profit
            'total_revenue': self._get_concept_value(
                self.REVENUE_CONCEPTS, period_end, form_type
            ),
            'cost_of_revenue': self._get_concept_value(
                self.COST_OF_REVENUE_CONCEPTS, period_end, form_type
            ),
            'gross_profit': self._get_concept_value(
                self.GROSS_PROFIT_CONCEPTS, period_end, form_type
            ),
            
            # Operating Expenses
            'research_and_development': self._get_concept_value(
                self.RD_EXPENSE_CONCEPTS, period_end, form_type
            ),
            'selling_general_administrative': self._get_concept_value(
                self.SGA_EXPENSE_CONCEPTS, period_end, form_type
            ),
            
            # Try to get granular breakdowns
            'selling_and_marketing': self._get_concept_value(
                self.SELLING_MARKETING_CONCEPTS, period_end, form_type
            ),
            'general_and_administrative': self._get_concept_value(
                self.GENERAL_ADMIN_CONCEPTS, period_end, form_type
            ),
            
            # Operating & Net Income
            'operating_income': self._get_concept_value(
                self.OPERATING_INCOME_CONCEPTS, period_end, form_type
            ),
            'net_income': self._get_concept_value(
                self.NET_INCOME_CONCEPTS, period_end, form_type
            ),
            'diluted_eps': self._get_concept_value(
                self.EPS_DILUTED_CONCEPTS, period_end, form_type
            ),
            
            # Non-GAAP Adjustments (if available in XBRL)
            'stock_based_compensation': self._get_concept_value(
                self.STOCK_BASED_COMP_CONCEPTS, period_end, form_type
            ),
            'restructuring_charges': self._get_concept_value(
                self.RESTRUCTURING_CONCEPTS, period_end, form_type
            ),
            'impairment_charges': self._get_concept_value(
                self.IMPAIRMENT_CONCEPTS, period_end, form_type
            ),
        }
    
    def extract_all_income_statements(self) -> List[Dict[str, Any]]:
        """
        Extract income statements for all available periods.
        
        Returns:
            List of income statement dicts with period metadata
        """
        periods = self.get_all_periods()
        statements = []
        
        for period in periods:
            statement = self.extract_income_statement(
                period_end=period['period_end'],
                form_type=period['form']
            )
            
            if statement and statement.get('total_revenue'):  # Only include if we got data
                statement.update({
                    'period_end': period['period_end'],
                    'fiscal_year': period['fiscal_year'],
                    'fiscal_period': period['fiscal_period'],
                    'form_type': period['form'],
                    'filed_date': period['filed_date']
                })
                statements.append(statement)
        
        return statements
```

---

## Phase 3: Non-GAAP from 8-K Press Releases

### Step 3.1: Find Earnings 8-Ks

```python
# backend/app/services/edgar_service.py (continued)

class EdgarService:
    # ... (previous methods)
    
    async def find_earnings_8ks(
        self,
        cik: str,
        since_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find 8-K filings that contain earnings announcements (Item 2.02).
        
        Args:
            cik: Company CIK
            since_date: Only filings after this date (YYYY-MM-DD)
        
        Returns:
            List of 8-K filing metadata
        """
        submissions = await self.get_submissions(cik)
        
        recent = submissions.get('filings', {}).get('recent', {})
        
        forms = recent.get('form', [])
        accession_numbers = recent.get('accessionNumber', [])
        filing_dates = recent.get('filingDate', [])
        primary_documents = recent.get('primaryDocument', [])
        
        earnings_8ks = []
        
        for i, form in enumerate(forms):
            if form != '8-K':
                continue
            
            filing_date = filing_dates[i]
            
            if since_date and filing_date < since_date:
                continue
            
            # Download the 8-K to check if it's Item 2.02 (earnings)
            accession = accession_numbers[i]
            
            try:
                filing_html = await self.get_8k_filing(cik, accession)
                
                # Check if it contains Item 2.02 (earnings announcement)
                if 'item 2.02' in filing_html.lower() or 'results of operations' in filing_html.lower():
                    earnings_8ks.append({
                        'accession_number': accession,
                        'filing_date': filing_date,
                        'primary_document': primary_documents[i]
                    })
            
            except Exception as e:
                # Some 8-Ks might not be accessible, skip them
                continue
        
        return earnings_8ks
```

### Step 3.2: Parse Non-GAAP Tables from Press Releases

```python
# backend/app/services/edgar_non_gaap_parser.py

from bs4 import BeautifulSoup
import re
from typing import Dict, List, Optional, Any

class NonGAAPParser:
    """
    Parse non-GAAP reconciliation tables from earnings press releases.
    
    These tables typically show:
    - GAAP Net Income: $X
    - Add: Stock-based compensation: $Y
    - Add: Restructuring charges: $Z
    - Non-GAAP Net Income: $X+Y+Z
    """
    
    def __init__(self, html_content: str):
        """
        Initialize parser with HTML from Exhibit 99.1
        
        Args:
            html_content: HTML string from 8-K exhibit
        """
        self.html = html_content
        self.soup = BeautifulSoup(html_content, 'html.parser')
    
    def find_reconciliation_tables(self) -> List[Any]:
        """
        Find tables that look like non-GAAP reconciliations.
        
        Heuristics:
        - Table contains words like "GAAP", "Non-GAAP", "Reconciliation"
        - Has rows with "Add back" or "Exclude" or "Adjustment"
        - Contains common adjustment terms (stock-based comp, restructuring, etc.)
        
        Returns:
            List of BeautifulSoup table elements
        """
        tables = self.soup.find_all('table')
        reconciliation_tables = []
        
        for table in tables:
            table_text = table.get_text().lower()
            
            # Check for reconciliation keywords
            has_reconciliation = any(keyword in table_text for keyword in [
                'non-gaap',
                'non gaap',
                'reconciliation',
                'gaap to non-gaap',
                'adjusted',
                'add back',
                'exclude'
            ])
            
            # Check for adjustment types
            has_adjustments = any(keyword in table_text for keyword in [
                'stock-based compensation',
                'stock based compensation',
                'share-based compensation',
                'restructuring',
                'acquisition',
                'amortization of intangibles',
                'impairment'
            ])
            
            if has_reconciliation or has_adjustments:
                reconciliation_tables.append(table)
        
        return reconciliation_tables
    
    def parse_table_to_dict(self, table: Any) -> List[Dict[str, Any]]:
        """
        Parse an HTML table into a list of dictionaries.
        
        Returns:
            [
                {'metric': 'GAAP net income', 'value': 1000000},
                {'metric': 'Stock-based compensation', 'value': 200000},
                ...
            ]
        """
        rows = table.find_all('tr')
        
        # Find header row (usually has <th> tags)
        headers = []
        for row in rows:
            ths = row.find_all('th')
            if ths:
                headers = [th.get_text().strip() for th in ths]
                break
        
        # If no headers, assume first row is headers
        if not headers and rows:
            headers = [td.get_text().strip() for td in rows[0].find_all(['th', 'td'])]
        
        # Parse data rows
        data = []
        for row in rows[1:]:  # Skip header row
            cells = row.find_all(['td', 'th'])
            if not cells:
                continue
            
            row_data = {}
            for i, cell in enumerate(cells):
                header = headers[i] if i < len(headers) else f'column_{i}'
                value = cell.get_text().strip()
                
                # Try to parse as number
                parsed_value = self._parse_value(value)
                
                row_data[header] = parsed_value
            
            data.append(row_data)
        
        return data
    
    def _parse_value(self, text: str) -> Any:
        """
        Parse a value from table cell text.
        
        Handles:
        - Dollar amounts: "$1,000,000" → 1000000
        - Percentages: "15.5%" → 0.155
        - Parentheses as negative: "($100)" → -100
        - Plain text: Returns as-is
        """
        text = text.strip()
        
        # Remove common formatting
        text = text.replace('$', '').replace(',', '').strip()
        
        # Handle parentheses (negative numbers)
        is_negative = text.startswith('(') and text.endswith(')')
        if is_negative:
            text = text[1:-1]
        
        # Try to parse as float
        try:
            value = float(text)
            return -value if is_negative else value
        except ValueError:
            # Return as text if not a number
            return text
    
    def extract_non_gaap_reconciliation(
        self,
        period_end: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract non-GAAP reconciliation for a specific period.
        
        Args:
            period_end: Expected period end date (for validation)
        
        Returns:
            Dict with GAAP value, adjustments, and non-GAAP value
        """
        tables = self.find_reconciliation_tables()
        
        if not tables:
            return None
        
        # Usually the first reconciliation table is the main one
        main_table = tables[0]
        data = self.parse_table_to_dict(main_table)
        
        # Extract key metrics
        reconciliation = {
            'gaap_net_income': None,
            'non_gaap_net_income': None,
            'adjustments': {}
        }
        
        for row in data:
            # Get metric name (usually first column)
            metric = list(row.values())[0] if row else ''
            if isinstance(metric, str):
                metric_lower = metric.lower()
                
                # Get value (usually second or third column)
                value = None
                for v in list(row.values())[1:]:
                    if isinstance(v, (int, float)):
                        value = v
                        break
                
                # Identify metric type
                if 'gaap net income' in metric_lower and 'non' not in metric_lower:
                    reconciliation['gaap_net_income'] = value
                
                elif any(term in metric_lower for term in ['non-gaap', 'non gaap', 'adjusted net income']):
                    reconciliation['non_gaap_net_income'] = value
                
                elif 'stock-based' in metric_lower or 'stock based' in metric_lower or 'share-based' in metric_lower:
                    reconciliation['adjustments']['stock_based_compensation'] = value
                
                elif 'restructuring' in metric_lower:
                    reconciliation['adjustments']['restructuring_charges'] = value
                
                elif 'acquisition' in metric_lower:
                    reconciliation['adjustments']['acquisition_costs'] = value
                
                elif 'amortization of intangible' in metric_lower:
                    reconciliation['adjustments']['amortization_of_intangibles'] = value
                
                elif 'impairment' in metric_lower:
                    reconciliation['adjustments']['impairment_charges'] = value
        
        return reconciliation if reconciliation['gaap_net_income'] else None
```

---

## Phase 4: Database Schema

### Step 4.1: Revised Schema (EDGAR-focused)

**Replace existing tables** with EDGAR-sourced data:

```sql
-- Drop old Yahoo-based tables
DROP TABLE IF EXISTS income_statements;
DROP TABLE IF EXISTS balance_sheets;
DROP TABLE IF EXISTS cash_flows;

-- Create new EDGAR-based tables
CREATE TABLE edgar_income_statements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(10) NOT NULL,
    cik VARCHAR(10) NOT NULL,
    
    -- Period Information
    period_end DATE NOT NULL,
    fiscal_year INT,
    fiscal_period VARCHAR(10),  -- 'FY', 'Q1', 'Q2', 'Q3', 'Q4'
    form_type VARCHAR(10),  -- '10-K' or '10-Q'
    filed_date DATE,
    
    -- Revenue & Gross Profit
    total_revenue NUMERIC(20, 2),
    cost_of_revenue NUMERIC(20, 2),
    gross_profit NUMERIC(20, 2),
    gross_margin NUMERIC(8, 6),  -- Calculated
    
    -- Operating Expenses (EDGAR can provide more detail than Yahoo)
    research_and_development NUMERIC(20, 2),
    selling_general_administrative NUMERIC(20, 2),
    selling_and_marketing NUMERIC(20, 2),  -- NEW - if available
    general_and_administrative NUMERIC(20, 2),  -- NEW - if available
    
    -- Operating Results
    operating_income NUMERIC(20, 2),
    operating_margin NUMERIC(8, 6),  -- Calculated
    ebit NUMERIC(20, 2),
    ebitda NUMERIC(20, 2),
    
    -- Net Income
    net_income NUMERIC(20, 2),
    net_margin NUMERIC(8, 6),  -- Calculated
    diluted_eps NUMERIC(12, 4),
    basic_eps NUMERIC(12, 4),
    diluted_average_shares BIGINT,
    basic_average_shares BIGINT,
    
    -- Other Items
    interest_expense NUMERIC(20, 2),
    tax_provision NUMERIC(20, 2),
    depreciation_amortization NUMERIC(20, 2),
    
    -- Non-GAAP Adjustments (from XBRL, if available)
    stock_based_compensation_xbrl NUMERIC(20, 2),
    restructuring_charges_xbrl NUMERIC(20, 2),
    impairment_charges_xbrl NUMERIC(20, 2),
    
    -- Metadata
    data_source VARCHAR(20) DEFAULT 'edgar_xbrl',  -- 'edgar_xbrl'
    currency VARCHAR(3) DEFAULT 'USD',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Prevent duplicates
    UNIQUE(cik, period_end, form_type)
);

CREATE INDEX idx_edgar_income_symbol ON edgar_income_statements(symbol);
CREATE INDEX idx_edgar_income_period ON edgar_income_statements(period_end DESC);
CREATE INDEX idx_edgar_income_cik ON edgar_income_statements(cik);

-- Non-GAAP Reconciliations (from 8-K press releases)
CREATE TABLE edgar_non_gaap_reconciliations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(10) NOT NULL,
    cik VARCHAR(10) NOT NULL,
    
    -- Period & Filing Info
    period_end DATE NOT NULL,
    filing_date DATE NOT NULL,
    accession_number VARCHAR(20) NOT NULL,  -- 8-K accession number
    exhibit_url TEXT,  -- URL to Exhibit 99.1
    
    -- Reconciliation: Operating Income
    gaap_operating_income NUMERIC(20, 2),
    non_gaap_operating_income NUMERIC(20, 2),
    
    -- Reconciliation: Net Income
    gaap_net_income NUMERIC(20, 2),
    non_gaap_net_income NUMERIC(20, 2),
    
    -- Reconciliation: EPS
    gaap_diluted_eps NUMERIC(12, 4),
    non_gaap_diluted_eps NUMERIC(12, 4),
    
    -- Individual Adjustments (add back to GAAP)
    stock_based_compensation NUMERIC(20, 2),
    restructuring_charges NUMERIC(20, 2),
    acquisition_costs NUMERIC(20, 2),
    amortization_of_intangibles NUMERIC(20, 2),
    impairment_charges NUMERIC(20, 2),
    litigation_settlements NUMERIC(20, 2),
    other_adjustments NUMERIC(20, 2),
    other_adjustments_description TEXT,
    
    -- Metadata
    data_source VARCHAR(20) DEFAULT 'edgar_8k',
    raw_table_html TEXT,  -- Store original table for debugging
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(cik, period_end, accession_number)
);

CREATE INDEX idx_non_gaap_symbol ON edgar_non_gaap_reconciliations(symbol);
CREATE INDEX idx_non_gaap_period ON edgar_non_gaap_reconciliations(period_end DESC);

-- Update company_profiles table
ALTER TABLE company_profiles
ADD COLUMN IF NOT EXISTS sec_cik VARCHAR(10),
ADD COLUMN IF NOT EXISTS edgar_last_fetched DATE,
ADD COLUMN IF NOT EXISTS last_8k_filing_date DATE;

CREATE INDEX idx_company_profiles_cik ON company_profiles(sec_cik);
```

### Step 4.2: Keep Yahoo for Estimates Only

```sql
-- Simplified analyst estimates table (Yahoo data)
CREATE TABLE analyst_estimates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(10) NOT NULL,
    
    -- Period targets
    target_period DATE NOT NULL,
    target_fiscal_year INT,
    target_fiscal_quarter INT,
    
    -- Revenue Estimates
    revenue_estimate_avg NUMERIC(20, 2),
    revenue_estimate_low NUMERIC(20, 2),
    revenue_estimate_high NUMERIC(20, 2),
    revenue_analyst_count INT,
    
    -- EPS Estimates
    eps_estimate_avg NUMERIC(12, 4),
    eps_estimate_low NUMERIC(12, 4),
    eps_estimate_high NUMERIC(12, 4),
    eps_analyst_count INT,
    
    -- Metadata
    data_source VARCHAR(20) DEFAULT 'yahoo_finance',
    fetched_at DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(symbol, target_period, fetched_at)
);

CREATE INDEX idx_analyst_estimates_symbol ON analyst_estimates(symbol);
CREATE INDEX idx_analyst_estimates_period ON analyst_estimates(target_period);
```

---

## Phase 5: Integration Workflow

### Step 5.1: Batch Orchestrator Integration

```python
# backend/app/batch/batch_orchestrator_v3.py

class BatchOrchestrator:
    
    async def phase_1_5_edgar_data_collection(self, portfolio_ids: List[int]):
        """
        Replace Phase 1.5 Yahoo fundamentals with EDGAR data.
        
        Process:
        1. Get all symbols
        2. For each symbol:
           a. Fetch EDGAR XBRL data (Company Facts)
           b. Extract income statements for all periods
           c. Find recent earnings 8-Ks
           d. Download and parse press releases for non-GAAP
           e. Store all data
        3. Separately: Fetch Yahoo analyst estimates
        """
        self.log_phase_start("1.5", "EDGAR Financial Data Collection")
        
        edgar_service = EdgarService()
        
        # Load CIK mapping once
        await edgar_service.load_cik_mapping()
        
        symbols = await self.get_portfolio_symbols(portfolio_ids)
        
        results = {
            'symbols_processed': 0,
            'income_statements_stored': 0,
            'non_gaap_reconciliations_stored': 0,
            'analyst_estimates_stored': 0,
            'errors': []
        }
        
        for symbol in symbols:
            try:
                # 1. Get CIK
                cik = await edgar_service.get_cik(symbol)
                if not cik:
                    logger.warning(f"⚠️  No CIK found for {symbol}")
                    continue
                
                # Update company profile with CIK
                await self.update_company_profile_cik(symbol, cik)
                
                # 2. Fetch Company Facts (XBRL data)
                logger.info(f"📊 Fetching EDGAR Company Facts for {symbol} (CIK: {cik})")
                company_facts = await edgar_service.get_company_facts(cik)
                
                # 3. Parse XBRL into income statements
                parser = EdgarXBRLParser(company_facts)
                income_statements = parser.extract_all_income_statements()
                
                logger.info(f"   Found {len(income_statements)} periods")
                
                # 4. Store income statements
                for stmt in income_statements:
                    await self.store_edgar_income_statement(symbol, cik, stmt)
                    results['income_statements_stored'] += 1
                
                # 5. Find recent earnings 8-Ks (last 2 years)
                since_date = (date.today() - timedelta(days=730)).isoformat()
                earnings_8ks = await edgar_service.find_earnings_8ks(cik, since_date)
                
                logger.info(f"   Found {len(earnings_8ks)} earnings 8-Ks")
                
                # 6. Process each 8-K for non-GAAP reconciliation
                for filing in earnings_8ks[:4]:  # Last 4 quarters
                    try:
                        # Find Exhibit 99.1 URL
                        exhibit_url = await edgar_service.find_exhibit_99_url(
                            cik,
                            filing['accession_number']
                        )
                        
                        if not exhibit_url:
                            continue
                        
                        # Download press release
                        html = await edgar_service.download_exhibit_99(exhibit_url)
                        
                        # Parse non-GAAP reconciliation
                        non_gaap_parser = NonGAAPParser(html)
                        
                        # We need to infer period_end from filing date
                        # Typically: filing date ≈ earnings date ≈ end of previous quarter
                        period_end = self.infer_period_end(filing['filing_date'])
                        
                        reconciliation = non_gaap_parser.extract_non_gaap_reconciliation(
                            period_end
                        )
                        
                        if reconciliation:
                            await self.store_non_gaap_reconciliation(
                                symbol=symbol,
                                cik=cik,
                                period_end=period_end,
                                filing_date=filing['filing_date'],
                                accession_number=filing['accession_number'],
                                exhibit_url=exhibit_url,
                                reconciliation=reconciliation,
                                raw_html=html
                            )
                            results['non_gaap_reconciliations_stored'] += 1
                    
                    except Exception as e:
                        logger.warning(f"   Failed to process 8-K {filing['accession_number']}: {e}")
                
                # 7. Fetch Yahoo analyst estimates (separate)
                try:
                    estimates = await self.fetch_yahoo_analyst_estimates(symbol)
                    await self.store_analyst_estimates(symbol, estimates)
                    results['analyst_estimates_stored'] += 1
                except Exception as e:
                    logger.warning(f"   Failed to fetch analyst estimates: {e}")
                
                results['symbols_processed'] += 1
                logger.info(f"✅ {symbol}: Complete")
                
            except Exception as e:
                logger.error(f"❌ Error processing {symbol}: {str(e)}")
                results['errors'].append({'symbol': symbol, 'error': str(e)})
        
        self.log_phase_complete("1.5", results)
        return results
    
    def infer_period_end(self, filing_date: str) -> str:
        """
        Infer period end date from 8-K filing date.
        
        8-Ks are typically filed within a few days of earnings release.
        Earnings are for the previous quarter.
        
        Logic:
        - If filed in Jan-Feb → Q4 (Dec 31)
        - If filed in Apr-May → Q1 (Mar 31)
        - If filed in Jul-Aug → Q2 (Jun 30)
        - If filed in Oct-Nov → Q3 (Sep 30)
        """
        filing_dt = datetime.strptime(filing_date, '%Y-%m-%d')
        month = filing_dt.month
        year = filing_dt.year
        
        if month in [1, 2, 3]:  # Q4 results
            return f"{year-1}-12-31"
        elif month in [4, 5, 6]:  # Q1 results
            return f"{year}-03-31"
        elif month in [7, 8, 9]:  # Q2 results
            return f"{year}-06-30"
        else:  # Q3 results
            return f"{year}-09-30"
```

---

## Phase 6: API Endpoints

### Step 6.1: Enhanced Financials Endpoint

```python
# backend/app/api/v1/endpoints/fundamentals.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

router = APIRouter()

@router.get("/financials/{symbol}")
async def get_company_financials(
    symbol: str,
    periods: int = Query(12, ge=1, le=40, description="Number of periods to return"),
    db: Session = Depends(get_db)
):
    """
    Get financial statements from EDGAR with non-GAAP reconciliations.
    
    Returns:
    {
        "symbol": "AAPL",
        "cik": "0000320193",
        "income_statements": [
            {
                "period_end": "2023-09-30",
                "fiscal_year": 2023,
                "fiscal_period": "FY",
                "form_type": "10-K",
                "total_revenue": 383285000000,
                "net_income": 96995000000,
                ...
                "has_non_gaap": true  // Indicates reconciliation available
            },
            ...
        ],
        "non_gaap_reconciliations": [
            {
                "period_end": "2023-09-30",
                "gaap_net_income": 96995000000,
                "non_gaap_net_income": 110000000000,
                "adjustments": {
                    "stock_based_compensation": 10500000000,
                    "restructuring_charges": 0,
                    ...
                }
            },
            ...
        ]
    }
    """
    # Get income statements from EDGAR
    income_statements = db.query(EdgarIncomeStatement)\
        .filter(EdgarIncomeStatement.symbol == symbol.upper())\
        .order_by(EdgarIncomeStatement.period_end.desc())\
        .limit(periods)\
        .all()
    
    if not income_statements:
        raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
    
    # Get non-GAAP reconciliations
    non_gaap_recs = db.query(EdgarNonGAAPReconciliation)\
        .filter(EdgarNonGAAPReconciliation.symbol == symbol.upper())\
        .order_by(EdgarNonGAAPReconciliation.period_end.desc())\
        .all()
    
    # Map non-GAAP to periods
    non_gaap_by_period = {
        rec.period_end: rec for rec in non_gaap_recs
    }
    
    # Format response
    income_statements_data = []
    for stmt in income_statements:
        stmt_dict = stmt.to_dict()
        stmt_dict['has_non_gaap'] = stmt.period_end in non_gaap_by_period
        income_statements_data.append(stmt_dict)
    
    return {
        'symbol': symbol.upper(),
        'cik': income_statements[0].cik if income_statements else None,
        'income_statements': income_statements_data,
        'non_gaap_reconciliations': [
            rec.to_dict() for rec in non_gaap_recs
        ]
    }

@router.get("/analyst-estimates/{symbol}")
async def get_analyst_estimates(
    symbol: str,
    db: Session = Depends(get_db)
):
    """
    Get forward-looking analyst estimates (from Yahoo Finance).
    
    This is the ONLY data we're still pulling from Yahoo.
    """
    estimates = db.query(AnalystEstimate)\
        .filter(AnalystEstimate.symbol == symbol.upper())\
        .order_by(AnalystEstimate.target_period.asc())\
        .all()
    
    if not estimates:
        raise HTTPException(status_code=404, detail=f"No estimates found for {symbol}")
    
    return {
        'symbol': symbol.upper(),
        'estimates': [est.to_dict() for est in estimates]
    }
```

---

## Implementation Timeline

### Week 1: Core Infrastructure
- Day 1-2: EdgarService class, rate limiter, CIK mapping
- Day 3-4: EdgarXBRLParser, test with 10 companies
- Day 5: Database schema migration

### Week 2: Non-GAAP Extraction
- Day 1-2: 8-K discovery, Exhibit 99.1 download
- Day 3-4: NonGAAPParser, HTML table parsing
- Day 5: Testing with diverse companies

### Week 3: Integration & Testing
- Day 1-2: Batch orchestrator integration
- Day 3: API endpoints
- Day 4-5: End-to-end testing, bug fixes

### Week 4: Deployment & Monitoring
- Day 1: Production deployment
- Day 2-3: Monitor batch runs, fix issues
- Day 4-5: Documentation, user testing

**Total: 3-4 weeks**

---

## Testing Strategy

### Phase 1: Unit Tests

```python
# Test EdgarService
async def test_get_cik():
    service = EdgarService()
    cik = await service.get_cik('AAPL')
    assert cik == '0000320193'

# Test XBRL parsing
def test_parse_income_statement():
    with open('test_data/apple_company_facts.json') as f:
        facts = json.load(f)
    
    parser = EdgarXBRLParser(facts)
    stmt = parser.extract_income_statement('2023-09-30')
    
    assert stmt['total_revenue'] > 380000000000  # Apple's revenue
    assert stmt['net_income'] > 90000000000

# Test non-GAAP parsing
def test_parse_non_gaap_table():
    with open('test_data/nvda_8k_exhibit.html') as f:
        html = f.read()
    
    parser = NonGAAPParser(html)
    reconciliation = parser.extract_non_gaap_reconciliation('2023-10-29')
    
    assert reconciliation['gaap_net_income'] is not None
    assert reconciliation['adjustments']['stock_based_compensation'] > 0
```

### Phase 2: Integration Tests

```python
async def test_full_workflow():
    """Test complete flow for one symbol"""
    service = EdgarService()
    
    # 1. Get CIK
    cik = await service.get_cik('NVDA')
    assert cik
    
    # 2. Fetch company facts
    facts = await service.get_company_facts(cik)
    assert facts
    
    # 3. Parse financials
    parser = EdgarXBRLParser(facts)
    statements = parser.extract_all_income_statements()
    assert len(statements) > 0
    
    # 4. Find 8-Ks
    earnings_8ks = await service.find_earnings_8ks(cik, '2023-01-01')
    assert len(earnings_8ks) > 0
    
    # 5. Parse non-GAAP
    # ... test full non-GAAP extraction
```

### Phase 3: Validation Tests

```bash
# Test with diverse companies
python scripts/test_edgar_integration.py --symbols AAPL,GOOGL,MSFT,NVDA,META,AMZN,TSLA,WMT,JPM,BAC

# Check data quality
python scripts/validate_edgar_data.py --check-coverage --check-accuracy
```

---

## Advantages Over Current Yahoo Approach

1. **Official Source** - SEC filings, not scraped data
2. **More Detail** - Full XBRL taxonomy, not just Yahoo's subset
3. **Non-GAAP Transparency** - See exactly what companies adjust
4. **Better Expense Breakdowns** - Can get more granular than SG&A
5. **Historical Depth** - Back to 2009 (XBRL start)
6. **Legal Accuracy** - Companies are legally required to file accurately
7. **No Scraping Fragility** - Official APIs, not web scraping

---

## Risks & Mitigation

### Risk 1: Rate Limits (10 req/sec)
**Mitigation**: Built-in rate limiter, use 9 req/sec, batch intelligently

### Risk 2: HTML Parsing Complexity
**Mitigation**: Start with common patterns (tech companies), expand coverage iteratively

### Risk 3: Missing XBRL Concepts
**Mitigation**: Fallback lists, multiple concept attempts, graceful degradation

### Risk 4: 8-K Press Release Format Variations
**Mitigation**: Table detection heuristics, manual review of edge cases

### Risk 5: Initial Backfill Time
**Mitigation**: Prioritize recent quarters first, backfill historical data in background

---

## Success Metrics

- [ ] 95%+ successful EDGAR data fetch rate
- [ ] Income statements for 90%+ of symbols
- [ ] Non-GAAP reconciliations for 70%+ of major tech stocks
- [ ] <5% discrepancy in known values (validate against public filings)
- [ ] Batch runtime acceptable (<30 min for 100 symbols first run)
- [ ] Zero rate limit violations

---

## Next Steps

Want to start implementing? I can help you:

1. **Proof of Concept** - Build for 3 symbols (AAPL, NVDA, GOOGL)
2. **Write the EdgarService** - Core API client
3. **Test XBRL parsing** - Verify we can extract key metrics
4. **Parse a real 8-K** - Get non-GAAP from Nvidia or Apple press release
5. **Create database migration** - Set up new schema

Which would you like to tackle first?
