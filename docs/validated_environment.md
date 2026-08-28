# v1.0 validated environment snapshot

This is the direct-package environment used for the local v1.0 release validation on 2026-08-28.
It is recorded for reproducibility and auditability. It is **not** a complete transitive lockfile;
`pyproject.toml` remains the package dependency contract.

- Python: 3.13.5
- numpy: 2.3.5
- pandas: 2.2.3
- scipy: 1.17.0
- scikit-learn: 1.8.0
- statsmodels: 0.14.6
- matplotlib: 3.10.8
- pydantic: 2.13.4
- PyYAML: 6.0.3
- pytest: 9.0.2
- pytest-cov: 7.0.0
- nbclient: 0.10.4
- nbformat: 5.10.4

Ruff and mypy are declared development dependencies and are run by CI. They were not installed in
the offline local release runtime, so the local validation receipt does not claim their execution.
