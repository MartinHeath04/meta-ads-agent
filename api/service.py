"""Analysis orchestration for the API.

Runs the agent for a demo tenant and tracks jobs/reports. The analyzer is exposed
via a dependency (`get_analyzer`) so tests can swap in a fast, LLM-free stub.

Job and report stores are in-memory (demo-grade; reset on restart). The agent's
own decisions/analyses are still persisted to its tenant-scoped SQLite memory.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Callable

from config.demo_tenants import get_demo_tenant
from data_layer.providers import FakeDataProvider
from agent.brain import AgentBrain
from agent.memory import AgentMemory
from agent.core import MetaAdsAgent
from api.schemas import AnalyzeJob, ReportOut, RecommendationOut

logger = logging.getLogger(__name__)

# In-memory stores (demo-grade; persistence is a future enhancement).
JOBS: dict[str, AnalyzeJob] = {}
REPORTS: dict[str, ReportOut] = {}

# An analyzer takes (tenant_id, date_range) and returns a ReportOut.
Analyzer = Callable[[str, str], ReportOut]


def run_analysis(tenant_id: str, date_range: str = "last_7d") -> ReportOut:
    """Run a real agent analysis for a demo tenant on seeded data (calls Claude)."""
    profile = get_demo_tenant(tenant_id)
    agent = MetaAdsAgent(
        meta_client=FakeDataProvider(profile=profile),
        brain=AgentBrain(business_profile=profile),
        memory=AgentMemory(tenant_id=profile.tenant_id),
        dry_run=True,
        business_profile=profile,
    )
    result = agent.run_daily_analysis(date_range=date_range)
    return ReportOut(
        report_id=uuid.uuid4().hex,
        tenant_id=profile.tenant_id,
        date_range=date_range,
        generated_at=datetime.now(timezone.utc).isoformat(),
        model=result.model,
        tokens_used=result.tokens_used,
        executive_summary=result.executive_summary,
        recommendations=[RecommendationOut.from_dict(r) for r in result.recommendations],
    )


def get_analyzer() -> Analyzer:
    """Dependency: the analyzer used by the analyze endpoint (overridable in tests)."""
    return run_analysis


def create_job(tenant_id: str) -> AnalyzeJob:
    job = AnalyzeJob(job_id=uuid.uuid4().hex, tenant_id=tenant_id, status="queued")
    JOBS[job.job_id] = job
    return job


def run_job(job_id: str, tenant_id: str, date_range: str, analyzer: Analyzer) -> None:
    """Background worker: run the analyzer and update the job + report stores."""
    job = JOBS[job_id]
    job.status = "running"
    try:
        report = analyzer(tenant_id, date_range)
        REPORTS[report.report_id] = report
        job.report_id = report.report_id
        job.status = "done"
        logger.info(f"Job {job_id} done -> report {report.report_id}")
    except Exception as e:  # noqa: BLE001 - surface any failure on the job
        job.status = "error"
        job.error = str(e)
        logger.error(f"Job {job_id} failed: {e}")


def get_job(job_id: str) -> AnalyzeJob | None:
    return JOBS.get(job_id)


def get_report(report_id: str) -> ReportOut | None:
    return REPORTS.get(report_id)
