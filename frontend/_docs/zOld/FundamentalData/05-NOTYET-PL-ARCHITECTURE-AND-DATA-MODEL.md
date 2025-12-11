# P&L Architecture & Data Model
**Date**: November 2, 2025
**Focus**: Building GAAP → Non-GAAP P&L from EDGAR data

---

## Executive Summary

**Goal**: Build a complete P&L that shows GAAP → Non-GAAP transition by adding back non-cash/non-recurring items.

**Architecture Decision**: 
- Primary Source: EDGAR XBRL (10-K/10-Q) for GAAP P&L
- SBC Breakdown: Try XBRL first, fallback to 10-Q/10-K HTML table parsing
- Final Check: Validate against 8-K press release totals

**Key Insight**: Most companies report SBC by function in their 10-Q/10-K footnotes or supplementary tables, even if not always in structured XBRL tags.

---

## P&L Structure (Your Design)

### GAAP P&L
```
Revenue                                    $100,000
- Cost of Goods Sold (COGS)                (40,000)
─────────────────────────────────────────────────
= Gross Profit                              60,000
  
- Sales & Marketing (S&M)                   (15,000)
- Research & Development (R&D)              (20,000)
- General & Administrative (G&A)            (10,000)
─────────────────────────────────────────────────
= Operating Income (EBIT)                   15,000
```

### Non-GAAP Adjustments (Add back non-cash/non-recurring)
```
GAAP Operating Income                       15,000

Add back Stock-Based Compensation:
  + SBC in COGS                              2,000
  + SBC in S&M                               3,000
  + SBC in R&D                               6,000
  + SBC in G&A                               1,500
─────────────────────────────────────────────────
= Non-GAAP Operating Income                 27,500

Add back Depreciation & Amortization:
  + D&A                                      5,000
─────────────────────────────────────────────────
= EBITDA (Non-GAAP)                         32,500
```

### Side-by-Side Display
```
                           GAAP      Non-GAAP    Difference
Revenue                  100,000      100,000           -
COGS                     (40,000)     (38,000)      2,000  ← SBC add-back
─────────────────────────────────────────────────────────
Gross Profit              60,000       62,000       2,000
Gross Margin %            60.0%        62.0%        +2.0pp

S&M                      (15,000)     (12,000)      3,000  ← SBC add-back
R&D                      (20,000)     (14,000)      6,000  ← SBC add-back
G&A                      (10,000)      (8,500)      1,500  ← SBC add-back
─────────────────────────────────────────────────────────
Operating Income          15,000       27,500      12,500
Operating Margin %        15.0%        27.5%       +12.5pp

+ D&A                          -        5,000       5,000
─────────────────────────────────────────────────────────
EBITDA                    20,000       32,500      12,500
EBITDA Margin %           20.0%        32.5%       +12.5pp
```

---

## Data Sources & Extraction Strategy

### Source 1: EDGAR XBRL (Company Facts API)

**What we get easily**:
- ✅ Revenue
- ✅ COGS
- ✅ Gross Profit
- ✅ R&D Expense
- ✅ SG&A Expense (combined)
- ✅ Operating Income
- ✅ Total SBC (from cash flow statement)
- ✅ D&A (from cash flow statement)

**What we DON'T get easily**:
- ❌ SBC broken down by function (COGS, R&D, S&M, G&A)
- ❌ S&M and G&A separated (often just "SG&A")
- ❌ Other adjustments (restructuring, acquisition costs, etc.)

### Source 2: 10-Q/10-K HTML Tables (Supplementary Data)

Many companies include a **supplementary table** in their 10-Q/10-K that shows:

**Example from a typical tech company**:
```
Stock-based compensation expense:
  Cost of revenues              $2,000
  Sales and marketing            3,000
  Research and development       6,000
  General and administrative     1,500
                              ─────────
  Total stock-based comp        $12,500
```

**Extraction Strategy**:
1. Get 10-Q/10-K filing URL from Submissions API
2. Download HTML
3. Search for section containing "stock-based compensation" table
4. Parse HTML table using BeautifulSoup
5. Extract values by function

### Source 3: Cash Flow Statement (Validation)

**Use for validation**:
- Total SBC from "Stock-based compensation" line in operating activities
- D&A from "Depreciation and amortization" line
- Cross-check our breakdown sums to the cash flow total

### Source 4: 8-K Press Release (Last Resort / Validation)

**Use only if**:
- Can't find SBC breakdown in 10-Q/10-K
- Want to validate our calculations
- Need most recent quarter before 10-Q is filed

---

## Database Schema Design

### Core Financial Statements Table

```sql
CREATE TABLE edgar_financial_statements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identification
    symbol VARCHAR(10) NOT NULL,
    cik VARCHAR(10) NOT NULL,
    
    -- Period Information
    period_end DATE NOT NULL,
    fiscal_year INT NOT NULL,
    fiscal_quarter INT,  -- NULL for annual
    period_type VARCHAR(10) NOT NULL,  -- 'quarterly' or 'annual'
    form_type VARCHAR(10) NOT NULL,  -- '10-Q' or '10-K'
    filed_date DATE NOT NULL,
    accession_number VARCHAR(20),
    
    -- ═══════════════════════════════════════════
    -- GAAP INCOME STATEMENT
    -- ═══════════════════════════════════════════
    
    -- Revenue & Gross Profit
    revenue NUMERIC(20, 2) NOT NULL,
    cost_of_revenue NUMERIC(20, 2),
    gross_profit NUMERIC(20, 2),
    
    -- Operating Expenses (as reported in GAAP)
    research_development_gaap NUMERIC(20, 2),  -- Includes SBC
    sales_marketing_gaap NUMERIC(20, 2),       -- Includes SBC (if separated)
    general_admin_gaap NUMERIC(20, 2),         -- Includes SBC (if separated)
    sg_and_a_gaap NUMERIC(20, 2),              -- If S&M and G&A not separated
    
    -- Operating Income
    operating_income_gaap NUMERIC(20, 2) NOT NULL,
    
    -- Below Operating Income
    interest_expense NUMERIC(20, 2),
    other_income_expense NUMERIC(20, 2),
    income_tax_expense NUMERIC(20, 2),
    
    -- Net Income
    net_income_gaap NUMERIC(20, 2) NOT NULL,
    
    -- Per Share
    basic_eps_gaap NUMERIC(12, 4),
    diluted_eps_gaap NUMERIC(12, 4),
    basic_shares BIGINT,
    diluted_shares BIGINT,
    
    -- ═══════════════════════════════════════════
    -- NON-CASH / NON-RECURRING ADJUSTMENTS
    -- ═══════════════════════════════════════════
    
    -- Stock-Based Compensation (by function)
    sbc_cost_of_revenue NUMERIC(20, 2),        -- Add back to COGS
    sbc_research_development NUMERIC(20, 2),   -- Add back to R&D
    sbc_sales_marketing NUMERIC(20, 2),        -- Add back to S&M
    sbc_general_admin NUMERIC(20, 2),          -- Add back to G&A
    sbc_total NUMERIC(20, 2),                  -- Should equal sum of above
    
    -- Depreciation & Amortization
    depreciation_amortization NUMERIC(20, 2),  -- Add back for EBITDA
    
    -- Other Adjustments (less common, but important)
    restructuring_charges NUMERIC(20, 2),
    acquisition_costs NUMERIC(20, 2),
    impairment_charges NUMERIC(20, 2),
    litigation_settlements NUMERIC(20, 2),
    other_adjustments NUMERIC(20, 2),
    other_adjustments_description TEXT,
    
    -- ═══════════════════════════════════════════
    -- CALCULATED NON-GAAP METRICS
    -- ═══════════════════════════════════════════
    
    -- Calculated: GAAP + SBC addback
    cost_of_revenue_non_gaap NUMERIC(20, 2),     -- COGS - SBC_COGS
    research_development_non_gaap NUMERIC(20, 2),-- R&D - SBC_R&D
    sales_marketing_non_gaap NUMERIC(20, 2),     -- S&M - SBC_S&M
    general_admin_non_gaap NUMERIC(20, 2),       -- G&A - SBC_G&A
    
    operating_income_non_gaap NUMERIC(20, 2),    -- GAAP OI + total SBC
    net_income_non_gaap NUMERIC(20, 2),          -- GAAP NI + adjustments
    diluted_eps_non_gaap NUMERIC(12, 4),         -- Non-GAAP NI / diluted shares
    
    ebitda NUMERIC(20, 2),                       -- OI + D&A + SBC
    
    -- ═══════════════════════════════════════════
    -- MARGINS (for easy querying)
    -- ═══════════════════════════════════════════
    
    gross_margin_gaap NUMERIC(8, 4),             -- GP / Revenue
    operating_margin_gaap NUMERIC(8, 4),         -- OI / Revenue
    net_margin_gaap NUMERIC(8, 4),               -- NI / Revenue
    
    gross_margin_non_gaap NUMERIC(8, 4),
    operating_margin_non_gaap NUMERIC(8, 4),
    net_margin_non_gaap NUMERIC(8, 4),
    ebitda_margin NUMERIC(8, 4),
    
    -- ═══════════════════════════════════════════
    -- METADATA
    -- ═══════════════════════════════════════════
    
    sbc_data_source VARCHAR(50),                 -- 'xbrl', '10q_table', '8k_press_release'
    data_quality_score INT,                      -- 0-100, based on completeness
    notes TEXT,                                  -- Any parsing notes/warnings
    
    currency VARCHAR(3) DEFAULT 'USD',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Prevent duplicates
    UNIQUE(cik, period_end, period_type)
);

-- Indexes for performance
CREATE INDEX idx_fin_stmt_symbol ON edgar_financial_statements(symbol);
CREATE INDEX idx_fin_stmt_period ON edgar_financial_statements(period_end DESC);
CREATE INDEX idx_fin_stmt_cik ON edgar_financial_statements(cik);
CREATE INDEX idx_fin_stmt_filed_date ON edgar_financial_statements(filed_date DESC);
```

### Supporting Tables

```sql
-- Balance Sheet (keep separate for clarity)
CREATE TABLE edgar_balance_sheets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(10) NOT NULL,
    cik VARCHAR(10) NOT NULL,
    period_end DATE NOT NULL,
    
    -- Assets
    cash_and_equivalents NUMERIC(20, 2),
    short_term_investments NUMERIC(20, 2),
    accounts_receivable NUMERIC(20, 2),
    inventory NUMERIC(20, 2),
    total_current_assets NUMERIC(20, 2),
    
    property_plant_equipment NUMERIC(20, 2),
    intangible_assets NUMERIC(20, 2),
    goodwill NUMERIC(20, 2),
    total_assets NUMERIC(20, 2),
    
    -- Liabilities
    accounts_payable NUMERIC(20, 2),
    accrued_expenses NUMERIC(20, 2),
    short_term_debt NUMERIC(20, 2),
    total_current_liabilities NUMERIC(20, 2),
    
    long_term_debt NUMERIC(20, 2),
    total_liabilities NUMERIC(20, 2),
    
    -- Equity
    common_stock NUMERIC(20, 2),
    retained_earnings NUMERIC(20, 2),
    total_equity NUMERIC(20, 2),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(cik, period_end)
);

-- Cash Flow Statement
CREATE TABLE edgar_cash_flows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(10) NOT NULL,
    cik VARCHAR(10) NOT NULL,
    period_end DATE NOT NULL,
    
    -- Operating Activities
    net_income NUMERIC(20, 2),
    depreciation_amortization NUMERIC(20, 2),
    stock_based_compensation NUMERIC(20, 2),
    changes_in_working_capital NUMERIC(20, 2),
    cash_from_operations NUMERIC(20, 2),
    
    -- Investing Activities
    capital_expenditures NUMERIC(20, 2),
    acquisitions NUMERIC(20, 2),
    cash_from_investing NUMERIC(20, 2),
    
    -- Financing Activities
    stock_repurchases NUMERIC(20, 2),
    dividends_paid NUMERIC(20, 2),
    debt_issued NUMERIC(20, 2),
    cash_from_financing NUMERIC(20, 2),
    
    -- Free Cash Flow (calculated)
    free_cash_flow NUMERIC(20, 2),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(cik, period_end)
);
```

---

## Data Extraction Logic

### Step 1: Get GAAP P&L from XBRL

```python
class EdgarXBRLParser:
    
    def extract_income_statement(self, period_end: str) -> Dict:
        """Extract GAAP income statement from Company Facts."""
        
        return {
            # Core P&L
            'revenue': self._get_concept_value(
                ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax'],
                period_end
            ),
            'cost_of_revenue': self._get_concept_value(
                ['CostOfRevenue', 'CostOfGoodsAndServicesSold'],
                period_end
            ),
            'gross_profit': self._get_concept_value(['GrossProfit'], period_end),
            
            # Operating Expenses (GAAP - includes SBC)
            'research_development_gaap': self._get_concept_value(
                ['ResearchAndDevelopmentExpense'],
                period_end
            ),
            'sg_and_a_gaap': self._get_concept_value(
                ['SellingGeneralAndAdministrativeExpense'],
                period_end
            ),
            
            # Try to get S&M and G&A separately
            'sales_marketing_gaap': self._get_concept_value(
                ['SellingAndMarketingExpense', 'MarketingExpense'],
                period_end
            ),
            'general_admin_gaap': self._get_concept_value(
                ['GeneralAndAdministrativeExpense'],
                period_end
            ),
            
            'operating_income_gaap': self._get_concept_value(
                ['OperatingIncomeLoss'],
                period_end
            ),
            'net_income_gaap': self._get_concept_value(
                ['NetIncomeLoss'],
                period_end
            ),
            
            # Per share
            'diluted_eps_gaap': self._get_concept_value(
                ['EarningsPerShareDiluted'],
                period_end
            ),
        }
```

### Step 2: Try to Get SBC Breakdown from XBRL

```python
def extract_sbc_breakdown_from_xbrl(self, period_end: str) -> Optional[Dict]:
    """
    Try to get SBC broken down by function from XBRL.
    
    Note: Not all companies tag this in structured XBRL.
    May return None if not available.
    """
    
    # Try common XBRL concepts for SBC by function
    sbc_breakdown = {
        'sbc_cost_of_revenue': self._get_concept_value(
            ['ShareBasedCompensationCostOfRevenue', 
             'AllocatedShareBasedCompensationCostOfRevenue'],
            period_end
        ),
        'sbc_research_development': self._get_concept_value(
            ['ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost',  # Sometimes tagged separately
             'ShareBasedCompensationResearchAndDevelopment'],
            period_end
        ),
        'sbc_sales_marketing': self._get_concept_value(
            ['ShareBasedCompensationSellingAndMarketing'],
            period_end
        ),
        'sbc_general_admin': self._get_concept_value(
            ['ShareBasedCompensationGeneralAndAdministrative'],
            period_end
        ),
    }
    
    # Check if we got any SBC breakdown data
    if not any(sbc_breakdown.values()):
        return None
    
    # Get total SBC for validation
    sbc_breakdown['sbc_total'] = self._get_concept_value(
        ['ShareBasedCompensation',
         'AllocatedShareBasedCompensationExpense'],
        period_end
    )
    
    return sbc_breakdown
```

### Step 3: Fallback - Parse SBC Table from 10-Q/10-K HTML

```python
class Edgar10QParser:
    """
    Parse 10-Q/10-K HTML to extract SBC breakdown table.
    
    This is our fallback when XBRL doesn't have SBC by function.
    """
    
    def __init__(self, filing_html: str):
        self.soup = BeautifulSoup(filing_html, 'html.parser')
    
    def find_sbc_table(self) -> Optional[Any]:
        """
        Find the table showing SBC by function.
        
        Look for tables with text like:
        - "Stock-based compensation"
        - "Cost of revenues"
        - "Research and development"
        - "Sales and marketing"
        """
        tables = self.soup.find_all('table')
        
        for table in tables:
            table_text = table.get_text().lower()
            
            # Check if this table has SBC breakdown
            has_sbc = 'stock-based compensation' in table_text or 'share-based compensation' in table_text
            has_functions = all(term in table_text for term in [
                'cost of', 'research', 'development'
            ])
            
            if has_sbc and has_functions:
                return table
        
        return None
    
    def extract_sbc_from_table(self, table: Any) -> Dict[str, float]:
        """
        Parse SBC amounts from the HTML table.
        
        Returns:
            {
                'sbc_cost_of_revenue': 2000000,
                'sbc_research_development': 6000000,
                'sbc_sales_marketing': 3000000,
                'sbc_general_admin': 1500000,
                'sbc_total': 12500000
            }
        """
        rows = table.find_all('tr')
        sbc_data = {}
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 2:
                continue
            
            # Get row label
            label = cells[0].get_text().strip().lower()
            
            # Get value (usually in second column for current period)
            value_text = cells[1].get_text().strip()
            value = self._parse_financial_value(value_text)
            
            # Match to our standardized fields
            if 'cost of' in label and 'revenue' in label:
                sbc_data['sbc_cost_of_revenue'] = value
            elif 'research' in label and 'development' in label:
                sbc_data['sbc_research_development'] = value
            elif 'sales' in label or 'marketing' in label:
                sbc_data['sbc_sales_marketing'] = value
            elif 'general' in label and 'administrative' in label:
                sbc_data['sbc_general_admin'] = value
            elif 'total' in label:
                sbc_data['sbc_total'] = value
        
        return sbc_data
    
    def _parse_financial_value(self, text: str) -> Optional[float]:
        """
        Parse dollar amount from table cell.
        
        Handles: "$1,234", "(1,234)", "1,234.5", etc.
        """
        # Remove $ and commas
        text = text.replace('$', '').replace(',', '').strip()
        
        # Handle parentheses (negative)
        is_negative = text.startswith('(') and text.endswith(')')
        if is_negative:
            text = text[1:-1]
        
        # Handle dashes (zero)
        if text in ['-', '—', '–']:
            return 0.0
        
        try:
            value = float(text)
            
            # Most tables are in thousands or millions
            # We'll need to check the table header for units
            # For now, assume thousands if < 100,000
            if value < 100000:
                value = value * 1000
            
            return -value if is_negative else value
        except ValueError:
            return None
```

### Step 4: Orchestration Logic

```python
class FinancialStatementExtractor:
    """
    Orchestrates extraction of complete financial statements with SBC breakdown.
    """
    
    async def extract_complete_financials(
        self,
        cik: str,
        period_end: str
    ) -> Dict[str, Any]:
        """
        Get complete financial statements with non-GAAP adjustments.
        
        Process:
        1. Get GAAP P&L from XBRL
        2. Try to get SBC breakdown from XBRL
        3. If not in XBRL, parse from 10-Q/10-K HTML
        4. Get D&A from cash flow statement
        5. Calculate non-GAAP metrics
        """
        
        # 1. Get Company Facts (XBRL)
        edgar_service = EdgarService()
        company_facts = await edgar_service.get_company_facts(cik)
        
        xbrl_parser = EdgarXBRLParser(company_facts)
        
        # 2. Extract GAAP P&L
        gaap_pl = xbrl_parser.extract_income_statement(period_end)
        
        # 3. Try to get SBC breakdown from XBRL
        sbc_breakdown = xbrl_parser.extract_sbc_breakdown_from_xbrl(period_end)
        
        # 4. If SBC not in XBRL, parse from 10-Q/10-K
        if not sbc_breakdown:
            # Get 10-Q filing URL
            submissions = await edgar_service.get_submissions(cik)
            filing_url = self._find_10q_url(submissions, period_end)
            
            # Download and parse
            filing_html = await edgar_service.download_filing(filing_url)
            filing_parser = Edgar10QParser(filing_html)
            
            sbc_table = filing_parser.find_sbc_table()
            if sbc_table:
                sbc_breakdown = filing_parser.extract_sbc_from_table(sbc_table)
                sbc_breakdown['_source'] = '10q_html_table'
            else:
                # Can't find SBC breakdown
                sbc_breakdown = self._estimate_sbc_allocation(
                    gaap_pl,
                    xbrl_parser.get_total_sbc(period_end)
                )
                sbc_breakdown['_source'] = 'estimated'
        else:
            sbc_breakdown['_source'] = 'xbrl'
        
        # 5. Get D&A from cash flow statement
        da = xbrl_parser.extract_depreciation_amortization(period_end)
        
        # 6. Calculate non-GAAP metrics
        non_gaap_pl = self._calculate_non_gaap(gaap_pl, sbc_breakdown, da)
        
        # 7. Combine everything
        return {
            'period_end': period_end,
            'gaap': gaap_pl,
            'adjustments': {
                'sbc_breakdown': sbc_breakdown,
                'depreciation_amortization': da
            },
            'non_gaap': non_gaap_pl,
            'data_quality': self._assess_data_quality(sbc_breakdown)
        }
    
    def _calculate_non_gaap(
        self,
        gaap: Dict,
        sbc: Dict,
        da: float
    ) -> Dict:
        """
        Calculate non-GAAP metrics by adding back SBC to each line.
        """
        
        # Non-GAAP COGS (subtract SBC from GAAP COGS)
        cost_of_revenue_non_gaap = (
            gaap['cost_of_revenue'] - sbc.get('sbc_cost_of_revenue', 0)
        )
        
        # Non-GAAP Operating Expenses
        rd_non_gaap = (
            gaap['research_development_gaap'] - sbc.get('sbc_research_development', 0)
        )
        sm_non_gaap = (
            gaap.get('sales_marketing_gaap', 0) - sbc.get('sbc_sales_marketing', 0)
        )
        ga_non_gaap = (
            gaap.get('general_admin_gaap', 0) - sbc.get('sbc_general_admin', 0)
        )
        
        # Non-GAAP Operating Income
        operating_income_non_gaap = (
            gaap['operating_income_gaap'] + sbc.get('sbc_total', 0)
        )
        
        # EBITDA
        ebitda = operating_income_non_gaap + da
        
        # Margins
        revenue = gaap['revenue']
        gross_margin_non_gaap = (
            (revenue - cost_of_revenue_non_gaap) / revenue if revenue else 0
        )
        operating_margin_non_gaap = operating_income_non_gaap / revenue if revenue else 0
        ebitda_margin = ebitda / revenue if revenue else 0
        
        return {
            'cost_of_revenue_non_gaap': cost_of_revenue_non_gaap,
            'research_development_non_gaap': rd_non_gaap,
            'sales_marketing_non_gaap': sm_non_gaap,
            'general_admin_non_gaap': ga_non_gaap,
            'operating_income_non_gaap': operating_income_non_gaap,
            'ebitda': ebitda,
            'gross_margin_non_gaap': gross_margin_non_gaap,
            'operating_margin_non_gaap': operating_margin_non_gaap,
            'ebitda_margin': ebitda_margin
        }
    
    def _estimate_sbc_allocation(
        self,
        gaap_pl: Dict,
        total_sbc: float
    ) -> Dict:
        """
        Estimate SBC allocation if we can't find the breakdown.
        
        Use industry-typical allocations:
        - Tech companies: ~70% R&D, ~15% S&M, ~10% G&A, ~5% COGS
        - Other: More evenly distributed
        """
        # This is a fallback - not ideal but better than nothing
        return {
            'sbc_cost_of_revenue': total_sbc * 0.05,
            'sbc_research_development': total_sbc * 0.70,
            'sbc_sales_marketing': total_sbc * 0.15,
            'sbc_general_admin': total_sbc * 0.10,
            'sbc_total': total_sbc,
            '_estimated': True
        }
    
    def _assess_data_quality(self, sbc_breakdown: Dict) -> int:
        """
        Score data quality 0-100.
        
        100: All SBC by function from XBRL
        80: SBC from 10-Q HTML table
        50: Estimated SBC allocation
        """
        source = sbc_breakdown.get('_source', 'unknown')
        
        if source == 'xbrl':
            return 100
        elif source == '10q_html_table':
            return 80
        elif source == 'estimated':
            return 50
        else:
            return 0
```

---

## Frontend Display Design

### Component 1: P&L Table (Primary View)

```jsx
// components/FinancialStatements/PLStatement.tsx

interface PLRow {
  label: string;
  gaap: number;
  nonGaap: number;
  adjustment: number;
  isHeader?: boolean;
  isSubtotal?: boolean;
  indent?: number;
}

function PLStatement({ data, periodEnd }: Props) {
  const rows: PLRow[] = [
    // Revenue
    {
      label: 'Revenue',
      gaap: data.revenue,
      nonGaap: data.revenue,
      adjustment: 0,
      isHeader: true
    },
    
    // COGS
    {
      label: 'Cost of Revenue',
      gaap: -data.cost_of_revenue_gaap,
      nonGaap: -data.cost_of_revenue_non_gaap,
      adjustment: data.sbc_cost_of_revenue,
      indent: 1
    },
    
    // Gross Profit
    {
      label: 'Gross Profit',
      gaap: data.gross_profit_gaap,
      nonGaap: data.gross_profit_non_gaap,
      adjustment: data.sbc_cost_of_revenue,
      isSubtotal: true
    },
    {
      label: 'Gross Margin %',
      gaap: data.gross_margin_gaap * 100,
      nonGaap: data.gross_margin_non_gaap * 100,
      adjustment: (data.gross_margin_non_gaap - data.gross_margin_gaap) * 100,
      isSubtotal: true,
      isPercentage: true
    },
    
    // Operating Expenses
    {
      label: 'Operating Expenses',
      isHeader: true
    },
    {
      label: 'Research & Development',
      gaap: -data.research_development_gaap,
      nonGaap: -data.research_development_non_gaap,
      adjustment: data.sbc_research_development,
      indent: 1
    },
    {
      label: 'Sales & Marketing',
      gaap: -data.sales_marketing_gaap,
      nonGaap: -data.sales_marketing_non_gaap,
      adjustment: data.sbc_sales_marketing,
      indent: 1
    },
    {
      label: 'General & Administrative',
      gaap: -data.general_admin_gaap,
      nonGaap: -data.general_admin_non_gaap,
      adjustment: data.sbc_general_admin,
      indent: 1
    },
    
    // Operating Income
    {
      label: 'Operating Income (EBIT)',
      gaap: data.operating_income_gaap,
      nonGaap: data.operating_income_non_gaap,
      adjustment: data.sbc_total,
      isSubtotal: true
    },
    {
      label: 'Operating Margin %',
      gaap: data.operating_margin_gaap * 100,
      nonGaap: data.operating_margin_non_gaap * 100,
      adjustment: (data.operating_margin_non_gaap - data.operating_margin_gaap) * 100,
      isSubtotal: true,
      isPercentage: true
    },
    
    // EBITDA
    {
      label: 'Add: Depreciation & Amortization',
      gaap: 0,
      nonGaap: data.depreciation_amortization,
      adjustment: data.depreciation_amortization,
      indent: 1
    },
    {
      label: 'EBITDA',
      gaap: data.operating_income_gaap + data.depreciation_amortization,
      nonGaap: data.ebitda,
      adjustment: data.sbc_total + data.depreciation_amortization,
      isSubtotal: true
    },
    {
      label: 'EBITDA Margin %',
      gaap: data.ebitda_margin_gaap * 100,
      nonGaap: data.ebitda_margin * 100,
      adjustment: (data.ebitda_margin - data.ebitda_margin_gaap) * 100,
      isSubtotal: true,
      isPercentage: true
    },
  ];
  
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b-2 border-gray-300">
            <th className="text-left p-2">Line Item</th>
            <th className="text-right p-2">GAAP</th>
            <th className="text-right p-2">Adjustment</th>
            <th className="text-right p-2">Non-GAAP</th>
            <th className="text-right p-2">Impact</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <PLRow key={idx} {...row} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PLRow({ 
  label, 
  gaap, 
  nonGaap, 
  adjustment, 
  isHeader, 
  isSubtotal,
  indent = 0,
  isPercentage = false
}: PLRow) {
  const formatValue = (val: number) => {
    if (isPercentage) {
      return `${val.toFixed(1)}%`;
    }
    return `$${(val / 1000000).toFixed(1)}M`;
  };
  
  const impact = nonGaap - gaap;
  const impactPct = gaap !== 0 ? (impact / Math.abs(gaap)) * 100 : 0;
  
  const rowClasses = clsx(
    'border-b border-gray-200',
    isHeader && 'font-bold bg-gray-50',
    isSubtotal && 'font-semibold border-t-2 border-gray-400'
  );
  
  return (
    <tr className={rowClasses}>
      <td className="p-2" style={{ paddingLeft: `${indent * 1.5}rem` }}>
        {label}
      </td>
      <td className="text-right p-2 font-mono">
        {!isHeader && formatValue(gaap)}
      </td>
      <td className="text-right p-2 font-mono text-green-600">
        {!isHeader && adjustment !== 0 && `+${formatValue(adjustment)}`}
      </td>
      <td className="text-right p-2 font-mono font-semibold">
        {!isHeader && formatValue(nonGaap)}
      </td>
      <td className="text-right p-2 text-sm text-gray-600">
        {!isHeader && impact !== 0 && (
          <span>
            {impact > 0 ? '+' : ''}{formatValue(impact)}
            <span className="text-xs ml-1">({impactPct.toFixed(0)}%)</span>
          </span>
        )}
      </td>
    </tr>
  );
}
```

### Component 2: SBC Breakdown Visualization

```jsx
// components/FinancialStatements/SBCBreakdown.tsx

function SBCBreakdown({ data }: Props) {
  const sbcData = [
    { label: 'COGS', amount: data.sbc_cost_of_revenue, color: 'blue' },
    { label: 'R&D', amount: data.sbc_research_development, color: 'green' },
    { label: 'S&M', amount: data.sbc_sales_marketing, color: 'yellow' },
    { label: 'G&A', amount: data.sbc_general_admin, color: 'purple' },
  ];
  
  const total = sbcData.reduce((sum, item) => sum + item.amount, 0);
  
  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h3 className="text-lg font-semibold mb-4">
        Stock-Based Compensation Breakdown
      </h3>
      
      {/* Bar Chart */}
      <div className="space-y-2">
        {sbcData.map((item) => {
          const percentage = (item.amount / total) * 100;
          return (
            <div key={item.label} className="flex items-center gap-3">
              <div className="w-20 text-sm font-medium">{item.label}</div>
              <div className="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden">
                <div 
                  className={`h-full bg-${item.color}-500 flex items-center justify-end pr-2`}
                  style={{ width: `${percentage}%` }}
                >
                  <span className="text-xs font-semibold text-white">
                    {percentage.toFixed(0)}%
                  </span>
                </div>
              </div>
              <div className="w-24 text-right font-mono text-sm">
                ${(item.amount / 1000000).toFixed(1)}M
              </div>
            </div>
          );
        })}
      </div>
      
      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="flex justify-between font-semibold">
          <span>Total SBC</span>
          <span className="font-mono">${(total / 1000000).toFixed(1)}M</span>
        </div>
        <div className="text-sm text-gray-600 mt-1">
          {(total / data.revenue * 100).toFixed(1)}% of Revenue
        </div>
      </div>
      
      {/* Data Quality Indicator */}
      {data.sbc_data_source && (
        <div className="mt-4 text-xs text-gray-500">
          Source: {data.sbc_data_source === 'xbrl' ? 'XBRL (Structured Data)' :
                   data.sbc_data_source === '10q_table' ? '10-Q HTML Table' :
                   'Estimated Allocation'}
        </div>
      )}
    </div>
  );
}
```

### Component 3: Multi-Period Comparison

```jsx
// components/FinancialStatements/MultiPeriodPL.tsx

function MultiPeriodPL({ periods }: Props) {
  // periods = [Q1 2024, Q2 2024, Q3 2024, Q4 2024]
  
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr>
            <th className="text-left p-2 sticky left-0 bg-white">Metric</th>
            {periods.map(p => (
              <th key={p.period_end} className="text-right p-2">
                {formatQuarter(p.period_end)}
              </th>
            ))}
            <th className="text-right p-2">Trend</th>
          </tr>
        </thead>
        <tbody>
          {/* Revenue */}
          <tr className="border-b">
            <td className="p-2 font-medium sticky left-0 bg-white">Revenue</td>
            {periods.map(p => (
              <td key={p.period_end} className="text-right p-2 font-mono">
                ${(p.revenue / 1000000).toFixed(1)}M
              </td>
            ))}
            <td className="text-right p-2">
              <TrendIndicator values={periods.map(p => p.revenue)} />
            </td>
          </tr>
          
          {/* Operating Margin (Non-GAAP) */}
          <tr className="border-b">
            <td className="p-2 font-medium sticky left-0 bg-white">
              Op. Margin (Non-GAAP)
            </td>
            {periods.map(p => (
              <td key={p.period_end} className="text-right p-2 font-mono">
                {(p.operating_margin_non_gaap * 100).toFixed(1)}%
              </td>
            ))}
            <td className="text-right p-2">
              <TrendIndicator 
                values={periods.map(p => p.operating_margin_non_gaap)} 
                isPercentage
              />
            </td>
          </tr>
          
          {/* More rows... */}
        </tbody>
      </table>
    </div>
  );
}
```

---

## API Endpoints

```python
# backend/app/api/v1/endpoints/financials.py

@router.get("/financials/{symbol}/income-statement")
async def get_income_statement(
    symbol: str,
    periods: int = Query(4, ge=1, le=20),
    period_type: str = Query("quarterly", enum=["quarterly", "annual"]),
    db: Session = Depends(get_db)
):
    """
    Get P&L with GAAP and Non-GAAP side-by-side.
    
    Returns:
    {
        "symbol": "AAPL",
        "periods": [
            {
                "period_end": "2024-09-30",
                "fiscal_year": 2024,
                "fiscal_quarter": 4,
                "gaap": {
                    "revenue": 94930000000,
                    "cost_of_revenue": 55180000000,
                    ...
                },
                "adjustments": {
                    "sbc_total": 12500000000,
                    "sbc_cost_of_revenue": 625000000,
                    ...
                },
                "non_gaap": {
                    "operating_income": 32100000000,
                    "operating_margin": 0.338,
                    ...
                },
                "data_quality_score": 100
            },
            ...
        ]
    }
    """
    statements = db.query(EdgarFinancialStatement)\
        .filter(
            EdgarFinancialStatement.symbol == symbol.upper(),
            EdgarFinancialStatement.period_type == period_type
        )\
        .order_by(EdgarFinancialStatement.period_end.desc())\
        .limit(periods)\
        .all()
    
    if not statements:
        raise HTTPException(404, f"No data found for {symbol}")
    
    return {
        'symbol': symbol.upper(),
        'period_type': period_type,
        'periods': [stmt.to_dict() for stmt in statements]
    }
```

---

## Implementation Timeline

### Week 1: XBRL Extraction + Database
- Day 1-2: XBRL parser for GAAP P&L
- Day 3: Try to get SBC from XBRL
- Day 4-5: Database schema migration and storage logic

### Week 2: HTML Table Parsing Fallback
- Day 1-2: 10-Q/10-K HTML downloader
- Day 3-4: SBC table parser with multiple company testing
- Day 5: Integration and validation

### Week 3: Calculations + API
- Day 1-2: Non-GAAP calculation logic
- Day 3: API endpoints
- Day 4-5: Testing with 20 companies

### Week 4: Frontend
- Day 1-2: P&L table component
- Day 3: SBC breakdown visualization
- Day 4-5: Multi-period views, polish

**Total: 4 weeks**

---

## Success Criteria

- [ ] GAAP P&L for 95%+ of symbols
- [ ] SBC breakdown for 80%+ of companies
  - 50%+ from XBRL
  - 30%+ from 10-Q table parsing
  - <20% estimated
- [ ] Calculations validate against company-reported non-GAAP (when available)
- [ ] Frontend displays cleanly for users
- [ ] Data quality scores help users understand reliability

---

## Questions for Review

1. **SBC Source Priority**: Try XBRL → 10-Q table → estimate. Agree?
2. **Table Structure**: Single wide table vs separate GAAP/Non-GAAP tables?
3. **Frontend View**: Side-by-side comparison (as shown) vs toggle between GAAP/Non-GAAP?
4. **8-K Usage**: Only for validation, not primary source? (Cleaner this way)

---

## Next Steps

Ready to start building? We can:
1. **Test XBRL extraction** - See if Apple, Nvidia, Google have SBC by function in XBRL
2. **Build HTML table parser** - Parse real 10-Q for SBC breakdown
3. **Create database schema** - Implement the full table structure
4. **Build calculation engine** - GAAP → Non-GAAP logic

Which would you like to start with?
