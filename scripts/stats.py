#!/usr/bin/env python3
"""Pädagogen-Wiki: liest Zahlen der letzten Posts (nur lesen, postet nichts).

Gibt nur Zahlen aus, keine Kommentartexte und keine Namen.
Insights (Aufrufe, Reichweite) brauchen ggf. zusätzliche Berechtigungen;
fehlt eine, steht das in der Ausgabe.
"""
import os
import sys

import requests

GRAPH = f"https://graph.facebook.com/{os.environ.get('GRAPH_VERSION', 'v27.0')}"
TOKEN = os.environ["META_PAGE_TOKEN"]
PAGE = os.environ["FB_PAGE_ID"]
IG = os.environ["IG_USER_ID"]


def get(path, **params):
    params["access_token"] = TOKEN
    r = requests.get(f"{GRAPH}/{path}", params=params, timeout=60)
    try:
        data = r.json()
    except ValueError:
        data = {}
    if r.status_code >= 400 or "error" in data:
        msg = data.get("error", {}).get("message", f"HTTP {r.status_code}")
        return None, msg.replace(TOKEN, "***")
    return data, None


def show(label, data, err):
    print(f"{label}: {data if err is None else 'nicht lesbar (' + err + ')'}")


def main():
    d, e = get(IG, fields="username,followers_count,media_count")
    show("Instagram-Profil", d and {k: d.get(k) for k in ("followers_count", "media_count")}, e)

    d, e = get(f"{IG}/media", fields="id,media_product_type,timestamp,like_count,comments_count,permalink", limit=25)
    for m in (d or {}).get("data", []):
        print(f"IG {m.get('media_product_type')} {m.get('timestamp')} {m.get('permalink')}: "
              f"Likes {m.get('like_count')}, Kommentare {m.get('comments_count')}")
        for metric in ("views", "reach", "saved", "shares", "total_interactions", "ig_reels_avg_watch_time"):
            i, ie = get(f"{m['id']}/insights", metric=metric)
            val = i["data"][0].get("values", [{}])[0].get("value") if i and i.get("data") else None
            print(f"   {metric}: {val if ie is None else 'nicht lesbar (' + ie[:120] + ')'}")
    if e:
        show("Instagram-Beiträge", None, e)

    d, e = get(PAGE, fields="followers_count,fan_count")
    show("Facebook-Seite", d and {k: d.get(k) for k in ("followers_count", "fan_count")}, e)

    d, e = get(f"{PAGE}/published_posts", fields="id,created_time,permalink_url,message", limit=25)
    if e:
        show("FB Beiträge", None, e)
    for x in (d or {}).get("data", []):
        print(f"FB Beitrag {x.get('created_time')} {x.get('permalink_url')} | {(x.get('message') or '')[:50]!r}")

    d, e = get(f"{PAGE}/video_reels", fields="id,created_time,permalink_url", limit=25)
    for v in (d or {}).get("data", []):
        print(f"FB Reel {v.get('created_time')} {v.get('permalink_url')}")
        for metric in ("blue_reels_play_count", "fb_reels_total_plays", "post_video_avg_time_watched", "post_video_likes_by_reaction_type"):
            i, ie = get(f"{v['id']}/video_insights", metric=metric)
            val = i["data"][0].get("values", [{}])[0].get("value") if i and i.get("data") else None
            print(f"   {metric}: {val if ie is None else 'nicht lesbar (' + ie[:120] + ')'}")
    if e:
        show("Facebook-Reels", None, e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
