#!/usr/bin/env python
"""Minimal test of the target prices API logic"""

import asyncio
from app.database import AsyncSessionLocal, get_async_session
from app.services.target_price_service import TargetPriceService
from app.schemas.target_prices import TargetPriceResponse
from app.models.users import User, Portfolio
from app.api.v1.auth import get_current_user
from uuid import UUID
from sqlalchemy import select
import traceback

async def test_api_logic_step_by_step():
    """Test each step of the API endpoint logic"""
    
    portfolio_id = UUID('e23ab931-a033-edfe-ed4f-9d02474780b4')
    user_id = UUID('9dacfb0f-2123-7a94-debc-0f982b90d845')
    
    async with AsyncSessionLocal() as db:
        print("1. Testing portfolio ownership verification...")
        try:
            # Test _verify_portfolio_ownership logic
            result = await db.execute(
                select(Portfolio).where(Portfolio.id == portfolio_id)
            )
            portfolio = result.scalar_one_or_none()
            
            if not portfolio:
                print("   ❌ Portfolio not found")
                return
            else:
                print(f"   ✅ Portfolio found: {portfolio.name}")
                print(f"   📊 Portfolio user_id: {portfolio.user_id}")
                print(f"   📊 Request user_id: {user_id}")
                
                if portfolio.user_id != user_id:
                    print("   ❌ User does not own portfolio")
                    return
                else:
                    print("   ✅ Portfolio ownership verified")
        except Exception as e:
            print(f"   ❌ Portfolio verification failed: {e}")
            traceback.print_exc()
            return
            
        print("\n2. Testing target price service call...")
        try:
            target_price_service = TargetPriceService()
            target_prices = await target_price_service.get_portfolio_target_prices(
                db, portfolio_id, symbol=None, position_type=None
            )
            print(f"   ✅ Service returned {len(target_prices)} records")
        except Exception as e:
            print(f"   ❌ Service call failed: {e}")
            traceback.print_exc()
            return
            
        print("\n3. Testing response model conversion...")
        try:
            # Use model_validate instead of from_orm (Pydantic v2)
            response_list = []
            for tp in target_prices[:3]:  # Test first 3 records
                try:
                    # Try the old from_orm method first
                    response_model = TargetPriceResponse.from_orm(tp)
                    response_list.append(response_model)
                    print(f"   ✅ from_orm works for {tp.symbol}")
                except Exception as e:
                    print(f"   ⚠️ from_orm failed for {tp.symbol}: {e}")
                    # Try model_validate as alternative
                    try:
                        response_model = TargetPriceResponse.model_validate(tp)
                        response_list.append(response_model)
                        print(f"   ✅ model_validate works for {tp.symbol}")
                    except Exception as e2:
                        print(f"   ❌ model_validate also failed for {tp.symbol}: {e2}")
                        
            print(f"   ✅ Successfully converted {len(response_list)} records")
            
        except Exception as e:
            print(f"   ❌ Response conversion failed: {e}")
            traceback.print_exc()
            return
            
        print("\n4. Testing JSON serialization...")
        try:
            # Test FastAPI's automatic JSON serialization
            import json
            response_data = [r.model_dump() for r in response_list]
            json_str = json.dumps(response_data, default=str)
            print(f"   ✅ JSON serialization works ({len(json_str)} chars)")
        except Exception as e:
            print(f"   ❌ JSON serialization failed: {e}")
            traceback.print_exc()
            return
            
        print("\n🎉 All API logic steps work correctly!")
        print("The 500 error might be in FastAPI routing or middleware.")

if __name__ == "__main__":
    asyncio.run(test_api_logic_step_by_step())