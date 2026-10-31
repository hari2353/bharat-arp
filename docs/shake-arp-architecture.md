# Shake ARP → Bharat ARP: borrowing the best ideas

Source: LinkedIn post by Mohan Reddy, Co-Founder/CTO of SHAKE
(https://www.linkedin.com/posts/mohankreddy_shake-agentic-resource-planning-activity-7508955217376284673-4NBJ)
and the SHAKE Category Manifesto (shakegraph.com/manifesto). SHAKE defines
"Agentic Resource Planning (ARP)" — the category after ERP — and Bharat ARP
already names itself after that thesis. This doc maps SHAKE's five ideas onto
Bharat ARP's modules so the borrowing is explicit.

## The five ideas and where they land

| # | SHAKE idea | Bharat ARP today | Borrowed change |
|---|---|---|---|
| 1 | **ARP is the category after ERP** — ERP is a filing cabinet with a rulebook; ARP watches the business and the economy and acts | `README.md` already says "inspired by Agentic Resource Planning thesis" | Strengthened positioning: Bharat ARP is the collections-side ARP, not an ERP add-on |
| 2 | **Autonomous business** — reordering/reconciling/collecting/negotiating inside owner-set limits; an agent earns authority like a new hire earns signing authority, one good call at a time, and loses it faster | `proposals.py` already approval-gated (`requires_approval=True`) | New `autonomy.py`: graduated autonomy (draft → suggest → auto) with earned authority and automatic demotion on failure |
| 3 | **Agentic means it acts** — (a) can it earn the right to act on its own, or draft-and-wait forever? (b) does it know which actions can't be undone? (c) does it learn from what happened after it acted? | `decisioning.py` ranks accounts; `metrics.py` measures payment outcomes | (a) autonomy gate; (b) action reversibility flag on proposals; (c) outcome feedback loop feeds the autonomy gate |
| 4 | **Millions of agents, one self-correcting framework** — 1M actions at 99% = 10,000 mistakes; the framework grades its own work; agents that prove themselves earn more room, agents that drift lose it automatically | `metrics.py` records whether an action led to payment | `autonomy.py` demotes on failure automatically; promotion requires sustained success |
| 5 | **ShakeFM: business foundation models** — frontier models learned the world from the internet, but a business runs on orders/invoices/inventory/cash; "a language model should never be the source of a number on your books"; looped reasoning for hard problems; long-running harnesses (minute or month); statistics for breadth, structure for truth | `decisioning.py` is already deterministic (no LLM in the math) | Reinforced as a hard rule in SPEC/docs: amounts, aging, DSO, scores are computed in code; LLM drafts text only |

## What changed in this repo

- `bharat_arp/autonomy.py` — graduated autonomy gate (NEW). Mirrors india-quant's
  live-plan/approve-plan/live-execute pattern: an agent starts at `draft`, earns
  `suggest` after 3 successes, earns `auto` after 5 more, and is demoted on any
  failure (2 consecutive failures → back to `draft`).
- `tests/test_autonomy.py` — unit tests for promotion, demotion, reversibility.

## What is explicitly NOT borrowed

- ShakeFM (custom foundation model) — out of scope; our numbers come from deterministic code.
- Millions-of-agents scale — Bharat ARP is single-tenant pilot; the self-grading loop is the part worth borrowing.
- ERP replacement — Bharat ARP never replaces the ERP (stated boundary).

## Mapping to existing modules

- `decisioning.py` (ranked accounts) → feeds `autonomy.gate_action`
- `proposals.py` (approval-gated drafts) → gated by `autonomy` level
- `metrics.py` (payment outcomes) → feeds `autonomy.record_outcome`
- `workflow.py` (persistent collection cases) → long-running harness for multi-week cases

