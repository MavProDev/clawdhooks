"""
Data Pipeline Anomaly Detection
================================

Demonstrates claude-hooks for inspecting data batches before ETL processing.
Claude evaluates metrics for anomalies and returns clean/warn/halt decisions.

Usage:
    export ANTHROPIC_API_KEY=your-key-here
    python examples/data_pipeline.py
"""
import asyncio
import os

from pydantic import BaseModel

from claudehooks import HookRouter


class DataBatch(BaseModel):
    source: str
    row_count: int
    null_percentage: float
    avg_value: float
    stddev: float
    schema_version: str


class AnomalyResult(BaseModel):
    decision: str  # "clean", "warn", or "halt"
    anomalies: list[str]
    confidence: float
    recommendation: str


router = HookRouter(
    api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
    calls_per_hour=60,
)


@router.hook(model="haiku", fallback="local")
async def check_batch(batch: DataBatch) -> AnomalyResult:
    """You are a data quality analyst. Inspect this data batch for anomalies.

    Check for:
    - Unusually high null percentages (>10% is suspicious, >25% is critical)
    - Row count deviations from expected (should be 1000-5000 per batch)
    - Statistical outliers (stddev > 3x avg_value is suspicious)
    - Schema version mismatches

    Return:
    - decision: "clean" (proceed), "warn" (flag for review), "halt" (stop pipeline)
    - anomalies: list of detected issues
    - confidence: 0.0-1.0
    - recommendation: what to do next
    """
    # Local fallback: basic rule-based checks
    anomalies = []
    if batch.null_percentage > 25:
        anomalies.append("Critical null percentage")
    if batch.row_count < 100 or batch.row_count > 10000:
        anomalies.append("Row count out of range")
    if batch.stddev > 3 * batch.avg_value:
        anomalies.append("High standard deviation")

    if anomalies:
        return AnomalyResult(
            decision="warn",
            anomalies=anomalies,
            confidence=0.3,
            recommendation="Manual review needed (fallback mode)",
        )
    return AnomalyResult(
        decision="clean",
        anomalies=[],
        confidence=0.3,
        recommendation="Proceed (fallback mode)",
    )


async def main():
    batches = [
        DataBatch(source="sales_db", row_count=2500, null_percentage=2.1,
                  avg_value=45.30, stddev=12.5, schema_version="v3"),
        DataBatch(source="user_events", row_count=50, null_percentage=35.0,
                  avg_value=1.2, stddev=18.7, schema_version="v2"),
        DataBatch(source="inventory", row_count=3200, null_percentage=0.5,
                  avg_value=100.0, stddev=15.0, schema_version="v3"),
    ]

    for batch in batches:
        result = await check_batch(batch)
        icon = {"clean": "OK", "warn": "!!", "halt": "XX"}[result.decision]
        print(f"[{icon}] {batch.source}: {result.decision}")
        if result.anomalies:
            for a in result.anomalies:
                print(f"     - {a}")
        print(f"     Recommendation: {result.recommendation}")
        print()

    stats = router.stats()
    print(f"--- Stats: {stats['total_calls']} calls, ${stats['total_cost_usd']:.6f} ---")


if __name__ == "__main__":
    asyncio.run(main())
