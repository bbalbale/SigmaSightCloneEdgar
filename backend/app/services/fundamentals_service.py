"""
Fundamentals Service Layer

Transforms raw YahooQuery data into structured Pydantic schemas
and calculates derived financial metrics.
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID, uuid4
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.clients.yahooquery_client import YahooQueryClient
from app.models.market_data import CompanyProfile
from app.models.fundamentals import IncomeStatement, BalanceSheet, CashFlow
from app.schemas.fundamentals import (
    IncomeStatementResponse,
    IncomeStatementPeriod,
    IncomeStatementMetrics,
    BalanceSheetResponse,
    BalanceSheetPeriod,
    BalanceSheetMetrics,
    Assets,
    CurrentAssets,
    NonCurrentAssets,
    Liabilities,
    CurrentLiabilities,
    NonCurrentLiabilities,
    Equity,
    BalanceSheetCalculatedMetrics,
    BalanceSheetRatios,
    CashFlowResponse,
    CashFlowPeriod,
    CashFlowMetrics,
    OperatingActivities,
    InvestingActivities,
    FinancingActivities,
    CashFlowCalculatedMetrics,
    AllStatementsResponse,
    Metadata,
    FinancialPeriod,
)

logger = logging.getLogger(__name__)


class FundamentalsService:
    """Service for retrieving and transforming fundamental financial data"""

    def __init__(self):
        self.client = YahooQueryClient()

    def _safe_decimal(self, value: Any) -> Optional[Decimal]:
        """
        Safely convert value to Decimal, returning None for invalid values

        Args:
            value: Value to convert

        Returns:
            Decimal or None
        """
        if value is None or pd.isna(value):
            return None

        try:
            return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except (ValueError, TypeError, ArithmeticError):
            return None

    def _safe_int(self, value: Any) -> Optional[int]:
        """Safely convert value to int, returning None for invalid values"""
        if value is None or pd.isna(value):
            return None

        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def _calculate_margin(self, numerator: Optional[Decimal], denominator: Optional[Decimal]) -> Optional[Decimal]:
        """
        Calculate margin (numerator / denominator)

        Args:
            numerator: Numerator value
            denominator: Denominator value

        Returns:
            Margin as decimal (e.g., 0.25 for 25%) or None
        """
        if numerator is None or denominator is None or denominator == 0:
            return None

        try:
            margin = (numerator / denominator).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
            return margin
        except (ValueError, ArithmeticError):
            return None

    def _extract_period_info(self, period_date: Any) -> Dict[str, Any]:
        """
        Extract fiscal period information from date

        Args:
            period_date: Date or datetime object

        Returns:
            Dictionary with period_date, fiscal_year, fiscal_quarter
        """
        if isinstance(period_date, datetime):
            date_obj = period_date.date()
        elif isinstance(period_date, date):
            date_obj = period_date
        else:
            # Try to parse string
            try:
                date_obj = pd.to_datetime(period_date).date()
            except:
                logger.warning(f"Could not parse date: {period_date}")
                return None

        # Extract fiscal quarter from month
        month = date_obj.month
        if month in [1, 2, 3]:
            quarter = "Q1"
        elif month in [4, 5, 6]:
            quarter = "Q2"
        elif month in [7, 8, 9]:
            quarter = "Q3"
        else:
            quarter = "Q4"

        return {
            'period_date': date_obj,
            'fiscal_year': date_obj.year,
            'fiscal_quarter': quarter
        }

    async def get_income_statement(
        self,
        symbol: str,
        frequency: str = 'q',
        periods: int = 12
    ) -> IncomeStatementResponse:
        """
        Get income statement data for a symbol

        Args:
            symbol: Stock symbol
            frequency: 'q' (quarterly) or 'a' (annual)
            periods: Number of periods to return (default: 12)

        Returns:
            IncomeStatementResponse
        """
        # Fetch raw data from YahooQuery
        raw_data = await self.client.get_income_statement(symbol, frequency)

        # raw_data is a dict like {symbol: DataFrame}
        if not raw_data or symbol not in raw_data:
            logger.warning(f"No income statement data for {symbol}")
            return IncomeStatementResponse(
                symbol=symbol,
                frequency=frequency,
                currency="USD",
                periods=[],
                metadata=Metadata(
                    data_source="yahooquery",
                    last_updated=datetime.now(),
                    periods_returned=0
                )
            )

        df = raw_data[symbol]

        if not isinstance(df, pd.DataFrame) or df.empty:
            logger.warning(f"Income statement DataFrame empty for {symbol}")
            return IncomeStatementResponse(
                symbol=symbol,
                frequency=frequency,
                currency="USD",
                periods=[],
                metadata=Metadata(
                    data_source="yahooquery",
                    last_updated=datetime.now(),
                    periods_returned=0
                )
            )

        # Filter to only quarterly periods (exclude TTM)
        if frequency == 'q':
            df = df[df['periodType'] == '3M']
        elif frequency == 'a':
            df = df[df['periodType'] == '12M']

        # Sort by date descending (most recent first)
        df = df.sort_values('asOfDate', ascending=False)

        # Limit to requested number of periods
        df = df.head(periods)

        # Transform DataFrame rows to periods
        statement_periods = []

        for idx, row in df.iterrows():
            # Extract period info from asOfDate column
            period_info = self._extract_period_info(row.get('asOfDate'))
            if not period_info:
                continue

            # Extract metrics from row
            revenue = self._safe_decimal(row.get('TotalRevenue') or row.get('OperatingRevenue'))
            cost_of_revenue = self._safe_decimal(row.get('CostOfRevenue') or row.get('ReconciledCostOfRevenue'))
            gross_profit = self._safe_decimal(row.get('GrossProfit'))
            rd = self._safe_decimal(row.get('ResearchAndDevelopment'))
            sga = self._safe_decimal(row.get('SellingGeneralAndAdministration'))
            operating_expense = self._safe_decimal(row.get('OperatingExpense'))
            operating_income = self._safe_decimal(row.get('OperatingIncome'))
            ebit = self._safe_decimal(row.get('EBIT'))
            interest_expense = self._safe_decimal(row.get('InterestExpense') or row.get('InterestExpenseNonOperating'))
            other_income = self._safe_decimal(row.get('OtherIncomeExpense'))
            pretax_income = self._safe_decimal(row.get('PretaxIncome'))
            tax_provision = self._safe_decimal(row.get('TaxProvision'))
            net_income = self._safe_decimal(row.get('NetIncome'))
            ebitda = self._safe_decimal(row.get('EBITDA') or row.get('NormalizedEBITDA'))
            depreciation = self._safe_decimal(row.get('ReconciledDepreciation') or row.get('DepreciationAndAmortization'))
            basic_eps = self._safe_decimal(row.get('BasicEPS'))
            diluted_eps = self._safe_decimal(row.get('DilutedEPS'))
            basic_shares = self._safe_int(row.get('BasicAverageShares'))
            diluted_shares = self._safe_int(row.get('DilutedAverageShares'))

            # Calculate margins
            gross_margin = self._calculate_margin(gross_profit, revenue)
            operating_margin = self._calculate_margin(operating_income, revenue)
            net_margin = self._calculate_margin(net_income, revenue)
            tax_rate = self._calculate_margin(tax_provision, pretax_income)

            # Create metrics object
            metrics = IncomeStatementMetrics(
                revenue=revenue,
                cost_of_revenue=cost_of_revenue,
                gross_profit=gross_profit,
                gross_margin=gross_margin,
                research_and_development=rd,
                selling_general_administrative=sga,
                total_operating_expenses=operating_expense,
                operating_income=operating_income,
                operating_margin=operating_margin,
                ebit=ebit,
                interest_expense=interest_expense,
                other_income_expense=other_income,
                pretax_income=pretax_income,
                tax_provision=tax_provision,
                tax_rate=tax_rate,
                net_income=net_income,
                net_margin=net_margin,
                ebitda=ebitda,
                depreciation_amortization=depreciation,
                basic_eps=basic_eps,
                diluted_eps=diluted_eps,
                basic_shares=basic_shares,
                diluted_shares=diluted_shares
            )

            # Create period
            period = IncomeStatementPeriod(
                period_date=period_info['period_date'],
                period_type="3M" if frequency == 'q' else "12M",
                fiscal_year=period_info['fiscal_year'],
                fiscal_quarter=period_info['fiscal_quarter'] if frequency == 'q' else None,
                metrics=metrics
            )

            statement_periods.append(period)

            # Limit to requested number of periods
            if len(statement_periods) >= periods:
                break

        return IncomeStatementResponse(
            symbol=symbol,
            frequency=frequency,
            currency="USD",  # YahooQuery defaults to USD
            periods=statement_periods,
            metadata=Metadata(
                data_source="yahooquery",
                last_updated=datetime.now(),
                periods_returned=len(statement_periods)
            )
        )

    async def get_balance_sheet(
        self,
        symbol: str,
        frequency: str = 'q',
        periods: int = 12
    ) -> BalanceSheetResponse:
        """
        Get balance sheet data for a symbol

        Args:
            symbol: Stock symbol
            frequency: 'q' (quarterly) or 'a' (annual)
            periods: Number of periods to return (default: 12)

        Returns:
            BalanceSheetResponse
        """
        # Fetch raw data
        raw_data = await self.client.get_balance_sheet(symbol, frequency)

        if not raw_data or symbol not in raw_data:
            logger.warning(f"No balance sheet data for {symbol}")
            return BalanceSheetResponse(
                symbol=symbol,
                frequency=frequency,
                currency="USD",
                periods=[],
                metadata=Metadata(
                    data_source="yahooquery",
                    last_updated=datetime.now(),
                    periods_returned=0
                )
            )

        df = raw_data[symbol]

        if not isinstance(df, pd.DataFrame) or df.empty:
            return BalanceSheetResponse(
                symbol=symbol,
                frequency=frequency,
                currency="USD",
                periods=[],
                metadata=Metadata(
                    data_source="yahooquery",
                    last_updated=datetime.now(),
                    periods_returned=0
                )
            )

        # Filter to only quarterly periods (exclude TTM)
        if frequency == 'q':
            df = df[df['periodType'] == '3M']
        elif frequency == 'a':
            df = df[df['periodType'] == '12M']

        # Sort by date descending (most recent first)
        df = df.sort_values('asOfDate', ascending=False)

        # Limit to requested number of periods
        df = df.head(periods)

        # Transform to periods
        statement_periods = []

        for idx, row in df.iterrows():
            # Extract period info from asOfDate column
            period_info = self._extract_period_info(row.get('asOfDate'))
            if not period_info:
                continue

            # Extract asset values
            cash = self._safe_decimal(row.get('CashAndCashEquivalents'))
            short_term_inv = self._safe_decimal(row.get('OtherShortTermInvestments'))
            cash_and_st_inv = self._safe_decimal(row.get('CashCashEquivalentsAndShortTermInvestments'))
            ar = self._safe_decimal(row.get('AccountsReceivable'))
            inventory = self._safe_decimal(row.get('Inventory'))
            other_current = self._safe_decimal(row.get('OtherCurrentAssets'))
            total_current_assets = self._safe_decimal(row.get('CurrentAssets'))

            # Non-current assets
            net_ppe = self._safe_decimal(row.get('NetPPE'))
            goodwill = self._safe_decimal(row.get('Goodwill'))
            intangibles = self._safe_decimal(row.get('OtherIntangibleAssets'))
            lt_investments = self._safe_decimal(row.get('LongTermEquityInvestment'))
            other_noncurrent = self._safe_decimal(row.get('OtherNonCurrentAssets'))
            total_noncurrent_assets = self._safe_decimal(row.get('TotalNonCurrentAssets'))
            total_assets = self._safe_decimal(row.get('TotalAssets'))

            # Extract liability values
            ap = self._safe_decimal(row.get('AccountsPayable'))
            short_term_debt = self._safe_decimal(row.get('CurrentDebt'))
            current_portion_lt_debt = self._safe_decimal(row.get('CurrentDebtAndCapitalLeaseObligation'))
            accrued = self._safe_decimal(row.get('CurrentAccruedExpenses'))
            deferred_rev = self._safe_decimal(row.get('CurrentDeferredRevenue'))
            other_current_liab = self._safe_decimal(row.get('OtherCurrentLiabilities'))
            total_current_liab = self._safe_decimal(row.get('CurrentLiabilities'))

            # Non-current liabilities
            lt_debt = self._safe_decimal(row.get('LongTermDebt'))
            deferred_tax_liab = self._safe_decimal(row.get('DeferredTaxLiabilitiesNonCurrent'))
            other_noncurrent_liab = self._safe_decimal(row.get('OtherNonCurrentLiabilities'))
            total_noncurrent_liab = self._safe_decimal(row.get('TotalNonCurrentLiabilitiesNetMinorityInterest'))
            total_liabilities = self._safe_decimal(row.get('TotalLiabilitiesNetMinorityInterest'))

            # Extract equity values
            common_stock = self._safe_decimal(row.get('CommonStock'))
            retained_earnings = self._safe_decimal(row.get('RetainedEarnings'))
            aoci = self._safe_decimal(row.get('AccumulatedOtherComprehensiveIncome'))
            treasury_stock = self._safe_decimal(row.get('TreasuryStock'))
            total_equity = self._safe_decimal(row.get('StockholdersEquity'))
            minority_interest = self._safe_decimal(row.get('MinorityInterest'))

            # Calculate derived metrics
            working_capital = None
            if total_current_assets and total_current_liab:
                working_capital = total_current_assets - total_current_liab

            total_debt = None
            if short_term_debt and lt_debt:
                total_debt = short_term_debt + lt_debt
            elif short_term_debt:
                total_debt = short_term_debt
            elif lt_debt:
                total_debt = lt_debt

            net_debt = None
            if total_debt and cash:
                net_debt = total_debt - cash

            # Calculate ratios
            current_ratio = self._calculate_margin(total_current_assets, total_current_liab)

            quick_ratio = None
            if total_current_assets and inventory and total_current_liab:
                quick_ratio = self._calculate_margin(total_current_assets - inventory, total_current_liab)

            cash_ratio = self._calculate_margin(cash, total_current_liab)
            debt_to_equity = self._calculate_margin(total_debt, total_equity)
            debt_to_assets = self._calculate_margin(total_debt, total_assets)
            equity_to_assets = self._calculate_margin(total_equity, total_assets)

            # Build nested schema
            current_assets_obj = CurrentAssets(
                cash_and_equivalents=cash,
                short_term_investments=short_term_inv,
                cash_and_short_term_investments=cash_and_st_inv,
                accounts_receivable=ar,
                inventory=inventory,
                other_current_assets=other_current,
                total_current_assets=total_current_assets
            )

            noncurrent_assets_obj = NonCurrentAssets(
                net_ppe=net_ppe,
                goodwill=goodwill,
                intangible_assets=intangibles,
                long_term_investments=lt_investments,
                other_non_current_assets=other_noncurrent,
                total_non_current_assets=total_noncurrent_assets
            )

            assets_obj = Assets(
                current_assets=current_assets_obj,
                non_current_assets=noncurrent_assets_obj,
                total_assets=total_assets
            )

            current_liab_obj = CurrentLiabilities(
                accounts_payable=ap,
                short_term_debt=short_term_debt,
                current_portion_long_term_debt=current_portion_lt_debt,
                accrued_liabilities=accrued,
                deferred_revenue=deferred_rev,
                other_current_liabilities=other_current_liab,
                total_current_liabilities=total_current_liab
            )

            noncurrent_liab_obj = NonCurrentLiabilities(
                long_term_debt=lt_debt,
                deferred_tax_liabilities=deferred_tax_liab,
                other_non_current_liabilities=other_noncurrent_liab,
                total_non_current_liabilities=total_noncurrent_liab
            )

            liabilities_obj = Liabilities(
                current_liabilities=current_liab_obj,
                non_current_liabilities=noncurrent_liab_obj,
                total_liabilities=total_liabilities
            )

            equity_obj = Equity(
                common_stock=common_stock,
                retained_earnings=retained_earnings,
                accumulated_other_comprehensive_income=aoci,
                treasury_stock=treasury_stock,
                total_stockholders_equity=total_equity,
                minority_interest=minority_interest
            )

            calculated_metrics_obj = BalanceSheetCalculatedMetrics(
                working_capital=working_capital,
                net_debt=net_debt,
                total_debt=total_debt,
                book_value=total_equity,
                book_value_per_share=None,  # TODO: Calculate with shares outstanding
                tangible_book_value=None,    # TODO: Calculate
                tangible_book_value_per_share=None
            )

            ratios_obj = BalanceSheetRatios(
                current_ratio=current_ratio,
                quick_ratio=quick_ratio,
                cash_ratio=cash_ratio,
                debt_to_equity=debt_to_equity,
                debt_to_assets=debt_to_assets,
                equity_to_assets=equity_to_assets
            )

            metrics = BalanceSheetMetrics(
                assets=assets_obj,
                liabilities=liabilities_obj,
                equity=equity_obj,
                calculated_metrics=calculated_metrics_obj,
                ratios=ratios_obj
            )

            period = BalanceSheetPeriod(
                period_date=period_info['period_date'],
                period_type="3M" if frequency == 'q' else "12M",
                fiscal_year=period_info['fiscal_year'],
                fiscal_quarter=period_info['fiscal_quarter'] if frequency == 'q' else None,
                metrics=metrics
            )

            statement_periods.append(period)

            if len(statement_periods) >= periods:
                break

        return BalanceSheetResponse(
            symbol=symbol,
            frequency=frequency,
            currency="USD",
            periods=statement_periods,
            metadata=Metadata(
                data_source="yahooquery",
                last_updated=datetime.now(),
                periods_returned=len(statement_periods)
            )
        )

    async def get_cash_flow(
        self,
        symbol: str,
        frequency: str = 'q',
        periods: int = 12
    ) -> CashFlowResponse:
        """
        Get cash flow statement data for a symbol

        Args:
            symbol: Stock symbol
            frequency: 'q' (quarterly) or 'a' (annual)
            periods: Number of periods to return (default: 12)

        Returns:
            CashFlowResponse
        """
        # Fetch raw data
        raw_data = await self.client.get_cash_flow(symbol, frequency)

        if not raw_data or symbol not in raw_data:
            logger.warning(f"No cash flow data for {symbol}")
            return CashFlowResponse(
                symbol=symbol,
                frequency=frequency,
                currency="USD",
                periods=[],
                metadata=Metadata(
                    data_source="yahooquery",
                    last_updated=datetime.now(),
                    periods_returned=0
                )
            )

        df = raw_data[symbol]

        if not isinstance(df, pd.DataFrame) or df.empty:
            return CashFlowResponse(
                symbol=symbol,
                frequency=frequency,
                currency="USD",
                periods=[],
                metadata=Metadata(
                    data_source="yahooquery",
                    last_updated=datetime.now(),
                    periods_returned=0
                )
            )

        # Filter to only quarterly periods (exclude TTM)
        if frequency == 'q':
            df = df[df['periodType'] == '3M']
        elif frequency == 'a':
            df = df[df['periodType'] == '12M']

        # Sort by date descending (most recent first)
        df = df.sort_values('asOfDate', ascending=False)

        # Limit to requested number of periods
        df = df.head(periods)

        # Transform to periods
        statement_periods = []

        for idx, row in df.iterrows():
            # Extract period info from asOfDate column
            period_info = self._extract_period_info(row.get('asOfDate'))
            if not period_info:
                continue

            # Extract operating activities
            operating_cf = self._safe_decimal(row.get('OperatingCashFlow'))
            depreciation = self._safe_decimal(row.get('DepreciationAndAmortization'))
            change_in_wc = self._safe_decimal(row.get('ChangeInWorkingCapital'))
            stock_comp = self._safe_decimal(row.get('StockBasedCompensation'))
            deferred_tax = self._safe_decimal(row.get('DeferredIncomeTax'))
            other_operating = self._safe_decimal(row.get('OtherNonCashItems'))

            operating_activities = OperatingActivities(
                operating_cash_flow=operating_cf,
                depreciation_amortization=depreciation,
                change_in_working_capital=change_in_wc,
                stock_based_compensation=stock_comp,
                deferred_income_tax=deferred_tax,
                other_operating_activities=other_operating
            )

            # Extract investing activities
            capex = self._safe_decimal(row.get('CapitalExpenditure'))
            acquisitions = self._safe_decimal(row.get('NetBusinessPurchaseAndSale'))
            purchases_inv = self._safe_decimal(row.get('PurchaseOfInvestment'))
            sales_inv = self._safe_decimal(row.get('SaleOfInvestment'))
            other_investing = self._safe_decimal(row.get('NetOtherInvestingChanges'))
            net_investing = self._safe_decimal(row.get('InvestingCashFlow'))

            investing_activities = InvestingActivities(
                capital_expenditures=capex,
                acquisitions=acquisitions,
                purchases_of_investments=purchases_inv,
                sales_of_investments=sales_inv,
                other_investing_activities=other_investing,
                net_investing_cash_flow=net_investing
            )

            # Extract financing activities
            dividends = self._safe_decimal(row.get('CashDividendsPaid'))
            repurchases = self._safe_decimal(row.get('RepurchaseOfCapitalStock'))
            debt_issued = self._safe_decimal(row.get('IssuanceOfDebt'))
            debt_repaid = self._safe_decimal(row.get('RepaymentOfDebt'))
            stock_issued = self._safe_decimal(row.get('CommonStockIssuance'))
            other_financing = self._safe_decimal(row.get('NetOtherFinancingCharges'))
            net_financing = self._safe_decimal(row.get('FinancingCashFlow'))

            financing_activities = FinancingActivities(
                dividends_paid=dividends,
                stock_repurchases=repurchases,
                debt_issuance=debt_issued,
                debt_repayment=debt_repaid,
                common_stock_issuance=stock_issued,
                other_financing_activities=other_financing,
                net_financing_cash_flow=net_financing
            )

            # Calculate free cash flow
            fcf = None
            fcf_margin = None
            fcf_per_share = None

            if operating_cf and capex:
                # FCF = Operating Cash Flow - CapEx (capex is typically negative)
                fcf = operating_cf + capex  # capex is negative, so we add

                # Get revenue for FCF margin calculation
                # We don't have revenue in cash flow statement, so we'll leave margin as None
                # The frontend or a separate endpoint can calculate this

            calculated_metrics = CashFlowCalculatedMetrics(
                free_cash_flow=fcf,
                fcf_margin=fcf_margin,
                fcf_per_share=fcf_per_share
            )

            # Extract cash changes
            net_change = self._safe_decimal(row.get('ChangesInCash'))
            beginning_cash = self._safe_decimal(row.get('BeginningCashPosition'))
            ending_cash = self._safe_decimal(row.get('EndCashPosition'))

            metrics = CashFlowMetrics(
                operating_activities=operating_activities,
                investing_activities=investing_activities,
                financing_activities=financing_activities,
                calculated_metrics=calculated_metrics,
                net_change_in_cash=net_change,
                beginning_cash=beginning_cash,
                ending_cash=ending_cash
            )

            period = CashFlowPeriod(
                period_date=period_info['period_date'],
                period_type="3M" if frequency == 'q' else "12M",
                fiscal_year=period_info['fiscal_year'],
                fiscal_quarter=period_info['fiscal_quarter'] if frequency == 'q' else None,
                metrics=metrics
            )

            statement_periods.append(period)

            if len(statement_periods) >= periods:
                break

        return CashFlowResponse(
            symbol=symbol,
            frequency=frequency,
            currency="USD",
            periods=statement_periods,
            metadata=Metadata(
                data_source="yahooquery",
                last_updated=datetime.now(),
                periods_returned=len(statement_periods)
            )
        )

    async def get_all_statements(
        self,
        symbol: str,
        frequency: str = 'q',
        periods: int = 12
    ) -> AllStatementsResponse:
        """
        Get all three financial statements in one call

        Args:
            symbol: Stock symbol
            frequency: 'q' (quarterly) or 'a' (annual)
            periods: Number of periods to return (default: 12)

        Returns:
            AllStatementsResponse with all three financial statements
        """
        # Fetch all three statements
        income_statement = await self.get_income_statement(symbol, frequency, periods)
        balance_sheet = await self.get_balance_sheet(symbol, frequency, periods)
        cash_flow = await self.get_cash_flow(symbol, frequency, periods)

        return AllStatementsResponse(
            symbol=symbol,
            frequency=frequency,
            currency="USD",
            income_statement=income_statement,
            balance_sheet=balance_sheet,
            cash_flow=cash_flow,
            metadata=Metadata(
                data_source="yahooquery",
                last_updated=datetime.now(),
                periods_returned=min(
                    income_statement.metadata.periods_returned,
                    balance_sheet.metadata.periods_returned,
                    cash_flow.metadata.periods_returned
                )
            )
        )

    # ========================================================================
    # DATABASE STORAGE METHODS (Phase 2)
    # ========================================================================

    async def should_fetch_fundamentals(
        self, db: AsyncSession, symbol: str
    ) -> Tuple[bool, str]:
        """
        Determine if we should fetch fundamental data for a symbol.

        Smart fetching logic:
        - Skip if data is current (last fetch < earnings + 3 days)
        - Fetch if no data exists
        - Fetch if earnings + 3 days has passed

        Args:
            db: Database session
            symbol: Stock symbol

        Returns:
            Tuple of (should_fetch: bool, reason: str)
        """
        try:
            # Get company profile
            result = await db.execute(
                select(CompanyProfile).where(CompanyProfile.symbol == symbol)
            )
            profile = result.scalar_one_or_none()

            # Case 1: No profile exists → fetch
            if not profile:
                logger.info(f"No company profile for {symbol} → FETCH")
                return True, "No company profile"

            # Case 2: Never fetched fundamentals → fetch
            if not profile.fundamentals_last_fetched:
                logger.info(f"Never fetched fundamentals for {symbol} → FETCH")
                return True, "Never fetched"

            # Case 3: No next earnings date → fetch
            if not profile.next_earnings_date:
                logger.info(f"No next earnings date for {symbol} → FETCH")
                return True, "No earnings date"

            # Case 4: Check if earnings + 3 days has passed
            earnings_release_buffer = profile.next_earnings_date + timedelta(days=3)
            current_date = date.today()

            if current_date >= earnings_release_buffer:
                logger.info(
                    f"Earnings released for {symbol} "
                    f"(next_earnings_date={profile.next_earnings_date}) → FETCH"
                )
                return True, f"Earnings released on {profile.next_earnings_date}"

            # Data is current, skip
            logger.info(
                f"Fundamentals current for {symbol} "
                f"(last_fetched={profile.fundamentals_last_fetched}, "
                f"next_earnings={profile.next_earnings_date}) → SKIP"
            )
            return False, f"Data current (next earnings: {profile.next_earnings_date})"

        except Exception as e:
            logger.error(f"Error checking if should fetch for {symbol}: {e}")
            # On error, default to fetching (safer)
            return True, f"Error checking: {str(e)}"

    def _calculate_fiscal_quarter_end(
        self,
        next_earnings_date: date,
        fiscal_year_end: str,
        offset: int = 0
    ) -> date:
        """
        Calculate absolute fiscal quarter end date.

        Args:
            next_earnings_date: When earnings will be reported (usually 2-4 weeks after quarter ends)
            fiscal_year_end: Company's fiscal year end in "MM-DD" format (e.g., "12-31", "01-31")
            offset: 0 for current quarter, 1 for next quarter, -1 for previous quarter

        Returns:
            Absolute fiscal quarter end date (e.g., 2024-03-31)

        Example:
            # Apple reports Q4 2025 earnings on Jan 30, 2026
            # Fiscal year end: "12-31"
            _calculate_fiscal_quarter_end(date(2026, 1, 30), "12-31", offset=0)
            # Returns: date(2025, 12, 31)  # Q4 2025 end
        """
        import calendar
        from datetime import timedelta

        # Parse fiscal year end
        fye_month, fye_day = map(int, fiscal_year_end.split('-'))

        # Determine which quarter we're reporting
        # Assumption: earnings are reported 2-4 weeks after quarter ends
        # So next_earnings_date - 3 weeks ≈ quarter end date
        estimated_quarter_end = next_earnings_date - timedelta(weeks=3)

        # Calculate fiscal quarter ends based on fiscal_year_end
        # Fiscal quarters end 3, 6, 9, and 12 months before fiscal year end
        year = estimated_quarter_end.year

        # Generate all 4 fiscal quarter end dates for current fiscal year
        fiscal_quarters = []
        for months_before in [3, 6, 9, 12]:
            qtr_month = (fye_month - months_before) % 12
            if qtr_month == 0:
                qtr_month = 12
            qtr_year = year if qtr_month <= fye_month else year - 1

            # Handle different day counts per month
            qtr_day = min(fye_day, calendar.monthrange(qtr_year, qtr_month)[1])

            fiscal_quarters.append(date(qtr_year, qtr_month, qtr_day))

        # Find the closest quarter end to estimated_quarter_end
        closest_quarter = min(fiscal_quarters, key=lambda d: abs((d - estimated_quarter_end).days))

        # Apply offset (0=current quarter, 1=next quarter)
        if offset != 0:
            # Move to next/previous quarter
            target_index = fiscal_quarters.index(closest_quarter) + offset
            if target_index < 0 or target_index >= 4:
                # Need to adjust year
                closest_quarter = self._add_fiscal_quarters(closest_quarter, offset, fiscal_year_end)
            else:
                closest_quarter = fiscal_quarters[target_index]

        return closest_quarter

    def _add_fiscal_quarters(
        self,
        base_date: date,
        num_quarters: int,
        fiscal_year_end: str
    ) -> date:
        """
        Add N fiscal quarters to a date.

        Args:
            base_date: Starting date
            num_quarters: Number of quarters to add (can be negative)
            fiscal_year_end: Company's fiscal year end in "MM-DD" format

        Returns:
            New date after adding quarters
        """
        import calendar

        months_to_add = num_quarters * 3
        new_month = base_date.month + months_to_add
        new_year = base_date.year + (new_month - 1) // 12
        new_month = ((new_month - 1) % 12) + 1

        # Handle day overflow (e.g., Jan 31 + 1 month = Feb 28/29, not March 3)
        fye_month, fye_day = map(int, fiscal_year_end.split('-'))
        new_day = min(base_date.day, calendar.monthrange(new_year, new_month)[1])

        return date(new_year, new_month, new_day)

    def _get_or_infer_fiscal_year_end(
        self,
        symbol: str,
        earnings_calendar: Optional[dict] = None
    ) -> str:
        """
        Get fiscal year end from company profile or infer from earnings calendar.

        Args:
            symbol: Stock symbol
            earnings_calendar: Optional earnings calendar data from YahooQuery

        Returns:
            Fiscal year end in "MM-DD" format (e.g., "12-31")
            Defaults to "12-31" (calendar year) if unknown
        """
        # For now, default to calendar year
        # TODO: Fetch from YahooQuery's company_info or earnings_calendar
        # Most companies use calendar year (December 31)
        return "12-31"

    async def store_income_statements(
        self,
        db: AsyncSession,
        symbol: str,
        data: Dict[str, Any],
        frequency: str
    ) -> int:
        """
        Store income statement data in database using UPSERT.

        Args:
            db: Database session
            symbol: Stock symbol
            data: Income statement data from YahooQuery (DataFrame or dict)
            frequency: 'q' (quarterly) or 'a' (annual)

        Returns:
            Number of periods stored
        """
        try:
            # Convert data to DataFrame if needed
            if isinstance(data, dict):
                df = pd.DataFrame(data)
            else:
                df = data

            if df.empty:
                logger.warning(f"No income statement data for {symbol}")
                return 0

            periods_stored = 0

            for idx, row in df.iterrows():
                # Extract period date from 'asOfDate' column (YahooQuery structure)
                as_of_date = row.get('asOfDate')
                if as_of_date is None:
                    logger.warning(f"No asOfDate found for row, skipping")
                    continue

                # Convert to date
                if isinstance(as_of_date, (datetime, date)):
                    period_date = as_of_date.date() if isinstance(as_of_date, datetime) else as_of_date
                elif isinstance(as_of_date, pd.Timestamp):
                    period_date = as_of_date.date()
                else:
                    try:
                        period_date = pd.to_datetime(as_of_date).date()
                    except:
                        logger.warning(f"Could not parse date from asOfDate: {as_of_date}")
                        continue

                # Prepare income statement record
                income_record = {
                    'id': uuid4(),
                    'symbol': symbol,
                    'period_date': period_date,
                    'frequency': frequency,
                    'fiscal_year': self._safe_int(row.get('asOfDate', row.get('fiscalYear'))),
                    'fiscal_quarter': self._safe_int(row.get('periodType', row.get('fiscalQuarter'))),

                    # Revenue & Costs
                    'total_revenue': self._safe_decimal(row.get('TotalRevenue', row.get('totalRevenue'))),
                    'cost_of_revenue': self._safe_decimal(row.get('CostOfRevenue', row.get('costOfRevenue'))),
                    'gross_profit': self._safe_decimal(row.get('GrossProfit', row.get('grossProfit'))),

                    # Operating Expenses
                    'research_and_development': self._safe_decimal(row.get('ResearchAndDevelopment', row.get('researchAndDevelopment'))),
                    'selling_general_and_administrative': self._safe_decimal(row.get('SellingGeneralAndAdministration', row.get('sellingGeneralAndAdministration'))),

                    # Operating Results
                    'operating_income': self._safe_decimal(row.get('OperatingIncome', row.get('operatingIncome'))),
                    'ebit': self._safe_decimal(row.get('EBIT', row.get('ebit'))),
                    'ebitda': self._safe_decimal(row.get('EBITDA', row.get('ebitda'))),

                    # Net Income
                    'net_income': self._safe_decimal(row.get('NetIncome', row.get('netIncome'))),
                    'diluted_eps': self._safe_decimal(row.get('DilutedEPS', row.get('dilutedEPS'))),
                    'basic_eps': self._safe_decimal(row.get('BasicEPS', row.get('basicEPS'))),
                    'basic_average_shares': self._safe_int(row.get('BasicAverageShares', row.get('basicAverageShares'))),
                    'diluted_average_shares': self._safe_int(row.get('DilutedAverageShares', row.get('dilutedAverageShares'))),

                    # Tax & Interest
                    'tax_provision': self._safe_decimal(row.get('TaxProvision', row.get('taxProvision'))),
                    'interest_expense': self._safe_decimal(row.get('InterestExpense', row.get('interestExpense'))),
                    'depreciation_and_amortization': self._safe_decimal(row.get('DepreciationAndAmortization', row.get('depreciationAndAmortization'))),

                    # Metadata
                    'currency': 'USD',
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow(),
                }

                # ✅ DATA QUALITY: Skip incomplete records (filter before UPSERT)
                # Only store records with complete core data
                if not income_record['total_revenue']:
                    logger.debug(f"Skipping incomplete income statement for {symbol} on {period_date} - missing revenue")
                    continue

                # Calculate margins
                revenue = income_record['total_revenue']
                if revenue and revenue > 0:
                    if income_record['gross_profit']:
                        income_record['gross_margin'] = self._calculate_margin(
                            income_record['gross_profit'], revenue
                        )
                    if income_record['operating_income']:
                        income_record['operating_margin'] = self._calculate_margin(
                            income_record['operating_income'], revenue
                        )
                    if income_record['net_income']:
                        income_record['net_margin'] = self._calculate_margin(
                            income_record['net_income'], revenue
                        )

                # UPSERT using PostgreSQL insert ... on conflict
                stmt = insert(IncomeStatement).values(**income_record)
                stmt = stmt.on_conflict_do_update(
                    constraint='uq_income_symbol_period_freq',
                    set_={
                        'total_revenue': stmt.excluded.total_revenue,
                        'cost_of_revenue': stmt.excluded.cost_of_revenue,
                        'gross_profit': stmt.excluded.gross_profit,
                        'gross_margin': stmt.excluded.gross_margin,
                        'research_and_development': stmt.excluded.research_and_development,
                        'selling_general_and_administrative': stmt.excluded.selling_general_and_administrative,
                        'operating_income': stmt.excluded.operating_income,
                        'operating_margin': stmt.excluded.operating_margin,
                        'ebit': stmt.excluded.ebit,
                        'ebitda': stmt.excluded.ebitda,
                        'net_income': stmt.excluded.net_income,
                        'net_margin': stmt.excluded.net_margin,
                        'diluted_eps': stmt.excluded.diluted_eps,
                        'basic_eps': stmt.excluded.basic_eps,
                        'basic_average_shares': stmt.excluded.basic_average_shares,
                        'diluted_average_shares': stmt.excluded.diluted_average_shares,
                        'tax_provision': stmt.excluded.tax_provision,
                        'interest_expense': stmt.excluded.interest_expense,
                        'depreciation_and_amortization': stmt.excluded.depreciation_and_amortization,
                        'updated_at': datetime.utcnow(),
                    }
                )

                await db.execute(stmt)
                periods_stored += 1

            await db.commit()
            logger.info(f"✅ Stored {periods_stored} income statement periods for {symbol} ({frequency})")
            return periods_stored

        except Exception as e:
            logger.error(f"Error storing income statements for {symbol}: {e}")
            await db.rollback()
            return 0

    async def store_balance_sheets(
        self,
        db: AsyncSession,
        symbol: str,
        data: Dict[str, Any],
        frequency: str
    ) -> int:
        """
        Store balance sheet data in database using UPSERT.

        Args:
            db: Database session
            symbol: Stock symbol
            data: Balance sheet data from YahooQuery (DataFrame or dict)
            frequency: 'q' (quarterly) or 'a' (annual)

        Returns:
            Number of periods stored
        """
        try:
            # Convert data to DataFrame if needed
            if isinstance(data, dict):
                df = pd.DataFrame(data)
            else:
                df = data

            if df.empty:
                logger.warning(f"No balance sheet data for {symbol}")
                return 0

            periods_stored = 0

            for idx, row in df.iterrows():
                # Extract period date from 'asOfDate' column
                as_of_date = row.get('asOfDate')
                if as_of_date is None:
                    logger.warning(f"No asOfDate found for row, skipping")
                    continue

                # Convert to date
                if isinstance(as_of_date, (datetime, date)):
                    period_date = as_of_date.date() if isinstance(as_of_date, datetime) else as_of_date
                elif isinstance(as_of_date, pd.Timestamp):
                    period_date = as_of_date.date()
                else:
                    try:
                        period_date = pd.to_datetime(as_of_date).date()
                    except:
                        logger.warning(f"Could not parse date from asOfDate: {as_of_date}")
                        continue

                # Prepare balance sheet record
                balance_record = {
                    'id': uuid4(),
                    'symbol': symbol,
                    'period_date': period_date,
                    'frequency': frequency,
                    'fiscal_year': self._safe_int(row.get('asOfDate', row.get('fiscalYear'))),
                    'fiscal_quarter': self._safe_int(row.get('periodType', row.get('fiscalQuarter'))),

                    # Assets (8 fields)
                    'total_assets': self._safe_decimal(row.get('TotalAssets', row.get('totalAssets'))),
                    'current_assets': self._safe_decimal(row.get('CurrentAssets', row.get('currentAssets'))),
                    'cash_and_cash_equivalents': self._safe_decimal(row.get('CashAndCashEquivalents', row.get('cashAndCashEquivalents'))),
                    'short_term_investments': self._safe_decimal(row.get('OtherShortTermInvestments', row.get('shortTermInvestments'))),
                    'accounts_receivable': self._safe_decimal(row.get('AccountsReceivable', row.get('accountsReceivable'))),
                    'inventory': self._safe_decimal(row.get('Inventory', row.get('inventory'))),
                    'property_plant_equipment': self._safe_decimal(row.get('NetPPE', row.get('propertyPlantEquipment'))),
                    'intangible_assets': self._safe_decimal(row.get('GoodwillAndOtherIntangibleAssets', row.get('intangibleAssets'))),

                    # Liabilities (6 fields)
                    'total_liabilities': self._safe_decimal(row.get('TotalLiabilitiesNetMinorityInterest', row.get('totalLiabilities'))),
                    'current_liabilities': self._safe_decimal(row.get('CurrentLiabilities', row.get('currentLiabilities'))),
                    'accounts_payable': self._safe_decimal(row.get('AccountsPayable', row.get('accountsPayable'))),
                    'short_term_debt': self._safe_decimal(row.get('CurrentDebt', row.get('shortTermDebt'))),
                    'long_term_debt': self._safe_decimal(row.get('LongTermDebt', row.get('longTermDebt'))),
                    'total_debt': self._safe_decimal(row.get('TotalDebt', row.get('totalDebt'))),

                    # Equity (3 fields)
                    'total_stockholders_equity': self._safe_decimal(row.get('TotalEquityGrossMinorityInterest', row.get('totalStockholdersEquity'))),
                    'retained_earnings': self._safe_decimal(row.get('RetainedEarnings', row.get('retainedEarnings'))),
                    'common_stock': self._safe_decimal(row.get('CommonStock', row.get('commonStock'))),

                    # Metadata
                    'currency': 'USD',
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow(),
                }

                # ✅ DATA QUALITY: Skip incomplete records (filter before UPSERT)
                # Only store records with complete core data
                if not balance_record['total_assets']:
                    logger.debug(f"Skipping incomplete balance sheet for {symbol} on {period_date} - missing total assets")
                    continue

                # Calculate financial ratios and metrics
                current_assets = balance_record['current_assets']
                current_liabilities = balance_record['current_liabilities']
                total_debt = balance_record['total_debt']
                cash = balance_record['cash_and_cash_equivalents']
                equity = balance_record['total_stockholders_equity']

                # Working Capital = Current Assets - Current Liabilities
                if current_assets and current_liabilities:
                    balance_record['working_capital'] = current_assets - current_liabilities

                # Net Debt = Total Debt - Cash
                if total_debt and cash:
                    balance_record['net_debt'] = total_debt - cash

                # Current Ratio = Current Assets / Current Liabilities
                if current_assets and current_liabilities and current_liabilities > 0:
                    balance_record['current_ratio'] = self._safe_decimal(
                        float(current_assets) / float(current_liabilities)
                    )

                # Debt-to-Equity = Total Debt / Total Equity
                if total_debt and equity and equity > 0:
                    balance_record['debt_to_equity'] = self._safe_decimal(
                        float(total_debt) / float(equity)
                    )

                # Book Value Per Share - requires shares outstanding
                # Try to get from row data
                shares_outstanding = self._safe_int(row.get('SharesOutstanding', row.get('sharesOutstanding')))
                if equity and shares_outstanding and shares_outstanding > 0:
                    balance_record['book_value_per_share'] = self._safe_decimal(
                        float(equity) / float(shares_outstanding)
                    )

                # UPSERT using PostgreSQL insert ... on conflict
                stmt = insert(BalanceSheet).values(**balance_record)
                stmt = stmt.on_conflict_do_update(
                    constraint='uq_balance_symbol_period_freq',
                    set_={
                        'total_assets': stmt.excluded.total_assets,
                        'current_assets': stmt.excluded.current_assets,
                        'cash_and_cash_equivalents': stmt.excluded.cash_and_cash_equivalents,
                        'short_term_investments': stmt.excluded.short_term_investments,
                        'accounts_receivable': stmt.excluded.accounts_receivable,
                        'inventory': stmt.excluded.inventory,
                        'property_plant_equipment': stmt.excluded.property_plant_equipment,
                        'intangible_assets': stmt.excluded.intangible_assets,
                        'total_liabilities': stmt.excluded.total_liabilities,
                        'current_liabilities': stmt.excluded.current_liabilities,
                        'accounts_payable': stmt.excluded.accounts_payable,
                        'short_term_debt': stmt.excluded.short_term_debt,
                        'long_term_debt': stmt.excluded.long_term_debt,
                        'total_debt': stmt.excluded.total_debt,
                        'total_stockholders_equity': stmt.excluded.total_stockholders_equity,
                        'retained_earnings': stmt.excluded.retained_earnings,
                        'common_stock': stmt.excluded.common_stock,
                        'working_capital': stmt.excluded.working_capital,
                        'net_debt': stmt.excluded.net_debt,
                        'current_ratio': stmt.excluded.current_ratio,
                        'debt_to_equity': stmt.excluded.debt_to_equity,
                        'book_value_per_share': stmt.excluded.book_value_per_share,
                        'updated_at': datetime.utcnow(),
                    }
                )

                await db.execute(stmt)
                periods_stored += 1

            await db.commit()
            logger.info(f"Stored {periods_stored} balance sheet periods for {symbol} ({frequency})")
            return periods_stored

        except Exception as e:
            logger.error(f"Error storing balance sheets for {symbol}: {e}")
            await db.rollback()
            return 0

    async def store_cash_flows(
        self,
        db: AsyncSession,
        symbol: str,
        data: Dict[str, Any],
        frequency: str,
        revenue_data: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Store cash flow statement data in database using UPSERT.

        Args:
            db: Database session
            symbol: Stock symbol
            data: Cash flow data from YahooQuery (DataFrame or dict)
            frequency: 'q' (quarterly) or 'a' (annual)
            revenue_data: Optional revenue data for FCF margin calculation

        Returns:
            Number of periods stored
        """
        try:
            # Convert data to DataFrame if needed
            if isinstance(data, dict):
                df = pd.DataFrame(data)
            else:
                df = data

            if df.empty:
                logger.warning(f"No cash flow data for {symbol}")
                return 0

            # Build revenue lookup dict for FCF margin
            revenue_lookup = {}
            if revenue_data is not None:
                if isinstance(revenue_data, dict):
                    revenue_df = pd.DataFrame(revenue_data)
                else:
                    revenue_df = revenue_data

                if not revenue_df.empty:
                    for idx, row in revenue_df.iterrows():
                        # Extract date from asOfDate column
                        as_of_date = row.get('asOfDate')
                        if as_of_date is None:
                            continue

                        if isinstance(as_of_date, (datetime, date)):
                            period_date = as_of_date.date() if isinstance(as_of_date, datetime) else as_of_date
                        elif isinstance(as_of_date, pd.Timestamp):
                            period_date = as_of_date.date()
                        else:
                            try:
                                period_date = pd.to_datetime(as_of_date).date()
                            except:
                                continue

                        revenue_lookup[period_date] = self._safe_decimal(
                            row.get('TotalRevenue', row.get('totalRevenue'))
                        )

            periods_stored = 0

            for idx, row in df.iterrows():
                # Extract period date from 'asOfDate' column
                as_of_date = row.get('asOfDate')
                if as_of_date is None:
                    logger.warning(f"No asOfDate found for row, skipping")
                    continue

                # Convert to date
                if isinstance(as_of_date, (datetime, date)):
                    period_date = as_of_date.date() if isinstance(as_of_date, datetime) else as_of_date
                elif isinstance(as_of_date, pd.Timestamp):
                    period_date = as_of_date.date()
                else:
                    try:
                        period_date = pd.to_datetime(as_of_date).date()
                    except:
                        logger.warning(f"Could not parse date from asOfDate: {as_of_date}")
                        continue

                # Prepare cash flow record
                cashflow_record = {
                    'id': uuid4(),
                    'symbol': symbol,
                    'period_date': period_date,
                    'frequency': frequency,
                    'fiscal_year': self._safe_int(row.get('asOfDate', row.get('fiscalYear'))),
                    'fiscal_quarter': self._safe_int(row.get('periodType', row.get('fiscalQuarter'))),

                    # Operating Activities (4 fields)
                    'operating_cash_flow': self._safe_decimal(row.get('OperatingCashFlow', row.get('operatingCashFlow'))),
                    'depreciation_and_amortization': self._safe_decimal(row.get('DepreciationAndAmortization', row.get('depreciationAndAmortization'))),
                    'stock_based_compensation': self._safe_decimal(row.get('StockBasedCompensation', row.get('stockBasedCompensation'))),
                    'change_in_working_capital': self._safe_decimal(row.get('ChangeInWorkingCapital', row.get('changeInWorkingCapital'))),

                    # Investing Activities (4 fields)
                    'investing_cash_flow': self._safe_decimal(row.get('InvestingCashFlow', row.get('investingCashFlow'))),
                    'capital_expenditures': self._safe_decimal(row.get('CapitalExpenditure', row.get('capitalExpenditures'))),
                    'acquisitions': self._safe_decimal(row.get('NetBusinessPurchaseAndSale', row.get('acquisitions'))),
                    'purchases_of_investments': self._safe_decimal(row.get('PurchaseOfInvestment', row.get('purchasesOfInvestments'))),

                    # Financing Activities (4 fields)
                    'financing_cash_flow': self._safe_decimal(row.get('FinancingCashFlow', row.get('financingCashFlow'))),
                    'dividends_paid': self._safe_decimal(row.get('CashDividendsPaid', row.get('dividendsPaid'))),
                    'stock_repurchases': self._safe_decimal(row.get('RepurchaseOfCapitalStock', row.get('stockRepurchases'))),
                    'debt_issuance_repayment': self._safe_decimal(row.get('NetIssuancePaymentsOfDebt', row.get('debtIssuanceRepayment'))),

                    # Summary (2 fields)
                    'net_change_in_cash': self._safe_decimal(row.get('ChangesInCash', row.get('netChangeInCash'))),
                    'beginning_cash_position': self._safe_decimal(row.get('BeginningCashPosition', row.get('beginningCashPosition'))),

                    # Calculated metrics (initialize to None)
                    'free_cash_flow': None,
                    'fcf_margin': None,

                    # Metadata
                    'currency': 'USD',
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow(),
                }

                # ✅ DATA QUALITY: Skip incomplete records (filter before UPSERT)
                # Only store records with complete core data
                if not cashflow_record['operating_cash_flow']:
                    logger.debug(f"Skipping incomplete cash flow for {symbol} on {period_date} - missing operating cash flow")
                    continue

                # Calculate Free Cash Flow = Operating Cash Flow - CapEx
                operating_cf = cashflow_record['operating_cash_flow']
                capex = cashflow_record['capital_expenditures']

                if operating_cf and capex:
                    # CapEx is typically negative in cash flow statements
                    # So we add (which is effectively subtracting the absolute value)
                    cashflow_record['free_cash_flow'] = operating_cf + capex

                # Calculate FCF Margin = Free Cash Flow / Revenue
                fcf = cashflow_record.get('free_cash_flow')
                revenue = revenue_lookup.get(period_date)

                if fcf and revenue and revenue > 0:
                    cashflow_record['fcf_margin'] = self._safe_decimal(
                        float(fcf) / float(revenue)
                    )

                # UPSERT using PostgreSQL insert ... on conflict
                stmt = insert(CashFlow).values(**cashflow_record)
                stmt = stmt.on_conflict_do_update(
                    constraint='uq_cashflow_symbol_period_freq',
                    set_={
                        'operating_cash_flow': stmt.excluded.operating_cash_flow,
                        'depreciation_and_amortization': stmt.excluded.depreciation_and_amortization,
                        'stock_based_compensation': stmt.excluded.stock_based_compensation,
                        'change_in_working_capital': stmt.excluded.change_in_working_capital,
                        'investing_cash_flow': stmt.excluded.investing_cash_flow,
                        'capital_expenditures': stmt.excluded.capital_expenditures,
                        'acquisitions': stmt.excluded.acquisitions,
                        'purchases_of_investments': stmt.excluded.purchases_of_investments,
                        'financing_cash_flow': stmt.excluded.financing_cash_flow,
                        'dividends_paid': stmt.excluded.dividends_paid,
                        'stock_repurchases': stmt.excluded.stock_repurchases,
                        'debt_issuance_repayment': stmt.excluded.debt_issuance_repayment,
                        'net_change_in_cash': stmt.excluded.net_change_in_cash,
                        'beginning_cash_position': stmt.excluded.beginning_cash_position,
                        'free_cash_flow': stmt.excluded.free_cash_flow,
                        'fcf_margin': stmt.excluded.fcf_margin,
                        'updated_at': datetime.utcnow(),
                    }
                )

                await db.execute(stmt)
                periods_stored += 1

            await db.commit()
            logger.info(f"Stored {periods_stored} cash flow periods for {symbol} ({frequency})")
            return periods_stored

        except Exception as e:
            logger.error(f"Error storing cash flows for {symbol}: {e}")
            await db.rollback()
            return 0

    async def update_company_profile_analyst_data(
        self,
        db: AsyncSession,
        symbol: str,
        earnings_estimates: Dict[str, Any],
        earnings_calendar: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update company_profiles table with analyst earnings estimates and fiscal calendar.

        Args:
            db: Database session
            symbol: Stock symbol
            earnings_estimates: Analyst estimates from YahooQuery (quarterly data)
            earnings_calendar: Optional earnings calendar for next earnings date

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get or create company profile
            result = await db.execute(
                select(CompanyProfile).where(CompanyProfile.symbol == symbol)
            )
            profile = result.scalar_one_or_none()

            if not profile:
                logger.warning(f"No company profile found for {symbol}, cannot update analyst data")
                return False

            # Get fiscal year end (default to calendar year)
            fiscal_year_end = self._get_or_infer_fiscal_year_end(symbol, earnings_calendar)
            profile.fiscal_year_end = fiscal_year_end

            # Extract next earnings date from earnings_calendar
            next_earnings_date = None
            if earnings_calendar and symbol in earnings_calendar:
                calendar_data = earnings_calendar[symbol]
                if isinstance(calendar_data, dict):
                    # Try various field names for earnings date
                    earnings_date_str = calendar_data.get('earningsDate', calendar_data.get('earnings_date'))
                    if earnings_date_str:
                        try:
                            next_earnings_date = pd.to_datetime(earnings_date_str).date()
                            profile.next_earnings_date = next_earnings_date
                        except:
                            pass

                    # Extract expected EPS and revenue for next earnings
                    profile.next_earnings_expected_eps = self._safe_decimal(
                        calendar_data.get('epsEstimate', calendar_data.get('eps_estimate'))
                    )
                    profile.next_earnings_expected_revenue = self._safe_decimal(
                        calendar_data.get('revenueEstimate', calendar_data.get('revenue_estimate'))
                    )

            # Parse earnings estimates from YahooQuery
            # Structure: {"trend": [{"period": "0q", "earningsEstimate": {...}, "revenueEstimate": {...}}, ...]}
            trend_data = []
            if isinstance(earnings_estimates, dict):
                if symbol in earnings_estimates:
                    # Extract trend array from symbol key
                    symbol_data = earnings_estimates[symbol]
                    if isinstance(symbol_data, dict) and 'trend' in symbol_data:
                        trend_data = symbol_data['trend']
                elif 'trend' in earnings_estimates:
                    # Direct trend array
                    trend_data = earnings_estimates['trend']

            if not trend_data:
                logger.warning(f"No analyst earnings estimates for {symbol}")
                return False

            # Find all 4 periods: current quarter, next quarter, current year, next year
            current_quarter_data = None
            next_quarter_data = None
            current_year_data = None
            next_year_data = None

            for item in trend_data:
                period = item.get('period', '').lower()

                if period == '0q':
                    current_quarter_data = item
                elif period == '+1q':
                    next_quarter_data = item
                elif period == '0y':
                    current_year_data = item
                elif period == '+1y':
                    next_year_data = item

            # Process current quarter estimates
            if current_quarter_data:
                earnings_est = current_quarter_data.get('earningsEstimate', {})
                revenue_est = current_quarter_data.get('revenueEstimate', {})

                profile.current_quarter_eps_avg = self._safe_decimal(earnings_est.get('avg'))
                profile.current_quarter_eps_low = self._safe_decimal(earnings_est.get('low'))
                profile.current_quarter_eps_high = self._safe_decimal(earnings_est.get('high'))
                profile.current_quarter_analyst_count = self._safe_int(earnings_est.get('numberOfAnalysts'))

                profile.current_quarter_revenue_avg = self._safe_decimal(revenue_est.get('avg'))
                profile.current_quarter_revenue_low = self._safe_decimal(revenue_est.get('low'))
                profile.current_quarter_revenue_high = self._safe_decimal(revenue_est.get('high'))

                # Calculate absolute target period date
                end_date_str = current_quarter_data.get('endDate')
                if end_date_str:
                    try:
                        profile.current_quarter_target_period_date = pd.to_datetime(end_date_str).date()
                    except:
                        pass

            # Process next quarter estimates
            if next_quarter_data:
                earnings_est = next_quarter_data.get('earningsEstimate', {})
                revenue_est = next_quarter_data.get('revenueEstimate', {})

                profile.next_quarter_eps_avg = self._safe_decimal(earnings_est.get('avg'))
                profile.next_quarter_eps_low = self._safe_decimal(earnings_est.get('low'))
                profile.next_quarter_eps_high = self._safe_decimal(earnings_est.get('high'))
                profile.next_quarter_analyst_count = self._safe_int(earnings_est.get('numberOfAnalysts'))

                profile.next_quarter_revenue_avg = self._safe_decimal(revenue_est.get('avg'))
                profile.next_quarter_revenue_low = self._safe_decimal(revenue_est.get('low'))
                profile.next_quarter_revenue_high = self._safe_decimal(revenue_est.get('high'))

                # Calculate absolute target period date
                end_date_str = next_quarter_data.get('endDate')
                if end_date_str:
                    try:
                        profile.next_quarter_target_period_date = pd.to_datetime(end_date_str).date()
                    except:
                        pass

            # Process current year estimates
            if current_year_data:
                earnings_est = current_year_data.get('earningsEstimate', {})
                revenue_est = current_year_data.get('revenueEstimate', {})

                profile.current_year_earnings_avg = self._safe_decimal(earnings_est.get('avg'))
                profile.current_year_earnings_low = self._safe_decimal(earnings_est.get('low'))
                profile.current_year_earnings_high = self._safe_decimal(earnings_est.get('high'))

                profile.current_year_revenue_avg = self._safe_decimal(revenue_est.get('avg'))
                profile.current_year_revenue_low = self._safe_decimal(revenue_est.get('low'))
                profile.current_year_revenue_high = self._safe_decimal(revenue_est.get('high'))

                # Calculate revenue growth
                profile.current_year_revenue_growth = self._safe_decimal(current_year_data.get('growth'))

                # Store fiscal year end date
                end_date_str = current_year_data.get('endDate')
                if end_date_str:
                    try:
                        profile.current_year_end_date = pd.to_datetime(end_date_str).date()
                    except:
                        pass

            # Process next year estimates
            if next_year_data:
                earnings_est = next_year_data.get('earningsEstimate', {})
                revenue_est = next_year_data.get('revenueEstimate', {})

                profile.next_year_earnings_avg = self._safe_decimal(earnings_est.get('avg'))
                profile.next_year_earnings_low = self._safe_decimal(earnings_est.get('low'))
                profile.next_year_earnings_high = self._safe_decimal(earnings_est.get('high'))

                profile.next_year_revenue_avg = self._safe_decimal(revenue_est.get('avg'))
                profile.next_year_revenue_low = self._safe_decimal(revenue_est.get('low'))
                profile.next_year_revenue_high = self._safe_decimal(revenue_est.get('high'))

                # Calculate revenue growth
                profile.next_year_revenue_growth = self._safe_decimal(next_year_data.get('growth'))

                # Store fiscal year end date
                end_date_str = next_year_data.get('endDate')
                if end_date_str:
                    try:
                        profile.next_year_end_date = pd.to_datetime(end_date_str).date()
                    except:
                        pass

            # Update last fetched timestamp
            profile.fundamentals_last_fetched = datetime.utcnow()

            # Commit changes
            await db.commit()
            logger.info(f"Updated analyst data for {symbol} in company_profiles")
            return True

        except Exception as e:
            logger.error(f"Error updating company profile analyst data for {symbol}: {e}")
            await db.rollback()
            return False

    async def update_fundamentals_timestamp(
        self,
        db: AsyncSession,
        symbol: str
    ) -> bool:
        """
        Update fundamentals_last_fetched timestamp for a symbol.

        Used when financial statements are stored but earnings estimates are not available.
        This ensures smart fetching logic works correctly.

        Args:
            db: Database session
            symbol: Stock symbol

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get or create company profile
            result = await db.execute(
                select(CompanyProfile).where(CompanyProfile.symbol == symbol)
            )
            profile = result.scalar_one_or_none()

            if not profile:
                # Create minimal company profile if it doesn't exist
                profile = CompanyProfile(
                    symbol=symbol,
                    fundamentals_last_fetched=datetime.utcnow()
                )
                db.add(profile)
            else:
                # Update existing profile
                profile.fundamentals_last_fetched = datetime.utcnow()

            await db.commit()
            logger.info(f"Updated fundamentals_last_fetched timestamp for {symbol}")
            return True

        except Exception as e:
            logger.error(f"Error updating fundamentals timestamp for {symbol}: {e}")
            await db.rollback()
            return False

    async def close(self):
        """Close the underlying client"""
        await self.client.close()


# Singleton instance
fundamentals_service = FundamentalsService()
