#!/usr/bin/env python3
import logging
from datetime import datetime
from pathlib import Path
log = logging.getLogger(__name__)

class SitePublisher:
    def __init__(self, site_dir):
        self.posts_dir = Path(site_dir) / "_posts"
        self.posts_dir.mkdir(parents=True, exist_ok=True)

    def publish(self, article):
        date     = article.get("date", datetime.utcnow().strftime("%Y-%m-%d"))
        filepath = self.posts_dir / f"{date}-{article['slug']}.md"
        tags     = ", ".join(f'"{k}"' for k in article.get("keywords",[]))
        fm = f"""---
layout: post
title: "{article['title'].replace('"',"'")}"
date: {date}
categories: [{article.get('category','tutorial')}]
tags: [{tags}]
description: "{article.get('meta_description','').replace('"',"'")}"
image: "{article.get('image','')}"
author: AutoBlog
sitemap: true
---"""
        filepath.write_text(fm + "\n\n" + article["content"], encoding="utf-8")
        log.info("Published: %s", filepath.name)
        return filepath
