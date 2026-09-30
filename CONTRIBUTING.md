# Contributing to Bharat ARP

Thank you for contributing. Bharat ARP is Apache-2.0 licensed open-source
software focused on deterministic, approval-gated collections workflows.

## Scope

Contributions should preserve these boundaries:

- ERPNext or another accounting system remains the system of record.
- The validation MVP is local, single-tenant, CSV-first, and offline-capable.
- Imported values are untrusted and must retain provenance.
- No proposal may send a message, change an accounting record, initiate a
  payment, file a legal claim, or perform a tax action.
- Do not add provider integrations or LLM authority without first updating the
  specification and adding an explicit approval gate.

## Development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q
python -m build
```

The project must remain usable without network access after dependencies are
installed. Tests must not contain real customer, contact, payment, or secret
data.

## Pull Requests

- Explain the user-facing behavior and the reason for the change.
- Add or update tests for every behavior change.
- Update the relevant specification, contract, or lifecycle document.
- Keep commits focused and do not include build output, virtual environments,
  `.env` files, or customer exports.
- Run `git diff --check` before submitting.

## Security and Privacy

Do not report security issues in a public issue. Follow
[SECURITY.md](SECURITY.md). Never commit credentials, private exports, or
personal contact data.
