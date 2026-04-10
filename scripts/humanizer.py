#!/usr/bin/env python3
import re, math, random, logging
from collections import Counter

log = logging.getLogger(__name__)

AI_PHRASES = {
    "it is important to note that": "keep in mind that",
    "it is worth mentioning that":  "worth noting:",
    "in conclusion,":               "to wrap up,",
    "in summary,":                  "to summarize quickly,",
    "furthermore,":                 "also,",
    "moreover,":                    "on top of that,",
    "in addition,":                 "plus,",
    "it should be noted that":      "note that",
    "utilize":                      "use",
    "leverage":                     "use",
    "facilitate":                   "help with",
    "endeavor":                     "try",
    "in order to":                  "to",
    "due to the fact that":         "because",
    "a wide range of":              "many",
    "a large number of":            "many",
    "at the end of the day":        "ultimately",
    "in today's world":             "today",
    "in today's fast-paced world":  "these days",
    "revolutionize":                "change",
    "game-changing":                "useful",
    "cutting-edge":                 "modern",
    "state-of-the-art":             "modern",
    "groundbreaking":               "new",
    "delve into":                   "explore",
    "take advantage of":            "use",
    "when it comes to":             "for",
}

HUMAN_INTROS = [
    "Here's the thing —",
    "Let me be honest:",
    "This trips up a lot of developers.",
    "Worth mentioning upfront:",
    "Quick heads up before we dive in:",
]

CONTRACTIONS = {
    "do not":     "don't",
    "does not":   "doesn't",
    "is not":     "isn't",
    "are not":    "aren't",
    "will not":   "won't",
    "cannot":     "can't",
    "could not":  "couldn't",
    "would not":  "wouldn't",
    "should not": "shouldn't",
    "it is":      "it's",
    "that is":    "that's",
    "there is":   "there's",
    "you are":    "you're",
    "we are":     "we're",
    "they are":   "they're",
}

def _sentence_split(text):
    return [s.strip() for s in re.split(r'[.!?]+', text) if len(s.strip()) > 10]

def detect_ai_score(text):
    sentences = _sentence_split(text)
    if len(sentences) < 3:
        return {"score": 0.0, "is_human": True}

    # Burstiness check
    lengths    = [len(s.split()) for s in sentences]
    mean_len   = sum(lengths) / len(lengths)
    variance   = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
    std_dev    = math.sqrt(variance)
    uniformity = max(0, 1 - (std_dev / (mean_len + 1))) * 100

    # Vocabulary ratio
    words   = re.findall(r'\b\w+\b', text.lower())
    vocab   = (1 - len(set(words)) / max(len(words), 1)) * 100

    # AI phrase count
    text_lower = text.lower()
    phrases    = min(sum(1 for p in AI_PHRASES if p in text_lower) * 10, 100)

    score = uniformity * 0.35 + vocab * 0.30 + phrases * 0.35

    return {
        "score":    round(score, 1),
        "is_human": score < 45,
    }

def _replace_phrases(text):
    for ai_phrase, human in AI_PHRASES.items():
        pattern = re.compile(re.escape(ai_phrase), re.IGNORECASE)
        text    = pattern.sub(human, text)
    return text

def _add_contractions(text):
    for formal, casual in CONTRACTIONS.items():
        def replace_sometimes(m):
            return casual if random.random() < 0.65 else m.group(0)
        text = re.sub(
            r'\b' + re.escape(formal) + r'\b',
            replace_sometimes, text, flags=re.IGNORECASE)
    return text

def _vary_sentences(text):
    lines  = text.split('\n')
    result = []
    for line in lines:
        if line.startswith(('#', '`', '-', '*', '|', '>')):
            result.append(line)
            continue
        words = line.split()
        if len(words) > 35:
            mid = len(words) // 2
            for i in range(mid - 4, mid + 4):
                if 0 < i < len(words):
                    if words[i].lower() in ('and','but','so','yet','or','while'):
                        line = (' '.join(words[:i]) + '. ' +
                                words[i].capitalize() + ' ' +
                                ' '.join(words[i+1:]))
                        break
        result.append(line)
    return '\n'.join(result)

def _inject_personality(text):
    paragraphs = text.split('\n\n')
    result     = []
    for i, para in enumerate(paragraphs):
        if (para.strip().startswith(('#','`','-','---','|')) or
                len(para.strip()) < 50):
            result.append(para)
            continue
        if i > 1 and random.random() < 0.15:
            intro = random.choice(HUMAN_INTROS)
            para  = intro + " " + para[0].lower() + para[1:]
        result.append(para)
    return '\n\n'.join(result)

def humanize(text, max_passes=3):
    """
    Always runs on every article.
    Keeps running until score < 45 or max_passes reached.
    """
    current = text

    for attempt in range(max_passes):
        # Always apply all transformations
        current = _replace_phrases(current)
        current = _vary_sentences(current)
        current = _add_contractions(current)

        if attempt == 0:
            current = _inject_personality(current)

        result = detect_ai_score(current)
        score  = result["score"]

        log.info("Humanizer pass %d: AI score = %.1f (is_human=%s)",
                 attempt + 1, score, result["is_human"])

        if result["is_human"]:
            log.info("✓ Passed human check! Score: %.1f", score)
            break
        else:
            log.info("Still AI-like (%.1f), running pass %d...",
                     score, attempt + 2)

    final = detect_ai_score(current)
    return {
        "text":     current,
        "score":    final["score"],
        "passes":   attempt + 1,
        "is_human": final["is_human"],
    }
