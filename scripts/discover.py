#!/usr/bin/env python3
import re, time, logging, requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)
HEADERS = {"User-Agent": "AutoBlog/1.0"}

def slugify(text):
    text = re.sub(r"[^\w\s-]", "", text.lower().strip())
    return re.sub(r"[\s_-]+", "-", text)[:80]

class TopicDiscoverer:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update(HEADERS)

    def _github(self, limit=15):
        topics = []
        try:
            soup = BeautifulSoup(self.s.get("https://github.com/trending", timeout=15).text, "html.parser")
            for repo in soup.select("article.Box-row")[:limit]:
                name = repo.select_one("h2 a")
                desc = repo.select_one("p")
                lang = repo.select_one("[itemprop='programmingLanguage']")
                if not name: continue
                full  = name.get_text(" ", strip=True).replace(" / ", "/")
                title = full.split("/")[-1].replace("-", " ").title()
                if lang: title += f" – {lang.get_text(strip=True)} Project"
                topics.append({
                    "title": title, "slug": slugify(title),
                    "description": desc.get_text(strip=True)[:200] if desc else title,
                    "source": "github_trending",
                    "keywords": [lang.get_text(strip=True).lower() if lang else "github", "open source"]
                })
        except Exception as e:
            log.warning("GitHub trending: %s", e)
        return topics

    def _reddit(self, limit=10):
        topics = []
        for sub in ["programming", "learnpython", "webdev", "javascript", "devops"]:
            try:
                data = self.s.get(f"https://www.reddit.com/r/{sub}/hot.json?limit=5", timeout=15).json()
                for post in data["data"]["children"]:
                    p = post["data"]
                    if p.get("score", 0) > 100 and len(p["title"]) > 10:
                        topics.append({
                            "title": p["title"][:120], "slug": slugify(p["title"]),
                            "description": p["title"], "source": f"reddit/{sub}",
                            "keywords": [sub, "programming"]
                        })
                time.sleep(1)
            except Exception as e:
                log.warning("Reddit r/%s: %s", sub, e)
            if len(topics) >= limit: break
        return topics[:limit]

    def _stackoverflow(self, limit=10):
        topics = []
        try:
            r = self.s.get("https://api.stackexchange.com/2.3/tags",
                params={"order":"desc","sort":"popular","site":"stackoverflow","pagesize":limit}, timeout=15)
            for tag in r.json().get("items", []):
                name  = tag["name"]
                title = f"{name.title()} Programming Guide"
                topics.append({
                    "title": title, "slug": slugify(title),
                    "description": f"Comprehensive {name} guide.",
                    "source": "stackoverflow",
                    "keywords": [name, "programming", "guide"],
                    "so_tag": name
                })
        except Exception as e:
            log.warning("StackOverflow: %s", e)
        return topics

    def get_top_topics(self, limit=20):
        all_t = self._github() + self._reddit() + self._stackoverflow()
        seen, unique = set(), []
        for t in all_t:
            if t["slug"] not in seen:
                seen.add(t["slug"]); unique.append(t)
        log.info("Discovered %d unique topics.", len(unique))
        return unique[:limit]
