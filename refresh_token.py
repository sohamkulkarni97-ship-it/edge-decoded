"""
Monthly Instagram token auto-refresh.

Refreshes the long-lived IG token (ig_refresh_token) and writes the new value
back into the repo's IG_ACCESS_TOKEN secret via the GitHub API — so the daily
poster never breaks at the ~60-day expiry. Run by .github/workflows/refresh.yml.

Env: IG_ACCESS_TOKEN, GH_PAT (PAT with Secrets write), GITHUB_REPOSITORY (auto).
"""
import base64
import os

import requests
from nacl import public


def _encrypt(public_key_b64, value):
    pk = public.PublicKey(base64.b64decode(public_key_b64))
    return base64.b64encode(public.SealedBox(pk).encrypt(value.encode())).decode()


def main():
    token = os.environ["IG_ACCESS_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]
    pat = os.environ["GH_PAT"]

    r = requests.get("https://graph.instagram.com/refresh_access_token",
                     params={"grant_type": "ig_refresh_token", "access_token": token}, timeout=60)
    r.raise_for_status()
    new_token = r.json()["access_token"]
    days = round(r.json().get("expires_in", 0) / 86400)

    h = {"Authorization": f"Bearer {pat}", "Accept": "application/vnd.github+json",
         "X-GitHub-Api-Version": "2022-11-28"}
    pk = requests.get(f"https://api.github.com/repos/{repo}/actions/secrets/public-key",
                      headers=h, timeout=60).json()
    body = {"encrypted_value": _encrypt(pk["key"], new_token), "key_id": pk["key_id"]}
    resp = requests.put(f"https://api.github.com/repos/{repo}/actions/secrets/IG_ACCESS_TOKEN",
                        headers=h, json=body, timeout=60)
    resp.raise_for_status()
    print(f"IG_ACCESS_TOKEN refreshed (valid ~{days} days) and saved to repo secrets.")


if __name__ == "__main__":
    main()
