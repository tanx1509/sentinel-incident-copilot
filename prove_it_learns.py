"""
PROVE IT LEARNS — The killer demo for judges.

Runs the main incident, then fires a SECOND similar incident to show 
that Sentinel now retrieves the incident it JUST resolved — proving the 
episodic memory actually updates and the system compounds intelligence.

This is what separates Sentinel from every GPT wrapper at the hackathon.
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from memory.store import EpisodicMemory, WorkingMemory
from agents.core import HistorianAgent
from demo.logger import ReasoningLogger, Colors


def main():
    logger = ReasoningLogger(slow_mode=True)

    logger.banner("🧪  LEARNING LOOP VERIFICATION TEST  🧪")
    print("  Hypothesis: After resolving INC-2026-04-19-0042, Sentinel's memory")
    print("  should contain it. When a SIMILAR incident fires 3 days later,")
    print("  Sentinel should retrieve the fresh incident as the closest prior.\n")
    time.sleep(1.5)

    # --- State 1: Memory BEFORE learning ---
    print(f"{Colors.BOLD}▶ STATE 1: Episodic memory before resolution{Colors.RESET}")
    em_before = EpisodicMemory()
    print(f"  Corpus size: {len(em_before.incidents)} incidents")
    print(f"  Most recent: {em_before.incidents[-1]['id']} — {em_before.incidents[-1]['title']}\n")
    time.sleep(1)

    # Simulate that INC-0042 was resolved and added
    new_resolved = {
        "id": "INC-2026-04-19-0042",
        "title": "KYC vendor rate-limit during Ramadan flash promo — ID",
        "symptoms": "GrabPay checkout success degraded in ID-JKT. ERR_KYC_TIMEOUT "
                    "dominant. kyc-proxy p99 8200ms (24x baseline). No internal deploys.",
        "root_cause": "External vendor-kyc-id rate-limited during unexpected traffic spike.",
        "mitigation": "Failover to vendor-kyc-backup via kubectl env swap. 4min MTTR.",
        "services_involved": ["payment-gateway", "kyc-proxy", "vendor-kyc-id"],
        "region": "ID-JKT",
        "mttr_minutes": 4,
        "resolved": True,
        "tags": ["kyc", "payment", "vendor", "indonesia", "ramadan", "rate-limit"],
    }
    em_before.add_incident(new_resolved)

    # --- State 2: Memory AFTER learning ---
    print(f"{Colors.BOLD}▶ STATE 2: Episodic memory after INC-0042 resolution{Colors.RESET}")
    print(f"  Corpus size: {len(em_before.incidents)} incidents (+1)")
    print(f"  Newest: {em_before.incidents[-1]['id']} — {em_before.incidents[-1]['title']}\n")
    time.sleep(1.5)

    # --- New incident fires 3 days later ---
    logger.banner("📟  THREE DAYS LATER: NEW ALERT FIRES  📟")
    new_alert = {
        "incident_id": "INC-2026-04-22-0007",
        "title": "Checkout success degraded in Jakarta",
        "region": "ID-JKT",
        "service": "payment-gateway",
        "value_before": 0.995,
        "value_now": 0.921,
        "threshold": 0.98,
        "metric": "payment.checkout.success_rate",
    }
    print(f"  {new_alert['incident_id']}")
    print(f"  {new_alert['title']}")
    print(f"  Success rate: {new_alert['value_before']*100:.1f}% → {new_alert['value_now']*100:.1f}%")
    print(f"  Region: {new_alert['region']}\n")
    time.sleep(1.5)

    # --- Historian runs on new incident ---
    print(f"{Colors.BOLD}▶ Historian queries episodic memory...{Colors.RESET}\n")
    time.sleep(1)

    triage_stub = {"dominant_error": "ERR_KYC_TIMEOUT"}
    wm = WorkingMemory(incident_id=new_alert["incident_id"])
    hist = HistorianAgent(wm, em_before, logger)
    result = hist.run(new_alert, triage_stub)

    # --- The payoff ---
    logger.banner("🎯  THE PROOF  🎯")
    print(f"  Sentinel's top-3 retrieved matches:\n")
    for i, m in enumerate(result["matches"][:3], 1):
        is_fresh = m["id"] == "INC-2026-04-19-0042"
        marker = "  ✨ FRESH " if is_fresh else "     "
        color = Colors.GREEN if is_fresh else Colors.WHITE
        print(f"  {marker}{color}{i}. [{m['similarity']:.3f}] {m['id']}{Colors.RESET}")
        print(f"           {m['title']}")
        print(f"           Prior MTTR: {m['mttr_minutes']} min\n")

    if result["matches"] and result["matches"][0]["id"] == "INC-2026-04-19-0042":
        print(f"{Colors.GREEN}{Colors.BOLD}  ✅ VERIFIED:{Colors.RESET}"
              f" Sentinel ranked the incident it resolved 3 days ago as the")
        print(f"     TOP match for this new page. The 4-minute MTTR from that run")
        print(f"     is now the starting reference for this one.\n")
        print(f"{Colors.BOLD}     What this means:{Colors.RESET}")
        print(f"     • Institutional memory no longer dies on incident close")
        print(f"     • Every incident makes future incidents shorter")
        print(f"     • The 'Cognitive Cold Start' is gone")
        print(f"     • This is a COMPOUNDING engineering asset, not a tool")
    else:
        print("  Learning loop did not promote fresh incident — memory wiring issue.")

    print()


if __name__ == "__main__":
    main()
