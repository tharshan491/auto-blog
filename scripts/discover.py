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
            soup = BeautifulSoup(
                self.s.get("https://github.com/trending", timeout=15).text,
                "html.parser")
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

    def _hackernews(self, limit=10):
        topics = []
        try:
            r = self.s.get(
                "https://hacker-news.firebaseio.com/v0/topstories.json",
                timeout=15)
            story_ids = r.json()[:20]
            for sid in story_ids:
                try:
                    story = self.s.get(
                        f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                        timeout=10).json()
                    title = story.get("title", "")
                    score = story.get("score", 0)
                    stype = story.get("type", "")
                    if stype != "story" or score < 50 or len(title) < 10:
                        continue
                    # Only programming related
                    prog_words = ["python","javascript","rust","go","java",
                                  "code","programming","developer","api",
                                  "framework","open source","github","linux",
                                  "database","ai","machine learning","tool"]
                    if not any(w in title.lower() for w in prog_words):
                        continue
                    topics.append({
                        "title": title[:120],
                        "slug": slugify(title),
                        "description": f"Trending on Hacker News with {score} points: {title}",
                        "source": "hackernews",
                        "keywords": ["hacker news", "programming", "tech"]
                    })
                    if len(topics) >= limit: break
                    time.sleep(0.2)
                except: continue
        except Exception as e:
            log.warning("HackerNews: %s", e)
        return topics[:limit]

    def _reddit(self, limit=10):
        topics = []
        for sub in ["programming","learnpython","webdev","javascript","devops"]:
            try:
                data = self.s.get(
                    f"https://www.reddit.com/r/{sub}/hot.json?limit=5",
                    timeout=15).json()
                for post in data["data"]["children"]:
                    p = post["data"]
                    if p.get("score", 0) > 100 and len(p["title"]) > 10:
                        topics.append({
                            "title": p["title"][:120],
                            "slug": slugify(p["title"]),
                            "description": p["title"],
                            "source": f"reddit/{sub}",
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
            r = self.s.get(
                "https://api.stackexchange.com/2.3/tags",
                params={"order":"desc","sort":"popular",
                        "site":"stackoverflow","pagesize":limit},
                timeout=15)
            for tag in r.json().get("items", []):
                name  = tag["name"]
                title = f"{name.title()} Programming Guide"
                topics.append({
                    "title": title,
                    "slug": slugify(title),
                    "description": f"Comprehensive {name} guide.",
                    "source": "stackoverflow",
                    "keywords": [name, "programming", "guide"],
                    "so_tag": name
                })
        except Exception as e:
            log.warning("StackOverflow: %s", e)
        return topics

    def _google_trends(self, limit=5):
        topics = []
        try:
            from pytrends.request import TrendReq
            pt = TrendReq(hl="en-US", tz=0, timeout=(10, 25))
            keywords = ["python tutorial", "javascript framework",
                        "rust programming", "machine learning", "docker tutorial"]
            pt.build_payload(keywords[:5], timeframe="now 7-d")
            related = pt.related_queries()
            seen = set()
            for kw, data in related.items():
                rising = data.get("rising")
                if rising is None or rising.empty: continue
                for _, row in rising.iterrows():
                    q = str(row.get("query", "")).strip()
                    if not q or q in seen or len(q) < 5: continue
                    seen.add(q)
                    title = q.title()
                    topics.append({
                        "title": title,
                        "slug": slugify(title),
                        "description": f"Rising Google trend: {q}",
                        "source": "google_trends",
                        "keywords": q.lower().split() + ["tutorial"]
                    })
                if len(topics) >= limit: break
        except ImportError:
            log.warning("pytrends not installed")
        except Exception as e:
            log.warning("Google Trends: %s", e)
        return topics[:limit]

    def get_top_topics(self, limit=20):
        log.info("Fetching from GitHub Trending...")
        all_t = self._github()
        log.info("Fetching from Hacker News...")
        all_t += self._hackernews()
        log.info("Fetching from Reddit...")
        all_t += self._reddit()
        log.info("Fetching from StackOverflow...")
        all_t += self._stackoverflow()
        log.info("Fetching from Google Trends...")
        all_t += self._google_trends()

        seen, unique = set(), []
        for t in all_t:
            if t["slug"] not in seen:
                seen.add(t["slug"])
                unique.append(t)

        log.info("Discovered %d unique topics from 5 sources.", len(unique))
        return unique[:limit]
