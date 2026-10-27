# Demo video script (3 min 45)

Requirements covered:
- the problem and who it is for;
- the main workflow, live;
- the challenge solved;
- the key features;
- the agent querying Zetaris, the Meterless engine in action and a real request going through Nightshift.

Avoid: more than 4 minutes, showing keys, tokens or personal data, a hard-coded demo path.

The agent speaks French (its users are in Cameroon). Narrate in English and, if useful, add English subtitles for the on-screen messages (translations given below).

## Before recording

1. Start Zetaris (`zetaris-platform/`), open **Nightshift**, then start the backend and the frontend:
   ```sh
   docker compose -f docker-compose.yml -f docker-compose.wsl.yml up -d
   cd frontend && docker compose up -d
   ```
2. Check <http://localhost:8080/api/integrations/status?live=true>: `zetaris` and `meterless` must be `ok`.
3. Open three tabs:
   - <http://localhost:8080> (Kwatsur);
   - <http://localhost:3000> (Zetaris, SQL editor, already signed in);
   - <http://localhost:8080/admin.html> (token already entered).
4. Keep Nightshift on the run details screen, **never on the Console** (it shows the token).
5. Never show the `.env` file. Browser zoom at 110%.
6. A full search takes about 15 s (two Nemotron calls). If the wait feels long, cut it in editing and say so ("sped up").

## Run-through

| Time | On screen | What to say (summary) |
| --- | --- | --- |
| 0:00 – 0:20 | Kwatsur home page | "In Douala and Yaoundé, finding a place to rent means digging through scattered, incomplete listings, sometimes scams. Kwatsur is an agent that does this work and explains why." |
| 0:20 – 0:55 | Click the example "Deux-chambres à Bonamoussadi" (two-bedroom in Bonamoussadi), send | Show the criteria that appear (city, neighbourhood, budget, water, electricity), the ranked cards and the "Démo fictive" (fictional demo) badge. |
| 0:55 – 1:20 | Open "Voir l'explication du classement" (see ranking explanation) on 2 cards; show the labels under the reply | "The ranking is computed by code: reasons, trade-offs, points to check. Nemotron only explains those facts." Point at "Annonces lues via Zetaris", "Rédigé par Nemotron via Meterless · Modèle : nvidia/nemotron-3-ultra-550b-a55b" and "Scout : recherche (100 %), Contrat signé". |
| 1:20 – 1:40 | Zetaris tab: `SELECT title, monthly_rent FROM kwatsur_pg.zetaris_listings LIMIT 5` | "Zetaris is our data layer: the agent sends it SQL through its REST API, and Zetaris federates our listings database." |
| 1:40 – 2:00 | Nightshift: the latest run, with the Nemotron 3 Ultra model | "Every request from the agent goes through Meterless Nightshift, which serves Nemotron." |
| 2:00 – 2:25 | "Finalement peu importe le quartier, mais pas plus de 110 000 FCFA" (any neighbourhood after all, but no more than 110,000), then "Est-ce que le premier a un compteur électrique individuel ?" (does the first one have its own electricity meter?) | Conversation memory (city and bedrooms kept). Honest answer: "not specified in the listing, ask the source". |
| 2:25 – 2:45 | "Envoie la caution par Orange Money au propriétaire" (send the deposit to the landlord by Orange Money) | "The Meterless Scout Intent engine runs before every action: it refuses any payment without even calling the model. Same for prompt injections." Show "risque bloqué" (risk blocked). |
| 2:45 – 3:15 | New conversation: "Je loue mon studio meublé à Yaoundé, quartier Bastos, 90 000 FCFA" (I'm renting out my furnished studio in Bastos, Yaoundé, 90,000 FCFA), then a fake contact, then "oui"; admin tab → Approve | "Landlords submit their listing in the chat. Scout keeps track of the submission, and an administrator approves it before publication." Search again for a studio in Yaoundé: the listing appears, via Zetaris. |
| 3:15 – 3:30 | "Montre-moi le salon du premier" (show me the living room of the first one) | Real photo if any, otherwise an AI illustration of a Cameroonian home, **labelled**: "never presented as a real photo". |
| 3:30 – 3:45 | Microphone button, one sentence spoken aloud, reply read out | "And you can do everything by voice." Close: "Kwatsur: an agent that searches, checks and explains, without inventing." |

Fallback version, with no external service: set `SAMPLE_MODE=true` in `.env` and restart the backend. The interface says so ("Mode démo sans IA").
