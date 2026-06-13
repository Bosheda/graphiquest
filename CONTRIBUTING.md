# Contributing to GraphiQuest

GraphiQuest is a local-first, dependency-light tool (Python standard library only).
It is built on top of the open-source [Graphify](https://github.com/safishamsi/graphify)
scanner by safishamsi (MIT) — GraphiQuest does not modify or vendor Graphify.

## Run it locally

```bash
uv tool install graphifyy      # the Graphify scanner CLI (one time)
graphify update .              # graph this repo
python scripts/start_graphify_dashboard.py
```

## Run the tests

```bash
python -m unittest discover -s tests -p "test_graphify_*.py"
```

All tests must pass before a PR. The package-clean guard
(`tests/test_graphify_package_clean.py`) fails the build if any shipped source
leaks project-specific taxonomy — keep the default taxonomy generic.

## Style

Standard library only for the dashboard; no new runtime dependencies. Match the
surrounding code. Keep the connector honest — never claim "connected" without
current-session proof.
