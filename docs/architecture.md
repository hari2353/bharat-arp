# Architecture Notes

## Why a Decision Layer?

The manifesto's useful distinction is between a legally defensible record and
a system that helps decide what happens next. Bharat ARP applies that idea
without pretending that an agent can replace accounting controls.

## Initial Contracts

The first contracts are intentionally small:

- `Invoice`: a normalized receivables fact from an ERP or import.
- `CollectionProposal`: a non-mutating recommendation with a channel,
  explanation, and approval requirement.

Future contracts should add `tenant_id`, source references, idempotency keys,
policy versions, and immutable decision records before integration side effects
are implemented.

## India Scope

The first target is Indian SMB order-to-cash operations. GST submission,
e-invoice, e-waybill, UPI, and bank integrations must remain explicit provider
boundaries. The core engine should work with fixtures and local data so a user
does not need a paid API account to evaluate the project.

## Safety Rules

- No autonomous payment initiation in the MVP.
- No autonomous GST submission in the MVP.
- No unrestricted SQL, shell, or HTTP tools exposed to a model.
- No customer data sent to a model provider without explicit configuration and
  an appropriate data-processing agreement.
- All outbound actions require an idempotency key and an audit record.
