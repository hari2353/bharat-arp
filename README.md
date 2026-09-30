# Bharat ARP

An open-source collections control tower for Indian B2B businesses using
ERPNext.

Bharat ARP is inspired by the Agentic Resource Planning thesis, but the product
starts with one measurable workflow: help finance teams recover overdue B2B
cash without replacing their ERP.

## Product Boundary

The project does **not** replace accounting, GST, banking, or legal systems. It
owns collection workflow state and proposes safe, traceable next actions around
the customer's system of record.

The first validation product is for Indian B2B distributors and light
manufacturers with material credit receivables:

- aggregate invoices and verified outstanding balances by customer
- rank the accounts most worth pursuing now
- explain the evidence behind each recommendation
- record promises to pay and later payment outcomes
- create approval-gated proposals without sending messages automatically

The first product is CSV-first and offline-capable. ERPNext, email, and
compliant messaging adapters are later gates, not prerequisites. GST/e-invoice,
UPI, bank, ONDC, Account Aggregator, payment initiation, and legal filing
workflows are explicitly deferred.

## Architecture Direction

```text
ERPNext export / CSV fixtures
                    |
           validated import
                    |
      normalized evidence ledger
                    |
      account-level decision policy
                    |
             approval workflow
                    |
          promise and payment outcomes
```

The design principles are:

- **System of record:** ERPNext remains authoritative for accounting records.
- **Governed autonomy:** deterministic policies propose; humans authorize
  sensitive actions. LLMs have no authority in the validation MVP.
- **Auditability:** every proposal will carry its source entities, policy
  version, decision, and approval history.
- **Tenant isolation:** customer and financial data must be scoped by tenant
  before retrieval, reasoning, or persistence.
- **Local-first validation:** provider integrations are optional adapters, not
  hard-coded assumptions.

## Specification-Driven Development

Read the documents in this order before implementing:

1. [Capability map](CAPABILITY-MAP.md)
2. [Product specification](SPEC.md)
3. [Domain glossary](CONTEXT.md)
4. [Implementation plan](tasks/plan.md)
5. [Task checklist](tasks/todo.md)

The plan is deliberately gated. Do not add integrations or agents before the
paid-pilot and data-quality assumptions are tested.

## Development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q
python -m build
```

The package also installs a `bharat-arp` command. The project is Apache-2.0
licensed and welcomes contributions; see [CONTRIBUTING.md](CONTRIBUTING.md),
[SECURITY.md](SECURITY.md), and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Offline Validation Workflow

The approved validation MVP is local, single-tenant, CSV-first, and has no
external side effects:

```powershell
python -m bharat_arp.cli --workspace .\workspace init --tenant TENANT-1
python -m bharat_arp.cli --workspace .\workspace import --tenant TENANT-1 --batch BATCH-1 --input .\fixtures\export
python -m bharat_arp.cli --workspace .\workspace queue --tenant TENANT-1 --as-of 2026-09-30 --format text
python -m bharat_arp.cli --workspace .\workspace queue --tenant TENANT-1 --as-of 2026-09-30 --format csv
python -m bharat_arp.cli --workspace .\workspace queue --tenant TENANT-1 --as-of 2026-09-30 --format html
python -m bharat_arp.cli --workspace .\workspace case create --tenant TENANT-1 --case CASE-1 --customer CUST-1
python -m bharat_arp.cli --workspace .\workspace promise record --tenant TENANT-1 --promise PROMISE-1 --customer CUST-1 --amount 125000.00 --due 2026-10-15
python -m bharat_arp.cli --workspace .\workspace metrics --tenant TENANT-1 --format json
python -m bharat_arp.cli --workspace .\workspace export --tenant TENANT-1 --output .\workspace\exported
python -m bharat_arp.cli --workspace .\workspace purge --tenant TENANT-1 --confirm
```

The import directory must contain the seven files specified in
[`docs/csv-contract.md`](docs/csv-contract.md). The queue uses the same
reconciliation and decisioning code covered by the test suite.

## Status

Offline validation MVP is available as open-source software. The API, data
model, and integration contracts are not stable. Do not use this repository for
production financial, tax, legal, or collection decisions. Paid pilot
validation is still pending. A synthetic end-to-end fixture is available in
[`examples/demo`](examples/demo).

## Research

- [SHAKE ARP Manifesto](https://shakegraph.com/manifesto)
- [ERPNext](https://github.com/frappe/erpnext)
- [India Compliance](https://github.com/resilient-tech/india-compliance)
- [MSME Samadhaan](https://samadhaan.msme.gov.in/)
- [Frappe Partners](https://frappe.io/partners)

See [docs/research-sources.md](docs/research-sources.md) for the public source
register and the product-boundary decisions drawn from it.
