from app.evidence_policy import calibrate_claim, inspection_calibration


def test_live_and_declared_claims_are_calibrated_differently() -> None:
    live = calibrate_claim("verified", "Authenticated compatible firmware telemetry")
    declared = calibrate_claim("verified", "Uploaded board definition")

    assert live["live_verified"] is True
    assert live["may_promote_live_claim"] is True
    assert declared["live_verified"] is False
    assert declared["may_promote_live_claim"] is False
    assert declared["score"] < live["score"]


def test_exact_board_requires_live_verified_claim() -> None:
    declared = inspection_calibration({
        "evidence": [{"source": "saved bench profile", "claim": "Exact board Demo", "status": "declared"}],
    })
    verified = inspection_calibration({
        "evidence": [{"source": "Authenticated compatible firmware telemetry", "claim": "Exact board Demo", "status": "verified"}],
    })

    assert declared["exact_board_live_verified"] is False
    assert verified["exact_board_live_verified"] is True
