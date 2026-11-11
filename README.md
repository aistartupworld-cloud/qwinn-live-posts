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

## How posting is timed
`Poster loop` keeps one GitHub Actions runner alive that checks every minute and posts each IST hour's approved question as soon as the hour starts. Each run lasts about 5h45m and then starts the next run itself, so posting does not depend on GitHub's own timer (which can skip hours). An hourly schedule restarts the chain if it ever breaks. Public repositories get these minutes free.

To post one slot by hand: Actions → "Hourly Instagram post (manual)" → Run workflow, with `slot` = `2026-11-06 14`.

## Growth features
- **Daily Reel**: put `posts/reels/YYYY-MM-DD/HH.mp4` (9:16, H.264 + AAC, with its music baked in) and `HH.txt` (caption). The loop posts it as a Reel, shared to the feed, at that IST hour, within `approved_through`. It is logged as `reel YYYY-MM-DD HH` in `posted.json`.
- **Winner Story at 10:05 PM** (`scripts/winner_story.py`, config `winner_story`): after the 10 PM draw picks a winner, it draws a Story image with the winner's handle into `posts/stories/`, pushes it, and posts it as a Story. No winner, no Story. Test the image with `DRY_RUN=1 STORY_DATE=2026-11-06 python3 scripts/winner_story.py`.
- **Tag-a-friend bonus** (config `tag_bonus`, Wednesdays from 18 Nov): a correct comment that also tags another account counts as 2 entries.
- **Friday mega draw** (config `mega_draw`, Fridays from 20 Nov, ₹200): besides the nightly winner, one more winner is picked from every correct entry of the 7 nights ending that Friday. Tonight's nightly winner is left out unless nobody else entered. Saved as `mega_winner` in `draws/<date>.json` and shown on the winner Story.
- Gift cards are still sent by the owner by hand.

## Notes
- Each hour's question is posted once, within about a minute of the hour (any time up to :44 if something was delayed).
- Instagram allows 100 API posts per account per 24 hours; we use 24.
- Max 5 hashtags per post.
