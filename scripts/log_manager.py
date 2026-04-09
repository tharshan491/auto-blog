#!/usr/bin/env python3
import json, logging
from datetime import datetime
from pathlib import Path
log = logging.getLogger(__name__)

class ArticleLog:
    def __init__(self, log_file):
        self.f = Path(log_file)
        self._d = json.loads(self.f.read_text(encoding="utf-8")) if self.f.exists() else {"articles":[],"slugs":[]}

    def _save(self):
        self.f.write_text(json.dumps(self._d, indent=2, ensure_ascii=False), encoding="utf-8")

    def already_published(self, slug):
        return slug in self._d.get("slugs", [])

    def record(self, slug, title, url, source, share_results):
        self._d.setdefault("articles",[]).append({
            "slug":slug, "title":title, "url":url, "source":source,
            "published_at":datetime.utcnow().isoformat(),
            "shares":share_results,
            "analytics":{"views":0,"clicks":0}
        })
        self._d.setdefault("slugs",[]).append(slug)
        self._save()
        log.info("Logged: %s", slug)
