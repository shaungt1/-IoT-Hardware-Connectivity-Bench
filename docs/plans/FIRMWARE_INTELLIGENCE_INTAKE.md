# Resource Intake: `docs/ideas/firmware_intellgence_layer.md`

Status: reviewed and incorporated  
Date: 2026-09-24

The note adds the missing software half of the device model. Its acquisition -> carving -> architecture
analysis -> code graph -> CMSIS-SVD correlation pipeline is now Phase 8 of the master plan and a
dedicated firmware-intelligence backlog.

The original note remains unchanged at
[`../ideas/firmware_intellgence_layer.md`](../ideas/firmware_intellgence_layer.md).

## Disposition

| Idea from note | Disposition | Reason |
| --- | --- | --- |
| Layer firmware into ROM/bootloader/HAL/runtime/middleware/app/data | Adopt | Makes images understandable and links naturally to evidence graph |
| Binwalk v3 before deeper analysis | Adopt in isolated worker | Useful carving/signature/entropy foundation |
| Ghidra headless | Adopt as optional primary deep analyzer | Scriptable and multi-architecture; output can normalize to software graph |
| SLEIGH for unknown architectures | Expert research workflow | Powerful but requires correct processor semantics, not automatic inference |
| CMSIS-SVD register correlation | Adopt | Converts raw addresses into named peripheral/register candidates |
| radare2/Rizin | Evaluate one | Useful JSON/scriptable alternative; avoid redundant default engines |
| EMBA | Optional isolated Linux/container profile | Valuable broad pipeline but heavy and hostile-input sensitive |
| OpenOCD and external-flash acquisition | Adopt per target/fixture | Useful only with known wiring, target, protection, and authorization |
| flashrom | Optional acquisition adapter | Reads/writes supported external flash; safety is target/programmer specific |
| sigrok signal inference | Already adopted in fixture phase | Complements firmware when code cannot be acquired |
| Avatar2 | Defer to hybrid-analysis milestone | Strong physical/emulator orchestration but too complex for first release |
| Kali hardware metapackage | Do not depend on | Integrate reviewed individual engines, not an OS/tool bundle |
| Probabilistic evidence fusion | Adopt in claim engine | Multiple weak signals can rank candidates without fabricating verification |

## Product rules added

- Acquisition is a separate operation from analysis. Importing a file is passive; reading physical
  flash may be disruptive and always requires a target-specific approved plan.
- Analyze only images/devices the operator owns or is authorized to inspect.
- Never attempt to bypass read protection, secure boot, encryption, signed firmware, or one-time
  programmable protections.
- Treat firmware, archives, filesystems, analyzer scripts, and extracted web content as hostile.
- Run deep analyzers in isolated, resource-limited workers with no device, secret, or network access
  unless explicitly required and approved.
- A code reference to I2C, SPI, camera, BLE, or a register proves software behavior/capability evidence;
  it does not verify that the physical component is populated or working.
- Preserve every image hash, range, base-address assumption, loader/analyzer version, script hash,
  timeout, warning, and confidence.
- Keep decompiler output read-only and labeled generated analysis; never present it as original source.

## Initial delivery slice

1. Firmware artifact and acquisition-receipt schema.
2. Safe file import plus known vendor-image fixture corpus.
3. Isolated Binwalk worker and normalized carved-region graph.
4. Architecture/load-address candidate service with user confirmation.
5. Isolated Ghidra headless worker and minimal function/string/reference graph.
6. CMSIS-SVD address correlation with ambiguity reporting.
7. Layered firmware UI linked to hardware evidence.
8. One known MCU image and one Linux image end-to-end acceptance test.

## Research evidence

- Binwalk v3 identifies and optionally extracts embedded data and supports entropy analysis:
  [official repository](https://github.com/ReFirmLabs/binwalk/blob/master/README.md).
- Ghidra supports command-line project import, analysis, and pre/post scripts:
  [headless analyzer](https://github.com/NationalSecurityAgency/ghidra/blob/master/Ghidra/RuntimeScripts/support/analyzeHeadlessREADME.md).
- SLEIGH describes instruction encoding and p-code semantics for Ghidra disassembly/decompilation:
  [language specification](https://ghidra.re/ghidra_docs/languages/html/sleigh.html).
- radare2 exposes analysis, functions, references, and JSON/r2pipe scripting:
  [analysis](https://book.rada.re/analysis/code_analysis.html) and
  [r2pipe](https://book.rada.re/scripting/r2pipe.html).
- EMBA combines extraction, static/dynamic analysis, SBOM, and reporting, while its installation guide
  warns against developer mode on untrusted inputs:
  [features](https://github.com/e-m-b-a/emba/wiki/Feature-overview) and
  [installation](https://github.com/e-m-b-a/emba/wiki/Installation).
- Avatar2 orchestrates physical and emulated targets with memory forwarding:
  [architecture](https://github.com/avatartwo/avatar2/blob/main/handbook/0x01_intro.md).

## Conclusion

Firmware intelligence is part of the production vision, but it follows dependable identity,
evidence, operations, and firmware acquisition. The first version should produce a transparent,
reviewable software graph, not promise universal decompilation or automatic recovery of source code.
