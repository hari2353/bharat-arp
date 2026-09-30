# Pilot Interface

The validation MVP uses a CLI and generated CSV/HTML reports. This is the
smallest surface that can be run on a customer's machine without introducing a
hosted authentication, browser, or provider dependency.

## Commands

```text
bharat-arp import --tenant TENANT --batch BATCH --input ./export/
bharat-arp queue --tenant TENANT --as-of 2026-09-30 --format html
bharat-arp case show --tenant TENANT --case CASE_ID
bharat-arp proposal decide --tenant TENANT --proposal PROPOSAL_ID --decision approve
bharat-arp promise record --tenant TENANT --case CASE_ID --amount 125000 --due 2026-10-15
bharat-arp outcome record --tenant TENANT --case CASE_ID --outcome payment_received
bharat-arp metrics --tenant TENANT --from 2026-09-01 --to 2026-10-31
bharat-arp export --tenant TENANT --output ./exported/
bharat-arp purge --tenant TENANT --confirm
```

The exact command names are implementation details; the capabilities are the
contract. Every command requires an explicit tenant and writes an audit event.
The queue report must show customer, verified exposure, ageing, risk flags,
source freshness, recommendation, evidence, and unresolved exceptions.

The next interface gate is a local web application only after the CLI workflow
has been used in paid pilots and the hosted authorization matrix is approved.
