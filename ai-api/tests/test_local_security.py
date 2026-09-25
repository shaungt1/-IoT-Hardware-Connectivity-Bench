from fastapi.testclient import TestClient

from app.api_contract import API_VERSION
from app.local_security import is_local_origin, is_loopback_host, local_request_allowed
from app.main import app


def test_loopback_host_and_origin_policy() -> None:
    assert is_loopback_host("127.0.0.1")
    assert is_loopback_host("::1")
    assert is_loopback_host("localhost")
    assert not is_loopback_host("192.168.1.20")
    assert not is_loopback_host("example.com")
    assert is_local_origin("http://127.0.0.1:5173")
    assert is_local_origin("https://localhost")
    assert not is_local_origin("https://example.com")
    assert local_request_allowed("127.0.0.1", None)
    assert not local_request_allowed("127.0.0.1", "https://example.com")


def test_http_middleware_rejects_nonlocal_browser_origin() -> None:
    with TestClient(app) as client:
        denied = client.get("/api/health", headers={"Origin": "https://example.com"})
        allowed = client.get("/api/health", headers={"Origin": "http://127.0.0.1:5173"})

    assert denied.status_code == 403
    assert allowed.status_code == 200
    assert allowed.json()["ok"] is True
    assert allowed.headers["X-IoT-Bench-API-Version"] == API_VERSION


def test_api_contract_is_versioned_and_keeps_hosted_control_disabled() -> None:
    # Do not start a second hardware lifespan in this process just to inspect a static contract.
    response = TestClient(app).get("/api/contract")

    assert response.status_code == 200
    assert response.headers["X-IoT-Bench-API-Version"] == API_VERSION
    contract = response.json()
    assert contract["api_version"] == API_VERSION
    assert contract["schemas"] == {"evidence_graph": "1.0", "prototype": "1.0", "test_pack": "1.0"}
    assert contract["surfaces"]["protected_mutation"]["authentication"].endswith("approval token")
    assert contract["surfaces"]["mcp"]["transport"] == "local stdio"
    assert contract["hosted_release"]["supported"] is False
