# Product and Delivery Documentation

This folder is the planning source of truth for turning IoT Hardware Connectivity Bench into a
production-ready, local-first hardware discovery, verification, programming, and prototyping system.

## Read in this order

1. [Product vision](PRODUCT_VISION.md) - the problem, audience, experience, and product boundaries.
2. [Product architecture](plans/PRODUCT_ARCHITECTURE.md) - services, evidence model, adapters, APIs,
   safety, storage, deployment, and MCP boundaries.
3. [Technology research](plans/TECHNOLOGY_RESEARCH.md) - what to adopt, evaluate, defer, or avoid.
4. [Resource intake](plans/RESOURCE_INTAKE.md) - disposition of the simulation/studio research note.
5. [Firmware intelligence intake](plans/FIRMWARE_INTELLIGENCE_INTAKE.md) - disposition of the
   firmware-analysis research note.
6. [Master implementation plan](plans/MASTER_IMPLEMENTATION_PLAN.md) - dependency-ordered phases and
   milestone exit criteria.
7. [Task backlog](plans/TASK_BACKLOG.md) - implementation-ready task IDs and acceptance criteria.
8. [QA and gap gates](plans/QA_GAP_GATES.md) - the review and testing loop required in every phase.
9. [Plan gap review](plans/PLAN_GAP_REVIEW.md) - requirement coverage, residual decisions, and first
   execution slice.

## Living status documents

- [Current gap analysis](../GAP_ANALYSIS.md) records what is verified now and what remains.
- [Connection manifest](../CONNECTION_MANIFEST.md) records installed and planned tools.
- [Agent and AI roadmap](../AGENT_AI_ROADMAP.md) records the existing evidence and AI direction.
- [Quick start](../QUICKSTART.md) is the short operator launch guide.

## Document policy

- `PRODUCT_VISION.md` changes only when product goals or boundaries change.
- `PRODUCT_ARCHITECTURE.md` records accepted architectural decisions, not speculative code.
- `TECHNOLOGY_RESEARCH.md` must include a source, license review status, and disposition.
- `MASTER_IMPLEMENTATION_PLAN.md` owns sequencing and milestone exit criteria.
- `TASK_BACKLOG.md` owns executable work. A checked task must reference test evidence.
- `GAP_ANALYSIS.md` is updated at every phase gate and before every release candidate.

No planning document may describe expected, catalog-derived, or visually inferred hardware as
verified. Verification always requires an identified evidence path.
