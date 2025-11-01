"""
Fundamentals Service Layer

Transforms raw YahooQuery data into structured Pydantic schemas
and calculates derived financial metrics.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
import pandas as pd

from app.clients.yahooquery_client import YahooQueryClient
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

    async def close(self):
        """Close the underlying client"""
        await self.client.close()
