#!/usr/bin/env python3
"""Post the current hour's Qwinn Live question to Instagram.

Runs from GitHub Actions every 5 minutes. In the first 45 minutes of each IST
hour it publishes
posts/<YYYY-MM-DD>/<HH>.jpg with the caption in posts/<YYYY-MM-DD>/<HH>.txt
through the Instagram API with Instagram Login. Already-posted slots are kept
in posted.json, so a rerun never double-posts.
"""
import datetime as dt, json, os, sys, time, urllib.parse, urllib.request

API_IG = "https://graph.instagram.com/v26.0"   # tokens from "Instagram login" (start with IG)
API_FB = "https://graph.facebook.com/v26.0"    # system-user / Facebook login tokens (start with EAA)
API = API_IG
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def call(method, path, **params):
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        req = urllib.request.Request(url + "?" + data.decode())
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        tok = params.get("access_token")
        if tok: body = body.replace(tok, "***")
        sys.exit(f"Instagram API error {e.code} on {path}: {body}")


def pick_slot(now):
    # Runs every few minutes; posts the current IST hour's question if it is
    # :00 to :44 and that hour has not been posted yet.
    if now.minute >= 45:
        return None
    return now.replace(minute=0, second=0, microsecond=0)


def main():
    global API
    token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    if token.startswith("EAA"):
        API = API_FB
    if not token and os.environ.get("DRY_RUN") != "1":
        print("::warning::IG_ACCESS_TOKEN secret is not set yet (Settings > Secrets and variables > Actions); nothing posted"); return
    ig_id = (os.environ.get("IG_USER_ID") or "").strip() or "me"
    if os.environ.get("CHECK_ONLY") == "1":
        me = call("GET", ig_id, fields="username", access_token=token)
        lim = call("GET", f"{ig_id}/content_publishing_limit", fields="quota_usage,config", access_token=token)
        print(f"Token OK for @{me.get('username')} via {API}; publishing limit: {json.dumps(lim)}"); return
    repo = os.environ["GITHUB_REPOSITORY"]  # owner/name, must be public for image_url
    branch = os.environ.get("POST_BRANCH", "main")
    dry = os.environ.get("DRY_RUN") == "1"
    ann = os.environ.get("ANNOUNCE", "").strip()
    if ann:  # one-off post, e.g. posts/announce/2026-11-06-winner (owner-approved), outside the hourly schedule
        return publish(ig_id, token, repo, branch, dry, ann, "announce " + ann)
    now = dt.datetime.now(IST)
    slot = pick_slot(now) if not os.environ.get("SLOT") else dt.datetime.strptime(os.environ["SLOT"], "%Y-%m-%d %H").replace(tzinfo=IST)
    if slot is None:
        print("Past :44 of the hour; the next hour's post goes out after the hour starts"); return
    key = slot.strftime("%Y-%m-%d %H")
    cfg = json.load(open(os.path.join(ROOT, "config.json")))
    start_at, approved = cfg.get("start_at", ""), cfg.get("approved_through", "")
    reel = f"posts/reels/{slot:%Y-%m-%d}/{slot:%H}"
    if os.path.exists(os.path.join(ROOT, reel + ".mp4")) and start_at <= key <= approved:
        publish(ig_id, token, repo, branch, dry, reel, "reel " + key, video=True)
    if key < start_at:
        print(f"{key} is before start_at {start_at} (posted by hand or Business Suite); skipping"); return
    lo, hi = cfg.get("post_hours", [0, 23])
    if not lo <= slot.hour <= hi:
        print(f"{key} is outside posting hours {lo}:00 to {hi}:00 IST; skipping"); return
    every = cfg.get("post_every", 1)
    if (slot.hour - lo) % every:
        print(f"{key}: posting only every {every} hours from {lo}:00 IST; skipping"); return
    if key > approved:
        print(f"{key} is after approved_through {approved}: waiting for owner approval; skipping"); return
    rel = f"posts/{slot:%Y-%m-%d}/{slot:%H}"
    return publish(ig_id, token, repo, branch, dry, rel, key)


def publish(ig_id, token, repo, branch, dry, rel, key, video=False):
    """Publish rel.jpg (feed photo) or, with video=True, rel.mp4 as a Reel shared to the feed."""
    ext = ".mp4" if video else ".jpg"
    img, cap = os.path.join(ROOT, rel + ext), os.path.join(ROOT, rel + ".txt")
    if not os.path.exists(img):
        print(f"No post for {key} ({rel}{ext} missing); nothing to do"); return
    log_path = os.path.join(ROOT, "posted.json")
    log = json.load(open(log_path)) if os.path.exists(log_path) else {}
    if key in log:
        print(f"{key} already posted as {log[key]}"); return
    caption = open(cap, encoding="utf-8").read().strip()
    image_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{rel}{ext}"
    print(f"Slot {key} IST, {'video' if video else 'image'} {image_url}")
    if dry:
        print("DRY_RUN: caption follows\n" + caption); return

    if video:
        container = call("POST", f"{ig_id}/media", media_type="REELS", video_url=image_url, caption=caption,
                         share_to_feed="true", access_token=token)["id"]
    else:
        container = call("POST", f"{ig_id}/media", image_url=image_url, caption=caption, access_token=token)["id"]
    for _ in range(30 if video else 10):
        status = call("GET", container, fields="status_code", access_token=token).get("status_code")
        if status == "FINISHED": break
        if status in ("ERROR", "EXPIRED"): sys.exit(f"Container {container} failed: {status}")
        time.sleep(20)
    media = call("POST", f"{ig_id}/media_publish", creation_id=container, access_token=token)["id"]
    log[key] = media
    json.dump(log, open(log_path, "w"), indent=1, sort_keys=True)
    print(f"Published {key} as media {media}")


if __name__ == "__main__":
    main()
