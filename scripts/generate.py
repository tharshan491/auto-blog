#!/usr/bin/env python3
import os, re, time, logging, requests
from datetime import datetime

log = logging.getLogger(__name__)
HF_API   = "https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-Instruct-v0.1"
HF_TOKEN = os.getenv("HF_TOKEN", "")
TYPES    = [
    "beginner tutorial",
    "project ideas",
    "troubleshooting guide",
    "top tools comparison",
    "AI and automation use-cases"
]

def slugify(text):
    text = re.sub(r"[^\w\s-]", "", text.lower().strip())
    return re.sub(r"[\s_-]+", "-", text)[:80]

def _wiki(query):
    try:
        r = requests.get("https://en.wikipedia.org/w/api.php",
            params={"action":"query","list":"search",
                    "srsearch":query,"format":"json","srlimit":1}, timeout=10)
        results = r.json()["query"]["search"]
        if not results: return ""
        title = results[0]["title"]
        r2 = requests.get("https://en.wikipedia.org/w/api.php",
            params={"action":"query","prop":"extracts","exintro":True,
                    "explaintext":True,"titles":title,"format":"json"}, timeout=10)
        pages = r2.json()["query"]["pages"]
        return next(iter(pages.values())).get("extract","")[:600]
    except: return ""

def _so_questions(tag, limit=5):
    try:
        r = requests.get("https://api.stackexchange.com/2.3/search/advanced",
            params={"order":"desc","sort":"votes","tagged":tag,
                    "site":"stackoverflow","pagesize":limit}, timeout=10)
        return [i["title"] for i in r.json().get("items",[])]
    except: return []

def _hf_generate(prompt):
    if not HF_TOKEN: return ""
    for i in range(3):
        try:
            r = requests.post(HF_API,
                headers={"Authorization": f"Bearer {HF_TOKEN}"},
                json={"inputs": prompt,
                      "parameters": {
                          "max_new_tokens": 1200,
                          "temperature": 0.7,
                          "return_full_text": False
                      }},
                timeout=90)
            if r.status_code == 503:
                time.sleep(20*(i+1)); continue
            r.raise_for_status()
            data = r.json()
            text = data[0].get("generated_text","") if isinstance(data,list) else ""
            if len(text.strip()) > 200: return text
        except Exception as e:
            log.warning("HF attempt %d: %s", i+1, e)
            time.sleep(5)
    return ""

def _template(topic, atype, context, so_qs):
    title = topic["title"]
    kw    = ", ".join(topic.get("keywords", []))
    src   = topic.get("source","")
    faq   = "\n".join(f"- {q}" for q in so_qs[:5]) if so_qs else "- No FAQs available."

    sections = {
        "beginner tutorial": [
            "Introduction", "Prerequisites", "Installation & Setup",
            "Step-by-Step Guide", "Code Examples", "Common Mistakes", "Next Steps"
        ],
        "project ideas": [
            "Why Build Projects?", "Beginner Projects", "Intermediate Projects",
            "Advanced Projects", "Tips for Success", "Resources"
        ],
        "troubleshooting guide": [
            "Overview", "Common Errors", "Debugging Strategies",
            "Quick Fixes", "Advanced Solutions", "Getting Help"
        ],
        "top tools comparison": [
            "Overview", "Top Free Tools", "Features Comparison",
            "How to Choose", "Getting Started", "Final Thoughts"
        ],
        "AI and automation use-cases": [
            "Introduction", "Practical Automation Ideas", "Code Examples",
            "Tools & Libraries", "Real-World Examples", "Conclusion"
        ],
    }

    secs = sections.get(atype, sections["beginner tutorial"])
    toc  = "\n".join(f"- [{s}](#{s.lower().replace(' ','-')})" for s in secs)

    body = ""
    for s in secs:
        body += f"\n## {s}\n\n"
        if s == "Introduction" and context:
            body += context[:300] + "\n\n"
        body += f"This section covers **{s.lower()}** for {title}. "
        body += f"Whether you are a beginner or experienced developer, mastering {title} will boost your skills.\n\n"
        if s in ("Code Examples", "Step-by-Step Guide", "Installation & Setup"):
            body += f"```bash\n# Example for {title}\npip install example-package\nprint('Hello from {title}!')\n```\n\n"

    source_note = f"\n> 📡 *Topic discovered from {src}*\n" if src else ""

    return f"""# {title}: Complete {atype.title()} Guide

> **Last updated:** {datetime.utcnow().strftime("%B %d, %Y")} · **Level:** Beginner to Advanced · **Keywords:** {kw}
{source_note}
## Table of Contents
{toc}

---
{body}
## Frequently Asked Questions

{faq}

---

## Conclusion

Mastering **{title}** takes practice and curiosity. Start small, build projects,
and keep experimenting. Bookmark this guide and revisit as you grow!

*Found this helpful? Share it with your network! 🚀*
"""

class ArticleGenerator:
    def generate(self, topic):
        title   = topic["title"]
        atype   = TYPES[hash(topic["slug"]) % len(TYPES)]
        context = _wiki(title)
        so_tag  = topic.get("so_tag") or (
            topic.get("keywords",["python"])[0].lower().split()[0])
        so_qs   = _so_questions(so_tag)

        log.info("Generating '%s' as '%s'", title, atype)

        prompt = (
            f"Write a detailed, SEO-optimised programming article in Markdown.\n"
            f"Title: {title}\n"
            f"Type: {atype}\n"
            f"Keywords: {', '.join(topic.get('keywords',[]))}\n"
            f"Background context: {context[:400]}\n\n"
            f"Requirements:\n"
            f"- Start with a compelling introduction\n"
            f"- Include a table of contents\n"
            f"- Write at least 6 detailed H2 sections\n"
            f"- Include practical code examples in fenced blocks\n"
            f"- Add a FAQ section with 5 questions\n"
            f"- End with a conclusion and call to action\n"
            f"- Target length: 800-1000 words\n"
            f"- Make it beginner-friendly but informative\n"
        )

        content = _hf_generate(prompt)
        if len(content.strip()) < 300:
            log.info("Using template fallback for: %s", title)
            content = _template(topic, atype, context, so_qs)

        slug = topic.get("slug") or slugify(title)
        meta = topic.get("description","")[:155] or f"Learn {title}: {atype} for developers."

        return {
            "title":            title,
            "slug":             slug,
            "meta_description": meta,
            "content":          content,
            "keywords":         topic.get("keywords", []),
            "category":         atype,
            "date":             datetime.utcnow().strftime("%Y-%m-%d"),
            "source":           topic.get("source", ""),
            "image":            ""
        }
