# NC-Bench / NCfold example

```bash
python scripts/lab.py samples --tool ncbp
```

```json
{
  "id": "6YW5_1_aa_A_1673_U",
  "top_k": 50,
  "name": "ncbp-demo"
}
```

```bash
python scripts/lab.py run --tool ncbp --params ncbp.json --wait --download --out runs
```

The sample id must be one returned by `samples`. The result contains
`top_pairs` with `i`, `j`, `pair` and `probability`, plus `pairs.csv`.
