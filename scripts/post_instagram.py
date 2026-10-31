#!/usr/bin/env python3
"""Post the current hour's Qwinn Live question to Instagram.

Runs from GitHub Actions a few minutes before each hour. Picks the slot for the
coming hour (IST), waits until the hour starts, then publishes
posts/<YYYY-MM-DD>/<HH>.jpg with the caption in posts/<YYYY-MM-DD>/<HH>.txt
through the Instagram API with Instagram Login. Already-posted slots are kept
in posted.json, so a rerun never double-posts.
"""
import datetime as dt, json, os, sys, time, urllib.parse, urllib.request

API = "https://graph.instagram.com/v26.0"
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
        body = e.read().decode(errors="replace").replace(params.get("access_token", "") or "x", "***")
        sys.exit(f"Instagram API error {e.code} on {path}: {body}")


def pick_slot(now):
    # Run at :50 to :59 -> the coming hour. Run at :00 to :44 (late runner) -> this hour.
    slot = now.replace(minute=0, second=0, microsecond=0)
    if now.minute >= 45:
        slot += dt.timedelta(hours=1)
    return slot


def main():
    token = os.environ["IG_ACCESS_TOKEN"]
    ig_id = os.environ.get("IG_USER_ID") or "me"
    repo = os.environ["GITHUB_REPOSITORY"]  # owner/name, must be public for image_url
    branch = os.environ.get("POST_BRANCH", "main")
    dry = os.environ.get("DRY_RUN") == "1"
    now = dt.datetime.now(IST)
    slot = pick_slot(now) if not os.environ.get("SLOT") else dt.datetime.strptime(os.environ["SLOT"], "%Y-%m-%d %H").replace(tzinfo=IST)
    key = slot.strftime("%Y-%m-%d %H")
    start_at = json.load(open(os.path.join(ROOT, "config.json"))).get("start_at", "")
    if key < start_at:
        print(f"{key} is before start_at {start_at} (posted by hand or Business Suite); skipping"); return
    rel = f"posts/{slot:%Y-%m-%d}/{slot:%H}"
    img, cap = os.path.join(ROOT, rel + ".jpg"), os.path.join(ROOT, rel + ".txt")
    if not os.path.exists(img):
        print(f"No post for {key} ({rel}.jpg missing); nothing to do"); return
    log_path = os.path.join(ROOT, "posted.json")
    log = json.load(open(log_path)) if os.path.exists(log_path) else {}
    if key in log:
        print(f"{key} already posted as {log[key]}"); return
    caption = open(cap, encoding="utf-8").read().strip()
    image_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{rel}.jpg"
    print(f"Slot {key} IST, image {image_url}")
    if dry:
        print("DRY_RUN: caption follows\n" + caption); return

    container = call("POST", f"{ig_id}/media", image_url=image_url, caption=caption, access_token=token)["id"]
    for _ in range(10):
        status = call("GET", container, fields="status_code", access_token=token).get("status_code")
        if status == "FINISHED": break
        if status in ("ERROR", "EXPIRED"): sys.exit(f"Container {container} failed: {status}")
        time.sleep(20)
    wait = (slot - dt.datetime.now(IST)).total_seconds()
    if wait > 0:
        print(f"Waiting {int(wait)}s for {key}:00 IST"); time.sleep(wait)
    media = call("POST", f"{ig_id}/media_publish", creation_id=container, access_token=token)["id"]
    log[key] = media
    json.dump(log, open(log_path, "w"), indent=1, sort_keys=True)
    print(f"Published {key} as media {media}")


if __name__ == "__main__":
    main()
