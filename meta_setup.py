"""
DECODE — one-time Meta token helper (Instagram API with Instagram Login).

Run this LOCALLY after generating an Instagram access token in the app dashboard.
It (1) finds your Instagram account ID, (2) extends the token to a long-lived
(~60-day) token if you supply the app secret, and (3) prints exactly what to
paste into GitHub Secrets. Nothing is sent anywhere except Meta's own API.

Set these first (PowerShell):
    $env:IG_TOKEN="<the token you copied>"
    $env:IG_APP_SECRET="<Instagram app secret from the dashboard>"   # optional but recommended
then:
    python meta_setup.py
"""
import os
import requests

BASE = "https://graph.instagram.com"
VER = "v21.0"


def main():
    token = os.environ.get("IG_TOKEN")
    if not token:
        raise SystemExit("Set IG_TOKEN first:  $env:IG_TOKEN=\"...\"")
    secret = os.environ.get("IG_APP_SECRET")

    # 1) who am I — get the IG account id used for publishing
    me = requests.get(f"{BASE}/{VER}/me",
                      params={"fields": "user_id,username,account_type",
                              "access_token": token}, timeout=30)
    if me.status_code >= 400:
        raise SystemExit(f"Token check failed: {me.text}")
    info = me.json()
    ig_id = info.get("user_id") or info.get("id")
    print("\n--- Instagram account ---")
    print("  username    :", info.get("username"))
    print("  account_type:", info.get("account_type"))
    print("  IG_USER_ID  :", ig_id)

    # 2) extend to long-lived (needs app secret)
    long_token, expires_days = token, "unknown"
    if secret:
        ex = requests.get(f"{BASE}/access_token", params={
            "grant_type": "ig_exchange_token",
            "client_secret": secret,
            "access_token": token,
        }, timeout=30)
        if ex.status_code >= 400:
            print("\n[warn] long-lived exchange failed:", ex.text)
        else:
            d = ex.json()
            long_token = d.get("access_token", token)
            expires_days = round(d.get("expires_in", 0) / 86400)
    else:
        print("\n[note] IG_APP_SECRET not set — skipping long-lived exchange.")
        print("       The dashboard token may already be long-lived; set the")
        print("       secret to be sure you get a 60-day token.")

    print("\n=== PASTE THESE INTO GITHUB SECRETS ===")
    print("  IG_USER_ID      =", ig_id)
    print("  IG_ACCESS_TOKEN =", long_token)
    print(f"  (token valid ~{expires_days} days)")
    print("\nDo NOT paste the token into chat — put it straight into GitHub.")


if __name__ == "__main__":
    main()
