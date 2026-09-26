# Drill 2 — URDF joint graph validator

Implement `validate_tree` in `starter.py`. It takes `(parent, child)` joint pairs and returns the single root. It must reject malformed pairs, duplicate children, self-parents, multiple roots, and cycles, including a cycle detached from the main tree.

## Run

```powershell
python -m pytest test_lab.py -q                                                          # your starter.py
$env:LAB_IMPL = "solution"; python -m pytest test_lab.py -q; Remove-Item Env:LAB_IMPL   # the reference
```

The tests fail until `starter.py` is complete. The docstring there is the specification. Record the first assumption that failed before you read `solution.py`.

Follow-up: parse the pairs from URDF XML with `xml.etree.ElementTree`.
