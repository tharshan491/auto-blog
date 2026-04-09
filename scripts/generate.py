#!/usr/bin/env python3
import os, re, time, logging, requests
from datetime import datetime

log = logging.getLogger(__name__)
HF_API   = "https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-Instruct-v0.1"
HF_TOKEN = os.getenv("HF_TOKEN", "")
TYPES    = ["beginner tutorial","project ideas","troubleshooting guide","top tools","AI/automation use-cases"]

def slugify(text):
    text = re.sub(r"[^\w\s-]", "", text.lower().strip())
    return re.sub(r"[\s_-]+", "-", text)[:80]

def _wiki(query):
    try:
        r = requests.get("https://en.wikipedia.org/w/api.php",
            params={"action":"query","list":"search","srsearch":query,"format":"json","srlimit":1}, timeout=10)
        title = r.json()["query"]["search"][0]["title"]
        r2 = requests.get("https://en.wikipedia.org/w/api.php",
            params={"action":"query","prop":"extracts","exintro":True,"explaintext":True,"titles":title,"format":"json"}, timeout=10)
        return next(iter(r2.json()["query"]["pages"].values())).get("extract","")[:600]
    except: return ""

def _hf(prompt):
    if not HF_TOKEN: return ""
    for i in range(3):
        try:
            r = requests.post(HF_API,
                headers={"Authorization": f"Bearer {HF_TOKEN}"},
                json={"inputs": prompt, "parameters": {"max_new_tokens": 1000, "temperature": 0.7, "return_full_text": False}},
                timeout=90)
            if r.status_code == 503: time.sleep(20*(i+1)); continue
            r.raise_for_status()
            data = r.json()
            return data[0].get("generated_text","") if isinstance(data, list) else ""
        except Exception as e:
            log.warning("HF attempt %d: %s", i+1, e); time.sleep(5)
    return ""

def _template(topic, atype, context):
    title    = topic["title"]
    kw       = ", ".join(topic.get("keywords", []))
    sections = ["Introduction","Prerequisites","Step-by-Step Guide","Code Examples","Common Mistakes","Conclusion"]
    toc      = "\n".join(f"- [{s}](#{s.lower().replace(' ','-')})" for s in sections)
    body     = ""
    for s in sections:
        body += f"\n## {s}\n\n"
        body += f"{context[:200] if context and s == 'Introduction' else ''}\n"
        body += f"This section covers **{s.lower()}** for {title}. Practice regularly to master this topic.\n\n"
        if s == "Code Examples":
            body += "```python\n# Example\nprint('Hello, World!')\n```\n\n"
    return f"# {title}: Complete {atype.title()}\n\n> **Keywords:** {kw}\n\n## Table of Contents\n{toc}\n{body}"

class ArticleGenerator:
    def generate(self, topic):
        title   = topic["title"]
        atype   = TYPES[hash(topic["slug"]) % len(TYPES)]
        context = _wiki(title)
        prompt  = (f"Write a detailed SEO-optimised programming article in Markdown.\n"
                   f"Title: {title}\nType: {atype}\n"
                   f"Keywords: {', '.join(topic.get('keywords',[]))}\n"
                   f"Background: {context[:300]}\n"
                   f"Include: intro, table of contents, 6 sections with code examples, FAQ, conclusion. ~800 words.")
        content = _hf(prompt)
        if len(content.strip()) < 300:
            log.info("Using template fallback.")
            content = _template(topic, atype, context)
        slug = topic.get("slug") or slugify(title)
        return {
            "title": title, "slug": slug,
            "meta_description": topic.get("description","")[:155] or f"Learn {title}.",
            "content": content, "keywords": topic.get("keywords",[]),
            "category": atype, "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "source": topic.get("source",""), "image": ""
        }
