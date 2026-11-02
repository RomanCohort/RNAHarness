# BioEase example

```json
{
  "cancer": "BRCA",
  "force": false,
  "name": "brca-from-claude"
}
```

```bash
python scripts/lab.py run --tool bioease --params brca.json --wait --download --out runs
```

BRCA is cached and normally returns in a few minutes. Do not set `force=true`
unless the user explicitly asks to ignore the cache. Other cohorts may trigger
a long download and should not be started without confirmation.

Read `summary.json` and report `data_source`, `quantification`, and
`data_warning`; do not describe the BRCA fallback as GDC raw counts.
