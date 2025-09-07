"""
Risk Metrics retrieval service (DB-first, v1)

Returns portfolio risk metrics using existing batch outputs only:
- Portfolio beta from FactorExposure ('Market Beta')
- Volatility from PortfolioSnapshot.daily_return (sample stddev * sqrt(252))
- Max drawdown from PortfolioSnapshot.total_value (running-peak percentage drawdown)

No new regressions or recomputation in v1.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from math import sqrt
from typing import Dict, Optional, List, Tuple
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.snapshots import PortfolioSnapshot
from app.models.market_data import FactorDefinition, FactorExposure
from app.constants.factors import REGRESSION_WINDOW_DAYS

import logging

logger = logging.getLogger(__name__)


class RiskMetricsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_portfolio_risk_metrics(
        self,
        portfolio_id: UUID,
        *,
        lookback_days: int = 90,
    ) -> Dict:
        """
        Compute portfolio risk metrics using existing DB data only.

        - Use latest snapshot date as window end; window start = end - lookback_days
        - Volatility from PortfolioSnapshot.daily_return (sample stddev)
        - Max drawdown from PortfolioSnapshot.total_value
        - Beta from FactorExposure ('Market Beta') on/<= window end
        - Partial results allowed; include warnings in metadata
        - Missing snapshots => available=false (reason: no_snapshots)
        """
        # 1) Determine window end as latest snapshot date
        end_stmt = (
            select(func.max(PortfolioSnapshot.snapshot_date))
            .where(PortfolioSnapshot.portfolio_id == portfolio_id)
        )
        end_res = await self.db.execute(end_stmt)
        end_date: Optional[date] = end_res.scalar_one_or_none()
        if end_date is None:
            return {
                "available": False,
                "portfolio_id": str(portfolio_id),
                "metadata": {"reason": "no_snapshots", "lookback_days": lookback_days},
            }

        start_date = end_date - timedelta(days=lookback_days)

        # 2) Load snapshots in window
        snaps_stmt = (
            select(PortfolioSnapshot)
            .where(
                and_(
                    PortfolioSnapshot.portfolio_id == portfolio_id,
                    PortfolioSnapshot.snapshot_date >= start_date,
                    PortfolioSnapshot.snapshot_date <= end_date,
                )
            )
            .order_by(PortfolioSnapshot.snapshot_date.asc())
        )
        snaps_res = await self.db.execute(snaps_stmt)
        snaps: List[PortfolioSnapshot] = list(snaps_res.scalars().all())

        if not snaps:
            return {
                "available": False,
                "portfolio_id": str(portfolio_id),
                "metadata": {
                    "reason": "no_snapshots",
                    "lookback_days": lookback_days,
                    "date_range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                },
            }

        warnings: List[str] = []

        # 3) Volatility (sample stddev of daily_return) × sqrt(252)
        returns: List[float] = [float(s.daily_return) for s in snaps if s.daily_return is not None]
        vol_annual: Optional[float] = None
        if len(returns) >= 2:
            mean = sum(returns) / len(returns)
            # sample variance (ddof=1)
            var = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
            vol_annual = (var ** 0.5) * sqrt(252.0)
        elif len(returns) == 1:
            vol_annual = 0.0
            warnings.append("few_snapshots")
        else:
            warnings.append("no_returns")

        # 4) Max drawdown from total_value
        values: List[float] = [float(s.total_value) for s in snaps if s.total_value is not None]
        max_dd: Optional[float] = None
        if values:
            peak = values[0]
            max_drawdown_pct = 0.0
            for v in values:
                if v > peak:
                    peak = v
                if peak > 0:
                    dd = (v / peak) - 1.0
                else:
                    dd = 0.0
                if dd < max_drawdown_pct:
                    max_drawdown_pct = dd
            max_dd = max_drawdown_pct
        else:
            warnings.append("no_values")

        # 5) Portfolio beta from FactorExposure ('Market Beta') on/<= end_date
        beta_value: Optional[float] = None
        beta_calc_date: Optional[date] = None
        beta_source = "unavailable"

        # Join FactorExposure -> FactorDefinition to find 'Market Beta'
        beta_stmt = (
            select(FactorExposure, FactorDefinition)
            .join(FactorDefinition, FactorExposure.factor_id == FactorDefinition.id)
            .where(
                and_(
                    FactorExposure.portfolio_id == portfolio_id,
                    FactorDefinition.name == "Market Beta",
                    FactorExposure.calculation_date <= end_date,
                )
            )
            .order_by(FactorExposure.calculation_date.desc())
            .limit(1)
        )
        beta_res = await self.db.execute(beta_stmt)
        beta_row = beta_res.first()
        if beta_row:
            fe: FactorExposure = beta_row[0]
            beta_value = float(fe.exposure_value) if fe.exposure_value is not None else None
            beta_calc_date = fe.calculation_date
            beta_source = "factor_exposure"
        else:
            warnings.append("beta_unavailable")

        # 6) Build response
        payload = {
            "portfolio_beta": beta_value,
            "annualized_volatility": vol_annual,
            "max_drawdown": max_dd,
        }

        meta: Dict[str, object] = {
            "lookback_days": lookback_days,
            "date_range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "observations": len(snaps),
            "calculation_timestamp": datetime.utcnow().isoformat() + "Z",
            "beta_source": beta_source,
        }
        if beta_calc_date:
            meta["beta_calculation_date"] = beta_calc_date.isoformat()
        meta["beta_window_days"] = REGRESSION_WINDOW_DAYS
        if warnings:
            meta["warnings"] = warnings

        return {
            "available": True,
            "portfolio_id": str(portfolio_id),
            "risk_metrics": payload,
            "metadata": meta,
        }

