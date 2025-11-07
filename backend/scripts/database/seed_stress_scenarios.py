#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Seed stress test scenarios from JSON configuration to database.

This script loads the stress scenarios from app/config/stress_scenarios.json
and populates the stress_test_scenarios table.
"""

import asyncio
import json
import sys
import io
from datetime import datetime
from pathlib import Path
from uuid import uuid4

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import get_async_session
from app.models.market_data import StressTestScenario
from app.calculations.stress_testing import load_stress_scenarios
from app.core.logging import get_logger
from sqlalchemy import select, delete

logger = get_logger(__name__)


async def clear_existing_scenarios(db):
    """Clear existing scenarios from database."""
    try:
        result = await db.execute(select(StressTestScenario))
        existing = result.scalars().all()
        
        if existing:
            logger.info(f"Clearing {len(existing)} existing scenarios")
            await db.execute(delete(StressTestScenario))
            await db.commit()
            return len(existing)
        return 0
    except Exception as e:
        logger.error(f"Error clearing scenarios: {str(e)}")
        await db.rollback()
        raise


async def seed_scenarios_from_config():
    """Load scenarios from JSON config and seed to database."""
    
    print("=" * 60)
    print("🌱 SEEDING STRESS TEST SCENARIOS")
    print("=" * 60)
    
    try:
        # Load scenarios from config
        config = load_stress_scenarios()
        
        if 'stress_scenarios' not in config:
            print("❌ No stress_scenarios found in config")
            return False
        
        scenarios_by_category = config['stress_scenarios']
        total_scenarios = sum(len(scenarios) for scenarios in scenarios_by_category.values())
        
        print(f"\n📊 Found {total_scenarios} scenarios in config")
        print(f"   Categories: {', '.join(scenarios_by_category.keys())}")
        
        async with get_async_session() as db:
            # Clear existing scenarios
            cleared = await clear_existing_scenarios(db)
            if cleared > 0:
                print(f"   Cleared {cleared} existing scenarios")
            
            # Process each category
            scenarios_created = 0
            
            for category, scenarios in scenarios_by_category.items():
                print(f"\n📁 Processing {category}:")
                
                for scenario_id, scenario_data in scenarios.items():
                    is_active = scenario_data.get('active', True)

                    # Create scenario object (include both active and inactive scenarios)
                    scenario = StressTestScenario(
                        id=uuid4(),
                        scenario_id=scenario_id,  # Use the key as scenario_id
                        name=scenario_data.get('name', scenario_id),
                        description=scenario_data.get('description', ''),
                        category=scenario_data.get('category', category),  # Use 'category' not 'scenario_type'
                        severity=scenario_data.get('severity', 'moderate'),
                        shock_config=scenario_data.get('shocked_factors', {}),  # Use 'shock_config' not 'shocked_factors'
                        active=is_active,  # Preserve active/inactive status
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    
                    db.add(scenario)
                    scenarios_created += 1

                    # Display shocked factors
                    shocked_str = ', '.join([
                        f"{k}: {v:+.1%}"
                        for k, v in scenario_data.get('shocked_factors', {}).items()
                    ])
                    status_icon = "✅" if is_active else "⚪"
                    status_text = "ACTIVE" if is_active else "inactive"
                    print(f"   {status_icon} {scenario.name} ({status_text})")
                    print(f"      Shocks: {shocked_str}")
            
            # Commit all scenarios
            await db.commit()
            
            print(f"\n✅ Successfully seeded {scenarios_created} scenarios")
            
            # Verify by counting in database
            result = await db.execute(select(StressTestScenario))
            db_scenarios = result.scalars().all()
            
            print(f"\n📊 Verification:")
            print(f"   Scenarios in database: {len(db_scenarios)}")
            
            # Show summary by category
            by_category = {}
            for scenario in db_scenarios:
                cat = scenario.category  # Use 'category' not 'scenario_type'
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(scenario.name)
            
            for cat, names in by_category.items():
                print(f"\n   {cat.upper()} ({len(names)} scenarios):")
                for name in names[:3]:  # Show first 3
                    print(f"      - {name}")
                if len(names) > 3:
                    print(f"      ... and {len(names) - 3} more")
            
            return True
            
    except Exception as e:
        logger.error(f"Error seeding scenarios: {str(e)}")
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_scenario_loading():
    """Test that scenarios can be loaded and used."""
    print("\n" + "=" * 60)
    print("🧪 TESTING SCENARIO LOADING")
    print("=" * 60)
    
    async with get_async_session() as db:
        result = await db.execute(select(StressTestScenario))
        scenarios = result.scalars().all()
        
        if not scenarios:
            print("❌ No scenarios found in database")
            return False
        
        print(f"\n✅ Successfully loaded {len(scenarios)} scenarios")
        
        # Test one scenario
        test_scenario = scenarios[0]
        print(f"\n📋 Sample Scenario:")
        print(f"   Name: {test_scenario.name}")
        print(f"   Type: {test_scenario.category}")
        print(f"   Severity: {test_scenario.severity}")
        print(f"   Shocked Factors: {test_scenario.shock_config}")
        
        return True


def main():
    """Main entry point."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Seed scenarios
        success = loop.run_until_complete(seed_scenarios_from_config())
        
        if success:
            # Test loading
            loop.run_until_complete(test_scenario_loading())
            print("\n✅ Stress scenarios ready for use!")
            return 0
        else:
            print("\n❌ Failed to seed scenarios")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        return 1
    finally:
        loop.close()


if __name__ == "__main__":
    sys.exit(main())