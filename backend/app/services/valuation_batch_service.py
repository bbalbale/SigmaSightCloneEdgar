"""
Valuation Batch Service - Efficient batch fetching of daily valuation metrics

This service uses yahooquery's batch capabilities to fetch valuation metrics
for many symbols at once, instead of individual API calls per symbol.

Performance:
- 50 symbols = ~10 seconds (batch mode)
- 1250 symbols = ~5 minutes (vs 30+ minutes with individual calls)

Metrics fetched (Tier 1 - Daily):
- pe_ratio (trailing P/E)
- forward_pe
- beta
- week_52_high / week_52_low
- market_cap
- dividend_yield

Usage:
    from app.services.valuation_batch_service import valuation_batch_service

    # Fetch for all symbols
    results = await valuation_batch_service.fetch_daily_valuations(symbols)

    # Update database
    updated = await valuation_batch_service.update_company_profiles(db, results)
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any, Optional
from yahooquery import Ticker

from app.core.logging import get_logger

logger = get_logger(__name__)

# Batch size for yahooquery (balance between speed and reliability)
BATCH_SIZE = 100


class ValuationBatchService:
    """
    Batch fetcher for daily valuation metrics using yahooquery.

    Uses yahooquery's efficient batch API to fetch PE, beta, 52-week range,
    market cap, and dividend yield for many symbols at once.
    """

    async def fetch_daily_valuations(
        self,
        symbols: List[str],
        batch_size: int = BATCH_SIZE,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fetch daily valuation metrics for multiple symbols using batch mode.

        Args:
            symbols: List of stock symbols to fetch
            batch_size: Number of symbols per batch (default 100)

        Returns:
            Dict mapping symbol -> valuation metrics dict
            {
                'AAPL': {
                    'pe_ratio': Decimal('34.84'),
                    'forward_pe': Decimal('28.44'),
                    'beta': Decimal('1.09'),
                    'week_52_high': Decimal('288.62'),
                    'week_52_low': Decimal('169.21'),
                    'market_cap': Decimal('3845545787392'),
                    'dividend_yield': Decimal('0.004'),
                },
                ...
            }
        """
        import sys

        if not symbols:
            logger.warning("No symbols provided to fetch_daily_valuations")
            return {}

        total_batches = (len(symbols) + batch_size - 1) // batch_size
        print(f"[VALUATION] Starting batch fetch: {len(symbols)} symbols in {total_batches} batches")
        sys.stdout.flush()
        logger.info(f"Fetching daily valuations for {len(symbols)} symbols in batches of {batch_size}")

        all_results = {}

        # Process in batches to avoid overwhelming the API
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            batch_num = (i // batch_size) + 1

            print(f"[VALUATION] Batch {batch_num}/{total_batches}: fetching {len(batch)} symbols...")
            sys.stdout.flush()

            # Run in thread pool to avoid blocking async event loop
            loop = asyncio.get_event_loop()
            batch_results = await loop.run_in_executor(
                None,
                self._fetch_batch_sync,
                batch,
            )

            all_results.update(batch_results)

            # Progress update
            print(f"[VALUATION] Batch {batch_num}/{total_batches}: got {len(batch_results)} results (total: {len(all_results)})")
            sys.stdout.flush()

            # Small delay between batches to avoid rate limiting
            if i + batch_size < len(symbols):
                await asyncio.sleep(0.5)

        success_count = len(all_results)
        print(f"[VALUATION] Complete: {success_count}/{len(symbols)} symbols successful")
        sys.stdout.flush()
        logger.info(f"Valuation fetch complete: {success_count}/{len(symbols)} symbols successful")

        return all_results

    def _fetch_batch_sync(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Synchronous batch fetch (runs in thread pool).

        Uses yahooquery's summary_detail which contains ALL needed metrics:
        - trailingPE, forwardPE, beta
        - fiftyTwoWeekHigh, fiftyTwoWeekLow
        - marketCap, dividendYield

        Optimized: Single API call instead of 3 (was: summary_detail + key_stats + price)
        """
        results = {}

        try:
            ticker = Ticker(symbols, asynchronous=False)

            # Single API call - summary_detail has everything we need
            summary_detail = ticker.summary_detail

            for symbol in symbols:
                try:
                    sd = summary_detail.get(symbol, {}) if isinstance(summary_detail, dict) else {}

                    # Skip if we got error response
                    if isinstance(sd, str):
                        logger.debug(f"{symbol}: skipped (error response)")
                        continue

                    # Extract valuation metrics - all from summary_detail
                    metrics = {
                        'pe_ratio': self._safe_decimal(sd.get('trailingPE')),
                        'forward_pe': self._safe_decimal(sd.get('forwardPE')),
                        'beta': self._safe_decimal(sd.get('beta')),
                        'week_52_high': self._safe_decimal(sd.get('fiftyTwoWeekHigh')),
                        'week_52_low': self._safe_decimal(sd.get('fiftyTwoWeekLow')),
                        'market_cap': self._safe_decimal(sd.get('marketCap')),
                        'dividend_yield': self._safe_decimal(sd.get('dividendYield')),
                    }

                    # Only include if we got at least some data
                    if any(v is not None for v in metrics.values()):
                        results[symbol] = metrics

                except Exception as e:
                    logger.debug(f"{symbol}: error extracting metrics - {e}")
                    continue

        except Exception as e:
            logger.error(f"Batch valuation fetch failed: {e}")

        return results

    async def update_company_profiles(
        self,
        db,  # AsyncSession
        valuations: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Update company_profiles table with daily valuation metrics.

        Only updates the Tier 1 (daily) fields:
        - pe_ratio, forward_pe, beta
        - week_52_high, week_52_low
        - market_cap, dividend_yield

        Args:
            db: Database session
            valuations: Dict from fetch_daily_valuations()

        Returns:
            Dict with update results
        """
        import sys
        from sqlalchemy import select
        from app.models.market_data import CompanyProfile

        if not valuations:
            return {"updated": 0, "created": 0, "failed": 0}

        updated = 0
        created = 0
        failed = 0
        total = len(valuations)
        processed = 0

        print(f"[VALUATION] Updating {total} company profiles in database...")
        sys.stdout.flush()

        for symbol, metrics in valuations.items():
            processed += 1
            try:
                # Check if profile exists
                result = await db.execute(
                    select(CompanyProfile).where(CompanyProfile.symbol == symbol)
                )
                profile = result.scalar_one_or_none()

                if profile:
                    # Update existing profile's valuation fields only
                    if metrics.get('pe_ratio') is not None:
                        profile.pe_ratio = metrics['pe_ratio']
                    if metrics.get('forward_pe') is not None:
                        profile.forward_pe = metrics['forward_pe']
                    if metrics.get('beta') is not None:
                        profile.beta = metrics['beta']
                    if metrics.get('week_52_high') is not None:
                        profile.week_52_high = metrics['week_52_high']
                    if metrics.get('week_52_low') is not None:
                        profile.week_52_low = metrics['week_52_low']
                    if metrics.get('market_cap') is not None:
                        profile.market_cap = metrics['market_cap']
                    if metrics.get('dividend_yield') is not None:
                        profile.dividend_yield = metrics['dividend_yield']
                    profile.updated_at = datetime.utcnow()
                    updated += 1
                else:
                    # Create new profile with valuation fields only
                    # Other fields (sector, industry, etc.) will be NULL
                    # and populated later by full profile sync
                    new_profile = CompanyProfile(
                        symbol=symbol,
                        pe_ratio=metrics.get('pe_ratio'),
                        forward_pe=metrics.get('forward_pe'),
                        beta=metrics.get('beta'),
                        week_52_high=metrics.get('week_52_high'),
                        week_52_low=metrics.get('week_52_low'),
                        market_cap=metrics.get('market_cap'),
                        dividend_yield=metrics.get('dividend_yield'),
                    )
                    db.add(new_profile)
                    created += 1

            except Exception as e:
                logger.warning(f"Failed to update profile for {symbol}: {e}")
                failed += 1

            # Progress logging every 200 symbols
            if processed % 200 == 0:
                print(f"[VALUATION] DB update progress: {processed}/{total} ({updated} updated, {created} created)")
                sys.stdout.flush()

        try:
            await db.commit()
            print(f"[VALUATION] DB commit successful: {updated} updated, {created} created, {failed} failed")
            sys.stdout.flush()
        except Exception as e:
            logger.error(f"Failed to commit profile updates: {e}")
            await db.rollback()
            print(f"[VALUATION] DB commit FAILED: {e}")
            sys.stdout.flush()
            return {"updated": 0, "created": 0, "failed": len(valuations), "error": str(e)}

        logger.info(f"Profile updates: {updated} updated, {created} created, {failed} failed")

        return {
            "updated": updated,
            "created": created,
            "failed": failed,
            "total_processed": updated + created,
        }

    def _safe_decimal(self, value: Any) -> Optional[Decimal]:
        """Safely convert to Decimal."""
        if value is None or value == '' or (isinstance(value, float) and value != value):  # NaN check
            return None
        try:
            dec_value = Decimal(str(value))
            return dec_value
        except (ValueError, TypeError, Exception):
            return None


# Global instance
valuation_batch_service = ValuationBatchService()
