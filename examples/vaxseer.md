# VaxSeer example

Inspect the available model and dataset matrix:

```bash
curl -sS https://www.romancohort.cloud/api/v1/tools/vaxseer/models \
  -H "Authorization: Bearer $ROMANCOHORT_API_KEY"

curl -sS https://www.romancohort.cloud/api/v1/tools/vaxseer/datasets \
  -H "Authorization: Bearer $ROMANCOHORT_API_KEY"
```

Built-in 2021 A/H3N2 screening:

```json
{
  "mode": "screen",
  "year": "2021",
  "subtype": "a_h3n2",
  "task": "both",
  "max_sequences": 128,
  "name": "vaxseer-screen-2021-h3n2"
}
```

```bash
python scripts/lab.py run --tool vaxseer --params vaxseer.json --wait --download
```

Custom FASTA mode uses the same fields plus `mode: "fasta"`,
`candidate_fasta`, and `virus_fasta`. Every virus FASTA header must include
`time_bin=`, `freq=`, and `bin_size=`, for example:

```text
>virus_a time_bin=110 freq=0.5 bin_size=1
MKTAY...
```

VaxSeer covers human HA A/H3N2 and A/H1N1 for model years 2012–2021 only.
Do not use it for H5N1/H9N2 or describe predictions beyond 2021 as temporal
extrapolation.
