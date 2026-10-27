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
| Public GitHub repository with README (setup, usage, dependencies) | [`06_github_repository_checklist.md`](./06_github_repository_checklist.md) | Repository public; **merge `version4.0` into `main`** |

## To do before 23:45 UTC

1. Record the video following `03_demo_video_script.md` (3 min 45). Show **no key**: not the `.env` file, not the Nightshift Console.
2. Merge the `version4.0` branch into `main` (the repository is already public).
3. On HackOS: create the submission, choose **a single track**, copy `01_submission_form.md`, attach the video, the PowerPoint, the GitHub link and the text of `02_sponsor_technology_explanation.md`.
4. Check that both team members are registered: the team is locked at the first submission.

## Verified for this submission (27/10/2026)

- 148 automated tests pass, without network.
- Meterless Scout Intent evaluation: all official thresholds met (`python -m scripts.run_scout_evals`).
- Real runs with Zetaris (local, 2.4.3), Meterless Nightshift and NVIDIA Nemotron 3 Ultra: search, refinement, comparison, question, picture of a room, owner listing submission approved by an administrator, injection and payment blocked.
- Fallback mode `SAMPLE_MODE=true`: works without Zetaris, Nightshift or Cloudflare.
