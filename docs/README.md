# Product and Delivery Documentation

This folder is the planning source of truth for turning IoT Hardware Connectivity Bench into a
production-ready, local-first hardware discovery, verification, programming, and prototyping system.

## Read in this order

1. [Recovery rule](ideas/getting_lost.md) - mandatory backtrace, gap, implementation, and re-verification loop.
2. [Active execution ledger](plans/REQUIREMENT_EXECUTION_LEDGER_2026-09-24.md) - authoritative verified state,
   remaining gaps, evidence, and current execution order.
3. [Product vision](PRODUCT_VISION.md) - the problem, audience, experience, and product boundaries.
4. [Product architecture](plans/PRODUCT_ARCHITECTURE.md) - services, evidence model, adapters, APIs,
   safety, storage, deployment, and MCP boundaries.
5. [Technology research](plans/TECHNOLOGY_RESEARCH.md) - what to adopt, evaluate, defer, or avoid.
6. [Resource intake](plans/RESOURCE_INTAKE.md) - disposition of the simulation/studio research note.
7. [Firmware intelligence intake](plans/FIRMWARE_INTELLIGENCE_INTAKE.md) - disposition of the
   firmware-analysis research note.
8. [Latest idea intake](plans/IDEA_INTAKE_2026-09-24.md) - hot-plug state, pin knowledge, firmware
   access, NPU catalog, and hybrid rapid-prototype decisions plus the first implementation receipt.
9. [SolderHub Phase One review](plans/SOLDERHUB_PHASE1_INTEGRATION_REVIEW_2026-09-25.md) - safe reuse of
   flashing, terminal, and firmware-workspace patterns, with prototype visuals explicitly deferred.
10. [Master implementation plan](plans/MASTER_IMPLEMENTATION_PLAN.md) - dependency-ordered phases and
   milestone exit criteria.
11. [Task backlog](plans/TASK_BACKLOG.md) - implementation-ready task IDs and acceptance criteria.
12. [QA and gap gates](plans/QA_GAP_GATES.md) - the review and testing loop required in every phase.
13. [Plan gap review](plans/PLAN_GAP_REVIEW.md) - requirement coverage, residual decisions, and first
   execution slice.
14. [Full implementation gap analysis](plans/FULL_GAP_ANALYSIS_2026-09-24.md) - preserved baseline audit;
    superseded by the active execution ledger for current status.

## Living status documents

- [Current gap analysis](../GAP_ANALYSIS.md) records what is verified now and what remains.
- [Active execution ledger](plans/REQUIREMENT_EXECUTION_LEDGER_2026-09-24.md) owns completion evidence.
- [Connection manifest](../CONNECTION_MANIFEST.md) records installed and planned tools.
- [Agent and AI roadmap](../AGENT_AI_ROADMAP.md) records the existing evidence and AI direction.
- [Quick start](../QUICKSTART.md) is the short operator launch guide.
- [Threat model](THREAT_MODEL.md) maps local hardware, import, tool, MCP, privacy, and release risks to controls.

## Document policy

- `PRODUCT_VISION.md` changes only when product goals or boundaries change.
- `PRODUCT_ARCHITECTURE.md` records accepted architectural decisions, not speculative code.
- `TECHNOLOGY_RESEARCH.md` must include a source, license review status, and disposition.
- `MASTER_IMPLEMENTATION_PLAN.md` owns sequencing and milestone exit criteria.
- `TASK_BACKLOG.md` owns executable work. A checked task must reference test evidence.
- `GAP_ANALYSIS.md` is updated at every phase gate and before every release candidate.

No planning document may describe expected, catalog-derived, or visually inferred hardware as
verified. Verification always requires an identified evidence path.
