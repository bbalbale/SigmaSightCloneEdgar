import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock
from decimal import Decimal
from datetime import date
import pandas as pd
import numpy as np
from uuid import uuid4

from app.services.correlation_service import CorrelationService
from app.models import Portfolio, Position

class TestCorrelationCrash(unittest.IsolatedAsyncioTestCase):
    async def test_crash(self):
        db = AsyncMock()
        service = CorrelationService(db)

        # Mock portfolio with positions
        portfolio_id = uuid4()
        positions = [
            Position(id=uuid4(), symbol="A", quantity=Decimal("10"), last_price=Decimal("100"), investment_class="PUBLIC"),
            Position(id=uuid4(), symbol="B", quantity=Decimal("20"), last_price=Decimal("50"), investment_class="PUBLIC"),
        ]
        portfolio = Portfolio(id=portfolio_id, positions=positions)
        
        # Mock DB queries
        service._get_portfolio_with_positions = AsyncMock(return_value=portfolio)
        service._get_portfolio_value_from_snapshot = AsyncMock(return_value=Decimal("2000"))
        service._get_existing_calculation = AsyncMock(return_value=None)
        service._cleanup_old_calculations = AsyncMock(return_value=0)
        
        # Mock pairwise correlations to return None
        # returns_df is needed for other parts, but we override the matrix
        returns_df = pd.DataFrame({
            "A": [0.01, 0.02],
            "B": [0.01, 0.02]
        })
        service._get_position_returns = AsyncMock(return_value=returns_df)
        
        # Mock calculate_pairwise_correlations to return matrix with None
        # We need to use object dtype to hold None
        matrix = pd.DataFrame([[1.0, None], [None, 1.0]], index=["A", "B"], columns=["A", "B"], dtype=object)
        service.calculate_pairwise_correlations = MagicMock(return_value=matrix)
        
        # Mock validation to return matrix as is (or it will crash if it tries to use None)
        service._validate_and_fix_psd = MagicMock(return_value=(matrix, False))
        
        # Mock validation
        service._validate_data_sufficiency = MagicMock(return_value=["A", "B"])
        
        # Run calculation
        try:
            await service.calculate_portfolio_correlations(
                portfolio_id=portfolio_id,
                calculation_date=date.today()
            )
            print("Success!")
        except Exception as e:
            print(f"Caught exception: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    unittest.main()
