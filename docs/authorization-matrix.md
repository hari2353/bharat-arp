# Authorization Matrix

## Validation MVP

The validation MVP is a single-tenant local deployment with one configured
`pilot_operator`. It has no hosted authentication and no external side effects.
The operator may import, inspect, rank, record a proposal decision, record a
Promise to Pay, export, or purge the local tenant. The CLI records the operator
identity in every audit event. This mode is for controlled pilot validation,
not multi-user production use.

## Later Hosted Mode

The following matrix is a gate for hosted or multi-user work:

| Action | Collections Operator | Finance Lead | Business Owner | Integration Admin |
|---|---:|---:|---:|---:|
| Import source batch | No | Yes | No | Yes |
| Edit data-quality annotation | Yes | Yes | No | No |
| Create proposal | Yes | Yes | No | No |
| Approve customer-contact draft | No | Yes | Yes | No |
| Resolve unknown eligibility | No | Yes | Yes | No |
| Approve credit escalation | No | Yes | Yes | No |
| Record Promise to Pay | Yes | Yes | No | No |
| Change policy weights | No | Yes | Yes | No |
| Export tenant data | No | Yes | Yes | Yes |
| Purge tenant data | No | No | Yes | No |
| Configure source/provider | No | No | No | Yes |

Additional hosted-mode rules:

- No user may approve their own proposal.
- Every authorization is tenant-scoped.
- A changed balance, dispute, permission, or policy version makes a proposal
  stale and requires re-evaluation.
- `denied` and `opted_out` communication states cannot be overridden by the
  approval matrix.
