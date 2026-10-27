# Kwatsur — submission folder (Open Agent Hackathon 2026)

Deadline (**firm**): **27 October 2026, 23:45 UTC**, on HackOS. Nothing can be added or changed afterwards.

This folder contains everything required by the "Submission requirements" page. French version: [`../fr/`](../fr/README.md).

| Required item | File | Status |
| --- | --- | --- |
| Form: name, description, team, track, pre-existing components | [`01_submission_form.md`](./01_submission_form.md) | Ready (copy into HackOS) |
| Sponsor technology explanation (10 points) | [`02_sponsor_technology_explanation.md`](./02_sponsor_technology_explanation.md) | Ready |
| Demo video, 1 to 4 min (15 points) | [`03_demo_video_script.md`](./03_demo_video_script.md) | **Script ready, video to record** |
| PowerPoint presentation | [`04_kwatsur_presentation.pptx`](./04_kwatsur_presentation.pptx) | Ready (to proofread) |
| Input/output examples, traces, model used (recommended) | [`05_input_output_examples.md`](./05_input_output_examples.md) | Ready (real outputs, 27/10/2026) |
| Public GitHub repository with README (setup, usage, dependencies) | [`06_github_repository_checklist.md`](./06_github_repository_checklist.md) | Check the submitted public branch and publish local changes there |

## To do before 23:45 UTC

1. Record the video following `03_demo_video_script.md` (3 min 45). Show **no key**: not the `.env` file, not the Nightshift Console.
2. Check the branch shown to judges and publish local changes there; this documentation update does not merge or publish code.
3. On HackOS: create the submission, choose **a single track**, copy `01_submission_form.md`, attach the video, the PowerPoint, the GitHub link and the text of `02_sponsor_technology_explanation.md`.
4. Check that both team members are registered: the team is locked at the first submission.

## Verified for this submission (27/10/2026)

- Latest offline suite: **214 passed, 2 skipped**.
- Meterless Scout Intent evaluation: all official thresholds met (`python -m scripts.run_scout_evals`).
- Historical traces with Zetaris (local, 2.4.3), Meterless Nightshift and NVIDIA Nemotron 3 Ultra: search, refinement, comparison and questions. Recent checks: real Cloudflare image, committed pending proposal then authenticated admin rejection; approval and photos covered offline. Recent Zetaris status is distinguished below.
- Fallback mode `SAMPLE_MODE=true`: works without Zetaris, Nightshift or Cloudflare.

## Product update

- Fragmented search retained; simplified routing by default (`SCOUT_ROUTING_ENABLED=false`), with explicit image and submission requests available.
- Listing cards and comparison in a collapsible panel below chat, closed by default.
- Images only on request, targets resolved by name/neighbourhood or rank, clarification on ambiguity; Cameroonian context reserved in the Cloudflare prompt (2,048 characters), never a claimed reconstruction.
- Moderation: `draft → pending → approved/rejected`, notes, dates, filters and admin logout. Recent live check: committed pending PostgreSQL proposal, then rejection; approval and photos covered offline.
- Older examples remain dated evidence. Recent checks encountered a Zetaris failure and explicitly reported PostgreSQL fallback; do not claim availability without a live check.
- Presentation screenshots are anonymised. Hard-refresh after rebuilding the frontend; never expose tokens or personal contacts.
