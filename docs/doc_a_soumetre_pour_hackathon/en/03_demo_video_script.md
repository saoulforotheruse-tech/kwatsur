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
2. Check <http://localhost:8080/api/integrations/status?live=true>: to demonstrate Zetaris live, `zetaris` and `meterless` must be `ok`. If Zetaris fails, show the PostgreSQL fallback and do not claim a successful Zetaris query. Check `/api/images/status` before generating.
3. Open three tabs:
   - <http://localhost:8080> (Kwatsur);
   - <http://localhost:3000> (Zetaris, SQL editor, already signed in);
   - <http://localhost:8080/admin.html> (token already entered).
4. Keep Nightshift on the run details screen, **never on the Console** (it shows the token).
5. Never show the `.env` file. Browser zoom at 110%.
6. A full search takes about 15 s (two Nemotron calls). If the wait feels long, cut it in editing and say so ("sped up").
7. After an update, rebuild containers and hard-refresh (Ctrl + F5). Changing `.env` requires recreating the API, not merely restarting it. Chat comparison/contact commands require `SCOUT_ROUTING_ENABLED=true`; default `false` retains fragmented search, submissions and explicit image requests.
8. Use explicitly fictional proposals and `test@example.invalid`, never personal phone numbers. Do not publish a fake offer into the shared database: demonstrate rejection live; demonstrate approval only in an isolated demo database, or explain its automated test.

## Run-through

| Time | On screen | What to say (summary) |
| --- | --- | --- |
| 0:00 – 0:20 | Kwatsur home page | "In Douala and Yaoundé, finding a place to rent means digging through scattered, incomplete listings, sometimes scams. Kwatsur is an agent that does this work and explains why." |
| 0:20 – 0:55 | Send "Deux-chambres à Bonamoussadi", then expand "Logements correspondants" | Show criteria, the count on the initially collapsed panel, then ranked cards and the fictional-demo badge. No images are sent spontaneously into the chat. |
| 0:55 – 1:20 | Open "Voir l'explication du classement" (see ranking explanation) on 2 cards; show the labels under the reply | "The ranking is computed by code: reasons, trade-offs, points to check. Nemotron only explains those facts." Point at "Annonces lues via Zetaris", "Rédigé par Nemotron via Meterless · Modèle : nvidia/nemotron-3-ultra-550b-a55b" and "Scout : recherche (100 %), Contrat signé". |
| 1:20 – 1:40 | Zetaris tab: `SELECT title, monthly_rent FROM kwatsur_pg.zetaris_listings LIMIT 5` | "Zetaris is our data layer: the agent sends it SQL through its REST API, and Zetaris federates our listings database." |
| 1:40 – 2:00 | Nightshift: the latest run, with the Nemotron 3 Ultra model | "Every request from the agent goes through Meterless Nightshift, which serves Nemotron." |
| 2:00 – 2:25 | "Finalement peu importe le quartier, mais pas plus de 110 000 FCFA" (any neighbourhood after all, but no more than 110,000), then "Est-ce que le premier a un compteur électrique individuel ?" (does the first one have its own electricity meter?) | Conversation memory (city and bedrooms kept). Honest answer: "not specified in the listing, ask the source". |
| 2:25 – 2:45 | "Envoie la caution par Orange Money au propriétaire" (send the deposit to the landlord by Orange Money) | "The Meterless Scout Intent engine runs before every action: it refuses any payment without even calling the model. Same for prompt injections." Show "risque bloqué" (risk blocked). |
| 2:45 – 3:15 | New chat: "Je mets en location une maison de test fictive à Douala, Logpom, 2 chambres, 100 000 FCFA, contact test@example.invalid", then "oui"; admin → pending | Show the persisted proposal without publication, details and approve/reject buttons. Reject this test with a note, then show the rejected filter. Approval publishes a listing and its photos, without certifying availability. |
| 3:15 – 3:30 | In a search containing Logpom: "Montre-moi les images de celui de Logpom" (show images of the one in Logpom) | Target Logpom even when it is not first. Reuse an existing illustration or call Cloudflare only when needed; show labels and disclaimer. Say "from the description", not "a real photo of this property". |
| 3:30 – 3:45 | Microphone button, one sentence spoken aloud, reply read out | "And you can do everything by voice." Close: "Kwatsur: an agent that searches, checks and explains, without inventing." |

Fallback version, with no external service: set `SAMPLE_MODE=true` in `.env` and restart the backend. The interface says so ("Mode démo sans IA").
