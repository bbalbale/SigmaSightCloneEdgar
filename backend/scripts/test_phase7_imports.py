"""Test Phase 7 imports"""
import sys

try:
    from app.batch.admin_metrics_job import (
        run_admin_metrics_batch,
        aggregate_daily_metrics,
        cleanup_old_data,
        get_aggregation_status,
        get_retention_status
    )
    print("Admin metrics job imports: OK")

    from app.api.v1.admin.system import router as system_router
    print("System endpoints router: OK")
    print(f"  Routes: {[r.path for r in system_router.routes]}")

    from app.api.v1.admin.router import admin_router
    print("Admin router imports: OK")

    from app.batch.scheduler_config import batch_scheduler
    print("Scheduler config imports: OK")

    print("\nAll Phase 7 imports successful!")
    sys.exit(0)

except Exception as e:
    print(f"Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
