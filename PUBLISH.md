# Publishing the Snapframe actor to the Apify Store

The actor code is complete and tested in `~/workspace/apify/snapframe-actor/`.
Everything below the "your steps" line is yours — account, money and publishing
are your calls.

## Your steps

### 1. Apify account + payouts (one time)
1. Create an Apify account at apify.com (use your email).
2. Finish identity verification (KYC) — required before you can receive payouts.
3. Link your PayPal for payouts: Console → Settings → Billing/Payouts.
   Minimum payout is $20; payouts are monthly.

### 2. Push the actor
```bash
cd ~/workspace/apify/snapframe-actor
npm i -g apify-cli        # or: pip install apify-cli
apify login               # paste your API token from Console → Settings → Integrations
apify push                # builds the Docker image on Apify and creates the actor
```
Alternative: push this folder to a GitHub repo, then in Console → Actors →
"Create" → "Link Git repository" so Apify rebuilds on every push.

### 3. Test it in Console
Open the actor → Input tab → run with the prefilled `https://example.com`.
Check the Dataset tab (one row per URL) and the Key-value store tab (the PNG file).

### 4. Set pricing (your call — prepared defaults below)
Actor → Pricing → model **Pay per event**, then add these two events
(copy from `.actor/pay_per_event.json`):

| Event name            | Title               | Price  |
|-----------------------|---------------------|--------|
| `screenshot-captured` | Screenshot captured | $0.003 |
| `pdf-captured`        | PDF captured        | $0.005 |

Event names must match the code exactly. Also enable **pass platform usage
costs to users** if offered — that bills Apify compute to the buyer, so the
event price is your full margin (you keep 80% of it).

### 5. Publish to the Store
Actor → Share/Publish → fill the Store description (the README is already
written for this) → Publish. Apify runs automated daily health checks on the
sample input — fix any failure within 48h.

## What the actor does
- Renders each URL in real Chromium: PNG/JPEG screenshots or print-ready PDFs.
- Batch up to 50 URLs per run; one bad URL never kills the batch.
- Device presets (desktop/laptop/tablet/mobile) or custom viewport + scale.
- PDF paper size, margins, orientation, background printing, header/footer HTML.
- Custom headers + cookies for authenticated pages.
- Arabic/RTL pages render with proper fonts (Noto) — no tofu boxes.
- SSRF guard: only public http(s) URLs; private/loopback/internal IPs blocked.
- Charges only on successful captures, never on failures or blocked URLs.

## Files
- `Dockerfile` — `apify/actor-python-playwright:3.12` + Arabic fonts.
- `.actor/actor.json` — actor config (memory/timeout/schemas).
- `.actor/INPUT_SCHEMA.json` — the Console input form.
- `.actor/OUTPUT_SCHEMA.json` / `.actor/dataset_schema.json` — output views.
- `.actor/pay_per_event.json` — pricing events for step 4.
- `src/main.py` — the capture engine.
- `README.md` — the Store listing copy.
