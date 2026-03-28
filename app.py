from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import requests
import time
from datetime import datetime, timedelta
import threading
import os

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

def fetch_wikipedia(topic):
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(topic)}"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            d = r.json()
            return {"source": "Wikipedia", "text": d.get("extract", ""), "url": d.get("content_urls", {}).get("desktop", {}).get("page", "")}
    except:
        pass
    return None

def fetch_simple_wikipedia(topic):
    try:
        url = f"https://simple.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(topic)}"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            d = r.json()
            return {"source": "Simple Wikipedia", "text": d.get("extract", ""), "url": d.get("content_urls", {}).get("desktop", {}).get("page", "")}
    except:
        pass
    return None

def fetch_wikiversity(topic):
    try:
        url = f"https://en.wikiversity.org/api/rest_v1/page/summary/{requests.utils.quote(topic)}"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            d = r.json()
            return {"source": "Wikiversity", "text": d.get("extract", ""), "url": d.get("content_urls", {}).get("desktop", {}).get("page", "")}
    except:
        pass
    return None

def fetch_wikibooks(topic):
    try:
        url = f"https://en.wikibooks.org/api/rest_v1/page/summary/{requests.utils.quote(topic)}"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            d = r.json()
            return {"source": "Wikibooks", "text": d.get("extract", ""), "url": d.get("content_urls", {}).get("desktop", {}).get("page", "")}
    except:
        pass
    return None

def fetch_wikiquote(topic):
    try:
        url = f"https://en.wikiquote.org/api/rest_v1/page/summary/{requests.utils.quote(topic)}"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            d = r.json()
            return {"source": "Wikiquote", "text": d.get("extract", ""), "url": d.get("content_urls", {}).get("desktop", {}).get("page", "")}
    except:
        pass
    return None

def fetch_wikinews(topic):
    try:
        url = f"https://en.wikinews.org/api/rest_v1/page/summary/{requests.utils.quote(topic)}"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            d = r.json()
            return {"source": "Wikinews", "text": d.get("extract", ""), "url": d.get("content_urls", {}).get("desktop", {}).get("page", "")}
    except:
        pass
    return None

def fetch_open_library(topic):
    try:
        url = f"https://openlibrary.org/search.json?q={requests.utils.quote(topic)}&limit=1"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            docs = r.json().get("docs", [])
            if docs:
                d = docs[0]
                text = f"{d.get('title', '')} by {', '.join(d.get('author_name', []))}"
                return {"source": "Open Library", "text": text, "url": f"https://openlibrary.org{d.get('key', '')}"}
    except:
        pass
    return None

def fetch_gutenberg(topic):
    try:
        url = f"https://gutendex.com/books/?search={requests.utils.quote(topic)}"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            results = r.json().get("results", [])
            if results:
                d = results[0]
                authors = ", ".join([a.get("name", "") for a in d.get("authors", [])])
                return {"source": "Project Gutenberg", "text": f"{d.get('title', '')} by {authors}", "url": f"https://www.gutenberg.org/ebooks/{d.get('id', '')}"}
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
                if meanings:
                    defs = meanings[0].get("definitions", [])
                    if defs:
                        return {"source": "Free Dictionary", "text": defs[0].get("definition", ""), "url": f"https://www.thefreedictionary.com/{word}"}
    except:
        pass
    return None

def fetch_pubmed(topic):
    try:
        api_key = os.environ.get("PUBMED_API_KEY", "")
        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={requests.utils.quote(topic)}&retmax=1&retmode=json&api_key={api_key}"
        r = requests.get(search_url, timeout=8)
        if r.status_code == 200:
            ids = r.json().get("esearchresult", {}).get("idlist", [])
            if ids:
                summary_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={ids[0]}&retmode=json&api_key={api_key}"
                r2 = requests.get(summary_url, timeout=8)
                if r2.status_code == 200:
                    result = r2.json().get("result", {}).get(ids[0], {})
                    return {"source": "PubMed", "text": result.get("title", ""), "url": f"https://pubmed.ncbi.nlm.nih.gov/{ids[0]}"}
    except:
        pass
    return None

def fetch_nasa(topic):
    try:
        api_key = os.environ.get("NASA_API_KEY", "DEMO_KEY")
        url = f"https://images-api.nasa.gov/search?q={requests.utils.quote(topic)}&media_type=image"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            items = r.json().get("collection", {}).get("items", [])
            if items:
                d = items[0].get("data", [{}])[0]
                return {"source": "NASA", "text": d.get("description", d.get("title", "")), "url": f"https://images.nasa.gov/"}
    except:
        pass
    return None

def build_response(topic, subject, results):
    combined_text = " ".join([r["text"] for r in results if r and r.get("text")])
    sources = [{"name": r["source"], "url": r.get("url", "")} for r in results if r]

    sentences = [s.strip() for s in combined_text.replace("!", ".").replace("?", ".").split(".") if len(s.strip()) > 40]

    summary = ". ".join(sentences[:3]) + "." if sentences else "No summary available."

    sections = []
    chunk_size = 5
    for i in range(0, min(len(sentences), 20), chunk_size):
        chunk = sentences[i:i+chunk_size]
        sections.append({
            "title": f"Section {i//chunk_size + 1}",
            "content": ". ".join(chunk) + "."
        })

    key_facts = sentences[3:8] if len(sentences) > 3 else sentences

    return {
        "topic": topic,
        "subject": subject,
        "summary": summary,
        "sections": sections,
        "keyFacts": key_facts,
        "sources": sources,
        "fullText": combined_text
    }

@app.route("/topic")
@limiter.limit("60 per minute")
def get_topic():
    topic = request.args.get("topic", "").strip()
    subject = request.args.get("subject", "").strip()

    if not topic:
        return jsonify({"error": "topic parameter required"}), 400

    cache_key = f"topic:{topic.lower()}:{subject.lower()}"
    cached = cache_get(cache_key)
    if cached:
        return jsonify(cached)

    fetchers = [
        fetch_wikiversity,
        fetch_simple_wikipedia,
        fetch_wikipedia,
        fetch_wikibooks,
        fetch_wikiquote,
        fetch_wikinews,
        fetch_open_library,
        fetch_gutenberg,
        fetch_free_dictionary,
        fetch_pubmed,
        fetch_nasa,
    ]

    results = []
    for fetcher in fetchers:
        result = fetcher(topic)
        if result and result.get("text"):
            results.append(result)

    if not results:
        return jsonify({"error": "No content found for this topic"}), 404

    response = build_response(topic, subject, results)
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
            urls = data[3] if len(data) > 3 else []
            for i, title in enumerate(titles):
                results.append({
                    "title": title,
                    "description": descriptions[i] if i < len(descriptions) else "",
                    "url": urls[i] if i < len(urls) else ""
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
        "sources": ["Wikiversity", "Simple Wikipedia", "Wikipedia", "Wikibooks", "Wikiquote", "Wikinews", "Open Library", "Project Gutenberg", "Free Dictionary", "PubMed", "NASA"],
        "cache_entries": len(_cache),
        "timestamp": datetime.utcnow().isoformat()
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
