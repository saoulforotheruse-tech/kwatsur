# Sponsor technology explanation

The evidence below records real calls on 27/10/2026, not permanent service availability. Recent searches received a Zetaris rejection and used the explicitly reported PostgreSQL fallback. Nightshift/Nemotron, Cloudflare generation and pending submission with admin rejection were verified live; approval and photo attachment are also covered offline. Technical details (French): `docs/sponsor-tech.md`, `docs/image-generation.md`.

## Zetaris — the agent's data layer

**Integration.** Zetaris runs locally in Docker (hackathon platform 2.4.3). Kwatsur uses it as the **configured primary listing source**, with a visible PostgreSQL fallback:
- every search (chat or filters) sends a SQL query to the Zetaris REST API (`POST /api/v1.0/sql-editor/sqls/run`, API key, `X-Org-ID`, `X-Request-ID`);
- the response (`headers` and `data`) is converted into listings; a `null` value stays "not specified";
- in Zetaris, Kwatsur's PostgreSQL database is registered as a federated source (`CREATE DATASOURCE kwatsur_pg`, then `REGISTER DATASOURCE TABLE`). Zetaris reads the `zetaris_listings` view through a **read-only** role limited to that view;
- listings that landlords submit in the chat become visible through Zetaris as soon as an administrator approves them, with no other step.

**Role.** Federation and query layer: tomorrow, other listing sources (partner APIs, agency CSV files) will be added in Zetaris without touching the agent's code.

**Historical evidence (recorded successful call).**
- `GET /api/integrations/status?live=true` → `zetaris: ok`.
- Searches in this recording carried `data_source: "zetaris"`; the interface must always report the source actually used.
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

### Current routing configuration

`SCOUT_ROUTING_ENABLED=false` is the default: search fragments are not classified, preserving accumulated criteria. Explicit image and listing-submission requests still use parameter binding, guards and signed contracts; chat comparison and contact commands require `true`. The classification metrics above describe full Scout mode, not the simplified mode. Fixed courtesy replies do not call the model.

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
- **Proof of the model used**: replies generated in the Nightshift checks state `scout.model = "nvidia/nemotron-3-ultra-550b-a55b"` and `reply_generated_by = "meterless"`. The interface and logs expose this provenance; fixed or fallback replies carry `template`, not a fabricated model attribution.

## Cloudflare — on-demand images

- No images are sent into the chat without an explicit visual request. Image metadata remains part of the text model's facts; it does not receive image pixels.
- Named targets are resolved before the call: Logpom is not replaced by a first-ranked home elsewhere. Ambiguous or missing names cause clarification, not generation.
- For the requested room: owner photo, credited sample photo, existing illustration, then a new FLUX.1 schnell illustration.
- `build_illustration_prompt` reserves Douala/Yaoundé context within 2,048 characters: documentary style, urban housing, known facts taking priority. Regional context is not evidence of the actual architecture.
- `IMAGE_GENERATION_DAILY_LIMIT` counts successfully stored generations application-wide since midnight UTC (1 a.m. in Cameroon), separately from Cloudflare quota. Reuse costs no new generation.
- A real call generated the fictional Logpom apartment facade from its description alone: the image was stored, served with HTTP 200 and explicitly labelled AI.

## Submissions and administration

Chat confirmation → `listing_submissions.pending` → decision at `/admin.html`, protected by `ADMIN_TOKEN`. No published `properties` row exists before approval. Approval creates the listing and attaches photos; rejection retains the proposal and note without publication. Dates, filters, decision notes and logout are available. Review locks the row to serialize concurrent decisions; a second decision returns 409. Approval never means a verified landlord or confirmed availability.

Latest offline suite: **214 passed, 2 skipped**. Live check: a fictional proposal was committed as pending in PostgreSQL, then rejected without publication. Dashboard interactions were also checked using simulated data, separately from that live verification.

## Cursor (with Space XAI)

The project was developed with AI coding assistants. The repository rules for coding agents (truthfulness, architecture, style, offline tests) are in `AGENTS.md`, which Cursor reads automatically. Part of the code was also written with Claude Code.

## What makes our use of the sponsor technologies unique

1. **Scout Intent is not window dressing.** It is the safeguard every action goes through:
   - no tool acts without a signed contract, and tests prove that forged contracts are refused;
   - it blocks the classic Cameroonian rental scams ("send the deposit by Orange Money") before any model call;
   - it is measured against the official Meterless thresholds.
2. **Zetaris federates a living database.** Listings that landlords submit in the chat, once approved by an administrator, immediately appear in searches made through Zetaris: the data layer stays the same as the sources grow.
3. **Nemotron explains computed facts.** It receives code results and listing declarations, not a certification of their accuracy. Its prompt forbids invention and requires missing information to be flagged.
4. **Demo reliability.**
   - `SAMPLE_MODE=true` runs the whole flow without Zetaris, Nightshift or Cloudflare (fictional listings, rules, Scout active);
   - latest offline suite: **214 passed, 2 skipped**;
   - historical real calls and recent fallback status are distinguished above.

## Complementary technologies (not sponsors)

- **Cloudflare Workers AI**:
  - FLUX.1 schnell generates **illustrations** on request after checking reusable photos or illustrations. The prompt reserves Cameroonian urban context and gives listing facts priority. Images are always labelled "AI-generated illustrative image";
  - LLaVA describes real photos to guide those illustrations;
  - the provider sits behind a common interface, so it can be replaced.
- **Web Speech** (browser): voice conversation; the reply is read aloud.
