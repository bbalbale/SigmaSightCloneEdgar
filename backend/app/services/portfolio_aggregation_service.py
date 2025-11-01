"""
Portfolio Aggregation Service

Implements portfolio-as-asset weighted average aggregation across multiple portfolios.
Each portfolio is treated as a conceptual investment, with metrics aggregated based on portfolio value weights.

Created: 2025-11-01
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.users import Portfolio, User
from app.models.positions import Position
from app.models.snapshots import PortfolioSnapshot
from app.models.market_data import PositionFactorExposure
from app.core.logging import get_logger

logger = get_logger(__name__)


class PortfolioAggregationService:
    """
    Service for aggregating metrics across multiple portfolios.

    Key Concept: Portfolio-as-Asset Aggregation
    - Calculate risk metrics per portfolio first
    - Aggregate using weighted averages based on portfolio value
    - Weight = portfolio_value / total_value

    Example:
        Portfolio A: $500k, Beta=1.2
        Portfolio B: $300k, Beta=0.8
        Total: $800k
        Aggregate Beta = (1.2 * 0.625) + (0.8 * 0.375) = 1.05
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_portfolios(
        self,
        user_id: UUID,
        include_inactive: bool = False
    ) -> List[Portfolio]:
        """
        Get all portfolios for a user.

        Args:
            user_id: User UUID
            include_inactive: Whether to include inactive portfolios

        Returns:
            List of Portfolio objects
        """
        query = select(Portfolio).where(Portfolio.user_id == user_id)

        if not include_inactive:
            query = query.where(Portfolio.is_active == True)

        result = await self.db.execute(query)
        portfolios = result.scalars().all()

        logger.info(f"Retrieved {len(portfolios)} portfolios for user {user_id}")
        return portfolios

    async def get_portfolio_values(
        self,
        portfolio_ids: List[UUID]
    ) -> Dict[UUID, Decimal]:
        """
        Get current market values for multiple portfolios.

        Uses the most recent PortfolioSnapshot for each portfolio.
        Falls back to equity_balance if no snapshot exists.

        Args:
            portfolio_ids: List of portfolio UUIDs

        Returns:
            Dict mapping portfolio_id to current market value
        """
        values = {}

        for portfolio_id in portfolio_ids:
            # Try to get most recent snapshot
            snapshot_result = await self.db.execute(
                select(PortfolioSnapshot)
                .where(PortfolioSnapshot.portfolio_id == portfolio_id)
                .order_by(PortfolioSnapshot.snapshot_date.desc())
                .limit(1)
            )
            snapshot = snapshot_result.scalar_one_or_none()

            if snapshot and snapshot.total_value:
                values[portfolio_id] = snapshot.total_value
            else:
                # Fallback to equity_balance
                portfolio_result = await self.db.execute(
                    select(Portfolio.equity_balance)
                    .where(Portfolio.id == portfolio_id)
                )
                equity_balance = portfolio_result.scalar_one_or_none()
                values[portfolio_id] = equity_balance or Decimal('0')

        logger.info(f"Retrieved values for {len(values)} portfolios, total: ${sum(values.values()):,.2f}")
        return values

    def calculate_weights(
        self,
        portfolio_values: Dict[UUID, Decimal]
    ) -> Dict[UUID, float]:
        """
        Calculate portfolio weights based on market values.

        Weight = portfolio_value / total_value

        Args:
            portfolio_values: Dict mapping portfolio_id to market value

        Returns:
            Dict mapping portfolio_id to weight (0.0 to 1.0)
        """
        total_value = sum(portfolio_values.values())

        if total_value == 0:
            logger.warning("Total portfolio value is zero, returning equal weights")
            # Equal weights if total is zero
            equal_weight = 1.0 / len(portfolio_values) if portfolio_values else 0.0
            return {pid: equal_weight for pid in portfolio_values.keys()}

        weights = {
            portfolio_id: float(value / total_value)
            for portfolio_id, value in portfolio_values.items()
        }

        logger.debug(f"Calculated weights: {weights}")
        return weights

    async def aggregate_portfolio_metrics(
        self,
        user_id: UUID,
        portfolio_ids: Optional[List[UUID]] = None
    ) -> Dict[str, Any]:
        """
        Aggregate portfolio-level metrics across multiple portfolios.

        This is the main entry point for portfolio aggregation.

        Args:
            user_id: User UUID
            portfolio_ids: Optional list of specific portfolio IDs to aggregate.
                          If None, aggregates all active portfolios for user.

        Returns:
            Dict containing:
                - total_value: Total market value across all portfolios
                - portfolio_count: Number of portfolios
                - portfolios: List of portfolio summaries with weights
                - aggregate_metrics: Weighted average metrics
        """
        # Get portfolios
        if portfolio_ids:
            portfolios = []
            for pid in portfolio_ids:
                result = await self.db.execute(
                    select(Portfolio).where(Portfolio.id == pid)
                )
                portfolio = result.scalar_one_or_none()
                if portfolio:
                    portfolios.append(portfolio)
        else:
            portfolios = await self.get_user_portfolios(user_id, include_inactive=False)

        if not portfolios:
            logger.warning(f"No portfolios found for user {user_id}")
            return {
                "total_value": 0,
                "portfolio_count": 0,
                "portfolios": [],
                "aggregate_metrics": {}
            }

        # Get portfolio values
        portfolio_ids_list = [p.id for p in portfolios]
        portfolio_values = await self.get_portfolio_values(portfolio_ids_list)

        # Calculate weights
        weights = self.calculate_weights(portfolio_values)

        # Build portfolio summaries
        portfolio_summaries = []
        for portfolio in portfolios:
            portfolio_summaries.append({
                "id": str(portfolio.id),
                "account_name": portfolio.account_name,
                "account_type": portfolio.account_type,
                "value": float(portfolio_values.get(portfolio.id, 0)),
                "weight": weights.get(portfolio.id, 0)
            })

        total_value = sum(portfolio_values.values())

        result = {
            "total_value": float(total_value),
            "portfolio_count": len(portfolios),
            "portfolios": portfolio_summaries,
            "aggregate_metrics": {}  # Will be populated by specific metric methods
        }

        logger.info(f"Aggregated {len(portfolios)} portfolios with total value ${total_value:,.2f}")
        return result

    async def aggregate_beta(
        self,
        portfolio_metrics: Dict[UUID, Dict[str, Any]]
    ) -> Optional[float]:
        """
        Aggregate portfolio betas using weighted average.

        Aggregate Beta = Σ(Beta_i × Weight_i)

        Args:
            portfolio_metrics: Dict mapping portfolio_id to dict containing 'beta' and 'weight'

        Returns:
            Weighted average beta, or None if no data
        """
        if not portfolio_metrics:
            return None

        weighted_sum = 0.0
        total_weight = 0.0

        for portfolio_id, metrics in portfolio_metrics.items():
            beta = metrics.get('beta')
            weight = metrics.get('weight', 0)

            if beta is not None:
                weighted_sum += beta * weight
                total_weight += weight

        if total_weight == 0:
            return None

        aggregate_beta = weighted_sum / total_weight
        logger.debug(f"Aggregate beta: {aggregate_beta:.4f}")
        return aggregate_beta

    async def aggregate_volatility(
        self,
        portfolio_metrics: Dict[UUID, Dict[str, Any]]
    ) -> Optional[float]:
        """
        Aggregate portfolio volatilities using weighted average.

        Note: This is a simplification. True portfolio volatility should account
        for correlations between portfolios. This provides a weighted average
        as an approximation.

        Args:
            portfolio_metrics: Dict mapping portfolio_id to dict containing 'volatility' and 'weight'

        Returns:
            Weighted average volatility, or None if no data
        """
        if not portfolio_metrics:
            return None

        weighted_sum = 0.0
        total_weight = 0.0

        for portfolio_id, metrics in portfolio_metrics.items():
            volatility = metrics.get('volatility')
            weight = metrics.get('weight', 0)

            if volatility is not None:
                weighted_sum += volatility * weight
                total_weight += weight

        if total_weight == 0:
            return None

        aggregate_volatility = weighted_sum / total_weight
        logger.debug(f"Aggregate volatility: {aggregate_volatility:.4f}")
        return aggregate_volatility

    async def aggregate_factor_exposures(
        self,
        portfolio_ids: List[UUID],
        weights: Dict[UUID, float]
    ) -> Dict[str, float]:
        """
        Aggregate factor exposures across portfolios using weighted average.

        For each factor:
            Aggregate Exposure = Σ(Portfolio_Exposure_i × Weight_i)

        Args:
            portfolio_ids: List of portfolio UUIDs
            weights: Dict mapping portfolio_id to weight

        Returns:
            Dict mapping factor names to aggregate exposures
        """
        # Get all factor exposures for these portfolios
        result = await self.db.execute(
            select(PositionFactorExposure)
            .join(Position)
            .where(Position.portfolio_id.in_(portfolio_ids))
        )
        factor_exposures = result.scalars().all()

        # Group by portfolio and factor
        portfolio_factors: Dict[UUID, Dict[str, List[float]]] = {}

        for exposure in factor_exposures:
            position_result = await self.db.execute(
                select(Position.portfolio_id)
                .where(Position.id == exposure.position_id)
            )
            portfolio_id = position_result.scalar_one()

            if portfolio_id not in portfolio_factors:
                portfolio_factors[portfolio_id] = {}

            # Collect all factor betas for each factor type
            factors = {
                'market': exposure.market_beta,
                'size': exposure.size_beta,
                'value': exposure.value_beta,
                'momentum': exposure.momentum_beta,
                'quality': exposure.quality_beta
            }

            for factor_name, beta_value in factors.items():
                if beta_value is not None:
                    if factor_name not in portfolio_factors[portfolio_id]:
                        portfolio_factors[portfolio_id][factor_name] = []
                    portfolio_factors[portfolio_id][factor_name].append(float(beta_value))

        # Calculate average factor exposure per portfolio
        portfolio_avg_factors: Dict[UUID, Dict[str, float]] = {}
        for portfolio_id, factors in portfolio_factors.items():
            portfolio_avg_factors[portfolio_id] = {
                factor_name: sum(betas) / len(betas)
                for factor_name, betas in factors.items()
            }

        # Aggregate across portfolios using weights
        aggregate_factors = {}
        factor_names = ['market', 'size', 'value', 'momentum', 'quality']

        for factor_name in factor_names:
            weighted_sum = 0.0
            total_weight = 0.0

            for portfolio_id, weight in weights.items():
                if portfolio_id in portfolio_avg_factors:
                    factor_value = portfolio_avg_factors[portfolio_id].get(factor_name)
                    if factor_value is not None:
                        weighted_sum += factor_value * weight
                        total_weight += weight

            if total_weight > 0:
                aggregate_factors[factor_name] = weighted_sum / total_weight

        logger.info(f"Aggregated factor exposures: {aggregate_factors}")
        return aggregate_factors


# Singleton instance factory
async def get_aggregation_service(db: AsyncSession) -> PortfolioAggregationService:
    """Factory function to create PortfolioAggregationService instance."""
    return PortfolioAggregationService(db)
