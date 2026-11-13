#!/usr/bin/env python3
"""Post tonight's draw winner as an Instagram Story at 10:05 PM IST.

Runs every minute from the Poster loop. Once draws/<today>.json exists, has a
winner, and it is 22:05 IST or later, it:
  1. draws the Story image (1080x1920) with Pillow into posts/stories/<date>-winner.jpg,
  2. commits and pushes it (Instagram fetches the image from its raw GitHub URL),
  3. publishes it as a Story and logs "story <date>" in posted.json.

Nights without a winner get no Story. Config "winner_story": {"from": "YYYY-MM-DD", "at": "22:05"}.
Env: STORY_DATE=YYYY-MM-DD (that night, any time), DRY_RUN=1 (draw the image only, no push, no post).
"""
import datetime as dt, json, os, subprocess, sys, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import post_instagram as P

IST = P.IST
ROOT = P.ROOT
NAVY, PANEL, YELLOW, LAV, WHITE = "#14123A", "#24215A", "#FFC93C", "#C9C6F2", "#FFFFFF"
FONTS = os.path.join(ROOT, "assets", "fonts")


def font(name, size):
    from PIL import ImageFont
    return ImageFont.truetype(os.path.join(FONTS, name), size)


def fit(draw, text, name, size, width):
    while size > 30 and draw.textlength(text, font=font(name, size)) > width:
        size -= 4
    return font(name, size)


def render(res, path):
    from PIL import Image, ImageDraw
    W, H = 1080, 1920
    im = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(im)
    # Logo: clock shaped like a Q, then "qwinn live"
    cx, cy, r = 112, 190, 34
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=YELLOW, width=12)
    d.line((cx, cy - 20, cx, cy + 2, cx + 15, cy + 2), fill=YELLOW, width=8, joint="curve")
    d.line((cx + 24, cy + 24, cx + 46, cy + 46), fill=YELLOW, width=12)
    d.text((180, 190), "qwinn", font=font("InterDisplay-ExtraBold.otf", 64), fill=WHITE, anchor="lm")
    d.text((180 + d.textlength("qwinn ", font=font("InterDisplay-ExtraBold.otf", 64)), 190), "live",
           font=font("InterDisplay-ExtraBold.otf", 64), fill=YELLOW, anchor="lm")
    day = dt.date.fromisoformat(res["date"])
    y = 430
    title = "TONIGHT'S WINNERS" if res.get("mega_winner") else "TONIGHT'S WINNER"
    d.text((80, y), f"{title} · {day:%d %b}".upper(), font=font("InterDisplay-Bold.otf", 40), fill=YELLOW)
    y += 90
    blocks = [(res["winner"], "wins a ₹100 gift card")]
    if res.get("mega_winner"):
        blocks.append((res["mega_winner"], f"wins the Friday mega draw: {res.get('mega_prize', '₹200')} gift card"))
    for handle, line in blocks:
        box_h = 330
        d.rounded_rectangle((60, y, W - 60, y + box_h), radius=40, fill=PANEL)
        f = fit(d, handle, "InterDisplay-ExtraBold.otf", 104, W - 200)
        d.text((W // 2, y + 130), handle, font=f, fill=WHITE, anchor="mm")
        f2 = fit(d, line, "Inter-Medium.otf", 44, W - 200)
        d.text((W // 2, y + 240), line, font=f2, fill=YELLOW, anchor="mm")
        y += box_h + 50
    y += 30
    for t in ["Congratulations! Please DM us within 48 hours", "to claim your gift card."]:
        d.text((W // 2, y), t, font=font("Inter-Medium.otf", 40), fill=WHITE, anchor="mm"); y += 60
    y += 60
    d.text((W // 2, y), "A winner every night at 10 PM.", font=font("InterDisplay-ExtraBold.otf", 56), fill=YELLOW, anchor="mm")
    y += 80
    d.text((W // 2, y), "New questions tomorrow from 12 PM.", font=font("Inter-Medium.otf", 42), fill=LAV, anchor="mm")
    d.line((80, H - 260, W - 80, H - 260), fill="#3A3680", width=3)
    for i, t in enumerate(["Free to enter. We never ask for money, OTPs or passwords.",
                           "Not sponsored, endorsed or administered by, or associated",
                           "with, Instagram or Meta."]):
        d.text((W // 2, H - 200 + i * 46), t, font=font("Inter-Medium.otf", 30), fill=LAV, anchor="mm")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, "JPEG", quality=92)


def git(*args):
    subprocess.run(["git", *args], cwd=ROOT, check=True)


def wait_public(url):
    for _ in range(20):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                if r.status == 200:
                    return
        except Exception:
            pass
        time.sleep(15)
    sys.exit(f"Story image never became reachable at {url}")


def main():
    cfg = json.load(open(os.path.join(ROOT, "config.json")))
    ws = cfg.get("winner_story") or {}
    dry = os.environ.get("DRY_RUN") == "1"
    now = dt.datetime.now(IST)
    if os.environ.get("STORY_DATE"):
        day = os.environ["STORY_DATE"]
    else:
        day = str(now.date())
        if not ws or now.strftime("%H:%M") < ws.get("at", "22:05"):
            return
    if day < ws.get("from", "9999-12-31") and not os.environ.get("STORY_DATE"):
        return
    res_path = os.path.join(ROOT, "draws", f"{day}.json")
    if not os.path.exists(res_path):
        return
    log_path = os.path.join(ROOT, "posted.json")
    log = json.load(open(log_path)) if os.path.exists(log_path) else {}
    key = f"story {day}"
    if key in log:
        return
    res = json.load(open(res_path))
    if not res.get("winner"):
        print(f"No winner on {day}; no winner Story"); return
    rel = f"posts/stories/{day}-winner.jpg"
    render(res, os.path.join(ROOT, rel))
    print(f"Drew {rel} for {res['winner']}" + (f" and mega winner {res['mega_winner']}" if res.get("mega_winner") else ""))
    if dry:
        print("DRY_RUN: not pushed or posted"); return
    token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    if not token:
        print("::warning::IG_ACCESS_TOKEN not set; winner Story not posted"); return
    if token.startswith("EAA"):
        P.API = P.API_FB
    ig_id = (os.environ.get("IG_USER_ID") or "").strip() or "me"
    git("add", rel)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode:
        git("commit", "-qm", f"Winner Story image for {day}")
        if subprocess.run(["git", "push", "-q"], cwd=ROOT).returncode:
            git("pull", "-q", "--rebase", "origin", "main"); git("push", "-q")
    branch = os.environ.get("POST_BRANCH", "main")
    url = f"https://raw.githubusercontent.com/{os.environ['GITHUB_REPOSITORY']}/{branch}/{rel}"
    wait_public(url)
    container = P.call("POST", f"{ig_id}/media", image_url=url, media_type="STORIES", access_token=token)["id"]
    for _ in range(10):
        status = P.call("GET", container, fields="status_code", access_token=token).get("status_code")
        if status == "FINISHED": break
        if status in ("ERROR", "EXPIRED"): sys.exit(f"Story container {container} failed: {status}")
        time.sleep(15)
    log = json.load(open(log_path)) if os.path.exists(log_path) else {}
    log[key] = f"attempted {container}"  # never retry a publish: Instagram may post despite an error
    json.dump(log, open(log_path, "w"), indent=1, sort_keys=True)
    media = P.call("POST", f"{ig_id}/media_publish", creation_id=container, access_token=token)["id"]
    log[key] = media
    json.dump(log, open(log_path, "w"), indent=1, sort_keys=True)
    print(f"Published winner Story for {day} as media {media}")


if __name__ == "__main__":
    main()
