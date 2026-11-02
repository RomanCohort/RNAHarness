# LNPDB search and download

Search by a free-text term:

```bash
python scripts/lab.py lnpdb-search --query siRNA --limit 20
```

Apply exact compact-index filters:

```bash
python scripts/lab.py lnpdb-search \
  --query siRNA --cargo siRNA --route in_vitro --limit 20 --json
```

Download the full CSV:

```bash
python scripts/lab.py lnpdb-download --out LNPDB.csv
```

LNPDB is query-only. Do not submit it as an asynchronous run.
