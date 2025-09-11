#!/usr/bin/env python3
"""
Analyze which specific calculation engines are failing for demo portfolios
"""
import sys
from pathlib import Path
import asyncio
import re

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2
from app.database import get_async_session
from app.models.users import Portfolio, User
from sqlalchemy import select
from sqlalchemy.orm import selectinload


async def analyze_calculation_engine_failures():
    """Run batch processing on demo portfolios and track which engines fail"""
    
    print('🔍 ANALYZING CALCULATION ENGINE FAILURES FOR DEMO PORTFOLIOS')
    print('=' * 80)
    
    # Our 3 target demo portfolios
    demo_portfolios = {
        'demo_individual@sigmasight.com': 'Demo Individual Investor Portfolio',
        'demo_hnw@sigmasight.com': 'Demo High Net Worth Investor Portfolio', 
        'demo_hedgefundstyle@sigmasight.com': 'Demo Hedge Fund Style Investor Portfolio'
    }
    
    async with get_async_session() as db:
        # Get the portfolio IDs
        portfolio_ids = {}
        
        for email, name in demo_portfolios.items():
            stmt = select(Portfolio).join(User).where(User.email == email)
            result = await db.execute(stmt)
            portfolio = result.scalar_one_or_none()
            
            if portfolio:
                portfolio_ids[email] = str(portfolio.id)
                print(f'📊 {email}: {portfolio.id}')
            else:
                print(f'❌ {email}: NOT FOUND')
        
        print(f'\n🚀 RUNNING BATCH PROCESSING ON ALL DEMO PORTFOLIOS...')
        print('=' * 60)
        
        # Run batch processing and capture results
        try:
            results = await batch_orchestrator_v2.run_daily_batch_sequence()
            
            print(f'\n📊 BATCH RESULTS ANALYSIS:')
            print('-' * 40)
            print(f'Total jobs executed: {len(results)}')
            
            # Group results by portfolio and engine type
            demo_results = {}
            other_results = []
            
            for result in results:
                job_name = result.get('job_name', 'unknown')
                job_type = result.get('job_type', result.get('description', 'unknown'))
                status = result.get('status', 'unknown')
                error = result.get('error', '')
                
                # Try to extract portfolio ID from job name
                portfolio_id_match = None
                for uid in portfolio_ids.values():
                    if uid in job_name:
                        portfolio_id_match = uid
                        break
                
                if portfolio_id_match:
                    # This is a demo portfolio job
                    portfolio_email = None
                    for email, pid in portfolio_ids.items():
                        if pid == portfolio_id_match:
                            portfolio_email = email
                            break
                    
                    if portfolio_email not in demo_results:
                        demo_results[portfolio_email] = []
                    
                    demo_results[portfolio_email].append({
                        'job_type': job_type,
                        'job_name': job_name,
                        'status': status,
                        'error': error
                    })
                else:
                    # Non-demo portfolio job
                    other_results.append({
                        'job_type': job_type,
                        'job_name': job_name,
                        'status': status,
                        'error': error
                    })
            
            # Analysis for each demo portfolio
            print(f'\n🎯 DEMO PORTFOLIO CALCULATION ENGINE ANALYSIS:')
            print('=' * 60)
            
            for email, portfolio_name in demo_portfolios.items():
                if email not in demo_results:
                    print(f'\n❌ {email}: NO BATCH JOBS FOUND')
                    continue
                
                print(f'\n📊 {email}')
                print(f'    Portfolio: {portfolio_name}')
                print(f'    ID: {portfolio_ids.get(email, "unknown")}')
                print('-' * 50)
                
                jobs = demo_results[email]
                successful_engines = []
                failed_engines = []
                
                for job in jobs:
                    job_type = job['job_type']
                    status = job['status']
                    error = job['error']
                    
                    if status == 'completed':
                        successful_engines.append(job_type)
                        print(f'    ✅ {job_type}')
                    elif status == 'failed':
                        failed_engines.append(job_type)
                        print(f'    ❌ {job_type}')
                        if error:
                            print(f'        Error: {error}')
                    else:
                        print(f'    ⚠️ {job_type}: {status}')
                        if error:
                            print(f'        Error: {error}')
                
                print(f'\\n    SUMMARY: {len(successful_engines)} successful, {len(failed_engines)} failed')
                
                if failed_engines:
                    print(f'    FAILED ENGINES: {", ".join(failed_engines)}')
            
            # Overall analysis
            print(f'\n🔍 OVERALL ANALYSIS:')
            print('-' * 40)
            
            # Count engine failures across all demo portfolios
            all_failed_engines = []
            all_successful_engines = []
            
            for email, jobs in demo_results.items():
                for job in jobs:
                    if job['status'] == 'failed':
                        all_failed_engines.append(job['job_type'])
                    elif job['status'] == 'completed':
                        all_successful_engines.append(job['job_type'])
            
            # Count unique engine types
            unique_failed = list(set(all_failed_engines))
            unique_successful = list(set(all_successful_engines))
            
            print(f'Engines that failed: {unique_failed}')
            print(f'Engines that succeeded: {unique_successful}')
            
            # Common failure patterns
            failure_counts = {}
            for engine in all_failed_engines:
                failure_counts[engine] = failure_counts.get(engine, 0) + 1
            
            if failure_counts:
                print(f'\\nMost common failures:')
                for engine, count in sorted(failure_counts.items(), key=lambda x: x[1], reverse=True):
                    print(f'  {engine}: {count} failures')
            
        except Exception as e:
            print(f'❌ Batch processing failed: {str(e)}')
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(analyze_calculation_engine_failures())