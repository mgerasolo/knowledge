"""Build term dictionary from video metadata.

Extracts proper nouns, product names, people, and technical terms from
video descriptions, chapters, and hashtags. Generates definitions via LLM.

The dictionary serves as:
1. Transcript correction source (mishearing → correct term)
2. Entity extraction seed (known terms get priority)
3. RAG context (definitions help LLM understand content)
4. Segmentation guide (term boundaries suggest topic shifts)
"""
import json
import os
import re
import requests
import time
from collections import Counter
from typing import Optional

SURREAL_URL = os.getenv('SURREAL_URL', 'http://10.0.0.33:5040')
SURREAL_USER = os.getenv('SURREAL_USER', 'root')
SURREAL_PASS = os.getenv('SURREAL_PASS', 'changeme')
SURREAL_NS = os.getenv('SURREAL_NS', 'knowledge')
SURREAL_DB = os.getenv('SURREAL_DB', 'transcripts')
LITELLM_URL = os.getenv('LITELLM_URL', 'http://10.0.0.27:2764/v1')
LITELLM_API_KEY = os.getenv('LITELLM_API_KEY', 'sk-nlf-litellm-65cf74289dcc9be237bf6143')
DEFINE_MODEL = os.getenv('DEFINE_MODEL', 'openai/gpt-4o-mini')

# Common English words to skip
COMMON_WORDS = frozenset([
    'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had',
    'her', 'was', 'one', 'our', 'out', 'has', 'his', 'how', 'its', 'may',
    'new', 'now', 'old', 'see', 'way', 'who', 'did', 'get', 'let', 'say',
    'she', 'too', 'use', 'what', 'why', 'with', 'this', 'that', 'from',
    'they', 'been', 'have', 'many', 'some', 'them', 'than', 'each', 'make',
    'like', 'long', 'look', 'just', 'over', 'such', 'take', 'come', 'made',
    'find', 'here', 'know', 'more', 'also', 'about', 'after', 'would', 'could',
    'should', 'these', 'other', 'which', 'their', 'there', 'first', 'being',
    'those', 'still', 'where', 'every', 'right', 'think', 'going', 'really',
    'thing', 'things', 'people', 'great', 'through', 'video', 'check',
    'episode', 'podcast', 'subscribe', 'follow', 'link', 'below', 'click',
    'watch', 'listen', 'join', 'free', 'learn', 'today', 'show', 'talk',
    'best', 'full', 'part', 'time', 'year', 'week', 'life', 'world',
    'work', 'help', 'good', 'well', 'much', 'even', 'very', 'most', 'only',
    'will', 'your', 'into', 'back', 'then', 'when', 'want', 'give', 'need',
    'does', 'down', 'keep', 'last', 'same', 'tell', 'real', 'ever', 'sure',
    'book', 'latest', 'start', 'support', 'channel', 'content', 'share',
])


def surreal_query(query):
    try:
        resp = requests.post(f'{SURREAL_URL}/sql', auth=(SURREAL_USER, SURREAL_PASS),
            headers={'Accept': 'application/json', 'surreal-ns': SURREAL_NS, 'surreal-db': SURREAL_DB},
            data=query, timeout=30)
        return resp.json() if resp.ok else []
    except Exception as e:
        print(f'SurrealDB error: {e}')
        return []


def escape_surreal(text):
    if not text:
        return ""
    return text.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")


def slugify(name):
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s-]+', '_', slug)
    return slug.strip('_')[:100]


def extract_proper_nouns_from_text(text):
    """Extract likely proper nouns from text using capitalization and pattern matching."""
    if not text:
        return []

    terms = set()

    # Multi-word capitalized sequences (e.g., "Claude Code", "Andrew Huberman")
    multi_word = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', text)
    for t in multi_word:
        if t.lower() not in COMMON_WORDS and len(t) > 3:
            terms.add(t)

    # CamelCase / PascalCase terms (e.g., "ChatGPT", "OpenClaw", "SurrealDB")
    camel = re.findall(r'\b([A-Z][a-z]+[A-Z][a-zA-Z]*)\b', text)
    for t in camel:
        terms.add(t)

    # ALL CAPS abbreviations 2+ chars (e.g., "MCP", "RAG", "TDD", "API")
    abbrevs = re.findall(r'\b([A-Z]{2,6})\b', text)
    for t in abbrevs:
        if t not in ('THE', 'AND', 'FOR', 'BUT', 'NOT', 'YOU', 'ALL', 'URL', 'HTTP', 'HTTPS'):
            terms.add(t)

    # Terms with special chars likely to be tech products (e.g., "n8n", "yt-dlp", "gpt-4o")
    tech_terms = re.findall(r'\b([a-z]+[0-9]+[a-z]*|[a-z]+-[a-z]+(?:-[a-z]+)*)\b', text)
    for t in tech_terms:
        if len(t) > 2 and t.lower() not in COMMON_WORDS:
            terms.add(t)

    # Single capitalized words that aren't sentence starters (look for mid-sentence caps)
    # Find words preceded by lowercase or punctuation
    single_caps = re.findall(r'(?<=[a-z,.!?]\s)([A-Z][a-z]{2,})\b', text)
    for t in single_caps:
        if t.lower() not in COMMON_WORDS:
            terms.add(t)

    return list(terms)


def extract_terms_from_hashtags(hashtags):
    """Extract terms from hashtag list."""
    terms = set()
    for tag in hashtags:
        # Split CamelCase hashtags: #ClaudeCode -> Claude Code
        split = re.sub(r'([a-z])([A-Z])', r'\1 \2', tag)
        if split != tag:
            terms.add(split)
        terms.add(tag)
    return list(terms)


def extract_terms_from_chapters(chapters):
    """Extract proper nouns from chapter titles."""
    terms = set()
    for ch in chapters:
        title = ch.get('title', '')
        for t in extract_proper_nouns_from_text(title):
            terms.add(t)
    return list(terms)


def generate_definition(term, context_snippets, domain):
    """Generate a definition for a term using LLM with context from descriptions."""
    context = '\n'.join(context_snippets[:3])

    try:
        resp = requests.post(f'{LITELLM_URL}/chat/completions',
            headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {LITELLM_API_KEY}'},
            json={
                'model': DEFINE_MODEL,
                'messages': [
                    {'role': 'system', 'content': (
                        'You are a technical dictionary writer. Given a term and context from YouTube video descriptions, '
                        'write a concise 1-2 sentence definition. Include: what it is, who made it (if applicable), '
                        'and why it matters. If you cannot determine what the term means from context, say "Unknown term." '
                        'Return ONLY the definition text, nothing else.'
                    )},
                    {'role': 'user', 'content': f'Term: {term}\nDomain: {domain}\nContext:\n{context}'}
                ],
                'temperature': 0.1,
                'max_tokens': 200,
            }, timeout=20)

        if resp.ok:
            return resp.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f'  LLM definition error: {e}')
    return None


def build_dictionary(generate_definitions=True, min_occurrences=2, limit=None):
    """Scan all video metadata and build the term dictionary."""

    # Get all videos with descriptions
    results = surreal_query(
        "SELECT youtube_id, title, description, chapters, hashtags, domain, uploader "
        "FROM video WHERE description != NONE AND description != '';"
    )
    if not results or not results[0].get('result'):
        print('No videos with descriptions found. Run metadata_backfill.py first.')
        return

    videos = results[0]['result']
    if limit:
        videos = videos[:limit]
    print(f'Scanning {len(videos)} videos for terms...\n')

    # Collect terms with frequency and source context
    term_counter = Counter()
    term_contexts = {}  # term -> list of description snippets
    term_domains = {}   # term -> set of domains
    term_sources = {}   # term -> set of video IDs

    for v in videos:
        yt_id = v.get('youtube_id', '')
        desc = v.get('description', '') or ''
        chapters = v.get('chapters', []) or []
        hashtags = v.get('hashtags', []) or []
        domain = v.get('domain', 'general')
        uploader = v.get('uploader', '')
        title = v.get('title', '')

        # Extract from all sources
        desc_terms = extract_proper_nouns_from_text(desc)
        title_terms = extract_proper_nouns_from_text(title)
        chapter_terms = extract_terms_from_chapters(chapters)
        hashtag_terms = extract_terms_from_hashtags(hashtags)

        # Also add uploader as a person term
        all_terms = set(desc_terms + title_terms + chapter_terms + hashtag_terms)
        if uploader and len(uploader) > 2:
            all_terms.add(uploader)

        for term in all_terms:
            term_counter[term] += 1
            if term not in term_contexts:
                term_contexts[term] = []
                term_domains[term] = set()
                term_sources[term] = set()
            # Store a context snippet (first 200 chars of description)
            if desc and len(term_contexts[term]) < 5:
                term_contexts[term].append(f"[{title[:50]}] {desc[:200]}")
            term_domains[term].add(domain)
            term_sources[term].add(yt_id)

    # Filter to terms appearing in min_occurrences+ videos
    significant_terms = {t: c for t, c in term_counter.items() if c >= min_occurrences}
    print(f'Found {len(term_counter)} unique terms, {len(significant_terms)} appear {min_occurrences}+ times\n')

    # Create/update tags in SurrealDB
    created = 0
    updated = 0
    defined = 0

    for term, count in sorted(significant_terms.items(), key=lambda x: -x[1]):
        slug = slugify(term)
        if not slug or len(slug) < 2:
            continue

        domains = term_domains.get(term, set())
        primary_domain = max(domains, key=lambda d: sum(1 for v in term_sources[term])) if domains else 'general'

        # Classify type from patterns
        tag_type = 'concept'
        if re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+$', term):
            tag_type = 'person'  # Two capitalized words = likely a person name
        elif re.match(r'^[A-Z][a-z]+[A-Z]', term):
            tag_type = 'product'  # CamelCase = likely a product
        elif re.match(r'^[A-Z]{2,}$', term):
            tag_type = 'technology'  # ALL CAPS = abbreviation/technology

        safe_term = escape_surreal(term)
        safe_slug = escape_surreal(slug)

        # Check if tag exists
        existing = surreal_query(f"SELECT id, definition FROM tag WHERE slug = '{safe_slug}';")
        if existing and existing[0].get('result'):
            tag_id = str(existing[0]['result'][0]['id'])
            has_definition = bool(existing[0]['result'][0].get('definition'))
            surreal_query(
                f"UPDATE {tag_id} SET mention_count = {count}, "
                f"source_videos = {json.dumps(list(term_sources.get(term, []))[:10])};"
            )
            updated += 1

            # Generate definition if missing
            if generate_definitions and not has_definition:
                definition = generate_definition(term, term_contexts.get(term, []), primary_domain)
                if definition and 'Unknown term' not in definition:
                    surreal_query(
                        f"UPDATE {tag_id} SET definition = '{escape_surreal(definition)}';"
                    )
                    defined += 1
                    print(f'  DEF [{tag_type:10s}] {term}: {definition[:80]}')
                    time.sleep(0.3)
        else:
            # Create new tag
            surreal_query(
                f"CREATE tag SET name = '{safe_term}', slug = '{safe_slug}', "
                f"type = '{tag_type}', mention_count = {count}, "
                f"source_videos = {json.dumps(list(term_sources.get(term, []))[:10])};"
            )
            created += 1

            # Generate definition
            if generate_definitions:
                # Get the tag ID we just created
                tag_result = surreal_query(f"SELECT id FROM tag WHERE slug = '{safe_slug}';")
                if tag_result and tag_result[0].get('result'):
                    tag_id = str(tag_result[0]['result'][0]['id'])
                    definition = generate_definition(term, term_contexts.get(term, []), primary_domain)
                    if definition and 'Unknown term' not in definition:
                        surreal_query(
                            f"UPDATE {tag_id} SET definition = '{escape_surreal(definition)}';"
                        )
                        defined += 1
                        print(f'  NEW [{tag_type:10s}] {term}: {definition[:80]}')
                    else:
                        print(f'  NEW [{tag_type:10s}] {term} (no definition)')
                    time.sleep(0.3)

        if created + updated > 0 and (created + updated) % 50 == 0:
            print(f'  ... {created + updated} terms processed')

    print(f'\n=== Dictionary Build Complete ===')
    print(f'Created: {created}')
    print(f'Updated: {updated}')
    print(f'Defined: {defined}')
    print(f'Total significant terms: {len(significant_terms)}')


if __name__ == '__main__':
    import sys
    no_defs = '--no-definitions' in sys.argv
    limit = None
    for arg in sys.argv[1:]:
        if arg.isdigit():
            limit = int(arg)

    build_dictionary(
        generate_definitions=not no_defs,
        min_occurrences=2,
        limit=limit
    )
