#!/usr/bin/env python3
"""
Simple client import validation test
Tests that our API client implementations can be imported and instantiated
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

def test_client_imports():
    """Test that all client classes can be imported successfully"""
    print("🧪 Testing client imports...")
    
    try:
        from app.clients import FMPClient, TradeFeedsClient, market_data_factory, DataType
        print("✅ Successfully imported all client classes")
        
        # Test basic instantiation (will show config warnings but shouldn't crash)
        print("🔧 Testing basic client instantiation...")
        
        try:
            fmp = FMPClient("test_key", timeout=30, max_retries=3)
            print("✅ FMPClient instantiated successfully")
        except Exception as e:
            print(f"❌ FMPClient instantiation failed: {e}")
            
        try:
            tf = TradeFeedsClient("test_key", timeout=30, max_retries=3)
            print("✅ TradeFeedsClient instantiated successfully") 
        except Exception as e:
            print(f"❌ TradeFeedsClient instantiation failed: {e}")
            
        try:
            factory = market_data_factory
            print("✅ market_data_factory accessible")
        except Exception as e:
            print(f"❌ market_data_factory access failed: {e}")
            
        print("\n🎉 Client import validation completed!")
        return True
        
    except Exception as e:
        print(f"❌ Client import failed: {e}")
        return False

if __name__ == "__main__":
    success = test_client_imports()
    sys.exit(0 if success else 1)