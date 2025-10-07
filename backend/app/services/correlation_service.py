"""
Position-to-position correlation analysis service
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Tuple, Set
from uuid import UUID
from collections import defaultdict
import numpy as np
import pandas as pd
from scipy import stats
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Portfolio, Position, MarketDataCache,
    CorrelationCalculation, CorrelationCluster, 
    CorrelationClusterPosition, PairwiseCorrelation
)
from app.models.tags_v2 import TagV2
from app.models import PositionTag
from app.schemas.correlations import (
    PositionFilterConfig, CorrelationCalculationCreate,
    PairwiseCorrelationCreate
)
from app.services.market_data_service import MarketDataService

logger = logging.getLogger(__name__)


class CorrelationService:
    """Service for calculating position-to-position correlations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.market_data_service = MarketDataService()
    
    async def calculate_portfolio_correlations(
        self,
        portfolio_id: UUID,
        calculation_date: datetime,
        min_position_value: Optional[Decimal] = Decimal("10000"),
        min_portfolio_weight: Optional[Decimal] = Decimal("0.01"),
        filter_mode: str = "both",
        correlation_threshold: Decimal = Decimal("0.7"),
        duration_days: int = 90,
        force_recalculate: bool = False
    ) -> Optional[CorrelationCalculation]:  # Phase 8.1 Task 7a: Can return None when skipped
        """
        Main orchestrator for portfolio correlation calculations
        """
        try:
            # Check for existing calculation (unless forced)
            if not force_recalculate:
                existing = await self._get_existing_calculation(
                    portfolio_id, duration_days, calculation_date
                )
                if existing:
                    logger.info(f"Using existing correlation calculation for portfolio {portfolio_id}")
                    return existing
            
            # Get portfolio with positions
            portfolio = await self._get_portfolio_with_positions(portfolio_id)
            if not portfolio:
                raise ValueError(f"Portfolio {portfolio_id} not found")
            
            # Calculate portfolio total value
            portfolio_value = sum(
                abs(p.quantity * p.last_price) for p in portfolio.positions
            )

            # Filter PRIVATE investment class positions (Phase 8.1 Task 2)
            public_positions = [
                p for p in portfolio.positions
                if p.investment_class != 'PRIVATE'
            ]
            private_count = len(portfolio.positions) - len(public_positions)
            if private_count > 0:
                logger.info(
                    f"Filtered {private_count} PRIVATE positions from correlation analysis "
                    f"(total positions: {len(portfolio.positions)}, public: {len(public_positions)})"
                )

            # Filter significant positions
            filtered_positions = self.filter_significant_positions(
                public_positions,  # Use filtered list instead of portfolio.positions
                portfolio_value,
                min_position_value,
                min_portfolio_weight,
                filter_mode
            )

            excluded_count = private_count + (len(public_positions) - len(filtered_positions))
            logger.info(
                f"Filtered {len(filtered_positions)} significant positions "
                f"from {len(portfolio.positions)} total "
                f"(excluded: {excluded_count} = {private_count} PRIVATE + {len(public_positions) - len(filtered_positions)} insignificant)"
            )
            
            # Get position returns data
            start_date = calculation_date - timedelta(days=duration_days)
            returns_df = await self._get_position_returns(
                filtered_positions, start_date, calculation_date
            )

            # Phase 8.1 Task 7a: Graceful skip instead of ValueError
            if returns_df.empty:
                logger.warning(
                    f"No return data available for correlation calculation (portfolio {portfolio_id}). "
                    f"All {private_count} PRIVATE positions were filtered. Skipping correlation calculation."
                )
                await self.db.rollback()
                return None  # Option B: Skip persistence, return None

            # Validate data sufficiency (minimum 20 days)
            valid_positions = self._validate_data_sufficiency(returns_df, min_days=20)
            returns_df = returns_df[valid_positions]

            # Phase 8.1 Task 7a: Graceful skip instead of ValueError
            if returns_df.empty:
                logger.warning(
                    f"No positions have sufficient data for correlation calculation (portfolio {portfolio_id}). "
                    f"All positions have <20 days of data. Skipping correlation calculation."
                )
                await self.db.rollback()
                return None  # Option B: Skip persistence, return None
            
            # Calculate pairwise correlations
            correlation_matrix = self.calculate_pairwise_correlations(returns_df)
            
            # Detect correlation clusters
            clusters = await self.detect_correlation_clusters(
                correlation_matrix, 
                filtered_positions,
                portfolio_value,
                threshold=float(correlation_threshold)
            )
            
            # Calculate portfolio-level metrics
            metrics = self.calculate_portfolio_metrics(
                correlation_matrix, 
                filtered_positions,
                clusters
            )
            
            # Create calculation record
            calculation = CorrelationCalculation(
                portfolio_id=portfolio_id,
                duration_days=duration_days,
                calculation_date=calculation_date,
                overall_correlation=metrics["overall_correlation"],
                correlation_concentration_score=metrics["concentration_score"],
                effective_positions=metrics["effective_positions"],
                data_quality=metrics["data_quality"],
                min_position_value=min_position_value,
                min_portfolio_weight=min_portfolio_weight,
                filter_mode=filter_mode,
                correlation_threshold=correlation_threshold,
                positions_included=len(valid_positions),
                positions_excluded=excluded_count + (len(filtered_positions) - len(valid_positions))
            )
            
            self.db.add(calculation)
            await self.db.flush()
            
            # Store correlation matrix
            await self._store_correlation_matrix(
                calculation.id, correlation_matrix, returns_df
            )
            
            # Store clusters
            await self._store_clusters(
                calculation.id, clusters, filtered_positions, portfolio_value
            )
            
            await self.db.commit()
            
            logger.info(
                f"Completed correlation calculation for portfolio {portfolio_id}: "
                f"overall_correlation={metrics['overall_correlation']:.4f}, "
                f"clusters={len(clusters)}"
            )
            
            return calculation
            
        except Exception as e:
            logger.error(f"Error calculating correlations for portfolio {portfolio_id}: {e}")
            await self.db.rollback()
            raise
    
    def filter_significant_positions(
        self,
        positions: List[Position],
        portfolio_value: Decimal,
        min_value: Optional[Decimal],
        min_weight: Optional[Decimal],
        filter_mode: str = "both"
    ) -> List[Position]:
        """
        Filter positions based on value and/or weight thresholds
        
        filter_mode options:
        - 'value_only': Only apply minimum value threshold
        - 'weight_only': Only apply minimum weight threshold  
        - 'both': Positions must meet BOTH thresholds (default)
        - 'either': Positions must meet at least ONE threshold
        """
        filtered = []
        
        for position in positions:
            # Calculate position metrics
            position_value = abs(position.quantity * position.last_price)
            position_weight = position_value / portfolio_value if portfolio_value > 0 else 0
            
            # Apply filters based on mode
            if filter_mode == "value_only":
                if min_value is None or position_value >= min_value:
                    filtered.append(position)
                    
            elif filter_mode == "weight_only":
                if min_weight is None or position_weight >= min_weight:
                    filtered.append(position)
                    
            elif filter_mode == "both":
                value_ok = min_value is None or position_value >= min_value
                weight_ok = min_weight is None or position_weight >= min_weight
                if value_ok and weight_ok:
                    filtered.append(position)
                    
            elif filter_mode == "either":
                value_ok = min_value is not None and position_value >= min_value
                weight_ok = min_weight is not None and position_weight >= min_weight
                if value_ok or weight_ok:
                    filtered.append(position)
        
        return filtered
    
    def calculate_pairwise_correlations(self, returns_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate full pairwise correlation matrix using log returns
        Returns full matrix including self-correlations and both directions
        """
        # Calculate correlation matrix using pandas
        correlation_matrix = returns_df.corr(method='pearson')
        
        # Ensure we have both directions and self-correlations
        # (pandas corr() already returns a symmetric matrix with diagonal = 1)
        
        return correlation_matrix
    
    async def detect_correlation_clusters(
        self,
        correlation_matrix: pd.DataFrame,
        positions: List[Position],
        portfolio_value: Decimal,
        threshold: float = 0.7
    ) -> List[Dict]:
        """
        Identify clusters of highly correlated positions using graph connectivity
        """
        symbols = list(correlation_matrix.columns)
        n = len(symbols)
        
        # Create adjacency matrix based on correlation threshold
        adj_matrix = (correlation_matrix.abs() >= threshold).values
        
        # Find connected components using depth-first search
        visited = [False] * n
        clusters = []
        
        def dfs(node: int, cluster: List[int]):
            visited[node] = True
            cluster.append(node)
            
            for neighbor in range(n):
                if not visited[neighbor] and adj_matrix[node][neighbor] and node != neighbor:
                    dfs(neighbor, cluster)
        
        # Find all clusters
        for i in range(n):
            if not visited[i]:
                cluster_indices = []
                dfs(i, cluster_indices)
                
                # Only consider clusters with 2+ positions
                if len(cluster_indices) >= 2:
                    cluster_symbols = [symbols[idx] for idx in cluster_indices]
                    
                    # Calculate average correlation within cluster
                    cluster_corr_values = []
                    for j, idx1 in enumerate(cluster_indices):
                        for idx2 in cluster_indices[j+1:]:
                            cluster_corr_values.append(
                                correlation_matrix.iloc[idx1, idx2]
                            )
                    
                    avg_correlation = np.mean(cluster_corr_values) if cluster_corr_values else 0
                    
                    # Generate cluster nickname
                    nickname = await self.generate_cluster_nickname(
                        cluster_symbols, positions
                    )
                    
                    clusters.append({
                        "symbols": cluster_symbols,
                        "indices": cluster_indices,
                        "avg_correlation": Decimal(str(avg_correlation)),
                        "nickname": nickname
                    })
        
        # Sort clusters by size (descending)
        clusters.sort(key=lambda x: len(x["symbols"]), reverse=True)
        
        return clusters
    
    async def generate_cluster_nickname(
        self, 
        cluster_symbols: List[str],
        positions: List[Position]
    ) -> str:
        """
        Generate human-readable cluster nickname using waterfall logic:
        1. Common tags
        2. Common sector
        3. Largest position + "lookalikes"
        """
        # Create symbol to position mapping
        symbol_to_position = {p.symbol: p for p in positions}
        cluster_positions = [
            symbol_to_position[s] for s in cluster_symbols 
            if s in symbol_to_position
        ]
        
        # 1. Check for common tags (position-level tagging system)
        if cluster_positions:
            position_ids = [p.id for p in cluster_positions if p.id]
            if position_ids:
                tag_query = (
                    select(TagV2)
                    .join(PositionTag, TagV2.id == PositionTag.tag_id)
                    .where(PositionTag.position_id.in_(position_ids))
                    .where(TagV2.is_archived == False)
                )
                result = await self.db.execute(tag_query)
                tags = result.scalars().all()

                tag_counts = defaultdict(int)
                for tag in tags:
                    tag_counts[tag.name] += 1

                if tag_counts:
                    most_common_tag = max(tag_counts, key=tag_counts.get)
                    if tag_counts[most_common_tag] >= len(cluster_positions) * 0.7:
                        return most_common_tag
        
        # 2. Check for common sector
        sectors = []
        for symbol in cluster_symbols:
            # Query market data cache for sector info
            query = select(MarketDataCache).where(
                MarketDataCache.symbol == symbol
            ).order_by(MarketDataCache.date.desc()).limit(1)
            
            result = await self.db.execute(query)
            market_data = result.scalar_one_or_none()
            
            if market_data and market_data.sector:
                sectors.append(market_data.sector)
        
        if sectors:
            # Find most common sector
            sector_counts = defaultdict(int)
            for sector in sectors:
                sector_counts[sector] += 1
            
            most_common_sector = max(sector_counts, key=sector_counts.get)
            if sector_counts[most_common_sector] >= len(cluster_symbols) * 0.7:  # 70% threshold
                return most_common_sector
        
        # 3. Use largest position + "lookalikes"
        if cluster_positions:
            # Find largest position by value
            largest_position = max(
                cluster_positions,
                key=lambda p: abs(p.quantity * p.last_price)
            )
            return f"{largest_position.symbol} lookalikes"
        
        # Fallback
        return f"Cluster {cluster_symbols[0]}"
    
    def calculate_portfolio_metrics(
        self,
        correlation_matrix: pd.DataFrame,
        positions: List[Position],
        clusters: List[Dict]
    ) -> Dict[str, Decimal]:
        """
        Calculate portfolio-level correlation metrics
        """
        # Get upper triangle of correlation matrix (excluding diagonal)
        upper_triangle = np.triu(correlation_matrix.values, k=1)
        non_zero_correlations = upper_triangle[upper_triangle != 0]
        
        # Overall correlation (average pairwise correlation)
        overall_correlation = (
            Decimal(str(np.mean(np.abs(non_zero_correlations))))
            if len(non_zero_correlations) > 0
            else Decimal("0")
        )
        
        # Calculate concentration score (% of portfolio in high-correlation clusters)
        clustered_symbols = set()
        for cluster in clusters:
            clustered_symbols.update(cluster["symbols"])
        
        # Calculate value of clustered positions
        clustered_value = Decimal("0")
        total_value = Decimal("0")
        
        for position in positions:
            position_value = abs(position.quantity * position.last_price)
            total_value += position_value
            
            if position.symbol in clustered_symbols:
                clustered_value += position_value
        
        concentration_score = (
            clustered_value / total_value 
            if total_value > 0 
            else Decimal("0")
        )
        
        # Calculate effective positions (based on correlation matrix)
        # Using the formula: N_eff = (sum of weights)^2 / sum of (weight_i * weight_j * corr_ij)
        n = len(positions)
        if n > 0:
            # Equal weights for simplicity (can be enhanced with actual weights)
            weights = np.ones(n) / n
            
            # Calculate denominator
            denominator = 0
            for i in range(n):
                for j in range(n):
                    if i < len(correlation_matrix) and j < len(correlation_matrix):
                        denominator += weights[i] * weights[j] * correlation_matrix.iloc[i, j]
            
            effective_positions = Decimal("1") / Decimal(str(denominator)) if denominator > 0 else Decimal(str(n))
        else:
            effective_positions = Decimal("0")
        
        # Determine data quality
        data_quality = "sufficient"  # We already filtered for min 20 days
        
        return {
            "overall_correlation": overall_correlation,
            "concentration_score": concentration_score,
            "effective_positions": effective_positions,
            "data_quality": data_quality
        }
    
    # Helper methods
    
    async def _get_existing_calculation(
        self,
        portfolio_id: UUID,
        duration_days: int,
        calculation_date: datetime
    ) -> Optional[CorrelationCalculation]:
        """Check for existing calculation"""
        query = select(CorrelationCalculation).where(
            and_(
                CorrelationCalculation.portfolio_id == portfolio_id,
                CorrelationCalculation.duration_days == duration_days,
                CorrelationCalculation.calculation_date == calculation_date
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_portfolio_with_positions(self, portfolio_id: UUID) -> Optional[Portfolio]:
        """Get portfolio with positions loaded"""
        query = select(Portfolio).where(
            Portfolio.id == portfolio_id
        ).options(selectinload(Portfolio.positions))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_position_returns(
        self,
        positions: List[Position],
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Get daily log returns for positions
        Returns DataFrame with dates as index and symbols as columns
        """
        returns_data = {}
        
        for position in positions:
            # Get price data from market data cache
            query = select(
                MarketDataCache.date,
                MarketDataCache.close
            ).where(
                and_(
                    MarketDataCache.symbol == position.symbol,
                    MarketDataCache.date >= start_date,
                    MarketDataCache.date <= end_date
                )
            ).order_by(MarketDataCache.date)
            
            result = await self.db.execute(query)
            price_data = result.all()
            
            if len(price_data) >= 2:  # Need at least 2 points for returns
                # Convert to pandas Series
                dates = [row.date for row in price_data]
                prices = [float(row.close) for row in price_data]
                
                price_series = pd.Series(prices, index=pd.DatetimeIndex(dates))
                
                # Calculate log returns: ln(price_t / price_t-1)
                log_returns = np.log(price_series / price_series.shift(1)).dropna()
                
                returns_data[position.symbol] = log_returns
        
        # Create DataFrame from returns data
        if returns_data:
            # Align all series to common dates
            returns_df = pd.DataFrame(returns_data)
            return returns_df
        else:
            return pd.DataFrame()
    
    def _validate_data_sufficiency(
        self, 
        returns_df: pd.DataFrame,
        min_days: int = 20
    ) -> List[str]:
        """
        Validate that positions have sufficient data points
        Returns list of valid position symbols
        """
        valid_positions = []
        
        for symbol in returns_df.columns:
            non_null_count = returns_df[symbol].notna().sum()
            if non_null_count >= min_days:
                valid_positions.append(symbol)
            else:
                logger.warning(
                    f"Position {symbol} has insufficient data: "
                    f"{non_null_count} days < {min_days} minimum"
                )
        
        return valid_positions
    
    async def _store_correlation_matrix(
        self,
        calculation_id: UUID,
        correlation_matrix: pd.DataFrame,
        returns_df: pd.DataFrame
    ):
        """Store full correlation matrix including both directions and self-correlations"""
        correlations_to_store = []
        
        for symbol1 in correlation_matrix.columns:
            for symbol2 in correlation_matrix.columns:
                # Store all pairs including self-correlations
                correlation_value = correlation_matrix.loc[symbol1, symbol2]
                
                # Count valid data points
                data_points = returns_df[[symbol1, symbol2]].dropna().shape[0]
                
                # Calculate statistical significance (p-value)
                if symbol1 != symbol2 and data_points >= 3:
                    # Use scipy stats for p-value calculation
                    _, p_value = stats.pearsonr(
                        returns_df[symbol1].dropna(),
                        returns_df[symbol2].dropna()
                    )
                    statistical_significance = Decimal(str(1 - p_value))
                else:
                    statistical_significance = Decimal("1") if symbol1 == symbol2 else None
                
                pairwise_corr = PairwiseCorrelation(
                    correlation_calculation_id=calculation_id,
                    symbol_1=symbol1,
                    symbol_2=symbol2,
                    correlation_value=Decimal(str(correlation_value)),
                    data_points=data_points,
                    statistical_significance=statistical_significance
                )
                
                correlations_to_store.append(pairwise_corr)
        
        # Bulk insert
        self.db.add_all(correlations_to_store)
        await self.db.flush()
    
    async def _store_clusters(
        self,
        calculation_id: UUID,
        clusters: List[Dict],
        positions: List[Position],
        portfolio_value: Decimal
    ):
        """Store correlation clusters and their positions"""
        # Create position lookup
        symbol_to_position = {p.symbol: p for p in positions}
        
        for i, cluster_data in enumerate(clusters):
            # Calculate cluster totals
            cluster_value = Decimal("0")
            cluster_positions = []
            
            for symbol in cluster_data["symbols"]:
                if symbol in symbol_to_position:
                    position = symbol_to_position[symbol]
                    position_value = abs(position.quantity * position.last_price)
                    cluster_value += position_value
                    cluster_positions.append((position, position_value))
            
            # Create cluster record
            cluster = CorrelationCluster(
                correlation_calculation_id=calculation_id,
                cluster_number=i + 1,
                nickname=cluster_data["nickname"],
                avg_correlation=cluster_data["avg_correlation"],
                total_value=cluster_value,
                portfolio_percentage=cluster_value / portfolio_value if portfolio_value > 0 else Decimal("0")
            )
            
            self.db.add(cluster)
            await self.db.flush()
            
            # Add cluster positions
            for position, position_value in cluster_positions:
                # Calculate correlation to cluster (average correlation with other cluster members)
                correlations_to_cluster = []
                for other_symbol in cluster_data["symbols"]:
                    if other_symbol != position.symbol:
                        # This would need access to the correlation matrix
                        # For now, use the average cluster correlation
                        correlations_to_cluster.append(float(cluster_data["avg_correlation"]))
                
                avg_correlation_to_cluster = (
                    Decimal(str(np.mean(correlations_to_cluster)))
                    if correlations_to_cluster
                    else cluster_data["avg_correlation"]
                )
                
                cluster_position = CorrelationClusterPosition(
                    cluster_id=cluster.id,
                    position_id=position.id,
                    symbol=position.symbol,
                    value=position_value,
                    portfolio_percentage=position_value / portfolio_value if portfolio_value > 0 else Decimal("0"),
                    correlation_to_cluster=avg_correlation_to_cluster
                )
                
            self.db.add(cluster_position)
        
            await self.db.flush()

    async def get_weighted_correlation(
        self,
        portfolio_id: UUID,
        lookback_days: int,
        min_overlap: int
    ) -> Dict[str, any]:
        """
        Compute weighted absolute portfolio correlation (0–1) using the full
        calculation symbol set for the latest correlation run matching the
        requested lookback (duration_days).

        Returns a light dict matching DiversificationScoreResponse.
        """
        # 1) Find latest calculation header for (portfolio_id, duration_days)
        calc_query = (
            select(CorrelationCalculation)
            .where(
                and_(
                    CorrelationCalculation.portfolio_id == portfolio_id,
                    CorrelationCalculation.duration_days == lookback_days,
                )
            )
            .order_by(CorrelationCalculation.calculation_date.desc())
        )

        calc_result = await self.db.execute(calc_query)
        calculation: Optional[CorrelationCalculation] = calc_result.scalars().first()

        if not calculation:
            return {
                "available": False,
                "portfolio_id": str(portfolio_id),
                "duration_days": lookback_days,
                "metadata": {
                    "reason": "no_calculation_available",
                    "lookback_days": lookback_days,
                    "min_overlap": min_overlap,
                    "selection_method": "full_calculation_set",
                },
            }

        # 2) Load pairwise correlations for this calculation with overlap filter
        pairs_query = (
            select(PairwiseCorrelation)
            .where(
                and_(
                    PairwiseCorrelation.correlation_calculation_id == calculation.id,
                    PairwiseCorrelation.data_points >= min_overlap,
                )
            )
        )
        pairs_result = await self.db.execute(pairs_query)
        pairs: List[PairwiseCorrelation] = list(pairs_result.scalars().all())

        # Build symbol set (exclude self-correlations for set construction)
        symbol_set: Set[str] = set()
        for p in pairs:
            if p.symbol_1 and p.symbol_2 and p.symbol_1 != p.symbol_2:
                symbol_set.add(p.symbol_1)
                symbol_set.add(p.symbol_2)

        if len(symbol_set) < 2:
            return {
                "available": False,
                "portfolio_id": str(portfolio_id),
                "duration_days": lookback_days,
                "calculation_date": calculation.calculation_date.date().isoformat() if calculation.calculation_date else None,
                "symbols_included": len(symbol_set),
                "metadata": {
                    "reason": "insufficient_symbols",
                    "lookback_days": lookback_days,
                    "min_overlap": min_overlap,
                    "selection_method": "full_calculation_set",
                },
            }

        # 3) Compute current gross weights for symbols in the calculation set
        #    If last_price is missing, fall back to entry_price.
        pos_query = select(Portfolio).where(Portfolio.id == portfolio_id).options(selectinload(Portfolio.positions))
        pos_result = await self.db.execute(pos_query)
        portfolio = pos_result.scalars().first()

        weights_raw: Dict[str, float] = {}
        if portfolio and portfolio.positions:
            for pos in portfolio.positions:
                sym = (pos.symbol or "").upper()
                if sym not in symbol_set:
                    continue
                price = pos.last_price if pos.last_price is not None else pos.entry_price
                try:
                    mv = abs(float(pos.quantity) * float(price)) if price is not None else 0.0
                except Exception:
                    mv = 0.0
                weights_raw[sym] = weights_raw.get(sym, 0.0) + mv

        # Normalize weights across symbols in symbol_set
        total_mv = sum(weights_raw.get(s, 0.0) for s in symbol_set)
        weights: Dict[str, float] = {}
        if total_mv > 0:
            for s in symbol_set:
                weights[s] = (weights_raw.get(s, 0.0) / total_mv)
        else:
            # Fallback to equal weights
            equal = 1.0 / float(len(symbol_set))
            weights = {s: equal for s in symbol_set}

        # 4) Build unique unordered pairs and aggregate
        #    Use absolute correlation for weighted similarity metric.
        seen_pairs: Set[frozenset] = set()
        # Build a lookup for correlations to avoid repeated scans
        corr_lookup: Dict[Tuple[str, str], float] = {}
        for p in pairs:
            if p.symbol_1 and p.symbol_2 and p.symbol_1 != p.symbol_2:
                corr_lookup[(p.symbol_1, p.symbol_2)] = float(p.correlation_value)

        numerator = 0.0
        denominator = 0.0
        symbols_list = sorted(symbol_set)
        for i in range(len(symbols_list)):
            for j in range(i + 1, len(symbols_list)):
                s1 = symbols_list[i]
                s2 = symbols_list[j]
                key = frozenset({s1, s2})
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                # correlation may be stored in either direction
                c = corr_lookup.get((s1, s2))
                if c is None:
                    c = corr_lookup.get((s2, s1))
                if c is None:
                    continue  # pair removed by min_overlap or not present
                w1 = weights.get(s1, 0.0)
                w2 = weights.get(s2, 0.0)
                w_prod = w1 * w2
                if w_prod <= 0:
                    continue
                numerator += w_prod * abs(c)
                denominator += w_prod

        if denominator <= 0:
            return {
                "available": False,
                "portfolio_id": str(portfolio_id),
                "duration_days": lookback_days,
                "calculation_date": calculation.calculation_date.date().isoformat() if calculation.calculation_date else None,
                "symbols_included": len(symbol_set),
                "metadata": {
                    "reason": "insufficient_symbols",
                    "lookback_days": lookback_days,
                    "min_overlap": min_overlap,
                    "selection_method": "full_calculation_set",
                },
            }

        portfolio_correlation = numerator / denominator
        return {
            "available": True,
            "portfolio_id": str(portfolio_id),
            "portfolio_correlation": float(portfolio_correlation),
            "duration_days": lookback_days,
            "calculation_date": calculation.calculation_date.date().isoformat() if calculation.calculation_date else None,
            "symbols_included": len(symbol_set),
            "metadata": {
                "lookback_days": lookback_days,
                "min_overlap": min_overlap,
                "selection_method": "full_calculation_set",
                "calculation_id": str(calculation.id),
            },
        }
    
    async def get_matrix(
        self,
        portfolio_id: UUID,
        lookback_days: int = 90,
        min_overlap: int = 30,
        max_symbols: int = 25
    ) -> Dict:
        """
        Retrieve pre-calculated correlation matrix for a portfolio.

        Phase 8.1 Task 13: Returns data_quality metrics when available=False

        Args:
            portfolio_id: Portfolio UUID
            lookback_days: Duration of the calculation period (must match existing calculation)
            min_overlap: Minimum data points required for correlation pairs
            max_symbols: Maximum number of symbols to include in matrix (by weight)

        Returns:
            Dict with correlation matrix or unavailable status
        """
        try:
            # Get the latest correlation calculation for this portfolio and lookback period
            stmt = select(CorrelationCalculation).where(
                and_(
                    CorrelationCalculation.portfolio_id == portfolio_id,
                    CorrelationCalculation.duration_days == lookback_days
                )
            ).order_by(CorrelationCalculation.calculation_date.desc()).limit(1)
            
            result = await self.db.execute(stmt)
            calculation = result.scalar_one_or_none()

            if not calculation:
                # Compute data_quality when no calculation available
                data_quality = await self._compute_data_quality(
                    portfolio_id=portfolio_id,
                    flag="NO_CORRELATION_CALCULATION",
                    message=f"No correlation calculation found for portfolio with {lookback_days}-day lookback",
                    positions_analyzed=0,
                    data_days=lookback_days
                )
                return {
                    "available": False,
                    "data_quality": data_quality,
                    "metadata": {
                        "reason": "no_calculation_available",
                        "requested_lookback_days": lookback_days,
                        "message": f"No correlation calculation found for portfolio {portfolio_id} with {lookback_days}-day lookback"
                    }
                }
            
            # Get all pairwise correlations for this calculation
            corr_stmt = select(PairwiseCorrelation).where(
                PairwiseCorrelation.correlation_calculation_id == calculation.id
            )
            corr_result = await self.db.execute(corr_stmt)
            correlations = corr_result.scalars().all()
            
            # Filter by min_overlap
            filtered_correlations = [
                c for c in correlations
                if c.data_points >= min_overlap
            ]

            if not filtered_correlations:
                # Compute data_quality when insufficient data
                data_quality = await self._compute_data_quality(
                    portfolio_id=portfolio_id,
                    flag="INSUFFICIENT_DATA",
                    message=f"No correlations meet the minimum overlap requirement of {min_overlap} data points",
                    positions_analyzed=0,
                    data_days=lookback_days
                )
                return {
                    "available": False,
                    "data_quality": data_quality,
                    "metadata": {
                        "reason": "insufficient_data",
                        "min_overlap": min_overlap,
                        "message": f"No correlations meet the minimum overlap requirement of {min_overlap} data points"
                    }
                }
            
            # Get current positions for weight ordering
            pos_stmt = select(Position).where(
                and_(
                    Position.portfolio_id == portfolio_id,
                    Position.exit_date.is_(None)
                )
            )
            pos_result = await self.db.execute(pos_stmt)
            positions = pos_result.scalars().all()
            
            # Calculate weights (gross market value with fallback to entry_price)
            symbol_weights = {}
            for pos in positions:
                price = pos.last_price if pos.last_price else pos.entry_price
                if price:
                    weight = abs(float(pos.quantity * price))
                    symbol_weights[pos.symbol] = weight
            
            # Get unique symbols from correlations
            symbols = set()
            for corr in filtered_correlations:
                symbols.add(corr.symbol_1)
                symbols.add(corr.symbol_2)
            
            # Order symbols by weight (descending), then alphabetically for those not in portfolio
            ordered_symbols = sorted(
                symbols,
                key=lambda s: (-symbol_weights.get(s, 0), s)
            )
            
            # Limit to max_symbols
            if len(ordered_symbols) > max_symbols:
                ordered_symbols = ordered_symbols[:max_symbols]
            
            # Build the matrix as nested dictionary
            matrix = {}
            for symbol1 in ordered_symbols:
                matrix[symbol1] = {}
                for symbol2 in ordered_symbols:
                    if symbol1 == symbol2:
                        matrix[symbol1][symbol2] = 1.0
                    else:
                        # Find correlation value (checking both directions)
                        corr_value = None
                        for corr in filtered_correlations:
                            if (corr.symbol_1 == symbol1 and corr.symbol_2 == symbol2) or \
                               (corr.symbol_1 == symbol2 and corr.symbol_2 == symbol1):
                                corr_value = float(corr.correlation_value)
                                break
                        
                        if corr_value is not None:
                            matrix[symbol1][symbol2] = corr_value
                        else:
                            # This shouldn't happen if data is complete, but handle gracefully
                            matrix[symbol1][symbol2] = 0.0
            
            # Check if we have enough symbols
            if len(ordered_symbols) < 2:
                # Compute data_quality when insufficient symbols
                data_quality = await self._compute_data_quality(
                    portfolio_id=portfolio_id,
                    flag="INSUFFICIENT_SYMBOLS",
                    message=f"Need at least 2 symbols for correlation matrix, found {len(ordered_symbols)}",
                    positions_analyzed=len(ordered_symbols),
                    data_days=lookback_days
                )
                return {
                    "available": False,
                    "data_quality": data_quality,
                    "metadata": {
                        "reason": "insufficient_symbols",
                        "symbols_found": len(ordered_symbols),
                        "message": f"Need at least 2 symbols for correlation matrix, found {len(ordered_symbols)}"
                    }
                }

            return {
                "data": {
                    "matrix": matrix,
                    "average_correlation": float(calculation.overall_correlation) if calculation.overall_correlation else None
                },
                "available": True,
                "data_quality": None,  # Phase 8.1: Future enhancement to compute quality metrics when available=True
                "metadata": {
                    "calculation_date": calculation.calculation_date.isoformat() if calculation.calculation_date else None,
                    "duration_days": lookback_days,
                    "symbols_included": len(ordered_symbols),
                    "lookback_days": lookback_days,
                    "min_overlap": min_overlap,
                    "max_symbols": max_symbols,
                    "selection_method": "weight"
                }
            }
            
        except Exception as e:
            logger.error(f"Error retrieving correlation matrix for portfolio {portfolio_id}: {str(e)}")
            raise

    async def _compute_data_quality(
        self,
        portfolio_id: UUID,
        flag: str,
        message: str,
        positions_analyzed: int,
        data_days: int
    ) -> Dict:
        """
        Compute data quality metrics for portfolio

        Phase 8.1 Task 13: Computes position counts to explain why correlations were skipped

        Args:
            portfolio_id: Portfolio UUID
            flag: Quality flag constant (e.g., NO_CORRELATION_CALCULATION)
            message: Human-readable explanation
            positions_analyzed: Number of positions included in calculation
            data_days: Number of days of historical data used

        Returns:
            Dictionary with data_quality metrics matching DataQualityInfo schema
        """
        from sqlalchemy import func

        # Count total positions in portfolio
        total_stmt = select(func.count(Position.id)).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.quantity != 0  # Only count active positions
            )
        )
        positions_total = (await self.db.execute(total_stmt)).scalar() or 0

        # Count PUBLIC positions (exclude PRIVATE investment_class per Phase 8.1)
        public_stmt = select(func.count(Position.id)).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.quantity != 0,
                or_(
                    Position.investment_class != 'PRIVATE',
                    Position.investment_class.is_(None)  # Include NULL (not yet classified)
                )
            )
        )
        public_positions = (await self.db.execute(public_stmt)).scalar() or 0

        # positions_skipped = total - analyzed
        positions_skipped = positions_total - positions_analyzed

        return {
            "flag": flag,
            "message": message,
            "positions_analyzed": positions_analyzed,
            "positions_total": positions_total,
            "positions_skipped": positions_skipped,
            "data_days": data_days
        }
