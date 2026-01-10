"""Check symbols in universe and compare with test portfolios."""
import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal

# Test portfolio symbols
PORTFOLIO_1_SYMBOLS = [
    "SPY", "QQQ", "XLV", "IBB",  # Likely in
    "EXAS", "HZNP", "SGEN", "ALNY", "SRPT", "BMRN", "NBIX", "INCY",
    "UTHR", "EXEL", "IONS", "RARE", "FOLD", "ARWR", "NTRA", "HALO"
]

PORTFOLIO_2_SYMBOLS = [
    "EFA", "VWO", "BABA", "TSM",  # Likely in
    "SE", "MELI", "GRAB", "CPNG", "BIDU", "JD", "PDD", "BILI",
    "NIO", "XPEV", "LI", "VNET", "TME", "ATHM", "YUMC", "HTHT"
]

PORTFOLIO_3_SYMBOLS = [
    "IWM", "VB", "ARKK", "XBI",  # Likely in
    "UPST", "AFRM", "SOFI", "HOOD", "COIN", "RBLX", "U", "PATH",
    "DDOG", "NET", "ZS", "CRWD", "OKTA", "MDB", "SNOW", "PLTR"
]

ALL_TEST_SYMBOLS = set(PORTFOLIO_1_SYMBOLS + PORTFOLIO_2_SYMBOLS + PORTFOLIO_3_SYMBOLS)


async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text('SELECT symbol FROM symbol_universe ORDER BY symbol'))
        universe = set(row[0] for row in result.fetchall())

        print(f"Total symbols in universe: {len(universe)}")
        print(f"Total test symbols: {len(ALL_TEST_SYMBOLS)}")
        print()

        in_universe = ALL_TEST_SYMBOLS & universe
        not_in_universe = ALL_TEST_SYMBOLS - universe

        print(f"Test symbols IN universe ({len(in_universe)}):")
        print(f"  {sorted(in_universe)}")
        print()
        print(f"Test symbols NOT in universe ({len(not_in_universe)}):")
        print(f"  {sorted(not_in_universe)}")
        print()

        # Per portfolio breakdown
        for name, symbols in [("Alpha", PORTFOLIO_1_SYMBOLS),
                               ("Beta", PORTFOLIO_2_SYMBOLS),
                               ("Gamma", PORTFOLIO_3_SYMBOLS)]:
            in_u = set(symbols) & universe
            not_in = set(symbols) - universe
            print(f"Portfolio {name}: {len(in_u)} in universe, {len(not_in)} NOT in universe")
            print(f"  NOT in: {sorted(not_in)}")


if __name__ == "__main__":
    asyncio.run(check())
