from flask import Flask, jsonify, request
import requests
import re

app = Flask(__name__)

def clean_text(text):
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'==+\s*(.*?)\s*==+', r'\1:', text)
    text = re.sub(r'\{\{.*?\}\}', '', text)
    text = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

def fetch_wiki(base_url, topic):
    try:
        search_url = f"{base_url}?action=query&list=search&srsearch={requests.utils.quote(topic)}&format=json&origin=*"
        search_res = requests.get(search_url, timeout=10)
        search_data = search_res.json()
        page_title = search_data['query']['search'][0]['title']

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
    keywords = ['is', 'are', 'was', 'were', 'defined', 'refers', 'known', 'called', 'used', 'found']
    for sentence in sentences:
        if any(kw in sentence.lower() for kw in keywords) and 20 < len(sentence) < 150:
            facts.append(sentence.strip())
        if len(facts) >= 5:
            break
    return facts

def make_summary(text):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return ' '.join(sentences[:3]) if len(sentences) >= 3 else text[:300]

@app.route('/topic', methods=['GET'])
def get_topic():
    topic = request.args.get('topic', '')
    subject = request.args.get('subject', '')

    if not topic:
        return jsonify({'error': 'Topic is required'}), 400

    sources_used = []
    combined_text = ''

    wikiversity = fetch_wiki('https://en.wikiversity.org/w/api.php', topic)
    if wikiversity:
        combined_text += f"Lesson:\n{wikiversity}\n\n"
        sources_used.append('Wikiversity')

    simple_wiki = fetch_wiki('https://simple.wikipedia.org/w/api.php', topic)
    if simple_wiki:
        combined_text += f"Overview:\n{simple_wiki}\n\n"
        sources_used.append('Simple Wikipedia')

    wikipedia = fetch_wiki('https://en.wikipedia.org/w/api.php', topic)
    if wikipedia:
        combined_text += f"Detailed Reference:\n{wikipedia}\n\n"
        sources_used.append('Wikipedia')

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
        'sources': sources_used
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'app': 'PocketScholar API'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

**Then create another file** named `requirements.txt`:
```
flask
requests
gunicorn
