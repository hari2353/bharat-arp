# Bharat ARP

An open-source, India-first decision layer for small-business operations.

Bharat ARP is inspired by the Agentic Resource Planning thesis: keep the ERP
as the auditable system of record, then add a governed decision layer that
combines business events, external signals, and human approvals.

## Product Boundary

The project does **not** replace accounting or GST systems. It proposes safe,
traceable next actions around them.

The first vertical slice is order-to-cash:

- detect overdue invoices
- choose a permitted follow-up channel
- create an approval-gated action proposal
- never send a message or change an ERP record automatically

Planned India-first adapters include ERPNext, GST/e-invoice workflows, and
UPI/bank reconciliation. These integrations will be isolated behind typed
adapters and will not be required to run the core policy engine.

## Architecture Direction

```text
ERPNext / India Compliance / payment providers
                    |
             adapter services
                    |
        normalized business event ledger
                    |
       decision policies + bounded agents
                    |
             approval inbox
                    |
        explicitly authorized side effects
```

The design principles are:

- **System of record:** ERPNext and India Compliance remain authoritative for
  accounting and tax records.
- **Governed autonomy:** agents propose; deterministic policies and humans
  authorize sensitive actions.
- **Auditability:** every proposal will carry its source entities, policy
  version, decision, and approval history.
- **Tenant isolation:** customer and financial data must be scoped by tenant
  before retrieval, reasoning, or persistence.
- **Local-first integrations:** India-specific providers are optional adapters,
  not hard-coded assumptions.

## Development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
```

## Status

Early prototype. The API, data model, and integration contracts are not stable
yet. Do not use this repository for production financial or tax decisions.

## Research

- [SHAKE ARP Manifesto](https://shakegraph.com/manifesto)
- [ERPNext](https://github.com/frappe/erpnext)
- [India Compliance](https://github.com/resilient-tech/india-compliance)
- [Temporal](https://docs.temporal.io/temporal)
