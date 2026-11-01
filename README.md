# Qwinn Live: hourly Instagram auto-poster

GitHub Actions posts one quiz question to Instagram every hour, on the hour (IST), using the official Instagram API.

- `posts/YYYY-MM-DD/HH.jpg` + `HH.txt`: the image (1080×1350, 4:5, JPEG, the API does not accept 3:4) and caption for that IST hour.
- `config.json` → `start_at`: the first slot the bot may post (`YYYY-MM-DD HH`, IST). Slots before it are skipped, so posts you already scheduled in Business Suite are not doubled.
- `config.json` → `approved_through`: the last slot the owner has approved. New batches are added to `posts/` ahead of time but only go out once this date is moved forward.
- `posted.json`: slots already published (the bot never posts a slot twice).
- `tools/render.js`: makes images and captions from a questions file.

**This repository must be public**, because Instagram fetches each image from its raw GitHub URL. Correct answers are never stored here.

## One-time setup (about 20 minutes)

### 1. Get an Instagram access token
1. Go to developers.facebook.com, log in, then **My Apps → Create app**.
2. Use case: **Manage messaging & content on Instagram**. Give it a name (for example "Qwinn Live Poster"). No business portfolio needed.
3. In the app, open **Instagram → API setup with Instagram login**.
4. Under **Generate access tokens**, click **Add account** and log in as the Qwinn Live Instagram account. Allow the permissions (it must include content publishing).
5. Click **Generate token** next to the account and copy it. Also copy the numeric **Instagram user ID** shown next to the account.
   Keep the app in Development mode: posting to your own account works without App Review.

### 2. Add the secrets to this repository
In GitHub: **Settings → Secrets and variables → Actions → New repository secret**:
- `IG_ACCESS_TOKEN`: the token from step 1.5
- `IG_USER_ID`: the numeric Instagram user ID
- `GH_PAT` (optional, for automatic token refresh): a fine-grained personal access token for this repo with **Secrets: read and write**. Without it, generate a new Instagram token every 60 days by hand.

Never paste tokens into chat or commit them.

### 3. Test
**Actions → Hourly Instagram post → Run workflow**, with `dry_run` = 1. The log shows which image and caption it would post. Then it runs on its own every hour.

To post one slot immediately: Run workflow with `slot` = `2026-11-01 14` and `dry_run` = 0.

## Make it post on time (recommended)
GitHub's own timer is best-effort and can skip or delay hourly runs by hours. A free external timer is far more punctual:
1. Create a fine-grained GitHub token for this repo with **Actions: read and write** (github.com → Settings → Developer settings → Fine-grained tokens).
2. At cron-job.org (free), create a job:
   - URL: `https://api.github.com/repos/aistartupworld-cloud/qwinn-live-posts/actions/workflows/hourly-post.yml/dispatches`
   - Schedule: every hour at minute 50, time zone Asia/Kolkata
   - Method: POST, body: `{"ref":"main"}`
   - Headers: `Authorization: Bearer <your token>`, `Accept: application/vnd.github+json`
GitHub's timer stays on as a backup; the bot never posts the same hour twice.

## Notes
- The workflow starts at :50 IST and waits for the hour. GitHub sometimes starts scheduled jobs late; if it starts after the hour, it posts right away (up to :44).
- Instagram allows 100 API posts per account per 24 hours; we use 24.
- Max 5 hashtags per post.
