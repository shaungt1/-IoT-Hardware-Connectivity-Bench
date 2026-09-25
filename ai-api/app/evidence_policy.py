from __future__ import annotations

from typing import Any


STATUS_SCORES = {
    "verified": 0.98,
    "detected": 0.82,
    "declared": 0.65,
    "expected": 0.52,
    "candidate": 0.35,
    "unknown": 0.10,
    "unavailable": 0.95,
}

LIVE_SOURCE_MARKERS = (
    "authenticated",
    "controlled",
    "live target",
    "runtime probe",
    "diagnostic handshake",
    "firmware initialization",
    "usb descriptor",
    "usb identity",
    "host enumeration",
    "windows usb enumeration",
    "mounted circuitpy",
)
DECLARED_SOURCE_MARKERS = (
    "definition",
    "specification",
    "catalog",
    "saved bench profile",
    "uploaded",
    "product",
    "pin map",
)


def calibrate_claim(status: Any, source: Any) -> dict[str, Any]:
    normalized_status = str(status or "unknown").lower()
    normalized_source = str(source or "unspecified").lower()
    source_class = "live_observation" if any(marker in normalized_source for marker in LIVE_SOURCE_MARKERS) else (
        "declared_definition" if any(marker in normalized_source for marker in DECLARED_SOURCE_MARKERS) else "unclassified"
    )
    score = STATUS_SCORES.get(normalized_status, STATUS_SCORES["unknown"])
    promotable = normalized_status in {"verified", "detected"} and source_class == "live_observation"
    if normalized_status == "verified" and source_class != "live_observation":
        score = min(score, 0.75)
        promotable = False
    band = "high" if score >= 0.85 else "medium" if score >= 0.55 else "low"
    return {
        "score": score,
        "band": band,
        "source_class": source_class,
        "live_verified": normalized_status == "verified" and source_class == "live_observation",
        "may_promote_live_claim": promotable,
        "rule": (
            "Live observation may promote only the claim and layer it directly measures."
            if promotable
            else "Definitions, catalog matches, and user declarations remain non-live evidence until an adapter verifies them."
        ),
    }


def inspection_calibration(inspection: dict[str, Any]) -> dict[str, Any]:
    evidence = inspection.get("evidence") or []
    calibrated = [calibrate_claim(item.get("status"), item.get("source")) for item in evidence]
    live_count = sum(1 for item in calibrated if item["live_verified"])
    exact_board_live = any(
        item.get("status") == "verified"
        and str(item.get("claim") or "").lower().startswith("exact board")
        and calibrate_claim(item.get("status"), item.get("source"))["live_verified"]
        for item in evidence
    )
    return {
        "policy_version": "1.0",
        "live_verified_claims": live_count,
        "exact_board_live_verified": exact_board_live,
        "definition_promotion": "prohibited_without_matching_live_evidence",
        "bridge_target_promotion": "prohibited_without_target_protocol_or_chip_signature",
    }
