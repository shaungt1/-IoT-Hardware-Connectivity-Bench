from __future__ import annotations

import json
from typing import Callable
from wsgiref.simple_server import make_server

from .inventory import collect_inventory


INDEX_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>IoT Hardware Connectivity Bench</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 2rem; background: #0f172a; color: #e2e8f0; }
      h1 { margin-bottom: 0.5rem; }
      .meta { color: #94a3b8; margin-bottom: 1.5rem; }
      .grid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }
      .card { background: #1e293b; border-radius: 0.75rem; padding: 1rem; box-shadow: 0 10px 25px rgba(15, 23, 42, 0.25); }
      .kind { font-size: 0.85rem; text-transform: uppercase; color: #38bdf8; margin-bottom: 0.5rem; }
      pre { white-space: pre-wrap; word-break: break-word; font-size: 0.85rem; }
      button { background: #38bdf8; border: 0; border-radius: 0.5rem; color: #082f49; cursor: pointer; font-weight: 700; padding: 0.6rem 1rem; }
    </style>
  </head>
  <body>
    <h1>IoT Hardware Connectivity Bench</h1>
    <p class="meta">Scan locally attached hardware and inspect the current inventory snapshot.</p>
    <button id="refresh">Refresh inventory</button>
    <p id="summary" class="meta"></p>
    <div id="devices" class="grid"></div>
    <script>
      async function loadInventory() {
        const response = await fetch('/api/inventory');
        const payload = await response.json();
        document.getElementById('summary').textContent =
          `${payload.device_count} device(s) detected on ${payload.host.hostname} at ${payload.captured_at}`;
        const devices = document.getElementById('devices');
        devices.innerHTML = '';
        for (const device of payload.devices) {
          const card = document.createElement('section');
          card.className = 'card';
          card.innerHTML =
            `<div class="kind">${device.kind}</div>` +
            `<strong>${device.identifier}</strong>` +
            `<p>${device.summary}</p>` +
            `<pre>${JSON.stringify(device.details, null, 2)}</pre>`;
          devices.appendChild(card);
        }
      }
      document.getElementById('refresh').addEventListener('click', loadInventory);
      loadInventory();
    </script>
  </body>
</html>
"""


def application(
    environ: dict[str, str],
    start_response: Callable[[str, list[tuple[str, str]]], None],
    inventory_provider: Callable[[], dict[str, object]] = collect_inventory,
):
    path = environ.get("PATH_INFO", "/")
    if path == "/":
        body = INDEX_HTML.encode("utf-8")
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body)))])
        return [body]

    if path == "/api/inventory":
        body = json.dumps(inventory_provider(), indent=2).encode("utf-8")
        start_response("200 OK", [("Content-Type", "application/json"), ("Content-Length", str(len(body)))])
        return [body]

    body = json.dumps({"error": "not_found", "path": path}).encode("utf-8")
    start_response("404 Not Found", [("Content-Type", "application/json"), ("Content-Length", str(len(body)))])
    return [body]


def run_web_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    with make_server(host, port, application) as server:
        print(f"IoT Hardware Connectivity Bench web UI listening on http://{host}:{port}")
        server.serve_forever()

