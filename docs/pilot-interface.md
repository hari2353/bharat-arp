# Pilot Interface

The validation MVP uses a CLI and generated CSV/HTML reports. This is the
smallest surface that can be run on a customer's machine without introducing a
hosted authentication, browser, or provider dependency.

## Commands

```text
bharat-arp import --tenant TENANT --batch BATCH --input ./export/
bharat-arp queue --tenant TENANT --as-of 2026-09-30 --format text|csv|html
bharat-arp case show --tenant TENANT --case CASE_ID
bharat-arp proposal decide --tenant TENANT --proposal PROPOSAL_ID --decision approve
bharat-arp proposal edit --tenant TENANT --proposal PROPOSAL_ID --action review_required --evidence EVIDENCE
bharat-arp case assign --tenant TENANT --case CASE_ID --assignee OPERATOR_ID
bharat-arp promise record --tenant TENANT --case CASE_ID --amount 125000 --due 2026-10-15
bharat-arp promise fulfil --tenant TENANT --promise PROMISE_ID --amount 50000
bharat-arp outcome record --tenant TENANT --case CASE_ID --outcome payment_received
bharat-arp metrics --tenant TENANT --from 2026-09-01 --to 2026-10-31 --format json
bharat-arp metrics --tenant TENANT --snapshot 2026-10-07 --format json
bharat-arp retention apply --tenant TENANT --as-of 2026-10-03
bharat-arp export --tenant TENANT --output ./exported/
bharat-arp purge --tenant TENANT --confirm
```

The exact command names are implementation details; the capabilities are the
contract. Every command requires an explicit tenant and writes an audit event.
The queue report shows customer, verified exposure, ageing, policy version,
recommendation evidence, and unresolved/risk inputs. HTML and CSV output are
deterministic and contain no external resources. The metrics command retains
persisted workflow/import counts and can create one immutable snapshot per
tenant and as-of date. Snapshots report account and INR coverage, ageing
cohorts, eligibility, and Promise-to-Pay status without causal claims about
observed payments.

The next interface gate is a local web application only after the CLI workflow
has been used in paid pilots and the hosted authorization matrix is approved.
