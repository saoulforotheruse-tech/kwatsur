# GitHub repository checklist

Repository: <https://github.com/saoulforotheruse-tech/kwatsur>

## Required

| Requirement | Where | Status |
| --- | --- | --- |
| **Public** repository | <https://github.com/saoulforotheruse-tech/kwatsur> | Done (checked 27/10: reachable without signing in) |
| Full source code | Branch `version4.0` | **To do**: merge `version4.0` into `main` (the branch judges see by default) |
| README: setup from a clean clone | README, sections "Démarrage rapide (Docker)" and "Dépendances" | Done |
| README: usage with example inputs | README, section "Utilisation" (7 examples) | Done |
| README: dependencies, including Zetaris and Nightshift | README, section "Dépendances" | Done |
| Colab links | — | Not applicable (no agent on Colab) |

The README is in French, like the product; the English summary of the project is in this folder.

## Recommended

| Recommendation | Where | Status |
| --- | --- | --- |
| At least 3 input/output examples | `05_input_output_examples.md` (7 real examples) | Done |
| Logs or traces, including the model of each request | `scout` field of every response (`model`, `contract_id`, `tool_plan`); logs `scout.decision` and `contract.*` | Done |
| Test showing the Meterless engine works | `tests/unit/test_scout.py`, `python -m scripts.run_scout_evals` (official thresholds) | Done |
| `.env.example` with placeholder values only | `.env.example` | Done (no secret) |
| `SAMPLE_MODE=true` fallback | `app/core/config.py` (`apply_sample_mode`), README | Done |
| No key or credential in the repository | `.env`, `frontend/.env`, `token.txt`, `zetaris-platform/` and `media/` ignored by git; history checked | Done |
| NVIDIA key in the Nightshift Providers tab, not in the project | `docs/outils.md`, section 3 | Done |

## Check from a clean clone (sample mode)

```sh
git clone https://github.com/saoulforotheruse-tech/kwatsur.git && cd kwatsur
cp .env.example .env              # no key: fictional listings, rules, Scout active
docker compose up --build -d      # backend: migrations and 20 fictional listings
cd frontend && cp .env.example .env && docker compose up --build -d
# → http://localhost:8080
```

The WhatsApp screenshots of the submission instructions (parent folder) are not versioned: they are phone screen photos.
