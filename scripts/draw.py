#!/usr/bin/env python3
"""Nightly ₹100 gift card draw for Qwinn Live.

At 10 PM IST (run every minute by the Poster loop) it:
  1. finds the posts from 10 PM yesterday to 9 PM today,
  2. reads every comment made before 10 PM tonight,
  3. keeps each person's FIRST comment on each post,
  4. counts one entry per correct answer (A, B, C or D),
  5. picks one entry at random and saves the result in draws/<date>.json.

Answers are never stored readable in this public repo. They are encrypted to a
key pair whose private half is itself encrypted with the IG_ACCESS_TOKEN secret,
so only this workflow can read them.

Env: DRAW_DATE=YYYY-MM-DD (draw a given night), DRAW_DRY=1 (count only, no pick,
nothing saved), ENSURE_KEY_ONLY=1 (just create the key pair if missing).
"""
import datetime as dt, glob, json, os, re, secrets, subprocess, sys, tempfile, urllib.parse, urllib.request

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANS = os.path.join(ROOT, "answers")
API = "https://graph.instagram.com/v26.0"
TOKEN = os.environ.get("IG_ACCESS_TOKEN", "").strip()
if TOKEN.startswith("EAA"):
    API = "https://graph.facebook.com/v26.0"
IG_ID = (os.environ.get("IG_USER_ID") or "").strip() or "me"


def get(path, **params):
    params["access_token"] = TOKEN
    url = path if path.startswith("http") else f"{API}/{path}?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Instagram API error {e.code} on {path}: {e.read().decode(errors='replace').replace(TOKEN, '***')}")


def pages(path, **params):
    data = get(path, **params)
    while True:
        yield from data.get("data", [])
        nxt = data.get("paging", {}).get("next")
        if not nxt:
            return
        data = get(nxt)


def openssl(*args):
    env = dict(os.environ, QPASS=TOKEN)
    subprocess.run(["openssl", *args], check=True, env=env, capture_output=True)


def ensure_key():
    pub = os.path.join(ANS, "key.pub")
    if os.path.exists(pub):
        return False
    os.makedirs(ANS, exist_ok=True)
    priv = os.path.join(ANS, "key.priv.enc")
    openssl("genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:3072",
            "-aes-256-cbc", "-pass", "env:QPASS", "-out", priv)
    openssl("pkey", "-in", priv, "-passin", "env:QPASS", "-pubout", "-out", pub)
    print("Created the answer key pair in answers/")
    return True


def load_answers():
    """Decrypt every answers/*.dat (with its .key) into {"YYYY-MM-DD HH": "A"}."""
    key = {}
    priv = os.path.join(ANS, "key.priv.enc")
    with tempfile.TemporaryDirectory() as tmp:
        for dat in sorted(glob.glob(os.path.join(ANS, "*.dat"))):
            k, out = os.path.join(tmp, "k"), os.path.join(tmp, "out.json")
            openssl("pkeyutl", "-decrypt", "-inkey", priv, "-passin", "env:QPASS",
                    "-pkeyopt", "rsa_padding_mode:oaep", "-in", dat[:-4] + ".key", "-out", k)
            openssl("enc", "-d", "-aes-256-cbc", "-pbkdf2", "-in", dat, "-out", out, "-pass", f"file:{k}")
            key.update(json.load(open(out)))
    return key


CAP = re.compile(r"⏰\s*(\d{1,2})\s*(AM|PM)", re.I)
PICK = re.compile(r"^[^A-Z0-9]*(?:(?:MY\s+)?(?:ANSWER|ANS|OPTION|OPT)(?:\s+IS)?[^A-Z0-9]*)?([ABCD])(?![A-Z])")


def slot_of(media):
    t = dt.datetime.strptime(media["timestamp"], "%Y-%m-%dT%H:%M:%S%z").astimezone(IST)
    m = CAP.search(media.get("caption") or "")
    if m:  # trust the "⏰ 1 AM question" label, on the post's day or the day before
        h = int(m.group(1)) % 12 + (12 if m.group(2).upper() == "PM" else 0)
        cand = t.replace(hour=h, minute=0, second=0, microsecond=0)
        if cand > t + dt.timedelta(hours=1):
            cand -= dt.timedelta(days=1)
        return cand
    return (t + dt.timedelta(minutes=30)).replace(minute=0, second=0, microsecond=0)


def draw(day, dry):
    start = dt.datetime.combine(day - dt.timedelta(days=1), dt.time(22), IST)
    close = dt.datetime.combine(day, dt.time(22), IST)
    me = get(IG_ID, fields="username").get("username", "")
    answers = {} if dry and not glob.glob(os.path.join(ANS, "*.dat")) else load_answers()
    posts = []
    for m in pages(f"{IG_ID}/media", fields="id,timestamp,caption", limit=50):
        s = slot_of(m)
        if s < start - dt.timedelta(days=1):
            break
        if start <= s < close:
            posts.append((s, m["id"]))
    posts.sort()
    entries, people, report = [], set(), []
    for s, mid in posts:
        key = s.strftime("%Y-%m-%d %H")
        first = {}
        for c in pages(f"{mid}/comments", fields="id,text,timestamp,username", limit=100):
            ct = dt.datetime.strptime(c["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
            u = (c.get("username") or "").lower()
            if not u or u == me.lower() or ct >= close:
                continue
            if u not in first or ct < first[u][0]:
                first[u] = (ct, c.get("text") or "")
        right = answers.get(key)
        ok = 0
        for u, (_, text) in first.items():
            people.add(u)
            m = PICK.match(text.strip().upper())
            if m and re.search(r"[,/&]\s*(OR\s+)?[ABCD](?![A-Z])", text.upper()):
                m = None  # more than one answer in the comment: no entry
            if right and m and m.group(1) == right:
                entries.append((u, key)); ok += 1
        report.append(f"{key} IST: {len(first)} people commented, {ok} correct" + ("" if right else " (no answer on file, not counted)"))
    print(f"Draw for {day} (posts {start:%d %b %I %p} to {close - dt.timedelta(hours=1):%d %b %I %p} IST, comments before {close:%d %b %I %p})")
    print("\n".join(report) or "No posts found in the window")
    result = {"date": str(day), "posts_counted": len(posts), "people": len(people), "entries": len(entries),
              "drawn_at_ist": dt.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")}
    if entries:
        u, key = secrets.SystemRandom().choice(entries)
        result.update(winner="@" + u, winning_entry=f"{key}:00 IST question")
    else:
        result["winner"] = None
    if dry:
        print("DRY RUN, nothing saved. Would record: " + json.dumps({k: v for k, v in result.items() if k not in ("winner", "winning_entry")}))
        return
    os.makedirs(os.path.join(ROOT, "draws"), exist_ok=True)
    json.dump(result, open(os.path.join(ROOT, "draws", f"{day}.json"), "w"), indent=1)
    print("RESULT " + json.dumps(result))


def main():
    if not TOKEN:
        print("::warning::IG_ACCESS_TOKEN not set; no draw"); return
    ensure_key()
    if os.environ.get("ENSURE_KEY_ONLY") == "1":
        return
    dry = os.environ.get("DRAW_DRY") == "1"
    if os.environ.get("DRAW_DATE"):
        return draw(dt.date.fromisoformat(os.environ["DRAW_DATE"]), dry)
    now = dt.datetime.now(IST)
    first_day = json.load(open(os.path.join(ROOT, "config.json"))).get("draws_from", "9999-12-31")
    days = [now.date() - dt.timedelta(days=1)] + ([now.date()] if now.hour >= 22 else [])
    for day in days:
        if str(day) >= first_day and not os.path.exists(os.path.join(ROOT, "draws", f"{day}.json")):
            draw(day, dry)


if __name__ == "__main__":
    main()
