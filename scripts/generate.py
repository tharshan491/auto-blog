#!/usr/bin/env python3
"""
generate.py – Advanced Article Generator
- 1500-2000 word articles
- Full SEO optimization
- Schema markup
- Internal links
- Table of contents
- Code examples
- Real FAQ from StackOverflow
- Humanizer integration
"""

import os, re, time, logging, requests
from datetime import datetime

log = logging.getLogger(__name__)

HF_API   = "https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-Instruct-v0.1"
HF_TOKEN = os.getenv("HF_TOKEN", "")

TYPES = [
    "beginner tutorial",
    "project ideas",
    "troubleshooting guide",
    "top tools comparison",
    "AI and automation use-cases",
]

# Internal links to inject automatically
INTERNAL_LINKS = {
    "python":       "/python-programming-guide/",
    "javascript":   "/javascript-tutorial/",
    "docker":       "/docker-beginners-guide/",
    "git":          "/git-crash-course/",
    "linux":        "/linux-command-line-guide/",
    "api":          "/rest-api-tutorial/",
    "machine learning": "/machine-learning-guide/",
    "react":        "/react-tutorial/",
    "nodejs":       "/nodejs-guide/",
    "sql":          "/sql-beginners-guide/",
}

# SEO meta templates
SEO_TEMPLATES = {
    "beginner tutorial":        "Learn {title} from scratch with this step-by-step beginner tutorial. Includes code examples, tips, and FAQs.",
    "project ideas":            "Discover {count} amazing {title} project ideas for beginners and advanced developers. Build real projects today!",
    "troubleshooting guide":    "Fix common {title} errors fast. Complete troubleshooting guide with solutions, code fixes, and expert tips.",
    "top tools comparison":     "Best {title} tools compared in {year}. Free and paid options reviewed with pros, cons, and recommendations.",
    "AI and automation use-cases": "How to use AI and automation with {title}. Practical examples, free tools, and step-by-step implementation guide.",
}


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
        return next(iter(pages.values())).get("extract","")[:800]
    except: return ""


def _so_questions(tag, limit=8):
    try:
        r = requests.get("https://api.stackexchange.com/2.3/search/advanced",
            params={"order":"desc","sort":"votes","tagged":tag,
                    "site":"stackoverflow","pagesize":limit}, timeout=10)
        items = r.json().get("items",[])
        return [(i["title"], i.get("answer_count",0)) for i in items]
    except: return []


def _so_answers(tag, limit=3):
    """Get actual answer snippets from StackOverflow."""
    try:
        r = requests.get("https://api.stackexchange.com/2.3/search/advanced",
            params={"order":"desc","sort":"votes","tagged":tag,
                    "site":"stackoverflow","pagesize":limit,
                    "filter":"withbody"}, timeout=10)
        items = r.json().get("items",[])
        results = []
        for item in items:
            title = item.get("title","")
            body  = re.sub(r'<[^>]+>', '', item.get("body",""))[:200]
            results.append({"question": title, "snippet": body})
        return results
    except: return []


def _inject_internal_links(content):
    """Add internal links to relevant keywords in the content."""
    linked = set()
    for keyword, path in INTERNAL_LINKS.items():
        if keyword.lower() in content.lower() and keyword not in linked:
            # Only link first occurrence
            pattern = re.compile(r'\b(' + re.escape(keyword) + r')\b', re.IGNORECASE)
            def make_link(m):
                return f"[{m.group(1)}]({path})"
            content = pattern.sub(make_link, content, count=1)
            linked.add(keyword)
    return content


def _build_meta_description(title, atype):
    template = SEO_TEMPLATES.get(atype, "Learn {title} with this comprehensive guide.")
    return template.format(
        title=title,
        count=10,
        year=datetime.utcnow().year
    )[:155]


def _hf_generate(prompt):
    if not HF_TOKEN: return ""
    for i in range(3):
        try:
            r = requests.post(HF_API,
                headers={"Authorization": f"Bearer {HF_TOKEN}"},
                json={"inputs": prompt,
                      "parameters": {
                          "max_new_tokens": 1800,
                          "temperature":    0.72,
                          "top_p":          0.9,
                          "return_full_text": False,
                      }},
                timeout=120)
            if r.status_code == 503:
                log.info("HF model loading, waiting %ds...", 20*(i+1))
                time.sleep(20*(i+1)); continue
            r.raise_for_status()
            data = r.json()
            text = data[0].get("generated_text","") if isinstance(data,list) else ""
            if len(text.strip()) > 400:
                return text
        except Exception as e:
            log.warning("HF attempt %d: %s", i+1, e)
            time.sleep(5)
    return ""


def _build_long_template(topic, atype, context, so_qs, so_answers):
    """
    Build a high-quality 1500-2000 word template article.
    Used as fallback when HF is unavailable.
    """
    title   = topic["title"]
    kw      = topic.get("keywords", [title.split()[0].lower()])
    src     = topic.get("source","")
    year    = datetime.utcnow().year
    primary_kw = kw[0] if kw else title.split()[0].lower()

    # Section structure per article type
    structures = {
        "beginner tutorial": {
            "sections": [
                ("Introduction",         f"What is {title} and why should you learn it?"),
                ("Prerequisites",        f"What you need before starting with {title}"),
                ("Installation & Setup", f"How to install and configure {title}"),
                ("Core Concepts",        f"The fundamental concepts of {title} explained simply"),
                ("Step-by-Step Guide",   f"Building your first project with {title}"),
                ("Code Examples",        f"Practical {title} code examples you can use today"),
                ("Common Mistakes",      f"Mistakes beginners make with {title} and how to avoid them"),
                ("Best Practices",       f"Professional {title} best practices"),
                ("Next Steps",           f"Where to go after learning the basics of {title}"),
            ]
        },
        "project ideas": {
            "sections": [
                ("Why Build Projects?",    f"Why building {title} projects accelerates your learning"),
                ("Beginner Projects",      f"5 beginner-friendly {title} project ideas"),
                ("Intermediate Projects",  f"5 intermediate {title} projects to challenge yourself"),
                ("Advanced Projects",      f"3 advanced {title} projects for experienced developers"),
                ("Project Planning Tips",  f"How to plan and execute a {title} project"),
                ("Tools & Resources",      f"Best free tools for {title} projects"),
                ("Getting Help",           f"Where to get help when stuck on your {title} project"),
                ("Showcasing Your Work",   f"How to showcase your {title} projects to employers"),
            ]
        },
        "troubleshooting guide": {
            "sections": [
                ("Overview",              f"Common {title} problems and why they happen"),
                ("Error Messages",        f"Most frequent {title} error messages explained"),
                ("Installation Issues",   f"Fixing {title} installation and setup problems"),
                ("Runtime Errors",        f"Solving {title} runtime and execution errors"),
                ("Performance Issues",    f"Diagnosing and fixing {title} performance problems"),
                ("Debugging Strategies",  f"Professional debugging techniques for {title}"),
                ("Quick Reference",       f"{title} troubleshooting quick reference guide"),
                ("Getting More Help",     f"Where to get expert help with {title} problems"),
            ]
        },
        "top tools comparison": {
            "sections": [
                ("Overview",              f"Best {title} tools in {year}"),
                ("Free Tools",            f"Top free {title} tools you can use today"),
                ("Premium Tools",         f"Best paid {title} tools worth the investment"),
                ("Feature Comparison",    f"Side-by-side {title} tools comparison"),
                ("Performance Benchmarks",f"Speed and performance comparison of {title} tools"),
                ("Ease of Use",           f"Which {title} tool is easiest to learn?"),
                ("Community & Support",   f"Community size and support quality for {title} tools"),
                ("How to Choose",         f"How to pick the right {title} tool for your needs"),
                ("Final Recommendation",  f"Our top {title} tool recommendation"),
            ]
        },
        "AI and automation use-cases": {
            "sections": [
                ("Introduction",          f"How AI is transforming {title}"),
                ("Use Cases",             f"Top AI and automation use cases for {title}"),
                ("Getting Started",       f"How to start automating {title} with AI"),
                ("Free AI Tools",         f"Free AI tools for {title} automation"),
                ("Code Examples",         f"AI-powered {title} code examples"),
                ("Real-World Examples",   f"Real companies using AI for {title}"),
                ("Challenges",            f"Common challenges when automating {title}"),
                ("Future Trends",         f"The future of AI in {title}"),
                ("Conclusion",            f"Getting started with AI and {title} today"),
            ]
        },
    }

    struct   = structures.get(atype, structures["beginner tutorial"])
    sections = struct["sections"]

    # Build TOC
    toc = "\n".join(
        f"{i+1}. [{name}](#{slugify(name)})"
        for i, (name, _) in enumerate(sections)
    )

    # Build body
    body = ""
    for i, (section_name, section_desc) in enumerate(sections):
        body += f"\n## {section_name}\n\n"

        # Add Wikipedia context to introduction
        if section_name == "Introduction" and context:
            body += f"{context[:400]}\n\n"

        body += f"{section_desc}. "
        body += f"Understanding this aspect of **{title}** is crucial for any developer "
        body += f"working with {primary_kw} in {year}.\n\n"

        # Add code examples to relevant sections
        if any(word in section_name.lower() for word in
               ["code", "setup", "install", "step", "example", "getting started"]):
            body += f"Here's a practical example:\n\n"
            body += f"```{primary_kw}\n"
            body += f"# {title} - Example {i+1}\n"
            body += f"# Install required packages first\n"
            body += f"# pip install {primary_kw}\n\n"
            body += f"# Basic usage example\n"
            body += f"print('Hello from {title}!')\n"
            body += f"```\n\n"

        # Add a tip box occasionally
        if i % 3 == 1:
            body += f"> 💡 **Pro Tip:** Always test your {title} code in a "
            body += f"development environment before deploying to production.\n\n"

        # Add SO answer snippets to relevant sections
        if so_answers and "error" in section_name.lower() or "troubleshoot" in section_name.lower():
            for ans in so_answers[:2]:
                body += f"**Q: {ans['question']}**\n\n"
                body += f"{ans['snippet']}\n\n"

    # Build FAQ from StackOverflow
    faq = ""
    if so_qs:
        faq = "\n".join(
            f"\n### {q}\n\nThis is one of the most common questions about {title}. "
            f"The answer depends on your specific use case, but generally you should "
            f"follow the official documentation and best practices. "
            f"There are {answers} answers on StackOverflow for this question.\n"
            for q, answers in so_qs[:6]
        )
    else:
        faq = f"""
### What is {title} used for?
{title} is widely used in modern software development for building scalable applications.

### Is {title} free to use?
Most {title} tools and frameworks are open source and completely free.

### How long does it take to learn {title}?
With consistent practice, you can learn the basics of {title} in 2-4 weeks.

### What are the prerequisites for {title}?
Basic programming knowledge is recommended before starting with {title}.

### Where can I find {title} documentation?
The official documentation is always the best starting point for learning {title}.

### What is the best way to practice {title}?
Building real projects is the most effective way to master {title}.
"""

    source_note = f"\n> 📡 *Topic discovered from: **{src}***\n" if src else ""
    meta_desc   = _build_meta_description(title, atype)

    article = f"""# {title}: Complete {atype.title()} Guide ({year})

{source_note}
> **{meta_desc}**

---

## Table of Contents

{toc}

---

{body}

---

## Frequently Asked Questions About {title}

{faq}

---

## Conclusion

Mastering **{title}** takes time and practice, but it's absolutely worth the effort.
In this guide, we covered everything from the basics to advanced techniques.

Here's what we learned:
- The core concepts of {title}
- How to set up and configure your environment
- Practical code examples you can use right away
- Common mistakes and how to avoid them
- The best tools and resources available

**Your next steps:**
1. Practice the code examples from this guide
2. Build a small project using {title}
3. Join the community on Reddit and Discord
4. Read the official documentation for deeper knowledge

*Found this helpful? Share it with a fellow developer! 🚀*

---

*Last updated: {datetime.utcnow().strftime("%B %d, %Y")} | Keywords: {', '.join(kw[:5])}*
"""
    return article


class ArticleGenerator:
    def generate(self, topic):
        title   = topic["title"]
        atype   = TYPES[hash(topic["slug"]) % len(TYPES)]
        context = _wiki(title)
        so_tag  = topic.get("so_tag") or (
            topic.get("keywords", ["python"])[0].lower().split()[0])
        so_qs      = _so_questions(so_tag, limit=8)
        so_answers = _so_answers(so_tag, limit=3)

        log.info("Generating '%s' as '%s'", title, atype)

        # Try HuggingFace first with a rich prompt
        prompt = f"""Write a comprehensive, SEO-optimised programming article in Markdown format.

Title: {title}
Type: {atype}
Primary keyword: {so_tag}
Related keywords: {', '.join(topic.get('keywords', [])[:6])}
Background: {context[:500]}

REQUIREMENTS:
1. Start with a compelling H1 title and introduction (150+ words)
2. Include a numbered Table of Contents
3. Write at least 8 detailed H2 sections (200+ words each)
4. Include 3+ practical code examples in fenced code blocks
5. Add a Pro Tips section with actionable advice
6. Include a FAQ section with 6 questions and detailed answers
7. End with a strong conclusion and call-to-action
8. Target length: 1500-2000 words
9. Use natural, conversational tone — not robotic
10. Include specific examples, numbers, and real use cases

Write the full article now:"""

        content = _hf_generate(prompt)

        if len(content.strip()) < 500:
            log.info("HF output too short, using advanced template for: %s", title)
            content = _build_long_template(topic, atype, context, so_qs, so_answers)

        # Inject internal links
        content = _inject_internal_links(content)

        # Always humanize
        try:
            from humanizer import humanize, detect_ai_score
            before = detect_ai_score(content)
            log.info("AI score BEFORE humanizing: %.1f", before["score"])
            result  = humanize(content, max_passes=3)
            content = result["text"]
            log.info("AI score AFTER humanizing:  %.1f (passes=%d, human=%s)",
                     result["score"], result["passes"], result["is_human"])
            ai_score  = result["score"]
            ai_passes = result["passes"]
        except Exception as e:
            log.warning("Humanizer error: %s", e)
            ai_score  = 0
            ai_passes = 0

        slug     = topic.get("slug") or slugify(title)
        meta     = _build_meta_description(title, atype)
        word_count = len(content.split())
        log.info("Article ready: '%s' (%d words)", title, word_count)

        return {
            "title":            title,
            "slug":             slug,
            "meta_description": meta,
            "content":          content,
            "keywords":         topic.get("keywords", []),
            "category":         atype,
            "date":             datetime.utcnow().strftime("%Y-%m-%d"),
            "source":           topic.get("source", ""),
            "image":            "",
            "ai_score":         ai_score,
            "humanizer_passes": ai_passes,
            "word_count":       word_count,
        }
