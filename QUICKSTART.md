# Local Quick Start

## First setup

From PowerShell in this folder:

```powershell
.\start.ps1 setup
```

## Run the HTML bench

```powershell
.\start.ps1 dashboard
```

Open `http://127.0.0.1:8765`.

## Run the React bench

Keep the HTML/API process running, open a second PowerShell window, then run:

```powershell
.\start.ps1 dashboard-react
```

Open `http://127.0.0.1:5173`.

## Verify or build

```powershell
.\start.ps1 test
```

This runs the Python tests and creates the React production bundle. Hardware identification is
passive until a clearly labeled probe is started. Flashing is never automatic; it requires a
device-specific command, port, and confirmation.
