# IoT Hardware Connect Bench Agent Rules

Before planning, implementing, reviewing, or declaring this project complete:

1. Read `docs/ideas/getting_lost.md`.
2. Read `docs/plans/REQUIREMENT_EXECUTION_LEDGER_2026-09-24.md` and the idea documents relevant to the slice being changed.
3. Backtrace the request through source, tests, live behavior, and prior plans; do not treat a UI label or mocked response as implementation evidence.
4. Work in the ledger's product order. The Prototype stage is last because it consumes verified discovery, pins, controls, tests, firmware, and tool contracts.
5. For every slice: record the baseline, implement, run focused tests, run the applicable full and browser/live gates, repeat the gap review, then update the ledger.
6. Never identify a USB bridge as the complete board, never claim non-enumerable circuitry was automatically discovered, and never drive unknown pins or flash hardware without a target-bound plan and explicit approval.
7. Keep runtime databases, captures, credentials, network identifiers, device secrets, firmware dumps, and private evidence out of Git.
8. Never start or restart a development server, API server, frontend server, watch process, or project listener, including for verification. The user exclusively owns server startup and must knowingly initiate it. Agents may provide the exact start command, inspect listener status, or stop project listeners only when the user explicitly requests that action. Static checks and tests that do not open persistent listeners remain allowed.

If work becomes unclear or appears complete, return to `docs/ideas/getting_lost.md` and the active gap matrix before stopping.
