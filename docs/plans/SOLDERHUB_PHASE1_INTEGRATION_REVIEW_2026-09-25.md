# SolderHub Phase One Integration Review

Reviewed local source: `C:\Users\Frontside\Documents\0.AI_LLM\solderhub-simulator` (MIT license).

## Adopt During Phase One

SolderHub's `use-esp-flasher.ts` and `esp-flasher-panel.tsx` provide useful interaction patterns: explicit connection state, staged erase/flash progress, terminal output, and guaranteed port cleanup. The bench should map those patterns onto its existing target-bound **plan -> approve -> execute -> audit** operation flow. Its code editor, project loader, and console also confirm the value of a unified firmware workspace with file selection and bounded diagnostic output, which the bench already exposes through Monaco, static firmware analysis, controlled operations, and the diagnostic drawer.

Direct browser Web Serial flashing should not be copied into the current server-owned serial path. Two owners opening one COM interface creates races, and a browser-only write could bypass target locks, approval expiry, hash/address validation, audit receipts, and recovery checks. A future browser transport can be added only as an exclusive alternative mode with the same safety contract.

## Defer Until Prototype Phase

SolderHub's component canvas, wire drawing, footprints, tabs, and digital AVR simulation are useful references for the later prototype redesign. They are deliberately not integrated in this phase. The simulator does not discover physical boards or prove their real wiring, passives, voltages, or sensor identity.

## Electrical Testing Boundary

SPICE can validate a declared schematic or netlist through DC, AC, transient, and operating-point analysis. It cannot determine whether an unknown physical capacitor is leaking or whether an uninstrumented board trace exists. Physical verification requires compatible measurement hardware such as a DMM, oscilloscope, logic analyzer, LCR meter, or controlled fixture. The Phase One probe matrix should continue to report those routes as instrument-required rather than simulate certainty.

## Current Phase One Result

- ESP ROM probing and flashing remain gated, audited operations.
- Hot-plug state is reconciled every two seconds with native Windows device events and immediate stale-device locking.
- Camera delivery uses latest-frame WebSocket semantics so queued JPEG history is skipped rather than replayed.
- Unsupported BLE and Wi-Fi capabilities are visible but disabled.
- Known pins can receive persistent user-declared component or sensor evidence without presenting it as automatic detection.
- The diagnostic console runs only adapter-advertised passive/read-only profiles or allowlisted Linux-board diagnostics; arbitrary shell input remains unavailable.

Remaining work requiring physical fixtures is tracked as an evidence limitation, not an application-completion claim.
