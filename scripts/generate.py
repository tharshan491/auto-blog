#!/usr/bin/env python3
import os, re, time, logging, requests
from datetime import datetime

log = logging.getLogger(__name__)
HF_API   = "https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-Instruct-v0.1"
HF_TOKEN = os.getenv("HF_TOKEN", "")
TYPES    = ["beginner tutorial","project ideas","troubleshooting guide","top tools comparison","AI and automation use-cases"]
INTERNAL_LINKS = {"python":"/python-guide/","javascript":"/javascript-tutorial/","docker":"/docker-guide/","git":"/git-guide/","linux":"/linux-guide/","api":"/api-tutorial/","react":"/react-tutorial/","sql":"/sql-guide/"}
SEO_TEMPLATES  = {"beginner tutorial":"Learn {title} from scratch with this step-by-step tutorial. Includes code examples, tips, and FAQs.","project ideas":"Discover 10 amazing {title} project ideas for beginners and advanced developers.","troubleshooting guide":"Fix common {title} errors fast. Complete troubleshooting guide with solutions and code fixes.","top tools comparison":"Best {title} tools compared in {year}. Free and paid options reviewed with pros and cons.","AI and automation use-cases":"How to use AI and automation with {title}. Practical examples and step-by-step guide."}

def slugify(text):
    text = re.sub(r"[^\w\s-]","",text.lower().strip())
    return re.sub(r"[\s_-]+","-",text)[:80]

def _wiki(query):
    try:
        r  = requests.get("https://en.wikipedia.org/w/api.php",params={"action":"query","list":"search","srsearch":query,"format":"json","srlimit":1},timeout=10)
        t  = r.json()["query"]["search"][0]["title"]
        r2 = requests.get("https://en.wikipedia.org/w/api.php",params={"action":"query","prop":"extracts","exintro":True,"explaintext":True,"titles":t,"format":"json"},timeout=10)
        return next(iter(r2.json()["query"]["pages"].values())).get("extract","")[:800]
    except: return ""

def _so_questions(tag,limit=8):
    try:
        r = requests.get("https://api.stackexchange.com/2.3/search/advanced",params={"order":"desc","sort":"votes","tagged":tag,"site":"stackoverflow","pagesize":limit},timeout=10)
        return [(i["title"],i.get("answer_count",0)) for i in r.json().get("items",[])]
    except: return []

def _hf_generate(prompt):
    if not HF_TOKEN: return ""
    for i in range(3):
        try:
            r = requests.post(HF_API,headers={"Authorization":f"Bearer {HF_TOKEN}"},json={"inputs":prompt,"parameters":{"max_new_tokens":1800,"temperature":0.72,"top_p":0.9,"return_full_text":False}},timeout=120)
            if r.status_code==503: time.sleep(20*(i+1)); continue
            r.raise_for_status()
            data = r.json()
            text = data[0].get("generated_text","") if isinstance(data,list) else ""
            if len(text.strip())>400: return text
        except Exception as e:
            log.warning("HF attempt %d: %s",i+1,e); time.sleep(5)
    return ""

def _inject_links(content):
    linked = set()
    for kw,path in INTERNAL_LINKS.items():
        if kw.lower() in content.lower() and kw not in linked:
            content = re.sub(r'\b('+re.escape(kw)+r')\b',f"[\\1]({path})",content,count=1,flags=re.IGNORECASE)
            linked.add(kw)
    return content

def _meta(title,atype):
    t = SEO_TEMPLATES.get(atype,"Learn {title} with this comprehensive guide.")
    return t.format(title=title,year=datetime.utcnow().year,count=10)[:155]

def _template(topic,atype,context,so_qs):
    title  = topic["title"]
    kw     = topic.get("keywords",[title.split()[0].lower()])
    src    = topic.get("source","")
    year   = datetime.utcnow().year
    pk     = kw[0] if kw else title.split()[0].lower()

    structs = {
        "beginner tutorial":["Introduction","Prerequisites","Installation & Setup","Core Concepts","Step-by-Step Guide","Code Examples","Common Mistakes","Best Practices","Next Steps"],
        "project ideas":["Why Build Projects?","Beginner Projects","Intermediate Projects","Advanced Projects","Project Planning Tips","Tools & Resources","Showcasing Your Work","Next Steps"],
        "troubleshooting guide":["Overview","Error Messages","Installation Issues","Runtime Errors","Performance Issues","Debugging Strategies","Quick Reference","Getting More Help"],
        "top tools comparison":["Overview","Free Tools","Premium Tools","Feature Comparison","Performance","Ease of Use","Community & Support","How to Choose","Recommendation"],
        "AI and automation use-cases":["Introduction","Use Cases","Getting Started","Free AI Tools","Code Examples","Real-World Examples","Challenges","Future Trends","Conclusion"],
    }
    secs = structs.get(atype,structs["beginner tutorial"])
    toc  = "\n".join(f"{i+1}. [{s}](#{slugify(s)})" for i,s in enumerate(secs))
    body = ""
    for i,s in enumerate(secs):
        body += f"\n## {s}\n\n"
        if s=="Introduction" and context: body += context[:400]+"\n\n"
        body += f"This section covers **{s.lower()}** for {title}. Whether you're a beginner or experienced developer, mastering {title} will boost your skills in {year}.\n\n"
        if any(w in s.lower() for w in ["code","setup","install","step","example"]):
            body += f"```{pk}\n# {title} example\n# pip install {pk}\nprint('Hello from {title}!')\n```\n\n"
        if i%3==1: body += f"> 💡 **Pro Tip:** Always test your {title} code in a development environment before deploying to production.\n\n"

    faq = ""
    if so_qs:
        for q,ans in so_qs[:6]:
            faq += f"\n### {q}\n\nThis is one of the most common {title} questions with {ans} answers on StackOverflow. Check the official docs for the most up-to-date answer.\n"
    else:
        faq = f"""
### What is {title} used for?
{title} is widely used in modern software development for building scalable applications.

### Is {title} free?
Most {title} tools are open source and completely free.

### How long to learn {title}?
With consistent practice, you can learn the basics in 2-4 weeks.

### What are the prerequisites?
Basic programming knowledge is recommended before starting with {title}.

### Where is the documentation?
The official docs are always the best starting point for {title}.

### Best way to practice {title}?
Building real projects is the most effective way to master {title}.
"""
    src_note = f"\n> 📡 *Discovered from: **{src}***\n" if src else ""
    return f"""# {title}: Complete {atype.title()} Guide ({year})
{src_note}
> **{_meta(title,atype)}**

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

Mastering **{title}** takes time and practice but is absolutely worth it.
In this guide we covered core concepts, setup, code examples, and best practices.

**Your next steps:**
1. Practice the code examples from this guide
2. Build a small project using {title}
3. Join the community on Reddit and Discord
4. Read the official documentation for deeper knowledge

*Found this helpful? Share it with a fellow developer! 🚀*

---
*Last updated: {datetime.utcnow().strftime("%B %d, %Y")} | Keywords: {", ".join(kw[:5])}*
"""

class ArticleGenerator:
    def generate(self,topic):
        title   = topic["title"]
        atype   = TYPES[hash(topic["slug"])%len(TYPES)]
        context = _wiki(title)
        so_tag  = topic.get("so_tag") or (topic.get("keywords",["python"])[0].lower().split()[0])
        so_qs   = _so_questions(so_tag,limit=8)

        log.info("Generating '%s' as '%s'",title,atype)

        prompt = (
            f"Write a comprehensive SEO-optimised programming article in Markdown.\n"
            f"Title: {title}\nType: {atype}\n"
            f"Keywords: {', '.join(topic.get('keywords',[])[:6])}\n"
            f"Background: {context[:500]}\n\n"
            f"Requirements:\n"
            f"- Compelling introduction (150+ words)\n"
            f"- Numbered Table of Contents\n"
            f"- 8 detailed H2 sections (200+ words each)\n"
            f"- 3+ code examples in fenced blocks\n"
            f"- Pro Tips boxes\n"
            f"- FAQ with 6 questions and answers\n"
            f"- Strong conclusion with call-to-action\n"
            f"- Target: 1500-2000 words\n"
            f"- Conversational natural tone\n"
            f"Write the full article now:\n"
        )

        content = _hf_generate(prompt)
        if len(content.strip())<500:
            log.info("Using advanced template for: %s",title)
            content = _template(topic,atype,context,so_qs)

        content = _inject_links(content)

        try:
            from humanizer import humanize,detect_ai_score
            before  = detect_ai_score(content)
            log.info("AI score BEFORE: %.1f",before["score"])
            result  = humanize(content,max_passes=3)
            content = result["text"]
            log.info("AI score AFTER:  %.1f (passes=%d)",result["score"],result["passes"])
            ai_score  = result["score"]
            ai_passes = result["passes"]
        except Exception as e:
            log.warning("Humanizer error: %s",e)
            ai_score  = 0
            ai_passes = 0

        words = len(content.split())
        log.info("Article ready: '%s' (%d words)",title,words)

        return {
            "title":            title,
            "slug":             topic.get("slug") or slugify(title),
            "meta_description": _meta(title,atype),
            "content":          content,
            "keywords":         topic.get("keywords",[]),
            "category":         atype,
            "date":             datetime.utcnow().strftime("%Y-%m-%d"),
            "source":           topic.get("source",""),
            "image":            "",
            "ai_score":         ai_score,
            "humanizer_passes": ai_passes,
            "word_count":       words,
        }
