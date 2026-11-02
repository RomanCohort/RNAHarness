# RomanCohort Lab resources (v1)

Base URL: `https://www.romancohort.cloud/api/v1`

Authentication: `Authorization: Bearer $ROMANCOHORT_API_KEY`

The live manifest is `GET /api/v1/tools`; this file is a human-readable
snapshot. If they disagree, trust the live manifest.

## Common job contract

```text
POST /runs                         submit {tool, params, name?}
GET  /runs/{run_id}                status + result + file names
GET  /runs/{run_id}/events         SSE logs
GET  /runs/{run_id}/files          file manifest (+ ?hash=1 for SHA-256)
GET  /runs/{run_id}/files/{name}   authenticated download
POST /runs/{run_id}/cancel         stop the backend job
GET  /usage                        key quota and usage
```

A `409` includes `run_id` when the active job belongs to the same key. A
`429` means the daily quota is exhausted. Inputs are JSON; keep each request
under the tool's body limit.

## GATRsite (`gatsite`)

- Input: `pdb` (RNA PDB text), `threshold` 0.05–0.95 (default 0.5), `name`.
- Output: `scores.csv`, `result.json`, `log.txt`, `query.pdb`.
- Runtime: about 15 seconds for a short RNA.
- Read: probability is a model score, not an experimental binding constant.
  `rnaencoder_2d_reconstructed` means the 10-D features were rebuilt locally.

## rDock (`rdock`)

- Input: `receptor_pdb`; exactly one of `ligand_smiles` / `ligand_sdf`;
  optional `center` `[x,y,z]`, `radius` 4–25, `keep_hetero`, `runs` 1–100,
  `seed`, `protocol` (`dock` / `dock_solv`), `name`.
- Output: `poses.sd`, `receptor.mol2`, `system.prm`, `log.txt`, `result.json`.
- Read: more negative SCORE is usually better only within the same receptor
  and protocol; not an experimental binding free energy.

## HADDOCK3 (`haddock3`)

- Input: `molecules` (2–6 PDB texts), optional `active` / `passive` residue
  arrays, `sampling`, `select`, `top_models`, `ncores`, `refine`,
  `reference_pdb`, `name`.
- Output: `config.toml`, `log.txt`, `result.json`; `run/` is listed but the
  backend does not package it for download.
- Read: DockQ/Fnat/iRMSD/LRMSD are meaningful only when a reference structure
  was supplied.

## SIGNALD (`signald`)

- Input: `receptor_mol2`, `ligands` array of `{name, mol2}` (1–50), `ncpus`.
- Output: `SIGNALD_pred.csv`, `log.txt`, `result.json`, `receptor.mol2`.
- Read: `pred_norm = prediction / heavy atoms`; lower is better. It scores
  poses, it does not dock.

## BioEase (`bioease`)

- Input: `cancer` (BRCA, LUAD, LUSC, LIHC, COAD, STAD, KIRC, THCA, PRAD, HNSC),
  `force` boolean, `name`.
- Output: `summary.json`, `volcano_plot.png`, `km_*.png`,
  `survival_stats.tsv`, `DESeq2_results_Tumor_vs_Normal.annotated.tsv`.
- BRCA is cached; other cohorts may need a download and can be very slow.
- BRCA uses UCSC Xena HiSeqV2 pseudo-counts, not GDC STAR raw counts. The
  summary's `data_source`, `quantification`, and `data_warning` are
  authoritative.

## NC-Bench / NCfold (`ncbp`)

- Model: `RiNALMo giga` (655.9M parameters) loaded from `Model/model.ckpt`
  (2.5 GB).
- CPU adaptation: fused `Wqkv` is split into standard attention
  `to_q`/`to_k`/`to_v`, and `out_proj` is remapped; the load reports 0
  unexpected keys and 33 `rotary_emb.inv_freq` buffers are initialized.
- Input: either `id` (a sample name from `GET /tools/ncbp/samples`) or both
  `idx` and `amt`; optional `top_k` (default 50), `name`.
- Output: `pairs.csv`, `result.json`, `log.txt`, `sample.idx`, `sample.amt`.
- Runtime: 15.9 s for the acceptance sample `6YW5_1_aa_A_1673_U` (43 nt,
  96 graph edges, 903 candidate pairs).
- Important: this is a link predictor over an existing `.idx` + `.amt`
  annotation. It does not build annotations from a raw PDB.
- Result fields include `top_pairs` (i, j, pair, probability), `pair_count`,
  `sequence`, and `length`. Acceptance top pairs include `32-33 GU`,
  `30-31 UG`, `16-38 AU`, `33-34 UA`.
- Backend endpoints: `/health`, `/api/samples`, `/api/run`, `/api/sse`,
  `/api/result`, `/api/file`, `/api/jobs`; the public facade exposes
  `/api/v1/tools/ncbp/samples` and `/api/v1/runs`.

## ESM-2 (`esm2`)

- Input: `sequences` array (1–64), `pooling` (`mean` or `cls`, default `mean`),
  `max_length` (8–1022, default 512), `name`.
- Output: `result.json` with `embeddings`, plus `embeddings.npy` and `log.txt`;
  the current checkpoint is `facebook/esm2_t33_650M_UR50D` (650M, 1280-D).
- Runtime: a few seconds per small batch; it depends on the host. The earlier
  8M checkpoint is retired; do not describe results as 320-D.

## VaxSeer (`vaxseer`)

- Use for retrospective human influenza HA vaccine-strain screening with
  combined dominance (`lm`) and antigenicity (`hi`) models.
- Coverage: model years 2012-2021, subtypes `a_h3n2` and `a_h1n1`, 20 model
  families and 40 checkpoint archives. Model archives are extracted on first
  use; they are not all loaded into GPU memory.
- `mode=screen` uses a built-in candidate dataset. Inputs: `year`, `subtype`,
  `task` (`lm`, `hi`, `both`), optional `max_sequences` 1-1000, `name`.
- `mode=fasta` accepts `candidate_fasta` and `virus_fasta` text as well as
  `year`, `subtype`, `task`, `name`. Each virus FASTA header must contain
  `time_bin=`, `freq=`, and `bin_size=`; missing metadata is rejected by the
  worker before inference.
- Output: `dominance.csv`, `antigenicity.csv`, `vaccine_scores.csv`,
  `result.json`, `log.txt`.
- `result.json` contains `dominance`, `dominance_ranking`, `antigenicity`,
  `vaccine_scores`, and `candidate_ranking`.
- Acceptance: 2021 A/H3N2 built-in screening completed in 42.607 s at
  2,965.2 MiB peak GPU memory; 2012 A/H1N1 custom mode completed in 49.687 s
  at 4,881.2 MiB.
- Matrix endpoints: `GET /tools/vaxseer/models` and
  `GET /tools/vaxseer/datasets` through the authenticated v1 facade.
- Important: only human HA H1N1/H3N2 are covered. There are no H5N1, H9N2 or
  other IAV subtype checkpoints. The latest model year is 2021 and temporal
  extrapolation beyond it is not supported. Rankings are model outputs, not
  clinical efficacy or experimental HI conclusions.

## RhoFold+ (`rhofold`)

- Input: `sequence` (20–1000 nt), optional `msa` text and `name`.
- Output: `model.pdb`, `scores.json`, `log.txt`.
- Runtime: minutes; length and MSA size dominate.

## PhysiCell (`physicell`)

- Input: `preset` (`cancer_immune`, `biorobots`, `heterogeneity`), `minutes`
  (1–10080), `seed`, optional free-form `params`, `name`.
- Output: `summary.json`, `log.txt`, and `frames/*.svg`; the summary is also
  present inline in the run result.
- Runtime: scales with simulated duration and preset.

## ViennaRNA (`vienna`)

- Input: `tool` (`fold`, `plfold`, `cofold`, `duplex`, `subopt`, `eval`,
  `alifold`, `distance`) and a free-form `params` object, optional `name`.
- Use `lab tools --json` or `GET /tools` for the current per-mode parameter
  contract; tool-specific parameters remain backend-defined.
- Output: inline result; logs stream over SSE.

## GEMORNA (`gemorna`)

- Input: `mode` (`cds`, `5utr`, `3utr`, `pred5utr`, `pred3utr`) and a
  free-form `params` object, optional `name`.
- Output: inline result; logs stream over SSE.
- Runtime: usually seconds on CPU.

## RNAdvisor (`rnadvisor`)

- Input: `pdb`, optional `native_pdb`, `scores` array, `name`.
- Output: inline score result; logs stream over SSE.
- Read: metric names and direction depend on the selected scorer/native
  reference; preserve them rather than normalizing every score to “higher is
  better”.

## LNPDB (`lnpdb`)

- Query-only; do not submit it through `POST /runs`.
- Search: `GET /lnpdb/search` with optional `q`, `cargo`, `route`, `model`,
  `limit` 1–200, `offset`.
- Download: `GET /lnpdb/download` returns the full 66-column `LNPDB.csv`.
- The search index contains 19,797 formulations. Filter fields in the compact
  index are `id`, `il`, `cargo`, `ctype`, `model`, `mtype`, `route`, `value`,
  `pmid`, `mw`, `logp`; the CSV has the complete formulation and lipid fields.
- Use `lab.py lnpdb-search` and `lab.py lnpdb-download`.

## Scope boundary

The friend key covers every externally hosted project listed by the live
manifest. Private self-hosted tools outside that group (for example TorusFold
and RNAQwen) remain outside this skill's scope. Always trust `lab tools --json`
for current scope and availability.
