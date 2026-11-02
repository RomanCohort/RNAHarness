# GATRsite example

```json
{
  "pdb": "ATOM      1  P       0.000   0.000   0.000  1.00  0.00           P\n",
  "threshold": 0.5,
  "name": "demo-gatsite"
}
```

```bash
export ROMANCOHORT_API_KEY='rc_lab_...'
python scripts/lab.py tools --json
python scripts/lab.py run --tool gatsite --params gatsite.json --wait --download --out runs
```

The final JSON contains `run_id`, `status`, `files`, and the output directory.
If the job was already running, the CLI reports `[attach]` and follows that
job instead of submitting a second one.
