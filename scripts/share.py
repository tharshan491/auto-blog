#!/usr/bin/env python3
import os, logging, textwrap, requests
from datetime import datetime
log = logging.getLogger(__name__)

def _post(url, *, json_=None, data=None, headers=None):
    try:
        r = requests.post(url, json=json_, data=data, headers=headers or {}, timeout=20)
        r.raise_for_status(); return r
    except Exception as e:
        log.warning("POST %s: %s", url, e); return None

def _summary(article, n=200):
    return textwrap.shorten(article.get("meta_description", article["title"]), width=n, placeholder="…")

class SocialSharer:
    def share_all(self, article, url):
        results = []
        title   = article["title"]
        summary = _summary(article)

        # Discord
        wh = os.getenv("DISCORD_WEBHOOK_URL","")
        if wh:
            r = _post(wh, json_={"embeds":[{"title":title,"description":summary,"url":url,"color":0x5865F2}]})
            results.append({"platform":"discord","status":"ok" if r else "error"})
        else:
            results.append({"platform":"discord","status":"skipped"})

        # Telegram
        tok = os.getenv("TELEGRAM_BOT_TOKEN",""); cid = os.getenv("TELEGRAM_CHAT_ID","")
        if tok and cid:
            r = _post(f"https://api.telegram.org/bot{tok}/sendMessage",
                json_={"chat_id":cid,"text":f"📝 *{title}*\n\n{summary}\n\n{url}","parse_mode":"Markdown"})
            results.append({"platform":"telegram","status":"ok" if r else "error"})
        else:
            results.append({"platform":"telegram","status":"skipped"})

        # Slack
        wh = os.getenv("SLACK_WEBHOOK_URL","")
        if wh:
            r = _post(wh, json_={"text": f"*{title}*\n{summary}\n{url}"})
            results.append({"platform":"slack","status":"ok" if r else "error"})
        else:
            results.append({"platform":"slack","status":"skipped"})

        # Dev.to
        key = os.getenv("DEVTO_API_KEY","")
        if key:
            tags = [k.lower().replace(" ","")[:20] for k in article.get("keywords",[])[:4]]
            r = _post("https://dev.to/api/articles",
                headers={"api-key":key,"Content-Type":"application/json"},
                json_={"article":{"title":title,"published":True,
                    "body_markdown":article["content"],"tags":tags,
                    "description":summary,"canonical_url":url}})
            results.append({"platform":"devto","status":"ok" if r else "error"})
        else:
            results.append({"platform":"devto","status":"skipped"})

        # Mastodon
        tok  = os.getenv("MASTODON_ACCESS_TOKEN","")
        inst = os.getenv("MASTODON_INSTANCE","https://mastodon.social")
        if tok:
            r = _post(f"{inst}/api/v1/statuses",
                headers={"Authorization":f"Bearer {tok}"},
                json_={"status":f"{title}\n\n{summary}\n\n{url}\n\n#programming #coding","visibility":"public"})
            results.append({"platform":"mastodon","status":"ok" if r else "error"})
        else:
            results.append({"platform":"mastodon","status":"skipped"})

        # Bluesky
        handle = os.getenv("BLUESKY_HANDLE",""); pw = os.getenv("BLUESKY_APP_PASSWORD","")
        if handle and pw:
            try:
                s = requests.post("https://bsky.social/xrpc/com.atproto.server.createSession",
                    json={"identifier":handle,"password":pw}, timeout=15).json()
                requests.post("https://bsky.social/xrpc/com.atproto.repo.createRecord",
                    headers={"Authorization":f"Bearer {s['accessJwt']}"},
                    json={"repo":s["did"],"collection":"app.bsky.feed.post",
                          "record":{"$type":"app.bsky.feed.post",
                                    "text":f"{title}\n{summary}\n{url}"[:300],
                                    "createdAt":datetime.utcnow().isoformat()+"Z"}}, timeout=15)
                results.append({"platform":"bluesky","status":"ok"})
            except Exception as e:
                results.append({"platform":"bluesky","status":"error","error":str(e)})
        else:
            results.append({"platform":"bluesky","status":"skipped"})

        # Medium
        tok = os.getenv("MEDIUM_INTEGRATION_TOKEN","")
        if tok:
            try:
                uid = requests.get("https://api.medium.com/v1/me",
                    headers={"Authorization":f"Bearer {tok}"}, timeout=10).json()["data"]["id"]
                _post(f"https://api.medium.com/v1/users/{uid}/posts",
                    headers={"Authorization":f"Bearer {tok}","Content-Type":"application/json"},
                    json_={"title":title,"contentFormat":"markdown","content":article["content"],
                           "tags":article.get("keywords",[])[:5],"canonicalUrl":url,"publishStatus":"public"})
                results.append({"platform":"medium","status":"ok"})
            except Exception as e:
                results.append({"platform":"medium","status":"error","error":str(e)})
        else:
            results.append({"platform":"medium","status":"skipped"})

        for r in results:
            log.info("  %-12s %s", r["platform"], r["status"])
        return results
