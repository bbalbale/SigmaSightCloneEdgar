"""
V2 Symbol Cache with Cold Start Support

Provides fast access to symbol data with DB fallback:
- Prices from market_data_cache
- Factors from symbol_factor_exposures
- Company info from company_profiles

Cold Start Behavior:
- Cache initializes in background (doesn't block app startup)
- During initialization, falls back to DB queries
- After initialization, serves from in-memory cache (300x faster)

Health Check Support:
- /health/live: Always 200 (liveness probe)
- /health/ready: 503 until cache ready OR 30s timeout (readiness probe)

Reference: PlanningDocs/V2BatchArchitecture/06-PORTFOLIO-CACHE.md
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional, Any, Set, Tuple

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.datetime_utils import utc_now
from app.database import get_async_session
from app.cache.price_cache import PriceCache

logger = get_logger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

V2_LOG_PREFIX = "[V2_SYMBOL_CACHE]"

# Cold start configuration
MAX_COLD_START_WAIT_SECONDS = 30  # Max wait for readiness check
DEFAULT_CACHE_LOOKBACK_DAYS = 10  # Days of price history to cache


# =============================================================================
# SYMBOL CACHE SERVICE
# =============================================================================

class SymbolCacheService:
    """
    In-memory symbol cache with cold start support.

    Features:
    - Background initialization (non-blocking)
    - DB fallback during cold start
    - Price and factor caching
    - Health check support for Kubernetes/Railway probes
    """

    def __init__(self):
        # State tracking
        self._initialized = False
        self._initializing = False
        self._init_error: Optional[str] = None
        self._init_started_at: Optional[datetime] = None
        self._init_completed_at: Optional[datetime] = None

        # Underlying caches
        self._price_cache = PriceCache()
        self._factor_cache: Dict[Tuple[str, date], Dict[str, float]] = {}
        self._symbols_loaded: Set[str] = set()
        self._dates_loaded: Set[date] = set()

        # Stats
        self._db_fallback_count = 0
        self._cache_hit_count = 0

    # =========================================================================
    # INITIALIZATION
    # =========================================================================

    async def initialize_async(self, target_date: Optional[date] = None):
        """
        Initialize cache in background (non-blocking).

        Call this from app lifespan event.
        """
        if self._initialized or self._initializing:
            return

        self._initializing = True
        self._init_started_at = utc_now()

        logger.info(f"{V2_LOG_PREFIX} Starting background initialization...")

        try:
            from app.core.trading_calendar import get_most_recent_trading_day

            if target_date is None:
                target_date = get_most_recent_trading_day()

            # Load price data
            await self._load_prices(target_date)

            # Load factor data
            await self._load_factors(target_date)

            self._initialized = True
            self._init_completed_at = utc_now()

            init_duration = (self._init_completed_at - self._init_started_at).total_seconds()
            logger.info(
                f"{V2_LOG_PREFIX} Initialization complete in {init_duration:.1f}s: "
                f"{len(self._symbols_loaded)} symbols, {len(self._dates_loaded)} dates"
            )

        except Exception as e:
            logger.error(f"{V2_LOG_PREFIX} Initialization failed: {e}", exc_info=True)
            self._init_error = str(e)

        finally:
            self._initializing = False

    async def _load_prices(self, target_date: date):
        """Load prices from market_data_cache."""
        from app.models.market_data import MarketDataCache

        start_date = target_date - timedelta(days=DEFAULT_CACHE_LOOKBACK_DAYS)

        async with get_async_session() as db:
            result = await db.execute(
                select(MarketDataCache)
                .where(
                    and_(
                        MarketDataCache.date >= start_date,
                        MarketDataCache.date <= target_date,
                        MarketDataCache.close > 0,
                    )
                )
            )
            records = result.scalars().all()

            for record in records:
                self._price_cache.set_price(record.symbol, record.date, record.close)
                self._symbols_loaded.add(record.symbol)
                self._dates_loaded.add(record.date)

            logger.info(
                f"{V2_LOG_PREFIX} Loaded {len(records)} price records"
            )

    async def _load_factors(self, target_date: date):
        """Load factors from symbol_factor_exposures."""
        from app.models.symbol_analytics import SymbolFactorExposure
        from app.models.market_data import FactorDefinition

        async with get_async_session() as db:
            # Load factor definitions for name mapping
            factor_result = await db.execute(select(FactorDefinition))
            factors = factor_result.scalars().all()
            factor_id_to_name = {f.id: f.name for f in factors}

            # Load factor exposures for target date
            result = await db.execute(
                select(SymbolFactorExposure)
                .where(SymbolFactorExposure.calculation_date == target_date)
            )
            exposures = result.scalars().all()

            # Build cache
            for exp in exposures:
                cache_key = (exp.symbol, exp.calculation_date)
                if cache_key not in self._factor_cache:
                    self._factor_cache[cache_key] = {}

                factor_name = factor_id_to_name.get(exp.factor_id, str(exp.factor_id))
                self._factor_cache[cache_key][factor_name] = float(exp.beta_value)

            logger.info(
                f"{V2_LOG_PREFIX} Loaded {len(exposures)} factor exposures for {len(self._factor_cache)} symbol-dates"
            )

    # =========================================================================
    # HEALTH CHECKS
    # =========================================================================

    def is_ready(self) -> bool:
        """
        Check if cache is ready for serving traffic.

        Returns True if:
        - Cache is fully initialized, OR
        - Cold start timeout has passed (30s)
        """
        if self._initialized:
            return True

        # Allow fallback to DB if cold start takes too long
        if self._init_started_at:
            elapsed = (utc_now() - self._init_started_at).total_seconds()
            if elapsed >= MAX_COLD_START_WAIT_SECONDS:
                logger.warning(
                    f"{V2_LOG_PREFIX} Cold start timeout ({MAX_COLD_START_WAIT_SECONDS}s), "
                    "allowing DB fallback mode"
                )
                return True

        return False

    def is_alive(self) -> bool:
        """
        Check if service is alive (liveness probe).

        Always returns True unless fatal error.
        """
        return True

    def get_health_status(self) -> Dict[str, Any]:
        """Get detailed health status."""
        return {
            "initialized": self._initialized,
            "initializing": self._initializing,
            "ready": self.is_ready(),
            "alive": self.is_alive(),
            "init_error": self._init_error,
            "init_started_at": self._init_started_at.isoformat() if self._init_started_at else None,
            "init_completed_at": self._init_completed_at.isoformat() if self._init_completed_at else None,
            "symbols_cached": len(self._symbols_loaded),
            "dates_cached": len(self._dates_loaded),
            "price_cache_stats": self._price_cache.get_stats(),
            "factor_cache_entries": len(self._factor_cache),
            "db_fallback_count": self._db_fallback_count,
            "cache_hit_count": self._cache_hit_count,
        }

    # =========================================================================
    # DATA ACCESS
    # =========================================================================

    async def get_latest_price(
        self,
        symbol: str,
        price_date: date,
        db: Optional[AsyncSession] = None,
    ) -> Optional[Decimal]:
        """
        Get price for symbol, with DB fallback.

        Args:
            symbol: Symbol to get price for
            price_date: Date to get price for
            db: Optional DB session for fallback

        Returns:
            Price as Decimal, or None if not found
        """
        # Try cache first
        price = self._price_cache.get_price(symbol, price_date)
        if price is not None:
            self._cache_hit_count += 1
            return price

        # Fallback to DB
        self._db_fallback_count += 1
        return await self._fetch_price_from_db(symbol, price_date, db)

    async def _fetch_price_from_db(
        self,
        symbol: str,
        price_date: date,
        db: Optional[AsyncSession] = None,
    ) -> Optional[Decimal]:
        """Fetch price from database."""
        from app.models.market_data import MarketDataCache

        # If db provided, use it directly (caller manages session)
        if db is not None:
            result = await db.execute(
                select(MarketDataCache.close)
                .where(
                    and_(
                        MarketDataCache.symbol == symbol,
                        MarketDataCache.date == price_date,
                        MarketDataCache.close > 0,
                    )
                )
            )
            price = result.scalar_one_or_none()

            # Cache the result (consistent with set_price - updates both sets)
            if price is not None:
                self._price_cache.set_price(symbol, price_date, price)
                self._symbols_loaded.add(symbol)
                self._dates_loaded.add(price_date)

            return price

        # No db provided - use proper async context manager (Railway-safe)
        async with get_async_session() as session:
            result = await session.execute(
                select(MarketDataCache.close)
                .where(
                    and_(
                        MarketDataCache.symbol == symbol,
                        MarketDataCache.date == price_date,
                        MarketDataCache.close > 0,
                    )
                )
            )
            price = result.scalar_one_or_none()

            # Cache the result (consistent with set_price - updates both sets)
            if price is not None:
                self._price_cache.set_price(symbol, price_date, price)
                self._symbols_loaded.add(symbol)
                self._dates_loaded.add(price_date)

            return price

    async def get_factors(
        self,
        symbol: str,
        calc_date: date,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, float]:
        """
        Get factor exposures for symbol, with DB fallback.

        Args:
            symbol: Symbol to get factors for
            calc_date: Calculation date
            db: Optional DB session for fallback

        Returns:
            Dict mapping factor names to beta values
        """
        cache_key = (symbol, calc_date)

        # Try cache first
        if cache_key in self._factor_cache:
            self._cache_hit_count += 1
            return self._factor_cache[cache_key]

        # Fallback to DB
        self._db_fallback_count += 1
        return await self._fetch_factors_from_db(symbol, calc_date, db)

    async def _fetch_factors_from_db(
        self,
        symbol: str,
        calc_date: date,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, float]:
        """Fetch factors from database."""
        from app.models.symbol_analytics import SymbolFactorExposure
        from app.models.market_data import FactorDefinition

        async def _do_fetch(session: AsyncSession) -> Dict[str, float]:
            """Inner function to fetch factors from a session."""
            # Load factor definitions for name mapping
            factor_result = await session.execute(select(FactorDefinition))
            factors = factor_result.scalars().all()
            factor_id_to_name = {f.id: f.name for f in factors}

            # Load factor exposures
            result = await session.execute(
                select(SymbolFactorExposure)
                .where(
                    and_(
                        SymbolFactorExposure.symbol == symbol,
                        SymbolFactorExposure.calculation_date == calc_date,
                    )
                )
            )
            exposures = result.scalars().all()

            # Build result
            factors_dict = {}
            for exp in exposures:
                factor_name = factor_id_to_name.get(exp.factor_id, str(exp.factor_id))
                factors_dict[factor_name] = float(exp.beta_value)

            # Cache the result
            cache_key = (symbol, calc_date)
            self._factor_cache[cache_key] = factors_dict

            return factors_dict

        # If db provided, use it directly (caller manages session)
        if db is not None:
            return await _do_fetch(db)

        # No db provided - use proper async context manager (Railway-safe)
        async with get_async_session() as session:
            return await _do_fetch(session)

    def set_price(self, symbol: str, price_date: date, price: Decimal):
        """Set price in cache (for manual updates)."""
        self._price_cache.set_price(symbol, price_date, price)
        self._symbols_loaded.add(symbol)
        self._dates_loaded.add(price_date)

    def clear(self):
        """Clear all cached data."""
        self._price_cache.clear()
        self._factor_cache.clear()
        self._symbols_loaded.clear()
        self._dates_loaded.clear()
        self._db_fallback_count = 0
        self._cache_hit_count = 0
        self._initialized = False
        logger.info(f"{V2_LOG_PREFIX} Cache cleared")


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

symbol_cache = SymbolCacheService()
