#!/usr/bin/env python3
"""Pädagogen-Wiki: veröffentlicht freigegebene Posts auf Instagram, Facebook und YouTube.

Ablauf
  - Jeder Post liegt in posts/<id>/ mit einer post.json und den Medien (JPG/MP4).
  - Ein Post wird nur veröffentlicht, wenn "approved": true gesetzt ist
    (das passiert erst, nachdem die Person im Chat "passt" geschrieben hat)
    und "publish_at" erreicht ist.
  - Ergebnisse (IDs, Fehler) werden in post.json unter "status" zurückgeschrieben,
    damit nichts doppelt gepostet wird.

Zugangsdaten kommen nur aus Umgebungsvariablen (GitHub Secrets), nie aus Dateien:
  META_PAGE_TOKEN, FB_PAGE_ID, IG_USER_ID,
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
Optional: GRAPH_VERSION (Standard v27.0), MEDIA_BASE_URL, DRY_RUN=1
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import sys
import time

import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
POSTS = ROOT / "posts"
GRAPH = f"https://graph.facebook.com/{os.environ.get('GRAPH_VERSION', 'v27.0')}"
MEDIA_BASE = os.environ.get(
    "MEDIA_BASE_URL", "https://buntetoene.github.io/paedagogen-wiki/posts"
).rstrip("/")
DRY = os.environ.get("DRY_RUN") == "1"
TIMEOUT = 120


class PublishError(Exception):
    pass


def log(msg: str) -> None:
    # Keine Tokens, keine Nutzerdaten ins Log.
    print(msg, flush=True)


def env(name: str) -> str:
    val = os.environ.get(name, "")
    if not val and not DRY:
        raise PublishError(f"Secret {name} fehlt")
    return val


def media_url(post_id: str, filename: str) -> str:
    return f"{MEDIA_BASE}/{post_id}/{filename}"


def check(resp: requests.Response, what: str) -> dict:
    try:
        data = resp.json()
    except ValueError:
        data = {}
    if resp.status_code >= 400 or "error" in data:
        err = data.get("error", {})
        raise PublishError(f"{what}: HTTP {resp.status_code} {err.get('message', resp.text[:200])}")
    return data


def wait_until_url_live(url: str, tries: int = 20) -> None:
    """GitHub Pages braucht nach dem Push etwas Zeit. Erst posten, wenn die Datei abrufbar ist."""
    if DRY:
        return
    for _ in range(tries):
        r = requests.head(url, timeout=30, allow_redirects=True)
        if r.status_code == 200:
            return
        time.sleep(15)
    raise PublishError(f"Datei noch nicht online: {url}")


# ---------------------------------------------------------------- Instagram
def ig_wait_container(cid: str, token: str) -> None:
    for _ in range(60):
        r = requests.get(f"{GRAPH}/{cid}", params={"fields": "status_code", "access_token": token}, timeout=TIMEOUT)
        status = check(r, "IG Status").get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise PublishError(f"IG Container {status}")
        time.sleep(10)
    raise PublishError("IG Container nicht rechtzeitig fertig")


def ig_publish(post: dict, post_id: str) -> dict:
    token, ig = env("META_PAGE_TOKEN"), env("IG_USER_ID")
    caption = post["caption"]
    kind = post["type"]
    if DRY:
        log(f"  [Probelauf] Instagram {kind}")
        return {"dry_run": True}

    if kind == "reel":
        params = {
            "media_type": "REELS",
            "video_url": media_url(post_id, post["video"]),
            "caption": caption,
            "share_to_feed": "true",
            "access_token": token,
        }
        if post.get("cover"):
            params["cover_url"] = media_url(post_id, post["cover"])
        cid = check(requests.post(f"{GRAPH}/{ig}/media", data=params, timeout=TIMEOUT), "IG Reel")["id"]
        ig_wait_container(cid, token)
    elif kind == "carousel":
        children = []
        for img in post["images"]:
            data = {"image_url": media_url(post_id, img["file"]), "is_carousel_item": "true", "access_token": token}
            if img.get("alt"):
                data["alt_text"] = img["alt"]
            children.append(check(requests.post(f"{GRAPH}/{ig}/media", data=data, timeout=TIMEOUT), "IG Kachel")["id"])
        for c in children:
            ig_wait_container(c, token)
        cid = check(requests.post(f"{GRAPH}/{ig}/media", data={
            "media_type": "CAROUSEL", "children": ",".join(children), "caption": caption, "access_token": token,
        }, timeout=TIMEOUT), "IG Karussell")["id"]
        ig_wait_container(cid, token)
    elif kind == "image":
        img = post["images"][0]
        data = {"image_url": media_url(post_id, img["file"]), "caption": caption, "access_token": token}
        if img.get("alt"):
            data["alt_text"] = img["alt"]
        cid = check(requests.post(f"{GRAPH}/{ig}/media", data=data, timeout=TIMEOUT), "IG Bild")["id"]
        ig_wait_container(cid, token)
    else:
        raise PublishError(f"Unbekannter Typ {kind}")

    media_id = check(requests.post(f"{GRAPH}/{ig}/media_publish", data={"creation_id": cid, "access_token": token},
                                   timeout=TIMEOUT), "IG Veröffentlichen")["id"]
    result = {"media_id": media_id}
    if post.get("first_comment"):
        try:
            c = check(requests.post(f"{GRAPH}/{media_id}/comments", data={
                "message": post["first_comment"], "access_token": token}, timeout=TIMEOUT), "IG Kommentar")
            result["first_comment_id"] = c.get("id")
        except PublishError as e:  # Kommentar ist nett, aber kein Grund zum Abbruch
            result["first_comment_error"] = str(e)
    return result


# ---------------------------------------------------------------- Facebook
def fb_publish(post: dict, post_id: str) -> dict:
    token, page = env("META_PAGE_TOKEN"), env("FB_PAGE_ID")
    caption = post.get("caption_facebook") or post["caption"]
    kind = post["type"]
    if DRY:
        log(f"  [Probelauf] Facebook {kind}")
        return {"dry_run": True}

    if kind == "reel":
        start = check(requests.post(f"{GRAPH}/{page}/video_reels", data={
            "upload_phase": "start", "access_token": token}, timeout=TIMEOUT), "FB Reel Start")
        vid = start["video_id"]
        up = requests.post(start["upload_url"], headers={
            "Authorization": f"OAuth {token}", "file_url": media_url(post_id, post["video"])}, timeout=TIMEOUT)
        check(up, "FB Reel Upload")
        check(requests.post(f"{GRAPH}/{page}/video_reels", data={
            "upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED",
            "description": caption, "access_token": token}, timeout=TIMEOUT), "FB Reel Finish")
        return {"video_id": vid}

    photo_ids = []
    for img in post["images"]:
        r = check(requests.post(f"{GRAPH}/{page}/photos", data={
            "url": media_url(post_id, img["file"]), "published": "false",
            "alt_text_custom": img.get("alt", ""), "access_token": token}, timeout=TIMEOUT), "FB Foto")
        photo_ids.append(r["id"])
    data = {"message": caption, "access_token": token}
    for i, pid in enumerate(photo_ids):
        data[f"attached_media[{i}]"] = json.dumps({"media_fbid": pid})
    r = check(requests.post(f"{GRAPH}/{page}/feed", data=data, timeout=TIMEOUT), "FB Beitrag")
    return {"post_id": r["id"]}


# ---------------------------------------------------------------- YouTube
def yt_publish(post: dict, post_id: str) -> dict:
    yt = post.get("youtube")
    if post["type"] != "reel" or not yt:
        return {"skipped": "kein Video"}
    if DRY:
        log("  [Probelauf] YouTube Short")
        return {"dry_run": True}
    tok = check(requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": env("YT_CLIENT_ID"), "client_secret": env("YT_CLIENT_SECRET"),
        "refresh_token": env("YT_REFRESH_TOKEN"), "grant_type": "refresh_token"}, timeout=TIMEOUT), "YT Token")
    access = tok["access_token"]
    meta = {
        "snippet": {
            "title": yt["title"][:100],
            "description": yt.get("description") or post["caption"],
            "tags": yt.get("tags", []),
            "categoryId": "27",  # Bildung
            "defaultLanguage": "de",
            "defaultAudioLanguage": "de",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": False,
        },
    }
    video_path = ROOT / "posts" / post_id / post["video"]
    init = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos",
        params={"uploadType": "resumable", "part": "snippet,status"},
        headers={"Authorization": f"Bearer {access}", "Content-Type": "application/json; charset=UTF-8",
                 "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(video_path.stat().st_size)},
        data=json.dumps(meta), timeout=TIMEOUT)
    if init.status_code >= 400:
        raise PublishError(f"YT Start: HTTP {init.status_code} {init.text[:200]}")
    with open(video_path, "rb") as fh:
        up = requests.put(init.headers["Location"], data=fh,
                          headers={"Authorization": f"Bearer {access}", "Content-Type": "video/mp4"}, timeout=600)
    data = check(up, "YT Upload")
    result = {"video_id": data["id"], "privacy": data.get("status", {}).get("privacyStatus")}
    if yt.get("playlist_id"):
        try:
            check(requests.post("https://www.googleapis.com/youtube/v3/playlistItems", params={"part": "snippet"},
                                headers={"Authorization": f"Bearer {access}"},
                                json={"snippet": {"playlistId": yt["playlist_id"],
                                                  "resourceId": {"kind": "youtube#video", "videoId": data["id"]}}},
                                timeout=TIMEOUT), "YT Playlist")
        except PublishError as e:
            result["playlist_error"] = str(e)
    return result


PLATFORMS = {"instagram": ig_publish, "facebook": fb_publish, "youtube": yt_publish}


def due(post: dict, now: dt.datetime) -> bool:
    if not post.get("approved"):
        return False
    when = dt.datetime.fromisoformat(post["publish_at"])
    return when <= now


def main() -> int:
    now = dt.datetime.now(dt.timezone.utc)
    failures = 0
    for pj in sorted(POSTS.glob("*/post.json")):
        post_id = pj.parent.name
        post = json.loads(pj.read_text(encoding="utf-8"))
        if not due(post, now):
            continue
        status = post.setdefault("status", {})
        todo = [p for p in post.get("platforms", PLATFORMS)
                if status.get(p, {}).get("state") not in ("done", "failed")]
        if not todo:
            continue
        log(f"Post {post_id}: {', '.join(todo)}")
        files = [post["video"]] if post["type"] == "reel" else [i["file"] for i in post["images"]]
        try:
            for f in files:
                wait_until_url_live(media_url(post_id, f))
        except PublishError as e:
            log(f"  wartet: {e}")
            continue
        for platform in todo:
            attempts = status.get(platform, {}).get("attempts", 0) + 1
            try:
                res = PLATFORMS[platform](post, post_id)
                status[platform] = {"state": "dry_run" if DRY else "done", "at": now.isoformat(), **res}
                log(f"  {platform}: ok")
            except (PublishError, requests.RequestException) as e:
                failures += 1
                state = "failed" if attempts >= 3 else "retry"
                status[platform] = {"state": state, "attempts": attempts, "error": str(e)[:300]}
                log(f"  {platform}: FEHLER ({state}) {e}")
        if not DRY:
            pj.write_text(json.dumps(post, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
