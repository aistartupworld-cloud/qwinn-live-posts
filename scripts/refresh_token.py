#!/usr/bin/env python3
"""Refresh the 60-day Instagram long-lived token and print the new one (masked in logs)."""
import json, os, urllib.request
tok = os.environ["IG_ACCESS_TOKEN"]
url = "https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=" + tok
new = json.load(urllib.request.urlopen(url, timeout=60))["access_token"]
print(f"::add-mask::{new}")
with open(os.environ["GITHUB_OUTPUT"], "a") as f:
    f.write(f"token={new}\n")
