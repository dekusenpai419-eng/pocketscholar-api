from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import requests
import re
import threading
import os
from datetime import datetime, timedelta

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["60 per minute"],
    storage_uri="memory://"
)

_cache = {}
_cache_lock = threading.Lock()
CACHE_TTL_HOURS = 24

def cache_get(key):
    with _cache_lock:
        entry = _cache.get(key)
        if entry and datetime.utcnow() < entry["expires"]:
            return entry["data"]
        if entry:
            del _cache[key]
        return None

def cache_set(key, data):
    with _cache_lock:
        _cache[key] = {
            "data": data,
            "expires": datetime.utcnow() + timedelta(hours=CACHE_TTL_HOURS)
        }

# ─── FETCHERS ────────────────────────────────────────────────────────────────

def fetch_wikipedia(topic):
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(topic)}"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            d = r.json()
            text = d.get("extract", "")
            if text:
                return {"source": "Wikipedia", "text": text, "url": d.get("content_urls", {}).get("desktop", {}).get("page", "")}
    except:
        pass
    return None

def fetch_wikipedia_full(topic):
    try:
        url = f"https://en.wikipedia.org/w/api.php?action=query&titles={requests.utils.quote(topic)}&prop=extracts&exintro=false&explaintext=true&format=json"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            pages = r.json().get("query", {}).get("pages", {})
            for page in pages.values():
                extract = page.get("extract", "")
                if extract and len(extract) > 200:
                    return {"source": "Wikipedia Full", "text": extract[:6000], "url": f"https://en.wikipedia.org/wiki/{requests.utils.quote(topic)}"}
    except:
        pass
    return None

def fetch_simple_wikipedia(topic):
    try:
        url = f"https://simple.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(topic)}"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            d = r.json()
            text = d.get("extract", "")
            if text:
                return {"source": "Simple Wikipedia", "text": text, "url": d.get("content_urls", {}).get("desktop", {}).get("page", "")}
    except:
        pass
    return None

def fetch_wikiversity(topic):
    try:
        url = f"https://en.wikiversity.org/api/rest_v1/page/summary/{requests.utils.quote(topic)}"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            d = r.json()
            text = d.get("extract", "")
            if text:
                return {"source": "Wikiversity", "text": text, "url": d.get("content_urls", {}).get("desktop", {}).get("page", "")}
    except:
        pass
    return None

def fetch_wikibooks(topic):
    try:
        url = f"https://en.wikibooks.org/api/rest_v1/page/summary/{requests.utils.quote(topic)}"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            d = r.json()
            text = d.get("extract", "")
            if text:
                return {"source": "Wikibooks", "text": text, "url": d.get("content_urls", {}).get("desktop", {}).get("page", "")}
    except:
        pass
    return None

def fetch_wikiquote(topic):
    try:
        url = f"https://en.wikiquote.org/api/rest_v1/page/summary/{requests.utils.quote(topic)}"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            d = r.json()
            text = d.get("extract", "")
            if text:
                return {"source": "Wikiquote", "text": text, "url": d.get("content_urls", {}).get("desktop", {}).get("page", "")}
    except:
        pass
    return None

def fetch_wikinews(topic):
    try:
        url = f"https://en.wikinews.org/api/rest_v1/page/summary/{requests.utils.quote(topic)}"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            d = r.json()
            text = d.get("extract", "")
            if text:
                return {"source": "Wikinews", "text": text, "url": d.get("content_urls", {}).get("desktop", {}).get("page", "")}
    except:
        pass
    return None

def fetch_open_library(topic):
    try:
        url = f"https://openlibrary.org/search.json?q={requests.utils.quote(topic)}&limit=3"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            docs = r.json().get("docs", [])
            texts = []
            for d in docs[:3]:
                title = d.get("title", "")
                authors = ", ".join(d.get("author_name", [])[:2])
                first_sentence = d.get("first_sentence", {})
                sentence = first_sentence.get("value", "") if isinstance(first_sentence, dict) else str(first_sentence) if first_sentence else ""
                if title:
                    entry = f"{title} by {authors}." if authors else title
                    if sentence:
                        entry += f" {sentence}"
                    texts.append(entry)
            if texts:
                return {"source": "Open Library", "text": " ".join(texts), "url": f"https://openlibrary.org/search?q={requests.utils.quote(topic)}"}
    except:
        pass
    return None

def fetch_gutenberg(topic):
    try:
        url = f"https://gutendex.com/books/?search={requests.utils.quote(topic)}"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            results = r.json().get("results", [])
            texts = []
            for d in results[:3]:
                authors = ", ".join([a.get("name", "") for a in d.get("authors", [])])
                title = d.get("title", "")
                subjects = ", ".join(d.get("subjects", [])[:3])
                if title:
                    entry = f"{title} by {authors}." if authors else title
                    if subjects:
                        entry += f" Subjects: {subjects}."
                    texts.append(entry)
            if texts:
                return {"source": "Project Gutenberg", "text": " ".join(texts), "url": f"https://www.gutenberg.org/ebooks/search/?query={requests.utils.quote(topic)}"}
    except:
        pass
    return None

def fetch_free_dictionary(topic):
    try:
        word = topic.split()[0]
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{requests.utils.quote(word)}"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            data = r.json()
            if data and isinstance(data, list):
                meanings = data[0].get("meanings", [])
                all_defs = []
                for meaning in meanings[:3]:
                    part = meaning.get("partOfSpeech", "")
                    for d in meaning.get("definitions", [])[:2]:
                        definition = d.get("definition", "")
                        example = d.get("example", "")
                        synonyms = ", ".join(d.get("synonyms", [])[:3])
                        text = f"({part}) {definition}"
                        if example:
                            text += f" Example: {example}"
                        if synonyms:
                            text += f" Synonyms: {synonyms}."
                        all_defs.append(text)
                if all_defs:
                    return {"source": "Free Dictionary", "text": " ".join(all_defs), "url": f"https://www.thefreedictionary.com/{word}"}
    except:
        pass
    return None

def fetch_pubmed(topic):
    try:
        api_key = os.environ.get("PUBMED_API_KEY", "")
        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={requests.utils.quote(topic)}&retmax=5&retmode=json&api_key={api_key}"
        r = requests.get(search_url, timeout=8)
        if r.status_code == 200:
            ids = r.json().get("esearchresult", {}).get("idlist", [])
            if ids:
                summary_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={','.join(ids)}&retmode=json&api_key={api_key}"
                r2 = requests.get(summary_url, timeout=8)
                if r2.status_code == 200:
                    result_data = r2.json().get("result", {})
                    texts = []
                    for pmid in ids:
                        result = result_data.get(pmid, {})
                        title = result.get("title", "")
                        source = result.get("source", "")
                        pubdate = result.get("pubdate", "")
                        if title:
                            entry = title
                            if source:
                                entry += f" ({source}"
                                if pubdate:
                                    entry += f", {pubdate}"
                                entry += ")"
                            texts.append(entry)
                    if texts:
                        return {"source": "PubMed", "text": " ".join(texts), "url": f"https://pubmed.ncbi.nlm.nih.gov/?term={requests.utils.quote(topic)}"}
    except:
        pass
    return None

def fetch_nasa(topic):
    try:
        url = f"https://images-api.nasa.gov/search?q={requests.utils.quote(topic)}&media_type=image"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            items = r.json().get("collection", {}).get("items", [])
            texts = []
            for item in items[:3]:
                d = item.get("data", [{}])[0]
                description = d.get("description", "")
                title = d.get("title", "")
                if description and len(description) > 30:
                    texts.append(description[:400])
                elif title:
                    texts.append(title)
            if texts:
                return {"source": "NASA", "text": " ".join(texts), "url": "https://images.nasa.gov/"}
    except:
        pass
    return None

# ─── TEXT PROCESSING ─────────────────────────────────────────────────────────

def split_sentences(text):
    text = re.sub(r'\s+', ' ', text).strip()
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    return [s.strip() for s in sentences if len(s.strip()) > 30]

def extract_key_facts(sentences, topic):
    fact_patterns = [
        r'\bis\b', r'\bare\b', r'\bwas\b', r'\bwere\b',
        r'\bdefined as\b', r'\brefers to\b', r'\bconsists of\b',
        r'\bcontains\b', r'\bproduces\b', r'\bcauses\b',
        r'\bresults in\b', r'\boccurs when\b', r'\bfound in\b',
        r'\bknown as\b', r'\bcalled\b', r'\bequals\b',
        r'\binvolves\b', r'\brequires\b', r'\bconverts\b',
        r'\d+', r'%', r'°C', r'°F', r'km', r'mg', r'mol'
    ]
    scored = []
    for sentence in sentences:
        score = 0
        lower = sentence.lower()
        for pattern in fact_patterns:
            if re.search(pattern, lower):
                score += 1
        if topic.lower() in lower:
            score += 2
        if len(sentence) > 60 and len(sentence) < 300:
            score += 1
        scored.append((score, sentence))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [s[1] for s in scored if s[0] > 0]

def build_free_sections(sentences, topic, subject):
    """3 sections for free users — introduction, core concept, subject link."""
    if not sentences:
        return []

    sections = []

    intro = sentences[:4]
    if intro:
        sections.append({
            "heading": f"What is {topic}?",
            "content": " ".join(intro)
        })

    core = sentences[4:9]
    if core:
        sections.append({
            "heading": "Key concepts",
            "content": " ".join(core)
        })

    link = sentences[9:13]
    if link:
        sections.append({
            "heading": f"{topic} in {subject}",
            "content": " ".join(link)
        })

    return sections

def build_premium_sections(sentences, topic, subject):
    """7 rich educational sections for premium users."""
    if not sentences:
        return []

    section_configs = [
        {"heading": f"What is {topic}?", "slice": (0, 4)},
        {"heading": "How it works", "slice": (4, 9)},
        {"heading": f"{topic} in {subject}", "slice": (9, 14)},
        {"heading": "Important details and mechanisms", "slice": (14, 19)},
        {"heading": "Real-world applications and examples", "slice": (19, 24)},
        {"heading": "Common misconceptions", "slice": (24, 28)},
        {"heading": "CSEC exam focus — what to know", "slice": (28, 33)},
    ]

    sections = []
    for config in section_configs:
        start, end = config["slice"]
        chunk = sentences[start:end]
        if chunk:
            content = " ".join(chunk)
            if len(content) > 40:
                sections.append({
                    "heading": config["heading"],
                    "content": content
                })

    return sections

# ─── RESPONSE BUILDER ────────────────────────────────────────────────────────

def build_response(topic, subject, results, depth="standard"):
    source_priority = [
        "Wikiversity", "Wikibooks", "Wikipedia Full",
        "Simple Wikipedia", "Wikipedia", "Free Dictionary",
        "PubMed", "NASA", "Open Library", "Project Gutenberg",
        "Wikiquote", "Wikinews"
    ]

    result_map = {}
    for r in results:
        if r and r.get("text"):
            result_map[r["source"]] = r

    all_texts = []
    for source_name in source_priority:
        if source_name in result_map:
            text = result_map[source_name]["text"].strip()
            if text and len(text) > 50:
                all_texts.append(text)

    for r in results:
        if r and r.get("text") and r["source"] not in source_priority:
            all_texts.append(r["text"].strip())

    combined_text = " ".join(all_texts)
    combined_text = re.sub(r'\s+', ' ', combined_text).strip()

    sources = [{"name": r["source"], "url": r.get("url", "")} for r in results if r]
    sentences = split_sentences(combined_text)

    if not sentences:
        return {
            "topic": topic,
            "subject": subject,
            "summary": f"{topic} is a topic in {subject}.",
            "sections": [],
            "keyFacts": [],
            "sources": sources,
            "fullText": combined_text,
            "tier": depth
        }

    summary = " ".join(sentences[:3])
    all_facts = extract_key_facts(sentences, topic)

    if depth == "extended":
        # Premium — rich content
        sections = build_premium_sections(sentences, topic, subject)
        key_facts = all_facts[:8]

        csec_tip = f"For CSEC {subject}, make sure you can define {topic}, explain its process or function, give a real-world example, and answer both structured and essay questions on it."
        key_facts.append(csec_tip)

        full_text = combined_text[:8000] if len(combined_text) > 8000 else combined_text
        premium_summary = " ".join(sentences[:5])

        return {
            "topic": topic,
            "subject": subject,
            "summary": premium_summary,
            "sections": sections,
            "keyFacts": key_facts[:9],
            "sources": sources,
            "fullText": full_text,
            "tier": "premium"
        }
    else:
        # Free — shorter content
        sections = build_free_sections(sentences, topic, subject)
        key_facts = all_facts[:4]

        full_text = combined_text[:2500] if len(combined_text) > 2500 else combined_text

        return {
            "topic": topic,
            "subject": subject,
            "summary": summary,
            "sections": sections,
            "keyFacts": key_facts,
            "sources": sources,
            "fullText": full_text,
            "tier": "free"
        }

# ─── ROUTES ──────────────────────────────────────────────────────────────────

@app.route("/topic")
@limiter.limit("60 per minute")
def get_topic():
    topic = request.args.get("topic", "").strip()
    subject = request.args.get("subject", "").strip()
    depth = request.args.get("depth", "standard").strip()

    if not topic:
        return jsonify({"error": "topic parameter required"}), 400

    cache_key = f"topic:{topic.lower()}:{subject.lower()}:{depth}"
    cached = cache_get(cache_key)
    if cached:
        return jsonify(cached)

    fetchers = [
        lambda: fetch_wikiversity(topic),
        lambda: fetch_wikibooks(topic),
        lambda: fetch_wikipedia_full(topic),
        lambda: fetch_simple_wikipedia(topic),
        lambda: fetch_wikipedia(topic),
        lambda: fetch_wikiquote(topic),
        lambda: fetch_wikinews(topic),
        lambda: fetch_open_library(topic),
        lambda: fetch_gutenberg(topic),
        lambda: fetch_free_dictionary(topic),
        lambda: fetch_pubmed(topic),
        lambda: fetch_nasa(topic),
    ]

    results = []
    threads = []
    lock = threading.Lock()

    def run_fetcher(fetcher):
        result = fetcher()
        if result and result.get("text") and len(result["text"]) > 30:
            with lock:
                results.append(result)

    for fetcher in fetchers:
        t = threading.Thread(target=run_fetcher, args=(fetcher,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=10)

    if not results:
        return jsonify({"error": "No content found for this topic"}), 404

    response = build_response(topic, subject, results, depth=depth)
    cache_set(cache_key, response)
    return jsonify(response)

@app.route("/search")
@limiter.limit("60 per minute")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "q parameter required"}), 400

    cache_key = f"search:{query.lower()}"
    cached = cache_get(cache_key)
    if cached:
        return jsonify(cached)

    try:
        url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={requests.utils.quote(query)}&limit=5&format=json"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            data = r.json()
            results = []
            titles = data[1] if len(data) > 1 else []
            descriptions = data[2] if len(data) > 2 else []
            urls_list = data[3] if len(data) > 3 else []
            for i, title in enumerate(titles):
                results.append({
                    "title": title,
                    "description": descriptions[i] if i < len(descriptions) else "",
                    "url": urls_list[i] if i < len(urls_list) else ""
                })
            cache_set(cache_key, {"results": results})
            return jsonify({"results": results})
    except:
        pass

    return jsonify({"results": []})

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "version": "3.0",
        "tiers": ["free (standard)", "premium (extended)"],
        "sources": [
            "Wikiversity", "Wikibooks", "Wikipedia Full", "Simple Wikipedia",
            "Wikipedia", "Wikiquote", "Wikinews", "Open Library",
            "Project Gutenberg", "Free Dictionary", "PubMed", "NASA"
        ],
        "cache_entries": len(_cache),
        "timestamp": datetime.utcnow().isoformat()
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
