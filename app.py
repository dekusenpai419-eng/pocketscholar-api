from flask import Flask, jsonify, request
import requests
import re
import os

app = Flask(__name__)

PUBMED_API_KEY = os.environ.get('PUBMED_API_KEY', '')
NASA_API_KEY = os.environ.get('NASA_API_KEY', '')

WIKI_SOURCES = [
    ('https://en.wikiversity.org/w/api.php', 'Wikiversity'),
    ('https://simple.wikipedia.org/w/api.php', 'Simple Wikipedia'),
    ('https://en.wikipedia.org/w/api.php', 'Wikipedia'),
    ('https://en.wikibooks.org/w/api.php', 'Wikibooks'),
    ('https://en.wikiquote.org/w/api.php', 'Wikiquote'),
    ('https://en.wikinews.org/w/api.php', 'Wikinews'),
]

def clean_text(text):
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'==+\s*(.*?)\s*==+', r'\1:', text)
    text = re.sub(r'\{\{.*?\}\}', '', text)
    text = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\(.*?\)', '', text)
    text = re.sub(r'See also:.*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'References:.*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'External links:.*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Further reading:.*', '', text, flags=re.IGNORECASE)
    return text.strip()

def fetch_wiki(base_url, source_name, topic):
    try:
        search_url = f"{base_url}?action=query&list=search&srsearch={requests.utils.quote(topic)}&format=json&origin=*"
        search_res = requests.get(search_url, timeout=10)
        search_data = search_res.json()
        results = search_data.get('query', {}).get('search', [])
        if not results:
            return None
        page_title = results[0]['title']
        content_url = f"{base_url}?action=query&prop=extracts&explaintext=true&titles={requests.utils.quote(page_title)}&format=json&origin=*"
        content_res = requests.get(content_url, timeout=10)
        content_data = content_res.json()
        pages = content_data['query']['pages']
        page = pages[list(pages.keys())[0]]
        extract = page.get('extract', '')
        if extract and len(extract) > 200:
            return clean_text(extract)
        return None
    except:
        return None

def fetch_openlibrary(topic):
    try:
        search_url = f"https://openlibrary.org/search.json?q={requests.utils.quote(topic)}&fields=title,author_name,first_sentence&limit=3"
        res = requests.get(search_url, timeout=10)
        data = res.json()
        docs = data.get('docs', [])
        results = []
        for doc in docs:
            title = doc.get('title', '')
            authors = ', '.join(doc.get('author_name', [])[:2])
            sentence = doc.get('first_sentence', '')
            if isinstance(sentence, dict):
                sentence = sentence.get('value', '')
            if sentence:
                results.append(f"{title} by {authors}: {sentence}")
        if results:
            return clean_text('\n'.join(results))
        return None
    except:
        return None

def fetch_gutenberg(topic):
    try:
        search_url = f"https://gutendex.com/books/?search={requests.utils.quote(topic)}&languages=en"
        res = requests.get(search_url, timeout=10)
        data = res.json()
        books = data.get('results', [])[:3]
        results = []
        for book in books:
            title = book.get('title', '')
            authors = ', '.join([a.get('name', '') for a in book.get('authors', [])[:2]])
            subjects = ', '.join(book.get('subjects', [])[:3])
            if title:
                results.append(f"{title} by {authors}. Topics: {subjects}")
        if results:
            return clean_text('\n'.join(results))
        return None
    except:
        return None

def fetch_dictionary(topic):
    try:
        word = topic.split()[0]
        res = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}", timeout=10)
        data = res.json()
        if isinstance(data, list) and data:
            entry = data[0]
            definitions = []
            for meaning in entry.get('meanings', [])[:2]:
                pos = meaning.get('partOfSpeech', '')
                for defn in meaning.get('definitions', [])[:2]:
                    definitions.append(f"{pos}: {defn.get('definition', '')}")
            if definitions:
                return clean_text('\n'.join(definitions))
        return None
    except:
        return None

def fetch_pubmed(topic):
    try:
        if not PUBMED_API_KEY:
            return None
        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={requests.utils.quote(topic)}&retmax=3&retmode=json&api_key={PUBMED_API_KEY}"
        search_res = requests.get(search_url, timeout=10)
        search_data = search_res.json()
        ids = search_data.get('esearchresult', {}).get('idlist', [])
        if not ids:
            return None
        ids_str = ','.join(ids[:3])
        fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={ids_str}&rettype=abstract&retmode=text&api_key={PUBMED_API_KEY}"
        fetch_res = requests.get(fetch_url, timeout=10)
        text = fetch_res.text
        if text and len(text) > 100:
            return clean_text(text[:2000])
        return None
    except:
        return None

def fetch_nasa(topic):
    try:
        if not NASA_API_KEY:
            return None
        search_url = f"https://images-api.nasa.gov/search?q={requests.utils.quote(topic)}&media_type=image&page_size=3"
        res = requests.get(search_url, timeout=10)
        data = res.json()
        items = data.get('collection', {}).get('items', [])
        results = []
        for item in items[:3]:
            item_data = item.get('data', [{}])[0]
            title = item_data.get('title', '')
            description = item_data.get('description', '')
            date = item_data.get('date_created', '')[:10]
            if title and description:
                results.append(f"{title} ({date}): {description[:300]}")
        if results:
            return clean_text('\n'.join(results))
        return None
    except:
        return None

def extract_sections(text):
    sections = []
    current_heading = 'Overview'
    current_content = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.endswith(':') and len(line) < 60:
            if current_content:
                sections.append({
                    'heading': current_heading,
                    'content': ' '.join(current_content)
                })
            current_heading = line[:-1]
            current_content = []
        else:
            current_content.append(line)
    if current_content:
        sections.append({
            'heading': current_heading,
            'content': ' '.join(current_content)
        })
    return sections

def extract_key_facts(text):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    facts = []
    keywords = ['is', 'are', 'was', 'were', 'defined', 'refers', 'known', 'called', 'used', 'found', 'means', 'describes']
    for sentence in sentences:
        if any(kw in sentence.lower() for kw in keywords) and 20 < len(sentence) < 150:
            facts.append(sentence.strip())
        if len(facts) >= 8:
            break
    return facts

def make_summary(text):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return ' '.join(sentences[:4]) if len(sentences) >= 4 else text[:400]

@app.route('/topic', methods=['GET'])
def get_topic():
    topic = request.args.get('topic', '')
    subject = request.args.get('subject', '')
    if not topic:
        return jsonify({'error': 'Topic is required'}), 400

    sources_used = []
    combined_text = ''

    source_labels = {
        'Wikiversity': 'Lesson',
        'Simple Wikipedia': 'Overview',
        'Wikipedia': 'Detailed Reference',
        'Wikibooks': 'Textbook',
        'Wikiquote': 'Quotes',
        'Wikinews': 'News',
    }

    for base_url, source_name in WIKI_SOURCES:
        content = fetch_wiki(base_url, source_name, topic)
        if content:
            label = source_labels.get(source_name, source_name)
            combined_text += f"{label}:\n{content}\n\n"
            sources_used.append(source_name)

    ol_content = fetch_openlibrary(topic)
    if ol_content:
        combined_text += f"Books:\n{ol_content}\n\n"
        sources_used.append('Open Library')

    gutenberg_content = fetch_gutenberg(topic)
    if gutenberg_content:
        combined_text += f"Classic Literature:\n{gutenberg_content}\n\n"
        sources_used.append('Project Gutenberg')

    dict_content = fetch_dictionary(topic)
    if dict_content:
        combined_text += f"Definition:\n{dict_content}\n\n"
        sources_used.append('Dictionary')

    pubmed_content = fetch_pubmed(topic)
    if pubmed_content:
        combined_text += f"Scientific Research:\n{pubmed_content}\n\n"
        sources_used.append('PubMed')

    nasa_content = fetch_nasa(topic)
    if nasa_content:
        combined_text += f"NASA:\n{nasa_content}\n\n"
        sources_used.append('NASA')

    if not combined_text:
        return jsonify({'error': 'No content found for this topic'}), 404

    sections = extract_sections(combined_text)
    key_facts = extract_key_facts(combined_text)
    summary = make_summary(combined_text)

    return jsonify({
        'topic': topic,
        'subject': subject,
        'summary': summary,
        'sections': sections,
        'keyFacts': key_facts,
        'sources': sources_used,
        'fullText': combined_text
    })

@app.route('/search', methods=['GET'])
def search_topics():
    query = request.args.get('q', '')
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    try:
        res = requests.get(
            f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={requests.utils.quote(query)}&format=json&origin=*",
            timeout=10
        )
        data = res.json()
        results = data.get('query', {}).get('search', [])
        return jsonify({
            'query': query,
            'results': [{'title': r['title'], 'snippet': re.sub(r'<.*?>', '', r.get('snippet', ''))} for r in results[:8]]
        })
    except:
        return jsonify({'error': 'Search failed'}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'app': 'PocketScholar API',
        'sources': [s[1] for s in WIKI_SOURCES] + ['Open Library', 'Project Gutenberg', 'Dictionary', 'PubMed', 'NASA']
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
