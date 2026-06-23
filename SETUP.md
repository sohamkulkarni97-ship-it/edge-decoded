# DECODE — go-live setup

The code is done. To flip it live you do three things once: connect the Instagram
account, put the keys into GitHub, and push the repo. After that it posts itself
daily with zero input.

---

## 1. Instagram / Meta (one-time, ~15 min) — only you can do this

1. **Make the IG account a Professional account.** Instagram app → Settings →
   Account type → switch to **Business** (or Creator).
2. **Create a Facebook Page** and link it to the Instagram account
   (IG app → Settings → Business tools / "Connect a Facebook Page").
3. **Create a Meta app:** https://developers.facebook.com → My Apps → Create App →
   type **Business**. Add the **Instagram Graph API** product.
4. Use the **Graph API Explorer** (or the app's tools) to grant these permissions
   and generate a token: `instagram_basic`, `instagram_content_publish`,
   `pages_show_list`, `pages_read_engagement`.
5. Collect three values:
   - **IG_USER_ID** — your Instagram Business account ID
   - **IG_ACCESS_TOKEN** — a long-lived access token (~60 days)
   - **FB_APP_ID / FB_APP_SECRET** — from the app's settings (used for token refresh)

> Tokens expire ~every 60 days. `publish.py refresh` extends them; add a monthly
> workflow (or just re-paste a fresh token) so it never lapses.

## 2. GitHub (one-time, ~5 min)

1. Create a new GitHub repo and push **the contents of `decode/` as the repo root**
   (so `render.py`, `requirements.txt`, and `.github/workflows/daily.yml` sit at the
   top level — GitHub only runs workflows found at the repo root).
2. Repo → **Settings → Secrets and variables → Actions → New repository secret**,
   add:
   - `ANTHROPIC_API_KEY`
   - `OPENAI_API_KEY`   (for the story cartoons)
   - `IG_USER_ID`
   - `IG_ACCESS_TOKEN`
3. Repo → **Settings → Actions → General → Workflow permissions** → set
   **Read and write permissions** (so the bot can commit rendered images).

## 3. Test + go live

- In the repo's **Actions** tab, open **"DECODE daily post"** → **Run workflow**
  (the manual trigger). Watch it fetch → write → render → commit → post.
- If the test post lands on Instagram, you're done. It now runs every day at the
  cron time. To change the time, edit `cron:` in `.github/workflows/daily.yml`
  (it's in UTC; `0 3 * * *` = 08:30 AM IST).

---

## Local commands (for tuning)

```bash
cd decode
pip install -r requirements.txt

python fetch.py                       # see today's candidate stories
$env:ANTHROPIC_API_KEY="sk-ant-..."   # PowerShell; use export on mac/linux
python run_all.py                     # fetch -> Sonnet -> render into output/
python render.py output/today_post.json   # re-render a tweaked JSON

# dry-run the publisher (checks images are public, doesn't post):
$env:DRY_RUN="1"; $env:IMAGE_BASE_URL="https://.../decode/output"; python publish.py
```

## Tuning knobs

- **Topics / sources:** edit `FEEDS` in `fetch.py`.
- **Engagement rubric & voice:** edit `SYSTEM` in `pick_and_write.py`.
- **Design (colors, fonts, layout):** edit the constants + slide renderers in `render.py`.
- **Name / handle:** change `HANDLE` in `pick_and_write.py` (and re-render).
- **Model:** swap `MODEL` in `pick_and_write.py` (e.g. to Haiku for lower cost, or
  Gemini by replacing `_call_model`).
