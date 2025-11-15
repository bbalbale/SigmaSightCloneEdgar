"""
Background Job Tracker - In-memory job status tracking
For Railway production where we can't use Redis
"""
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BackgroundJobTracker:
    """Simple in-memory job tracker (single instance, not distributed)"""

    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}

    def create_job(self, job_id: str, job_type: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Create a new job entry"""
        job = {
            "job_id": job_id,
            "job_type": job_type,
            "status": JobStatus.PENDING,
            "params": params or {},
            "created_at": datetime.utcnow().isoformat(),
            "started_at": None,
            "completed_at": None,
            "progress": None,
            "result": None,
            "error": None
        }
        self._jobs[job_id] = job
        return job

    def start_job(self, job_id: str):
        """Mark job as running"""
        if job_id in self._jobs:
            self._jobs[job_id]["status"] = JobStatus.RUNNING
            self._jobs[job_id]["started_at"] = datetime.utcnow().isoformat()

    def update_progress(self, job_id: str, progress: str):
        """Update job progress message"""
        if job_id in self._jobs:
            self._jobs[job_id]["progress"] = progress

    def complete_job(self, job_id: str, result: Dict[str, Any]):
        """Mark job as completed with result"""
        if job_id in self._jobs:
            self._jobs[job_id]["status"] = JobStatus.COMPLETED
            self._jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
            self._jobs[job_id]["result"] = result

    def fail_job(self, job_id: str, error: str):
        """Mark job as failed with error message"""
        if job_id in self._jobs:
            self._jobs[job_id]["status"] = JobStatus.FAILED
            self._jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
            self._jobs[job_id]["error"] = error

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status"""
        return self._jobs.get(job_id)

    def list_jobs(self) -> Dict[str, Dict[str, Any]]:
        """List all jobs"""
        return self._jobs.copy()


# Global singleton instance
job_tracker = BackgroundJobTracker()
