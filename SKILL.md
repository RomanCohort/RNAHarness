---
name: romancohort-lab
description: Use RomanCohort's externally hosted lab resources through one API key, including RNA structure and binding, molecular docking, TCGA analysis, protein embeddings, influenza screening, cell simulation, LNPDB search/download, and other hosted projects. Use when the user asks to inspect, submit, monitor, cancel, query, or download a lab resource.
---

# RomanCohort Lab

Use this skill for experiments hosted on `https://www.romancohort.cloud`.
The API is versioned under `/api/v1/`; do not call the per-tool `/api/...`
endpoints directly.

## Before choosing a tool

Always run:

```bash
python scripts/lab.py tools --json
```

The returned manifest is the source of truth for tool ids, parameter schemas,
limits, cached data, and current availability. If a tool is absent or
`status != "ready"`, say it is unavailable; do not invent parameters or
results.

## Authentication

The key is read from `ROMANCOHORT_API_KEY`. Never print it, put it in a URL,
commit it, or write it into a parameters file. If it is missing or rejected,
ask the user to set it and stop.

```bash
export ROMANCOHORT_API_KEY='rc_lab_...'
```

## Tools in v1

| id | Use for | Typical output |
|---|---|---|
| `gatsite` | RNA binding-site probabilities | `scores.csv`, `result.json`, `log.txt`, `query.pdb` |
| `rdock` | rDock small-molecule docking | `poses.sd`, `receptor.mol2`, `log.txt`, `result.json` |
| `haddock3` | 2–6 molecule HADDOCK3 docking | `config.toml`, `log.txt`, `result.json` |
| `signald` | Score ligand poses | `SIGNALD_pred.csv`, `log.txt`, `result.json` |
| `bioease` | TCGA DESeq2 + survival | `summary.json`, `volcano_plot.png`, KM PNGs, TSVs |
| `ncbp` | NC-Bench / NCfold non-canonical base-pair scoring | `pairs.csv`, `result.json`, `sample.idx`, `sample.amt` |
| `esm2` | ESM-2 protein embeddings (650M, 1280-D) | `result.json` with `embeddings` |
| `vaxseer` | Influenza HA dominance + antigenicity screening | rankings, CSVs, `result.json`, `log.txt` |
| `rhofold` | RNA 3D structure prediction | `model.pdb`, `scores.json`, `log.txt` |
| `physicell` | Agent-based multicellular simulation | `summary.json`, `log.txt`, SVG frames |
| `vienna` | ViennaRNA folding and ensemble calculations | inline result |
| `gemorna` | mRNA CDS/UTR design or UTR scoring | inline result |
| `rnadvisor` | RNA 3D structure scoring | inline scores |
| `lnpdb` | Search/download lipid-nanoparticle formulations | JSON rows or `LNPDB.csv` |

Detailed inputs, outputs and caveats are in `references/resources.md`.

## Run workflow

1. Write the chosen tool's parameters to a JSON file. Use only fields from
   `lab tools --json`.
2. Submit and follow the job:

```bash
python scripts/lab.py run --tool gatsite --params params.json --wait --download --out runs
```

3. Report the returned `run_id`, final status, downloaded files, and any
   backend warnings. The CLI prints logs to stderr and the final JSON to
   stdout, so Claude can read the machine-readable result.

For long jobs, run without `--wait` first, keep the `run_id`, and use:

```bash
python scripts/lab.py status RUN_ID
python scripts/lab.py logs RUN_ID
python scripts/lab.py download RUN_ID --out runs
```

For NC-Bench / NCfold, list the available samples first:

```bash
python scripts/lab.py samples --tool ncbp
python scripts/lab.py run --tool ncbp --params ncbp.json --wait --download --out runs
```

`ncbp` accepts either a sample `id`, or `idx` + `amt`; it does not accept a raw
PDB. ESM-2 expects a `sequences` list; the installed checkpoint is the 650M
model with 1280-dimensional embeddings (up to 64 sequences, max_length 8–1022).
VaxSeer supports 2012–2021 human HA A/H3N2 and A/H1N1. Use
`mode=screen` for the built-in candidate set or `mode=fasta` with
`candidate_fasta` and `virus_fasta`; it has no H5N1/H9N2 checkpoints and does
not extrapolate beyond model year 2021.

LNPDB is query-only, so use its dedicated commands instead of `/runs`:

```bash
python scripts/lab.py lnpdb-search --query siRNA --limit 20
python scripts/lab.py lnpdb-download --out LNPDB.csv
```

VaxSeer's model and dataset matrices are available through:

```bash
python scripts/lab.py models --tool vaxseer
python scripts/lab.py datasets --tool vaxseer
```

## Failure rules

- `409` means a job is already running. The CLI attaches to the returned
  `run_id`; do not submit a second job.
- `429` means the key's daily quota is exhausted. Report the quota and stop.
- `401`/`403` means a key or scope problem; do not retry blindly.
- `5xx` means the service or a tool is offline. Show the error and do not
  fabricate a result.
- `stopped`/`error` jobs are not successful experiments. Show the log tail and
  say they failed or were cancelled.

## Output discipline

- Keep the backend `result.json` fields intact; do not rename `pred_norm`,
  `log2FoldChange`, `padj`, or `HR`.
- For BioEase, preserve the provenance warning: BRCA currently uses UCSC Xena
  pseudo-counts, not GDC STAR raw counts. Uncached cohorts may be
  download-bound.
- Do not turn a docking score or survival p-value into a causal claim.
