"""
Hybrid Context Builder - Aggregates portfolio data for AI investigation.

Builds comprehensive investigation context from multiple sources:
1. Batch calculation results (preferred - fastest)
2. API endpoints (fallback - cached data)
3. On-demand calculations (last resort - slowest)

Gracefully handles incomplete data and tracks data quality.
"""
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.users import Portfolio
from app.models.positions import Position
from app.models.snapshots import PortfolioSnapshot
from app.models.market_data import PositionGreeks, PositionFactorExposure
from app.models.correlations import CorrelationCalculation

logger = get_logger(__name__)


class HybridContextBuilder:
    """
    Builds investigation context from batch results, APIs, and on-demand calculations.

    Implements graceful degradation:
    - Try batch calculation results first (fastest)
    - Fall back to API data if batch incomplete (moderate speed)
    - Calculate on-demand if needed (slowest)

    Tracks data quality for transparent AI analysis.
    """

    async def build_context(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        focus_area: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build comprehensive investigation context.

        Args:
            db: Database session
            portfolio_id: Portfolio to investigate
            focus_area: Optional specific focus area

        Returns:
            Dict containing:
                - portfolio_summary: Basic portfolio info
                - positions: Current positions with P&L
                - risk_metrics: Volatility, Greeks, correlations
                - factor_exposure: Factor analysis
                - data_quality: Quality assessment per metric
                - snapshot_date: When data was calculated
        """
        logger.info(f"Building investigation context for portfolio {portfolio_id}")

        context = {
            "portfolio_id": str(portfolio_id),
            "focus_area": focus_area,
            "build_timestamp": datetime.utcnow().isoformat(),
        }

        # 1. Get portfolio summary
        portfolio_summary = await self._get_portfolio_summary(db, portfolio_id)
        context["portfolio_summary"] = portfolio_summary

        # 2. Get latest snapshot for baseline metrics
        snapshot = await self._get_latest_snapshot(db, portfolio_id)
        if snapshot:
            context["snapshot"] = {
                "date": snapshot.snapshot_date.isoformat(),
                "equity_balance": float(snapshot.equity_balance) if snapshot.equity_balance else None,  # Current equity (rolled forward)
                "net_asset_value": float(snapshot.net_asset_value) if snapshot.net_asset_value else None,
                "total_value": float(snapshot.net_asset_value) if snapshot.net_asset_value else None,
                "cash_value": float(snapshot.cash_value) if snapshot.cash_value else None,
                "long_value": float(snapshot.long_value) if snapshot.long_value else None,
                "short_value": float(snapshot.short_value) if snapshot.short_value else None,
                "gross_exposure": float(snapshot.gross_exposure) if snapshot.gross_exposure else None,
                "net_exposure": float(snapshot.net_exposure) if snapshot.net_exposure else None,
                "portfolio_delta": float(snapshot.portfolio_delta) if snapshot.portfolio_delta else None,
                "realized_volatility_21d": float(snapshot.realized_volatility_21d) if snapshot.realized_volatility_21d else None,
                "beta_calculated_90d": float(snapshot.beta_calculated_90d) if snapshot.beta_calculated_90d else None,
                "daily_pnl": float(snapshot.daily_pnl) if snapshot.daily_pnl else None,
                "cumulative_pnl": float(snapshot.cumulative_pnl) if snapshot.cumulative_pnl else None,
                "num_positions": snapshot.num_positions,
                # Target price analytics (portfolio-level)
                "target_price_return_eoy": float(snapshot.target_price_return_eoy) if snapshot.target_price_return_eoy else None,
                "target_price_return_next_year": float(snapshot.target_price_return_next_year) if snapshot.target_price_return_next_year else None,
                "target_price_downside_return": float(snapshot.target_price_downside_return) if snapshot.target_price_downside_return else None,
                "target_price_upside_eoy_dollars": float(snapshot.target_price_upside_eoy_dollars) if snapshot.target_price_upside_eoy_dollars else None,
                "target_price_upside_next_year_dollars": float(snapshot.target_price_upside_next_year_dollars) if snapshot.target_price_upside_next_year_dollars else None,
                "target_price_downside_dollars": float(snapshot.target_price_downside_dollars) if snapshot.target_price_downside_dollars else None,
                "target_price_coverage_pct": float(snapshot.target_price_coverage_pct) if snapshot.target_price_coverage_pct else None,
                "target_price_positions_count": snapshot.target_price_positions_count,
                "target_price_total_positions": snapshot.target_price_total_positions,
                "target_price_last_updated": snapshot.target_price_last_updated.isoformat() if snapshot.target_price_last_updated else None,
            }

        # 3. Get positions
        positions = await self._get_positions(db, portfolio_id)
        context["positions"] = positions

        # 4. Get risk metrics (Greeks, volatility, etc.)
        risk_metrics = await self._get_risk_metrics(db, portfolio_id)
        context["risk_metrics"] = risk_metrics

        # 5. Get factor exposures
        factor_exposure = await self._get_factor_exposure(db, portfolio_id)
        context["factor_exposure"] = factor_exposure

        # 6. Get correlations
        correlations = await self._get_correlations(db, portfolio_id)
        context["correlations"] = correlations

        # 7. Get volatility analytics
        volatility_analytics = await self._get_volatility_analytics(db, portfolio_id)
        context["volatility_analytics"] = volatility_analytics

        # 8. Get spread factors
        spread_factors = await self._get_spread_factors(db, portfolio_id)
        context["spread_factors"] = spread_factors

        # 9. Assess data quality
        data_quality = self._assess_data_quality(context)
        context["data_quality"] = data_quality

        # 10. Build summary statistics
        context["summary_stats"] = self._build_summary_stats(context)

        logger.info(f"Context built: {len(positions.get('items', []))} positions, "
                   f"quality={data_quality.get('overall', 'unknown')}")

        return context

    async def _get_portfolio_summary(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
    ) -> Dict[str, Any]:
        """Get basic portfolio information."""
        result = await db.execute(
            select(Portfolio).where(Portfolio.id == portfolio_id)
        )
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            return {"available": False}

        return {
            "available": True,
            "name": portfolio.name,
            "currency": portfolio.currency,
            "equity_balance": float(portfolio.equity_balance) if portfolio.equity_balance else None,
            "description": portfolio.description,
        }

    async def _get_latest_snapshot(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
    ) -> Optional[PortfolioSnapshot]:
        """Get most recent portfolio snapshot."""
        result = await db.execute(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.portfolio_id == portfolio_id)
            .order_by(desc(PortfolioSnapshot.snapshot_date))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_positions(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
    ) -> Dict[str, Any]:
        """Get current positions with basic info."""
        result = await db.execute(
            select(Position).where(Position.portfolio_id == portfolio_id)
        )
        positions = result.scalars().all()

        if not positions:
            return {"available": False, "count": 0, "items": []}

        position_list = []
        for pos in positions:
            position_list.append({
                "symbol": pos.symbol,
                "position_type": pos.position_type.value if pos.position_type else None,
                "quantity": float(pos.quantity) if pos.quantity else 0,
                "entry_price": float(pos.entry_price) if pos.entry_price else None,
                "last_price": float(pos.last_price) if pos.last_price else None,
                "market_value": float(pos.market_value) if pos.market_value else None,
                "unrealized_pnl": float(pos.unrealized_pnl) if pos.unrealized_pnl else None,
            })

        return {
            "available": True,
            "count": len(position_list),
            "items": position_list,
        }

    async def _get_risk_metrics(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
    ) -> Dict[str, Any]:
        """Get risk metrics (Greeks, volatility, etc.)."""
        # Get Greeks for options positions
        result = await db.execute(
            select(PositionGreeks)
            .join(Position)
            .where(Position.portfolio_id == portfolio_id)
            .order_by(desc(PositionGreeks.calculation_date))
        )
        greeks = result.scalars().all()

        if not greeks:
            return {
                "greeks": {"available": False},
                "volatility": {"available": False},
            }

        # Aggregate Greeks
        total_delta = sum(float(g.delta or 0) for g in greeks)
        total_gamma = sum(float(g.gamma or 0) for g in greeks)
        total_theta = sum(float(g.theta or 0) for g in greeks)
        total_vega = sum(float(g.vega or 0) for g in greeks)

        return {
            "greeks": {
                "available": True,
                "count": len(greeks),
                "total_delta": total_delta,
                "total_gamma": total_gamma,
                "total_theta": total_theta,
                "total_vega": total_vega,
                "last_calculation": greeks[0].calculation_date.isoformat() if greeks else None,
            },
            "volatility": {
                "available": False,  # TODO: Add volatility metrics when available
            },
        }

    async def _get_factor_exposure(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
    ) -> Dict[str, Any]:
        """Get factor exposures."""
        from sqlalchemy.orm import selectinload
        from app.models.market_data import FactorDefinition

        result = await db.execute(
            select(PositionFactorExposure)
            .join(Position)
            .options(selectinload(PositionFactorExposure.factor))
            .where(Position.portfolio_id == portfolio_id)
        )
        exposures = result.scalars().all()

        if not exposures:
            return {"available": False}

        # Group by factor
        factor_totals = {}
        for exp in exposures:
            factor_name = exp.factor.name if exp.factor else "Unknown"
            if factor_name not in factor_totals:
                factor_totals[factor_name] = 0.0
            factor_totals[factor_name] += float(exp.exposure_value or 0)

        return {
            "available": True,
            "count": len(exposures),
            "factors": factor_totals,
        }

    async def _get_correlations(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
    ) -> Dict[str, Any]:
        """Get correlation data."""
        result = await db.execute(
            select(CorrelationCalculation)
            .where(CorrelationCalculation.portfolio_id == portfolio_id)
            .order_by(desc(CorrelationCalculation.calculation_date))
            .limit(1)
        )
        correlation = result.scalar_one_or_none()

        if not correlation:
            return {"available": False}

        return {
            "available": True,
            "calculation_date": correlation.calculation_date.isoformat(),
            "overall_correlation": float(correlation.overall_correlation) if correlation.overall_correlation else None,
            "correlation_concentration_score": float(correlation.correlation_concentration_score) if correlation.correlation_concentration_score else None,
            "effective_positions": float(correlation.effective_positions) if correlation.effective_positions else None,
            "data_quality": correlation.data_quality,
        }

    async def _get_volatility_analytics(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
    ) -> Dict[str, Any]:
        """
        Get portfolio and position volatility analytics.

        Returns realized volatility (21d, 63d), expected volatility (HAR forecast),
        volatility trend, and percentile vs historical distribution.
        """
        # Get latest portfolio snapshot for portfolio-level volatility
        result = await db.execute(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.portfolio_id == portfolio_id)
            .order_by(desc(PortfolioSnapshot.snapshot_date))
            .limit(1)
        )
        snapshot = result.scalar_one_or_none()

        if not snapshot:
            return {"available": False}

        return {
            "available": True,
            "portfolio_level": {
                "realized_volatility_21d": float(snapshot.realized_volatility_21d) if snapshot.realized_volatility_21d else None,
                "realized_volatility_63d": float(snapshot.realized_volatility_63d) if snapshot.realized_volatility_63d else None,
                "expected_volatility_21d": float(snapshot.expected_volatility_21d) if snapshot.expected_volatility_21d else None,
                "volatility_trend": snapshot.volatility_trend,
                "volatility_percentile": float(snapshot.volatility_percentile) if snapshot.volatility_percentile else None,
            }
        }

    async def _get_spread_factors(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
    ) -> Dict[str, Any]:
        """
        Get spread factor exposures (Growth-Value, Momentum, Size, Quality).

        Spread factors are long-short factors that eliminate multicollinearity:
        - Growth-Value Spread (VUG - VTV)
        - Momentum Spread (MTUM - SPY)
        - Size Spread (IWM - SPY)
        - Quality Spread (QUAL - SPY)
        """
        from app.models.market_data import FactorDefinition, FactorExposure
        from sqlalchemy import and_, func

        # Get active spread factors
        spread_factors_stmt = (
            select(FactorDefinition.id, FactorDefinition.name)
            .where(and_(
                FactorDefinition.is_active == True,
                FactorDefinition.factor_type == 'spread'
            ))
            .order_by(FactorDefinition.display_order.asc())
        )
        spread_result = await db.execute(spread_factors_stmt)
        spread_factor_ids = [row[0] for row in spread_result.all()]

        if not spread_factor_ids:
            return {"available": False}

        # Find latest calculation date
        latest_date_stmt = (
            select(func.max(FactorExposure.calculation_date))
            .where(and_(
                FactorExposure.portfolio_id == portfolio_id,
                FactorExposure.factor_id.in_(spread_factor_ids)
            ))
        )
        latest_date_result = await db.execute(latest_date_stmt)
        latest_date = latest_date_result.scalar_one_or_none()

        if not latest_date:
            return {"available": False}

        # Load spread factor exposures
        exposures_stmt = (
            select(FactorExposure, FactorDefinition)
            .join(FactorDefinition, FactorExposure.factor_id == FactorDefinition.id)
            .where(and_(
                FactorExposure.portfolio_id == portfolio_id,
                FactorExposure.calculation_date == latest_date,
                FactorExposure.factor_id.in_(spread_factor_ids)
            ))
        )
        exposures_result = await db.execute(exposures_stmt)
        exposure_rows = exposures_result.all()

        if not exposure_rows:
            return {"available": False}

        # Build spread factors dict with interpretations
        factors = {}
        for exposure, definition in exposure_rows:
            try:
                from app.calculations.factor_interpretation import interpret_spread_beta

                beta = float(exposure.exposure_value)
                interpretation = interpret_spread_beta(definition.name, beta)

                factors[definition.name] = {
                    "beta": beta,
                    "direction": interpretation['direction'],
                    "magnitude": interpretation['magnitude'],
                    "risk_level": interpretation['risk_level'],
                    "explanation": interpretation['explanation']
                }
            except Exception as e:
                logger.warning(f"Failed to interpret spread factor {definition.name}: {e}")
                # Add basic data even if interpretation fails
                factors[definition.name] = {
                    "beta": float(exposure.exposure_value),
                    "direction": "unknown",
                    "magnitude": "unknown",
                    "risk_level": "unknown",
                    "explanation": "Interpretation unavailable"
                }

        return {
            "available": True,
            "calculation_date": latest_date.isoformat(),
            "factors": factors
        }

    def _assess_data_quality(self, context: Dict[str, Any]) -> Dict[str, str]:
        """
        Assess data quality for each metric.

        Returns quality levels:
        - complete: Full data available
        - partial: Some data available
        - incomplete: Minimal data
        - unreliable: Data present but questionable
        """
        quality = {}

        # Portfolio summary
        portfolio_summary = context.get("portfolio_summary", {})
        quality["portfolio_info"] = "complete" if portfolio_summary.get("available") else "incomplete"

        # Snapshot
        snapshot = context.get("snapshot")
        if snapshot and (snapshot.get("net_asset_value") or snapshot.get("total_value")):
            quality["snapshot"] = "complete"
        else:
            quality["snapshot"] = "incomplete"

        # Positions
        positions = context.get("positions", {})
        if positions.get("available") and positions.get("count", 0) > 0:
            quality["positions"] = "complete"
        else:
            quality["positions"] = "incomplete"

        # Greeks
        greeks = context.get("risk_metrics", {}).get("greeks", {})
        if greeks.get("available"):
            quality["greeks"] = "complete"
        else:
            quality["greeks"] = "incomplete"

        # Factor exposure
        factor_exp = context.get("factor_exposure", {})
        if factor_exp.get("available"):
            quality["factor_exposure"] = "partial"  # Always partial until we have full factor data
        else:
            quality["factor_exposure"] = "incomplete"

        # Correlations
        corr = context.get("correlations", {})
        if corr.get("available"):
            quality["correlations"] = "complete"
        else:
            quality["correlations"] = "incomplete"

        # Volatility analytics
        vol = context.get("volatility_analytics", {})
        if vol.get("available"):
            quality["volatility_analytics"] = "complete"
        else:
            quality["volatility_analytics"] = "incomplete"

        # Spread factors
        spread = context.get("spread_factors", {})
        if spread.get("available"):
            quality["spread_factors"] = "complete"
        else:
            quality["spread_factors"] = "incomplete"

        # Overall quality
        complete_count = sum(1 for v in quality.values() if v == "complete")
        if complete_count >= 6:  # Increased from 4 to account for new metrics
            quality["overall"] = "complete"
        elif complete_count >= 3:  # Increased from 2
            quality["overall"] = "partial"
        else:
            quality["overall"] = "incomplete"

        return quality

    def _build_summary_stats(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Build summary statistics for quick reference."""
        positions = context.get("positions", {})
        snapshot = context.get("snapshot", {})

        return {
            "position_count": positions.get("count", 0),
            "total_value": snapshot.get("total_value"),
            "gross_exposure": snapshot.get("gross_exposure"),
            "net_exposure": snapshot.get("net_exposure"),
            "portfolio_delta": snapshot.get("portfolio_delta"),
            "realized_volatility_21d": snapshot.get("realized_volatility_21d"),
            "beta_calculated_90d": snapshot.get("beta_calculated_90d"),
            "daily_pnl": snapshot.get("daily_pnl"),
            "data_completeness": context.get("data_quality", {}).get("overall", "unknown"),
        }


# Singleton instance
hybrid_context_builder = HybridContextBuilder()
