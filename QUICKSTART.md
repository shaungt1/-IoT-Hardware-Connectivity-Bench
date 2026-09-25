# Local Quick Start

## First setup

From Git Bash in this folder:

```bash
./start.sh setup
```

Or from PowerShell:

```powershell
.\start.ps1 setup
```

## Choose what to run

Both launchers require an explicit mode. Running either launcher without a mode opens this menu and
waits for you to choose `1`, `2`, or `3`; nothing starts until you make that selection:

| Option | Mode | Result |
| --- | --- | --- |
| `1` | React | React on `5173`; hardware API and WebSocket on `8765`; legacy HTML disabled |
| `2` | HTML | Legacy HTML, hardware API, and WebSocket on `8765`; React is not started |
| `3` | Both | React on `5173`; legacy HTML, hardware API, and WebSocket on `8765` |

From Git Bash:

```bash
./start.sh 1  # React
./start.sh 2  # HTML
./start.sh 3  # Both
```

From PowerShell:

```powershell
.\start.ps1 1  # React
.\start.ps1 2  # HTML
.\start.ps1 3  # Both
```

The named aliases `react`, `html`, and `both` remain available in both launchers. The launcher owns an
API process it starts; pressing `Ctrl+C` stops that owned API together with React.

Check or stop the complete bench from Git Bash:

```bash
./start.sh status
./start.sh stop
```

The legacy HTML client is disabled. Port `8765` remains API-only because React proxies hardware
requests to it.

Use these explicit modes when needed:

```powershell
.\start.ps1 react  # React primary, HTML disabled
.\start.ps1 html   # Legacy HTML only at http://127.0.0.1:8765
.\start.ps1 both   # React at 5173 and legacy HTML at 8765
.\start.ps1 status # Show bench listeners and process IDs
.\start.ps1 stop   # Stop bench listeners on 5173, 5174, and 8765
```

Running `npm run dev` directly only starts React and must be run from `react-app`; it does not start the
hardware API. Prefer `start.ps1 react` for the complete React bench.

## MCP for an agent

Keep the bench running, then configure the agent's stdio MCP command as:

```powershell
.\start-mcp.ps1
```

The MCP can inspect, test, read source, and create operation plans. It cannot approve or execute
physical mutations. Its `get_api_contract` tool reports the same version and safety boundaries used by
the browser client.

## Verify or build

```powershell
.\start.ps1 test
```

This runs the Python tests and creates the React production bundle. The API and firmware toolchains
use separate virtual environments so PlatformIO cannot constrain the web server's security updates. Hardware identification is
passive until a clearly labeled probe is started. Flashing is never automatic; it requires a
device-specific command, port, and confirmation.

For a fast development check without creating a production bundle:

```powershell
Push-Location ai-api; ..\.venv\Scripts\python.exe -m pytest -q; Pop-Location
Push-Location react-app; bun run check; Pop-Location
```
