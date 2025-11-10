"""
Position-to-position correlation analysis service
"""

import logging
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import List, Dict, Optional, Tuple, Set
from uuid import UUID
from collections import defaultdict
import numpy as np
import pandas as pd
from scipy import stats
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Portfolio, Position, MarketDataCache,
    CorrelationCalculation, CorrelationCluster,
    CorrelationClusterPosition, PairwiseCorrelation
)
from sqlalchemy import delete
from app.models.snapshots import PortfolioSnapshot
from app.models.tags_v2 import TagV2
from app.models import PositionTag
from app.schemas.correlations import (
    PositionFilterConfig, CorrelationCalculationCreate,
    PairwiseCorrelationCreate
)
from app.calculations.market_data import get_position_valuation
from app.services.market_data_service import MarketDataService

logger = logging.getLogger(__name__)


class CorrelationService:
    """Service for calculating position-to-position correlations"""

    def __init__(self, db: AsyncSession, price_cache=None):
        self.db = db
        self.market_data_service = MarketDataService()
        self.price_cache = price_cache  # PriceCache for optimized price lookups

    async def _get_portfolio_value_from_snapshot(
        self,
        portfolio_id: UUID,
        calculation_date: date,
        max_staleness_days: int = 3
    ) -> Optional[Decimal]:
        """
        Get portfolio gross exposure (total value) from snapshot.

        Priority:
        1. Use latest snapshot if recent (within max_staleness_days)
        2. Return None if no suitable snapshot found

        Returns:
            Portfolio gross exposure (total value) as Decimal or None if unavailable
        """
        # Try to get latest snapshot
        snapshot_stmt = (
            select(PortfolioSnapshot)
            .where(
                and_(
                    PortfolioSnapshot.portfolio_id == portfolio_id,
                    PortfolioSnapshot.snapshot_date <= calculation_date
                )
            )
            .order_by(PortfolioSnapshot.snapshot_date.desc())
            .limit(1)
        )

        snapshot_result = await self.db.execute(snapshot_stmt)
        latest_snapshot = snapshot_result.scalar_one_or_none()

        # Check if snapshot is recent enough
        if latest_snapshot:
            staleness = (calculation_date - latest_snapshot.snapshot_date).days
            if staleness <= max_staleness_days:
                logger.info(
                    f"Using snapshot gross_exposure from {latest_snapshot.snapshot_date} "
                    f"({staleness} days old): ${float(latest_snapshot.gross_exposure):,.0f}"
                )
                return Decimal(str(latest_snapshot.gross_exposure))
            else:
                logger.warning(
                    f"Latest snapshot is too stale ({staleness} days old), "
                    f"falling back to real-time calculation"
                )
        else:
            logger.warning("No snapshot found, falling back to real-time calculation")

        return None

    async def _cleanup_old_calculations(
        self,
        portfolio_id: UUID,
        duration_days: int,
        calculation_date: date
    ) -> int:
        """
        Clean up old correlation calculations for a specific portfolio, duration, and date.

        Deletes existing calculation for (portfolio_id, duration_days, calculation_date) to ensure
        new calculation replaces old one for the same date. This prevents data loss when
        running batch calculations for multiple dates.

        Deletes in proper order respecting foreign key constraints:
        1. correlation_cluster_positions
        2. correlation_clusters
        3. pairwise_correlations
        4. correlation_calculations

        Args:
            portfolio_id: Portfolio to clean up
            duration_days: Duration period to clean up (e.g., 90 for 90-day correlations)
            calculation_date: Specific calculation date to clean up

        Returns:
            Number of calculations deleted
        """
        # Find calculations for this portfolio, duration, AND date to delete
        # CRITICAL: Must filter by date to prevent deleting other dates' data
        stmt = (
            select(CorrelationCalculation.id)
            .where(
                and_(
                    CorrelationCalculation.portfolio_id == portfolio_id,
                    CorrelationCalculation.duration_days == duration_days,
                    func.date(CorrelationCalculation.calculation_date) == calculation_date
                )
            )
        )

        result = await self.db.execute(stmt)
        old_calculation_ids = [row[0] for row in result.all()]

        if not old_calculation_ids:
            return 0

        logger.info(
            f"Cleaning up {len(old_calculation_ids)} old correlation calculation(s) "
            f"for portfolio {portfolio_id} with {duration_days}-day duration "
            f"(will be replaced by new calculation)"
        )

        deleted_count = 0
        for calc_id in old_calculation_ids:
            # Get clusters for this calculation
            cluster_stmt = select(CorrelationCluster).where(
                CorrelationCluster.correlation_calculation_id == calc_id
            )
            cluster_result = await self.db.execute(cluster_stmt)
            clusters = cluster_result.scalars().all()

            # Delete cluster positions first (innermost foreign key)
            for cluster in clusters:
                delete_positions_stmt = delete(CorrelationClusterPosition).where(
                    CorrelationClusterPosition.cluster_id == cluster.id
                )
                await self.db.execute(delete_positions_stmt)

            # Delete clusters
            delete_clusters_stmt = delete(CorrelationCluster).where(
                CorrelationCluster.correlation_calculation_id == calc_id
            )
            await self.db.execute(delete_clusters_stmt)

            # Delete pairwise correlations
            delete_pairs_stmt = delete(PairwiseCorrelation).where(
                PairwiseCorrelation.correlation_calculation_id == calc_id
            )
            await self.db.execute(delete_pairs_stmt)

            # Delete calculation
            delete_calc_stmt = delete(CorrelationCalculation).where(
                CorrelationCalculation.id == calc_id
            )
            await self.db.execute(delete_calc_stmt)

            deleted_count += 1

        await self.db.flush()
        logger.info(f"[OK] Cleaned up {deleted_count} old correlation calculations")

        return deleted_count

    async def calculate_portfolio_correlations(
        self,
        portfolio_id: UUID,
        calculation_date: date,
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

            # Clean up old calculations before creating new one
            # Delete only calculations for this specific date to preserve other dates' data
            # This ensures we can maintain historical calculations for multiple dates
            await self._cleanup_old_calculations(portfolio_id, duration_days, calculation_date)
            
            # Get portfolio with positions
            portfolio = await self._get_portfolio_with_positions(portfolio_id)
            if not portfolio:
                raise ValueError(f"Portfolio {portfolio_id} not found")

            # Get portfolio total value from snapshot (preferred) or calculate
            portfolio_value = await self._get_portfolio_value_from_snapshot(
                portfolio_id, calculation_date
            )

            if portfolio_value is None:
                # Fallback: Calculate from positions if snapshot unavailable
                logger.warning(
                    "Calculating portfolio value from positions (snapshot unavailable). "
                    "This duplicates work already done by portfolio aggregation."
                )
                portfolio_value = sum(
                    get_position_valuation(p).abs_market_value
                    for p in portfolio.positions
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
                # Note: No rollback needed - no changes were made, let caller manage transaction
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
                # Note: No rollback needed - no changes were made, let caller manage transaction
                return None  # Option B: Skip persistence, return None
            
            # Calculate pairwise correlations with adaptive minimum overlap requirement
            # Require at least 1/3 of lookback period, minimum 20 days for statistical reliability
            min_overlap = max(20, duration_days // 3)
            correlation_matrix = self.calculate_pairwise_correlations(returns_df, min_periods=min_overlap)

            # Validate and fix PSD property (Positive Semi-Definite matrix required for correlation)
            correlation_matrix, psd_corrected = self._validate_and_fix_psd(correlation_matrix)

            # SKIP CLUSTER DETECTION - Not used by frontend, causes hang bug on 3rd consecutive day
            # The cluster/nickname generation was querying market data in a way that hung after 2-3 days
            # Pairwise correlations are sufficient for the correlation matrix display
            clusters = []

            # Calculate portfolio-level metrics (without clusters)
            metrics = self.calculate_portfolio_metrics(
                correlation_matrix,
                filtered_positions,
                clusters  # Empty list
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

            # SKIP STORING CLUSTERS - Not used by frontend/API
            # Removed to eliminate hang bug in cluster nickname generation
            # (was querying market data for sector info in a loop that hung on 3rd day)

            # Log comprehensive data quality metrics before commit
            total_pairs = len(correlation_matrix) * len(correlation_matrix)
            valid_pairs = (~correlation_matrix.isna()).sum().sum()
            filtered_pairs = correlation_matrix.isna().sum().sum()

            logger.info(
                f"Correlation calculation data quality for portfolio {portfolio_id}:\n"
                f"  - Duration: {duration_days} days\n"
                f"  - Positions included: {len(valid_positions)}\n"
                f"  - Positions excluded: {excluded_count + (len(filtered_positions) - len(valid_positions))}\n"
                f"  - Min overlap required: {min_overlap} days\n"
                f"  - Total correlation pairs: {total_pairs}\n"
                f"  - Valid pairs (sufficient data): {valid_pairs}\n"
                f"  - Filtered pairs (insufficient overlap): {filtered_pairs}\n"
                f"  - PSD validation: {'CORRECTED' if psd_corrected else 'PASSED'}\n"
                f"  - Overall correlation: {metrics['overall_correlation']:.4f}\n"
                f"  - Effective positions: {metrics['effective_positions']:.2f}\n"
                f"  - Cluster detection: SKIPPED (not used by frontend, was causing hang bug)"
            )

            # Note: Do NOT commit here - let caller manage transaction boundaries
            # Committing expires session objects and causes greenlet errors
            logger.debug(f"Staged correlations for portfolio {portfolio_id} (will be committed by caller)")

            logger.info(
                f"Completed correlation calculation for portfolio {portfolio_id}: "
                f"overall_correlation={metrics['overall_correlation']:.4f}, "
                f"pairwise_correlations={total_pairs}"
            )

            return calculation

        except Exception as e:
            logger.error(f"Error calculating correlations for portfolio {portfolio_id}: {e}")
            # Note: Do NOT rollback here - let caller manage transaction
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
            valuation = get_position_valuation(position)
            if valuation.price is None:
                logger.warning(
                    f"Position {position.symbol} has no price data (last_price and entry_price both None). "
                    f"Excluding from correlation analysis."
                )
                continue

            position_value = valuation.abs_market_value
            position_weight = (
                position_value / portfolio_value if portfolio_value > 0 else Decimal("0")
            )
            
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
    
    def calculate_pairwise_correlations(
        self,
        returns_df: pd.DataFrame,
        min_periods: int = 30
    ) -> pd.DataFrame:
        """
        Calculate full pairwise correlation matrix using log returns with minimum overlap requirement.

        Args:
            returns_df: DataFrame with dates as index and symbols as columns
            min_periods: Minimum number of overlapping observations required (default: 30)

        Returns:
            Correlation matrix with NaN for pairs with insufficient overlap.
            Full matrix including self-correlations and both directions.
        """
        # Calculate correlation matrix using pandas with minimum period requirement
        correlation_matrix = returns_df.corr(method='pearson', min_periods=min_periods)

        # Ensure we have both directions and self-correlations
        # (pandas corr() already returns a symmetric matrix with diagonal = 1)

        # Log any pairs filtered out due to insufficient data
        nan_count = correlation_matrix.isna().sum().sum()
        total_pairs = len(correlation_matrix) * len(correlation_matrix)
        if nan_count > 0:
            logger.info(
                f"Filtered {nan_count}/{total_pairs} correlation pairs due to insufficient overlap "
                f"(min_periods={min_periods})"
            )

        return correlation_matrix

    def _validate_and_fix_psd(
        self,
        correlation_matrix: pd.DataFrame
    ) -> tuple[pd.DataFrame, bool]:
        """
        Validate that correlation matrix is Positive Semi-Definite (PSD).
        If not PSD, log warning and apply nearest PSD correction.

        A correlation matrix must be PSD (all eigenvalues >= 0) to be mathematically valid.
        Non-PSD matrices can occur due to:
        - Numerical precision issues
        - Insufficient or inconsistent data
        - Pairwise deletion with different date ranges per pair

        Args:
            correlation_matrix: Correlation matrix to validate

        Returns:
            Tuple of (corrected_matrix, was_corrected_flag)
        """
        # Handle empty or all-NaN matrices
        if correlation_matrix.empty or correlation_matrix.isna().all().all():
            logger.warning("Empty or all-NaN correlation matrix, skipping PSD validation")
            return correlation_matrix, False

        # Check for PSD property (all eigenvalues >= 0)
        try:
            eigenvalues = np.linalg.eigvalsh(correlation_matrix.values)
            min_eigenvalue = np.min(eigenvalues)
        except np.linalg.LinAlgError as e:
            logger.error(f"Failed to compute eigenvalues for PSD validation: {e}")
            return correlation_matrix, False

        # Tolerance for numerical precision (-1e-10 allows for floating point errors)
        if min_eigenvalue < -1e-10:
            logger.warning(
                f"Non-PSD correlation matrix detected. "
                f"Min eigenvalue: {min_eigenvalue:.6f}. "
                f"This indicates numerical issues or insufficient data. "
                f"Applying nearest PSD correction..."
            )

            # Apply nearest PSD correction using eigenvalue clipping
            # This is a simplified version of Higham's algorithm
            eigenvalues_clipped = np.maximum(eigenvalues, 0)

            # Reconstruct matrix from corrected eigenvalues
            eigenvectors = np.linalg.eigh(correlation_matrix.values)[1]
            corrected_matrix = eigenvectors @ np.diag(eigenvalues_clipped) @ eigenvectors.T

            # Rescale to ensure diagonal = 1.0 (required for correlation matrix)
            d = np.sqrt(np.diag(corrected_matrix))
            # Avoid division by zero
            d = np.where(d == 0, 1, d)
            corrected_matrix = corrected_matrix / d[:, None] / d[None, :]

            # Convert back to DataFrame with original index/columns
            corrected_df = pd.DataFrame(
                corrected_matrix,
                index=correlation_matrix.index,
                columns=correlation_matrix.columns
            )

            logger.info(
                f"PSD correction applied. "
                f"New min eigenvalue: {np.min(np.linalg.eigvalsh(corrected_df.values)):.6f}"
            )

            return corrected_df, True

        # Matrix is already PSD
        return correlation_matrix, False

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
        logger.debug(f"[SEARCH] Detecting correlation clusters (threshold: {threshold})")
        symbols = list(correlation_matrix.columns)
        n = len(symbols)
        logger.debug(f"  Correlation matrix: {n} symbols")

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
        logger.debug(f"  Finding connected components via DFS...")
        for i in range(n):
            if not visited[i]:
                cluster_indices = []
                dfs(i, cluster_indices)

                # Only consider clusters with 2+ positions
                if len(cluster_indices) >= 2:
                    cluster_symbols = [symbols[idx] for idx in cluster_indices]
                    logger.debug(f"  Found cluster with {len(cluster_symbols)} symbols: {cluster_symbols[:3]}...")

                    # Calculate average correlation within cluster
                    cluster_corr_values = []
                    for j, idx1 in enumerate(cluster_indices):
                        for idx2 in cluster_indices[j+1:]:
                            cluster_corr_values.append(
                                correlation_matrix.iloc[idx1, idx2]
                            )

                    avg_correlation = np.mean(cluster_corr_values) if cluster_corr_values else 0
                    logger.debug(f"    Avg correlation: {avg_correlation:.4f}")

                    # Generate cluster nickname
                    logger.debug(f"    Generating nickname...")
                    nickname = await self.generate_cluster_nickname(
                        cluster_symbols, positions
                    )
                    logger.debug(f"    [OK] Nickname generated: {nickname}")
                    
                    clusters.append({
                        "symbols": cluster_symbols,
                        "indices": cluster_indices,
                        "avg_correlation": Decimal(str(avg_correlation)),
                        "nickname": nickname
                    })
                    logger.debug(f"    Cluster added to results")

        # Sort clusters by size (descending)
        clusters.sort(key=lambda x: len(x["symbols"]), reverse=True)

        logger.debug(f"[OK] Detected {len(clusters)} clusters total")
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
        logger.debug(f"[SEARCH] Generating nickname for cluster: {cluster_symbols[:3]}... ({len(cluster_symbols)} symbols)")

        # Create symbol to position mapping
        symbol_to_position = {p.symbol: p for p in positions}
        cluster_positions = [
            symbol_to_position[s] for s in cluster_symbols
            if s in symbol_to_position
        ]

        logger.debug(f"  Mapped {len(cluster_positions)} positions from {len(cluster_symbols)} symbols")

        # 1. Check for common tags (position-level tagging system)
        if cluster_positions:
            logger.debug(f"  Step 1: Checking common tags for {len(cluster_positions)} positions")
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
                logger.debug(f"  Found {len(tags)} tags")

                tag_counts = defaultdict(int)
                for tag in tags:
                    tag_counts[tag.name] += 1

                if tag_counts:
                    most_common_tag = max(tag_counts, key=tag_counts.get)
                    if tag_counts[most_common_tag] >= len(cluster_positions) * 0.7:
                        logger.debug(f"  [OK] Using tag nickname: {most_common_tag}")
                        return most_common_tag

            logger.debug(f"  No common tags found (threshold: 70%)")
        
        # 2. Check for common sector
        logger.debug(f"  Step 2: Checking common sectors for {len(cluster_symbols)} symbols")
        sectors = []
        for i, symbol in enumerate(cluster_symbols):
            logger.debug(f"    Querying sector for symbol {i+1}/{len(cluster_symbols)}: {symbol}")
            # Query market data cache for sector info
            query = select(MarketDataCache).where(
                MarketDataCache.symbol == symbol
            ).order_by(MarketDataCache.date.desc()).limit(1)

            result = await self.db.execute(query)
            market_data = result.scalar_one_or_none()

            if market_data and market_data.sector:
                sectors.append(market_data.sector)
                logger.debug(f"      Found sector: {market_data.sector}")
            else:
                logger.debug(f"      No sector data")
        
        logger.debug(f"  Collected {len(sectors)} sector values from {len(cluster_symbols)} symbols")

        if sectors:
            # Find most common sector
            sector_counts = defaultdict(int)
            for sector in sectors:
                sector_counts[sector] += 1

            most_common_sector = max(sector_counts, key=sector_counts.get)
            logger.debug(f"  Most common sector: {most_common_sector} ({sector_counts[most_common_sector]}/{len(cluster_symbols)} = {sector_counts[most_common_sector]/len(cluster_symbols)*100:.1f}%)")

            if sector_counts[most_common_sector] >= len(cluster_symbols) * 0.7:  # 70% threshold
                logger.debug(f"  [OK] Using sector nickname: {most_common_sector}")
                return most_common_sector

        logger.debug(f"  No common sector found (threshold: 70%)")
        
        # 3. Use largest position + "lookalikes"
        logger.debug(f"  Step 3: Using largest position fallback")
        if cluster_positions:
            # Find largest position by value (with fallback to entry_price)
            largest_position = max(
                cluster_positions,
                key=lambda p: get_position_valuation(p).abs_market_value
            )
            nickname = f"{largest_position.symbol} lookalikes"
            logger.debug(f"  [OK] Using largest position nickname: {nickname}")
            return nickname

        # Fallback
        nickname = f"Cluster {cluster_symbols[0]}"
        logger.debug(f"  [OK] Using fallback nickname: {nickname}")
        return nickname
    
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
            valuation = get_position_valuation(position)
            if valuation.price is None:
                continue  # Skip positions with no price data

            position_value = valuation.abs_market_value
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
        calculation_date: date
    ) -> Optional[CorrelationCalculation]:
        """Check for existing calculation"""
        query = select(CorrelationCalculation).where(
            and_(
                CorrelationCalculation.portfolio_id == portfolio_id,
                CorrelationCalculation.duration_days == duration_days,
                func.date(CorrelationCalculation.calculation_date) == calculation_date
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
        Get daily log returns for positions, aligned to common trading dates

        IMPORTANT: Returns are calculated AFTER date alignment to ensure all returns
        are single-day returns over the same time periods. This prevents misaligned
        correlation calculations (e.g., correlating 2-day returns with 1-day returns).

        Returns DataFrame with dates as index and symbols as columns
        """
        price_data: Dict[str, pd.Series] = {}

        # Normalize date bounds to plain dates to match MarketDataCache schema
        start_bound = start_date.date() if isinstance(start_date, datetime) else start_date
        end_bound = end_date.date() if isinstance(end_date, datetime) else end_date

        # Build unique list of symbols (preserve case) for a single batched query
        symbols = [p.symbol for p in positions if p.symbol]
        seen: Set[str] = set()
        ordered_symbols: List[str] = []
        for symbol in symbols:
            if symbol not in seen:
                ordered_symbols.append(symbol)
                seen.add(symbol)

        if not ordered_symbols:
            return pd.DataFrame()

        # Step 1: Fetch all price data - use cache if available for HUGE speedup
        rows = []

        if self.price_cache:
            # OPTIMIZATION: Use preloaded price cache instead of database query
            logger.info(f"CACHE: Loading {len(ordered_symbols)} symbols from cache for date range {start_bound} to {end_bound}")
            cache_hits = 0
            cache_misses = 0

            # Generate all dates in range (approximation - includes weekends but cache will miss those)
            current_date = start_bound
            date_list = []
            while current_date <= end_bound:
                date_list.append(current_date)
                current_date += timedelta(days=1)

            # Try to get all prices from cache
            for symbol in ordered_symbols:
                for check_date in date_list:
                    price = self.price_cache.get_price(symbol, check_date)
                    if price is not None:
                        rows.append({'symbol': symbol, 'date': check_date, 'close': price})
                        cache_hits += 1
                    else:
                        cache_misses += 1

            logger.info(f"CACHE STATS: {cache_hits} hits, {cache_misses} misses (hit rate: {cache_hits/(cache_hits+cache_misses)*100:.1f}%)")

        if not rows:
            # Fallback to database query if cache not available or empty
            logger.info("Using database query for historical prices (no cache or cache empty)")
            price_query = (
                select(
                    MarketDataCache.symbol,
                    MarketDataCache.date,
                    MarketDataCache.close
                )
                .where(
                    and_(
                        MarketDataCache.symbol.in_(ordered_symbols),
                        MarketDataCache.date >= start_bound,
                        MarketDataCache.date <= end_bound
                    )
                )
                .order_by(MarketDataCache.symbol, MarketDataCache.date)
            )

            price_result = await self.db.execute(price_query)
            rows = price_result.mappings().all()

        if not rows:
            logger.warning(
                "No historical price data found for correlation calculation after batched query"
            )
            return pd.DataFrame()

        symbol_to_rows: Dict[str, List[Tuple[date, float]]] = defaultdict(list)
        for row in rows:
            close_value = row["close"]
            if close_value is None:
                continue
            symbol_to_rows[row["symbol"]].append((row["date"], float(close_value)))

        logger.info(
            "Loaded %s price records across %s symbols for correlation returns calculation",
            len(rows),
            len(symbol_to_rows),
        )

        for symbol, symbol_rows in symbol_to_rows.items():
            if len(symbol_rows) < 2:
                continue

            symbol_rows.sort(key=lambda item: item[0])
            dates = [record_date for record_date, _ in symbol_rows]
            prices = [price for _, price in symbol_rows]

            price_series = pd.Series(prices, index=pd.DatetimeIndex(dates))

            duplicates_count = price_series.index.duplicated().sum()
            if duplicates_count > 0:
                logger.warning(
                    f"Position {symbol}: {duplicates_count} duplicate dates found. Keeping last value for each date."
                )
                price_series = price_series[~price_series.index.duplicated(keep='last')]

            invalid_prices = (price_series <= 0).sum()
            if invalid_prices > 0:
                logger.warning(
                    f"Position {symbol}: {invalid_prices} non-positive prices found. Removing these data points before return calculation."
                )
                price_series = price_series[price_series > 0]

            if len(price_series) >= 2:
                price_data[symbol] = price_series
            else:
                logger.warning(
                    f"Position {symbol}: Insufficient valid data after sanitization ({len(price_series)} points remaining, need 2+). Excluding from analysis."
                )

        if not price_data:
            return pd.DataFrame()

        # Step 2: Create price DataFrame with all positions
        price_df = pd.DataFrame(price_data)

        # Step 3: Drop dates where ANY position is missing (ensure alignment)
        # This ensures all returns are calculated over the same dates
        price_df_aligned = price_df.dropna()

        if price_df_aligned.empty:
            logger.warning("No overlapping dates found across all positions")
            return pd.DataFrame()

        logger.info(
            f"Aligned {len(price_df_aligned)} common trading dates "
            f"across {len(price_df_aligned.columns)} positions "
            f"(original: {len(price_df)} dates before alignment)"
        )

        # Step 4: Calculate log returns on aligned price DataFrame
        # Now .shift(1) operates on the same date sequence for all positions
        with np.errstate(divide='ignore', invalid='ignore'):
            returns_df = np.log(price_df_aligned / price_df_aligned.shift(1))

        # Handle infinite values from zero/negative prices
        inf_mask = np.isinf(returns_df)
        if inf_mask.any().any():
            inf_counts = inf_mask.sum()
            for symbol in inf_counts[inf_counts > 0].index:
                logger.warning(
                    f"Position {symbol}: {inf_counts[symbol]} infinite log returns "
                    f"(likely from zero/negative prices). Replacing with NaN."
                )
            returns_df = returns_df.replace([np.inf, -np.inf], np.nan)

        # Drop NaN values (first row after shift, and any infinite values)
        returns_df = returns_df.dropna()

        logger.info(
            f"Calculated {len(returns_df)} days of aligned returns "
            f"for {len(returns_df.columns)} positions"
        )

        return returns_df
    
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

                # Get paired observations (both symbols must have data)
                # CRITICAL: Use same observations for both data_points count and stats.pearsonr()
                paired_data = returns_df[[symbol1, symbol2]].dropna()
                data_points = len(paired_data)

                # Calculate statistical significance (p-value)
                if symbol1 != symbol2 and data_points >= 3:
                    # Use scipy stats for p-value calculation on SAME paired observations
                    _, p_value = stats.pearsonr(
                        paired_data[symbol1],  # ← Same observations as data_points
                        paired_data[symbol2]   # ← Same observations as data_points
                    )
                    statistical_significance = Decimal(str(1 - p_value))

                    # Log low-confidence correlations (p > 0.05 = less than 95% confidence)
                    if p_value > 0.05:
                        logger.debug(
                            f"Low-confidence correlation: {symbol1}-{symbol2} "
                            f"(r={correlation_value:.3f}, p={p_value:.3f}, n={data_points})"
                        )
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
        portfolio_value: Decimal,
        correlation_matrix: pd.DataFrame,
    ):
        """Store correlation clusters and their positions with precise correlation stats"""
        # Create position lookup
        symbol_to_position = {p.symbol: p for p in positions}
        
        for i, cluster_data in enumerate(clusters):
            # Calculate cluster totals
            cluster_value = Decimal("0")
            cluster_positions = []
            
            for symbol in cluster_data["symbols"]:
                if symbol in symbol_to_position:
                    position = symbol_to_position[symbol]
                    valuation = get_position_valuation(position)
                    if valuation.price is None:
                        continue  # Skip positions with no price data

                    position_value = valuation.abs_market_value
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
            cluster_position_records: List[CorrelationClusterPosition] = []
            for position, position_value in cluster_positions:
                # Calculate correlation to cluster (average correlation with other cluster members)
                correlation_values: List[Decimal] = []
                for other_symbol in cluster_data["symbols"]:
                    if other_symbol == position.symbol:
                        continue

                    if (
                        position.symbol in correlation_matrix.index
                        and other_symbol in correlation_matrix.columns
                    ):
                        correlation_values.append(
                            Decimal(
                                str(
                                    correlation_matrix.loc[
                                        position.symbol, other_symbol
                                    ]
                                )
                            )
                        )

                if correlation_values:
                    avg_correlation_to_cluster = sum(correlation_values) / Decimal(
                        len(correlation_values)
                    )
                else:
                    avg_correlation_to_cluster = cluster_data["avg_correlation"]

                cluster_position_records.append(
                    CorrelationClusterPosition(
                        cluster_id=cluster.id,
                        position_id=position.id,
                        symbol=position.symbol,
                        value=position_value,
                        portfolio_percentage=position_value / portfolio_value if portfolio_value > 0 else Decimal("0"),
                        correlation_to_cluster=avg_correlation_to_cluster,
                    )
                )      

            if cluster_position_records:
                self.db.add_all(cluster_position_records)

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
                valuation = get_position_valuation(pos)
                mv = float(valuation.abs_market_value)
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
                valuation = get_position_valuation(pos)
                if valuation.abs_market_value > 0:
                    symbol_weights[pos.symbol] = float(valuation.abs_market_value)
            
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
