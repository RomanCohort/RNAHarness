# RomanCohort Lab skill

This folder is a Claude Code skill plus a small CLI client.

## Install

Copy the folder to one of:

- `~/.claude/skills/romancohort-lab/`
- `<project>/.claude/skills/romancohort-lab/`

Set the key:

```bash
export ROMANCOHORT_API_KEY='rc_lab_...'
```

Smoke test:

```bash
python scripts/lab.py tools
python scripts/lab.py usage
```

No third-party Python packages are required. The client uses only the standard
library.

## Commands

```text
lab.py tools [--json]
lab.py health
lab.py run --tool TOOL --params params.json [--wait] [--download]
lab.py status RUN_ID
lab.py logs RUN_ID
lab.py files RUN_ID [--hash]
lab.py download RUN_ID --out runs
lab.py cancel RUN_ID
lab.py samples --tool ncbp
lab.py models --tool vaxseer
lab.py datasets --tool vaxseer
lab.py lnpdb-search --query siRNA --limit 20
lab.py lnpdb-download --out LNPDB.csv
lab.py usage
```

The API key is sent as `Authorization: Bearer ...`; it is never printed or
stored in the output directory.
