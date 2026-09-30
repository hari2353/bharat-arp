# Workflow Lifecycles

These transitions are normative for the validation MVP. Invalid transitions
must fail without mutating the current state.

## Collection Case

| From | Event | To |
|---|---|---|
| `new` | verified overdue exposure | `open` |
| `open` | assigned to operator | `assigned` |
| `assigned` | proposal accepted or manual action recorded | `in_progress` |
| `in_progress` | payment fully settles exposure | `resolved` |
| `in_progress` | no further action justified | `closed` |
| `resolved` | later source correction reopens exposure | `reopened` |
| `closed` | new overdue exposure | `reopened` |

One active case per `(tenant_id, customer_id, as_of_date)` is allowed. Multiple
invoices may belong to one case. A payment may contribute to multiple cases,
but its allocation remains authoritative in the source model.

## Collection Proposal

`proposed -> edited -> approved -> executed -> outcome_recorded`

Alternative terminal paths are `proposed -> rejected`, `proposed -> expired`,
and `approved -> execution_failed`. A proposal becomes stale when the source
balance, open-dispute state, communication eligibility, or policy version
changes. Stale proposals require re-evaluation before approval.

Approval is not execution. The validation MVP has no external execution, so
`approved` is the terminal state for customer-contact proposals until a later
provider adapter is approved.

## Promise to Pay

`proposed -> accepted -> fulfilled`

Alternative paths are `accepted -> broken`, `accepted -> cancelled`, and
`proposed -> rejected`. A partial payment records a partial outcome and does
not become `fulfilled` until the committed amount is reached or an authorized
operator explicitly closes the promise with a reason.

## Communication Eligibility

- `unknown`: only `review_required` or evidence-request proposals are allowed.
- `eligible`: a draft-only customer-contact proposal may be prepared, subject
  to approval.
- `denied` or `opted_out`: no customer-contact proposal is allowed.
- `stale` or `conflicting`: only review is allowed.

Only an explicitly authorized future role may resolve `unknown` to `eligible`;
ordinary proposal approval cannot override `denied` or `opted_out`.
