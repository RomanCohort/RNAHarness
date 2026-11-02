# ESM-2 example

```json
{
  "sequences": ["MKTAYIAKQRQISFVKSHFSRQDILDLWIYHTQGYFP"],
  "pooling": "mean",
  "max_length": 512,
  "name": "esm2-demo"
}
```

```bash
python scripts/lab.py run --tool esm2 --params esm2.json --wait --out runs
```

The result contains one 1280-dimensional embedding per sequence. The current
checkpoint is the ESM-2 650M model; the earlier 8M model is retired.
