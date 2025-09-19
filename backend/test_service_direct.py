#!/usr/bin/env python
"""Test service layer and response model serialization separately"""

import asyncio
from app.database import AsyncSessionLocal
from app.services.target_price_service import TargetPriceService
from app.schemas.target_prices import TargetPriceResponse
from uuid import UUID
import json

async def test_service_and_serialization():
    portfolio_id = UUID('e23ab931-a033-edfe-ed4f-9d02474780b4')
    
    async with AsyncSessionLocal() as db:
        service = TargetPriceService()
        
        print("🔧 Testing service layer...")
        try:
            target_prices = await service.get_portfolio_target_prices(db, portfolio_id)
            print(f"   ✅ Service works: {len(target_prices)} records")
            
            if target_prices:
                print(f"   📊 Sample raw record: {target_prices[0].symbol}")
                
                print("\n🎯 Testing response model serialization...")
                try:
                    # Test converting first record to response model
                    first_tp = target_prices[0]
                    response_model = TargetPriceResponse.from_orm(first_tp)
                    print(f"   ✅ Response model works for: {response_model.symbol}")
                    
                    # Test serializing to dict/JSON
                    response_dict = response_model.dict()
                    print(f"   ✅ Dict conversion works")
                    
                    json_str = json.dumps(response_dict, default=str)
                    print(f"   ✅ JSON serialization works")
                    
                    print(f"\n📋 Sample response structure:")
                    print(json.dumps({
                        "symbol": response_dict.get("symbol"),
                        "target_price_eoy": response_dict.get("target_price_eoy"),
                        "current_price": response_dict.get("current_price"),
                        "expected_return_eoy": response_dict.get("expected_return_eoy")
                    }, indent=2, default=str))
                    
                except Exception as e:
                    print(f"   ❌ Response model error: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    # Let's examine the raw record attributes
                    print(f"\n🔍 Raw record attributes:")
                    for attr in dir(first_tp):
                        if not attr.startswith('_'):
                            try:
                                value = getattr(first_tp, attr)
                                print(f"   {attr}: {type(value)} = {value}")
                            except Exception as ex:
                                print(f"   {attr}: ERROR - {ex}")
                
        except Exception as e:
            print(f"   ❌ Service error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_service_and_serialization())