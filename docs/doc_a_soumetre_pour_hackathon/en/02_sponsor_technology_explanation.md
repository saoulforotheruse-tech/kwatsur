# Sponsor technology explanation

All the integrations below are **working and verified with real calls** (27/10/2026), not just mentioned. Technical details (in French): `docs/sponsor-tech.md`, `docs/outils.md`, `docs/image-generation.md`.

## Zetaris — the agent's data layer

**Integration.** Zetaris runs locally in Docker (hackathon platform 2.4.3). Kwatsur uses it as the **single access point to listings**:
- every search (chat or filters) sends a SQL query to the Zetaris REST API (`POST /api/v1.0/sql-editor/sqls/run`, API key, `X-Org-ID`, `X-Request-ID`);
- the response (`headers` and `data`) is converted into listings; a `null` value stays "not specified";
- in Zetaris, Kwatsur's PostgreSQL database is registered as a federated source (`CREATE DATASOURCE kwatsur_pg`, then `REGISTER DATASOURCE TABLE`). Zetaris reads the `zetaris_listings` view through a **read-only** role limited to that view;
- listings that landlords submit in the chat become visible through Zetaris as soon as an administrator approves them, with no other step.

**Role.** Federation and query layer: tomorrow, other listing sources (partner APIs, agency CSV files) will be added in Zetaris without touching the agent's code.

**Proof.**
- `GET /api/integrations/status?live=true` → `zetaris: ok`.
- Every response carries `data_source: "zetaris"`, and the interface shows "Listings read via Zetaris".
- Real log: `POST http://127.0.0.1:8888/api/v1.0/sql-editor/sqls/run "HTTP/1.1 200 OK"`.
- If Zetaris goes down, a visible fallback to PostgreSQL is announced in the response.

Code: `app/integrations/data/zetaris.py`, view `db/migrations/versions/0002_zetaris_listings_view.py`.

## Meterless — Scout Intent engine and Nightshift

### Engine implemented: Scout Intent

Python implementation of the public `engines/scout-intent` specification (Apache-2.0), in `app/engines/scout/`. **It runs before every action of the agent**:

| Stage | What Kwatsur does |
| --- | --- |
| Sense | Deterministic scoring of the 7 intents in the catalogue: search, comparison, contact draft, landlord listing submission, picture of a room, payment, general help. Start-up self-test: under 16 ms (measured: 0.1 ms). |
| Interpret | Parameters bound to the message ("number 2", "the shower"). Four clarification triggers: low confidence, tie, missing parameter, high risk. A message with no keyword that follows a search in progress ("I'm in Bastos") continues that search. |
| Guard | Five layers: prompt injection, policy (Kwatsur makes **no payment**), scope, personal data, rate. |
| Route | Capability → tool graph: search, writing, comparison, contact, submission, photos, image generation. |
| Recommend | **Signed execution contract** (HMAC-SHA256, valid for 5 minutes), which also names the model. Every tool checks the contract before acting. A missing, altered, expired or out-of-scope contract is refused (`contract.refused`). |

**The signed contract, in plain words.** Scout is not a generative AI: it is a fast rule engine (1 ms) that decides *before* the AI. When it accepts a message, it hands the tools an **authorisation ticket**:

| What the ticket says | Example |
| --- | --- |
| Which request it authorises | `housing.search` (a search) |
| Which tools may act | listing search, reply writing |
| Risk level | `low` |
| Which model handles the request | `nvidia/nemotron-3-ultra-550b-a55b` |
| Valid until | 5 minutes |

The ticket is **signed** with a server secret key (HMAC-SHA256): change a single letter and the signature no longer matches. Every tool checks the ticket before acting; without a valid ticket, **it refuses**. As a result, even if a crafted message fooled the AI, it could not trigger any unauthorised action, such as a payment. Code: `app/engines/scout/contract.py`.

**Features it carries.**
- Routing each message to the right path: search, comparison, contact, listing submission, picture.
- Blocking injections and payment requests, without calling the model.
- Keeping the listing submission flow: while a landlord describes their property, "150,000 FCFA, 2 bedrooms" or "reachable at 69…" stay part of their description.

**Test results.**
- **Official evaluation** (thresholds from Meterless `thresholds.yaml`, regression set of 59 intents, 22 injection cases including the 10 official ones, 6 edge cases): top-1 **0.98** (floor 0.85), top-3 **1.00**, injection precision and recall **1.00**, tool precision **1.00**, clarification **0.00** (ceiling 0.25). Command: `docker exec kwatsur-api-1 python -m scripts.run_scout_evals`.
- Unit tests: `tests/unit/test_scout.py`, including altered, expired or out-of-scope contracts, all refused.
- End-to-end tests: `tests/integration/test_agent_service.py`, `tests/integration/test_submissions.py`.
- **Live**, every chat response contains its Scout trace (intent, confidence, risk, contract id, tools, model), shown under the reply, and the logs contain `scout.decision`, `contract.issued` and `contract.verified`.

### Meterless Nightshift — primary AI provider

Kwatsur calls Nightshift, and only Nightshift, for AI (`LLM_PROVIDER=meterless`), through its OpenAI-compatible API at `http://127.0.0.1:8088/v1`:
- Runtime token read from the Nightshift Console;
- headers `meterless-app: kwatsur` and `meterless-scope: user`;
- model discovery with `GET /v1/models`.

A transient outage (`502 fetch failed`) is retried once automatically. Nemotron 3 Ultra is a reasoning model: Kwatsur asks it to answer without hidden reasoning (`enable_thinking=false`, configurable with `LLM_THINKING_ENABLED`), which makes each call about four times faster (measured: 26.5 s → 6.9 s for the same extraction, identical result). Code: `app/integrations/agent_runtime/meterless.py`.

## NVIDIA — Nemotron via Nightshift

- **Model used: `nvidia/nemotron-3-ultra-550b-a55b`**, pinned in Nightshift. `meterless/auto` could route to another model. The NVIDIA key is stored in the Nightshift *Providers* tab, never in the project.
- **What Nemotron does, in operational features**:
  - understands the request and extracts the criteria as validated JSON, including the city deduced from a well-known neighbourhood ("an apartment in Bastos" → Yaoundé) (prompt `criteria_extraction.md`);
  - understands a landlord's description and fills in their listing (`listing_extraction.md`);
  - writes the explanation of the results and answers questions about a listing ("does the first one have its own meter?"), based only on the facts provided and the last 8 messages (`housing_agent.md`).
- **It does not filter, rank or decide anything**: that is the code's job.
- **Proof of the model used**: every response states `scout.model = "nvidia/nemotron-3-ultra-550b-a55b"` and `reply_generated_by = "meterless"`, and the interface shows "Written by Nemotron via Meterless · Model: nvidia/nemotron-3-ultra-550b-a55b". The log line `contract.issued … profile=nvidia/nemotron-3-ultra-550b-a55b` confirms it for every request.

## Cursor (with Space XAI)

The project was developed with AI coding assistants. The repository rules for coding agents (truthfulness, architecture, style, offline tests) are in `AGENTS.md`, which Cursor reads automatically. Part of the code was also written with Claude Code.

## What makes our use of the sponsor technologies unique

1. **Scout Intent is not window dressing.** It is the safeguard every action goes through:
   - no tool acts without a signed contract, and tests prove that forged contracts are refused;
   - it blocks the classic Cameroonian rental scams ("send the deposit by Orange Money") before any model call;
   - it is measured against the official Meterless thresholds.
2. **Zetaris federates a living database.** Listings that landlords submit in the chat, once approved by an administrator, immediately appear in searches made through Zetaris: the data layer stays the same as the sources grow.
3. **Nemotron explains without inventing.** It only receives verified facts and is instructed never to invent. When information is missing, it says so ("the description does not specify…; ask the source").
4. **Demo reliability.**
   - `SAMPLE_MODE=true` runs the whole flow without Zetaris, Nightshift or Cloudflare (fictional listings, rules, Scout active);
   - 148 tests pass without network;
   - the integrations were verified with real calls.

## Complementary technologies (not sponsors)

- **Cloudflare Workers AI**:
  - FLUX.1 schnell generates **illustrations** of a room when no photo exists. The prompt starts with an explicit instruction to depict a real home in Cameroon, followed by the listing description and Cameroonian housing context. Images are always labelled "AI-generated illustrative image";
  - LLaVA describes real photos to guide those illustrations;
  - the provider sits behind a common interface, so it can be replaced.
- **Web Speech** (browser): voice conversation; the reply is read aloud.
