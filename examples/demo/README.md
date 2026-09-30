# Synthetic Demo Data

This directory contains deliberately synthetic INR records for a local smoke
test. It is not real customer or ERPNext data and must not be used as a
financial decision.

Run from the repository root:

```powershell
python -m bharat_arp.cli --workspace .\examples\demo init --tenant DEMO-1
python -m bharat_arp.cli --workspace .\examples\demo import --tenant DEMO-1 --batch DEMO-BATCH-1 --input .\examples\demo\input
python -m bharat_arp.cli --workspace .\examples\demo queue --tenant DEMO-1 --as-of 2026-09-30 --format html
python -m bharat_arp.cli --workspace .\examples\demo export --tenant DEMO-1 --output .\examples\demo\exported
```

The generated tenant state and export are ignored by Git.
