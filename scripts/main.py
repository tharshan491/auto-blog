#!/usr/bin/env python3
import os, sys, logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from discover    import TopicDiscoverer
from generate    import ArticleGenerator
from publish     import SitePublisher
from share       import SocialSharer
from log_manager import ArticleLog
from image_fetch import ImageFetcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(),
              logging.FileHandler("autoblog.log", encoding="utf-8")],
)
log = logging.getLogger(__name__)

SITE_DIR   = Path(__file__).parent.parent / "site"
LOG_FILE   = Path(__file__).parent.parent / "article_log.json"
MAX_TOPICS = int(os.getenv("MAX_TOPICS", "2"))

def run():
    log.info("AutoBlog started: %s", datetime.utcnow().isoformat())
    article_log = ArticleLog(LOG_FILE)

    log.info("STEP 1 › Discovering topics…")
    topics     = TopicDiscoverer().get_top_topics(limit=MAX_TOPICS * 3)
    new_topics = [t for t in topics if not article_log.already_published(t["slug"])]
    if not new_topics:
        log.info("No new topics. Exiting.")
        return

    selected = new_topics[:MAX_TOPICS]
    log.info("Selected: %s", [t["title"] for t in selected])

    generator = ArticleGenerator()
    fetcher   = ImageFetcher()
    publisher = SitePublisher(SITE_DIR)
    sharer    = SocialSharer()

    for topic in selected:
        try:
            log.info("── Processing: %s", topic["title"])
            article          = generator.generate(topic)
            article["image"] = fetcher.get_image(topic["title"])
            publisher.publish(article)
            site_url         = os.getenv("SITE_URL", "https://tharshan491.github.io/auto-blog")
            article_url      = f"{site_url}/{article['slug']}/"
            share_results    = sharer.share_all(article, article_url)
            article_log.record(article["slug"], article["title"],
                               article_url, topic.get("source",""), share_results)
            log.info("✓ Published: %s", article_url)
        except Exception as exc:
            log.exception("✗ Failed '%s': %s", topic["title"], exc)

    log.info("AutoBlog complete.")

if __name__ == "__main__":
    run()
