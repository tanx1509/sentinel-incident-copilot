"""
Sentinel Tools — the action surface the agent uses to investigate & act.

Every tool is classified as READ or WRITE. Write tools require human approval.
Tools return structured data that the agent can reason over.
"""
import json
import os
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent.parent / "data"

def _load(name: str) -> dict:
    with open(DATA_DIR / name) as f:
        return json.load(f)

# ============================================================
# READ-ONLY TOOLS (safe, no approval needed)
# ============================================================

def datadog_query_metrics(metric: str, region: str | None = None, window: str = "30m") -> dict:
    """Fetch time-series metric data. READ-ONLY."""
    tel = _load("telemetry.json")
    metrics = tel["metrics"]
    if metric not in metrics:
        return {"error": f"metric {metric} not found", "available": list(metrics.keys())}
    data = metrics[metric]
    if region and isinstance(data, dict) and region in data:
        return {"metric": metric, "region": region, "window": window, "series": data[region]}
    return {"metric": metric, "window": window, "data": data}

def datadog_query_logs(service: str, window: str = "10m") -> dict:
    """Fetch recent logs for a service. READ-ONLY."""
    tel = _load("telemetry.json")
    logs = tel["logs"].get(service, [])
    return {"service": service, "window": window, "count": len(logs), "lines": logs}

def github_diff_last_deploy(service: str, hours: int = 24) -> dict:
    """List deploys in the last N hours with diff metadata. READ-ONLY."""
    tel = _load("telemetry.json")
    deploys = tel["deploys"].get(service, [])
    return {"service": service, "hours": hours, "count": len(deploys), "deploys": deploys}

def service_graph_blast_radius(service: str, direction: str = "downstream") -> dict:
    """Traverse service topology. READ-ONLY."""
    tel = _load("telemetry.json")
    graph = tel["service_graph"]
    if service not in graph:
        return {"error": f"service {service} not in graph"}
    node = graph[service]
    return {
        "service": service,
        "direction": direction,
        "dependencies": node.get(direction, []),
        "metadata": {k: v for k, v in node.items() if k not in ("upstream", "downstream")}
    }

def k8s_describe_pods(service: str) -> dict:
    """Get pod state for a service. READ-ONLY."""
    tel = _load("telemetry.json")
    pods = tel["k8s_pods"].get(service, {}).get("pods", [])
    return {
        "service": service,
        "pod_count": len(pods),
        "pods": pods,
        "total_restarts_24h": sum(p["restarts"] for p in pods),
        "total_oom_24h": sum(p["oom_kills_24h"] for p in pods),
    }

def runbook_retrieve(topic: str) -> dict:
    """Search runbooks by topic. READ-ONLY."""
    tel = _load("telemetry.json")
    runbooks = tel["runbooks"]
    matches = {k: v for k, v in runbooks.items() if topic.lower() in k.lower() or topic.lower() in v["title"].lower()}
    return {"query": topic, "matches": matches}

def business_impact_estimate(region: str) -> dict:
    """Estimate $ impact of outage in a region. READ-ONLY."""
    tel = _load("telemetry.json")
    return tel["business_impact"].get(region, {"error": f"no data for region {region}"})

# ============================================================
# WRITE TOOLS (require human approval via approval_gate)
# ============================================================

def k8s_apply_manifest(manifest: str, dry_run: bool = True, approval_token: str | None = None) -> dict:
    """Apply a k8s manifest. WRITE — requires approval_token for non-dry-run."""
    BLOCKED_PATTERNS = ["DROP ", "DELETE FROM", "rm -rf", "DELETE *"]
    for pat in BLOCKED_PATTERNS:
        if pat.lower() in manifest.lower():
            return {"blocked": True, "reason": f"hard blocklist match: {pat}"}

    if dry_run:
        return {
            "dry_run": True,
            "would_apply": manifest,
            "validation": "PASS",
            "affected_resources": ["deployment/kyc-proxy"],
            "note": "Re-run with dry_run=False and valid approval_token to execute."
        }

    if not approval_token or not approval_token.startswith("HUMAN_APPROVED_"):
        return {
            "executed": False,
            "error": "WRITE_BLOCKED: valid approval_token required for non-dry-run execution.",
            "hint": "Sentinel must post the proposed action to Slack and wait for human /approve."
        }

    # Simulated execution
    return {
        "executed": True,
        "approval_token": approval_token,
        "rollout_time_seconds": 34,
        "status": "Deployment rolled out successfully",
        "affected_pods": 3,
    }

def slack_post_threaded(channel: str, message: str, confidence: float) -> dict:
    """Post to incident channel. WRITE (soft) — confidence-gated."""
    MIN_CONFIDENCE = 0.75
    if confidence < MIN_CONFIDENCE:
        return {
            "posted": False,
            "reason": f"confidence {confidence} below broadcast threshold {MIN_CONFIDENCE}",
            "logged_only": True,
        }
    return {"posted": True, "channel": channel, "message_preview": message[:120] + "...", "timestamp": "14:32:19"}

# ============================================================
# TOOL REGISTRY — what the agent can introspect
# ============================================================

TOOL_REGISTRY = {
    # READ
    "datadog_query_metrics": {"fn": datadog_query_metrics, "access": "READ"},
    "datadog_query_logs":    {"fn": datadog_query_logs,    "access": "READ"},
    "github_diff_last_deploy": {"fn": github_diff_last_deploy, "access": "READ"},
    "service_graph_blast_radius": {"fn": service_graph_blast_radius, "access": "READ"},
    "k8s_describe_pods":     {"fn": k8s_describe_pods,     "access": "READ"},
    "runbook_retrieve":      {"fn": runbook_retrieve,      "access": "READ"},
    "business_impact_estimate": {"fn": business_impact_estimate, "access": "READ"},
    # WRITE
    "k8s_apply_manifest":    {"fn": k8s_apply_manifest,    "access": "WRITE"},
    "slack_post_threaded":   {"fn": slack_post_threaded,   "access": "WRITE_SOFT"},
}

def call_tool(name: str, **kwargs) -> dict:
    """Typed dispatch — rejects unknown tools. This is a guardrail."""
    if name not in TOOL_REGISTRY:
        return {"error": f"UNKNOWN_TOOL: {name}. Hallucinated tools are blocked."}
    return TOOL_REGISTRY[name]["fn"](**kwargs)
