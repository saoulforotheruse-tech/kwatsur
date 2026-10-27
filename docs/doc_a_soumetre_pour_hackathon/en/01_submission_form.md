# HackOS submission form

Texts ready to copy into the form.

## Project name

**Kwatsur**

## Short description (one sentence)

Kwatsur is a conversational agent that helps people find a home to rent in Cameroon: it understands requests typed or spoken in French, queries listings through Zetaris, ranks the results and explains every recommendation without ever inventing information.

## Full description

In Douala and Yaoundé, looking for a place to rent means digging through scattered, incomplete and sometimes outdated listings, with a real risk of scams (advance payment requested before any visit). Kwatsur does this work for the user.

**For people looking for a home.** They describe what they need as they would to a friend ("a two-bedroom in Douala near Bonamoussadi, 150,000 FCFA max, with water and electricity"), by keyboard or by voice. The agent:
- extracts the criteria with NVIDIA Nemotron, including the city deduced from a well-known neighbourhood ("an apartment in Bastos" → Yaoundé);
- queries the listings through **Zetaris**;
- applies the mandatory criteria and ranks the results with deterministic code, with reasons, trade-offs and points to check;
- flags potential risks (unusually low rent, old listing);
- has Nemotron explain all of this, based only on the computed facts.

They can refine ("actually 110,000 max"), compare ("compare the first and the second"), ask a question about a listing, draft a message to the landlord, or see a room ("show me the shower of number 2"). In that case Kwatsur distinguishes owner photos, credited sample photos and clearly labelled AI illustrations.

**For landlords.** They describe their property in the chat ("I'm renting out my studio in Bastos…"). The agent asks for what is missing, accepts photos, then sends the listing to an administrator who approves it before anything is published.

**Conversation-first interface.** Listing cards and comparison live in a collapsible panel, closed by default, with a visible result count. Users can describe a search across several messages without losing previously collected criteria.

**Images only on request.** Ordinary searches do not send images into the chat. A request naming Logpom targets that listing rather than automatically picking the first result; ambiguous targets require clarification. Owner photos, credited sample photos and AI illustrations remain distinct. The Cloudflare prompt reserves room for Cameroonian urban context within 2,048 characters, without claiming to reconstruct the actual home. Existing illustrations are reused without new generation; the daily limit applies across the application.

**Persistent moderation.** Confirmed proposals are stored in `listing_submissions` as `pending`, without a published listing. At `/admin.html`, administrators review details and photos, approve or reject with a note, and filter past decisions. Approval creates the listing in `properties` and attaches its photos; it does not certify the landlord or availability. The dashboard requires `ADMIN_TOKEN` and includes logout.

**Before tool actions**, the **Meterless Scout Intent** engine:
- recognises the intent;
- blocks prompt injections and any payment request;
- signs an execution contract that every tool checks.

By default, `SCOUT_ROUTING_ENABLED=false` avoids classifying search fragments: standalone greetings receive fixed replies, while explicit image and submission requests retain guards and signed contracts. Chat comparison and contact commands require `true`; their card buttons remain available.

The model is served by **Meterless Nightshift** (primary AI provider), with **NVIDIA Nemotron 3 Ultra** pinned.

Design rule: *AI understands and explains, code decides*. Unknown information stays "not specified", never guessed.

## Team

| Member | GitHub |
| --- | --- |
| Raoul DARIL Tankam Soh | saoulforotheruse-tech |
| NOUBISSI mEIKEM Indira Leslie | ravenger26 |

Team name on HackOS: **Kwatsur** (2 members).

## Track (only one)

Recommended: **The Agent That Can Explain Why**. Kwatsur produces evidence-based recommendations:
- every proposed listing comes with its reasons, trade-offs, points to check and risk signals, computed from the data;
- the explanation is written by Nemotron based on those facts only;
- when information is missing, the agent says so.

Alternative: *Solving Fragmented Intelligence* (scattered listings brought together behind Zetaris).

## Pre-existing components (declaration)

- No code written before the build window opened (22/10/2026). First commit of the repository: 23/10/2026.
- Open-source libraries: FastAPI, SQLAlchemy, Alembic, Pydantic, httpx, pytest, nginx, PostgreSQL.
- Meterless Scout Intent specification, evaluation thresholds and injection set: public Meterless repository (Apache-2.0). The Python implementation is ours.
- 4 sample photos from Wikimedia Commons (CC BY-SA, credits shown) and 20 **fictional** listings for the demo.
