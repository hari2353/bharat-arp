# Security Policy

## Supported Versions

Only the latest commit on `main` is supported while the project is in
validation. The package is not a production financial, tax, legal, messaging,
or payment system.

## Reporting a Vulnerability

Do not open a public issue for a suspected vulnerability. Contact the
repository maintainers privately through the GitHub repository owner profile
and include:

- a short description of the impact;
- the affected file, command, or version;
- reproducible steps using synthetic data only;
- a suggested mitigation, if known.

Do not include secrets, real customer records, contact details, or financial
exports in a report.

## Security Boundaries

- The CLI is local and has no hosted authentication.
- Tenant identifiers are explicit and validated.
- CSV input is size-limited and formula-bearing exports are neutralized.
- Communication eligibility is never inferred from a phone number or email
  address.
- Approval never executes an external side effect.
- ERPNext, banking, GST, Account Aggregator, messaging, payment, and legal
  integrations are intentionally out of scope for the validation MVP.
