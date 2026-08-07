"""Entity validation and classification via spaCy-entity-linker + Wikidata.

Takes raw entities from kg-gen and:
1. Validates them against Wikidata (are they real/notable?)
2. Classifies them (product, company, person, technology, health, concept)
3. Extracts hierarchy (parent-child chains from Wikidata)
4. Scores significance (Wikidata-matched = high, domain-specific = medium, generic = low/skip)
"""
import spacy
from typing import Optional

# Lazy-loaded spaCy pipeline
_nlp = None

# Common noise words to always skip
NOISE_WORDS = frozenset([
    'he', 'she', 'they', 'we', 'you', 'it', 'this', 'that', 'them',
    'his', 'her', 'its', 'our', 'your', 'their',
    'thing', 'things', 'stuff', 'way', 'ways', 'part', 'parts',
    'time', 'times', 'day', 'days', 'year', 'years',
    'people', 'person', 'someone', 'something', 'everyone', 'everything',
    'video', 'videos', 'channel', 'content', 'watching', 'thank you',
    'next one', 'one', 'two', 'three', 'first', 'second', 'third',
    'lot', 'lots', 'bit', 'kind', 'type', 'types',
    'example', 'examples', 'question', 'questions', 'answer', 'answers',
    'point', 'points', 'problem', 'problems', 'issue', 'issues',
    'information', 'data', 'result', 'results',
    'feature', 'features', 'option', 'options', 'setting', 'settings',
    'step', 'steps', 'process', 'approach', 'method',
    'beginning', 'end', 'start', 'middle',
    'case', 'cases', 'situation', 'fact', 'idea', 'ideas',
    'best practices', 'systematic process', 'phase two', 'phase one',
])


def get_nlp():
    """Lazy-load spaCy pipeline with entity linker."""
    global _nlp
    if _nlp is None:
        _nlp = spacy.load('en_core_web_md')
        _nlp.add_pipe('entityLinker', last=True)
    return _nlp


# Wikidata type mapping: Wikidata super-entity labels -> our tag types
WIKIDATA_TYPE_MAP = {
    # Companies/Organizations
    'enterprise': 'company', 'business': 'company', 'company': 'company',
    'corporation': 'company', 'organization': 'company', 'nonprofit': 'company',
    'technology company': 'company', 'startup': 'company',
    # People
    'human': 'person', 'person': 'person',
    # Technology/Software
    'software': 'product', 'application': 'product', 'mobile app': 'product',
    'programming language': 'technology', 'framework': 'technology',
    'operating system': 'product', 'web browser': 'product',
    'free software': 'product', 'open-source software': 'product',
    'free and open-source software': 'product',
    'virtualization': 'technology', 'database': 'technology',
    'algorithm': 'technology', 'protocol': 'technology',
    'machine learning': 'technology', 'artificial intelligence': 'technology',
    # Health
    'diet': 'health', 'disease': 'health', 'symptom': 'health',
    'biological process': 'health', 'medical procedure': 'health',
    'medication': 'health', 'drug': 'health', 'therapy': 'health',
    'exercise': 'health', 'nutrient': 'health',
    # Academic
    'university': 'concept', 'research': 'concept',
    # Places
    'city': 'concept', 'country': 'concept', 'state': 'concept',
}


def classify_from_wikidata(super_entities: list) -> Optional[str]:
    """Classify entity type from Wikidata super-entity chain."""
    for se in super_entities:
        label = se.get_label().lower()
        if label in WIKIDATA_TYPE_MAP:
            return WIKIDATA_TYPE_MAP[label]
        # Partial matching for compound types
        for key, tag_type in WIKIDATA_TYPE_MAP.items():
            if key in label:
                return tag_type
    return None


def validate_entity(name: str, context_text: str = '') -> dict:
    """Validate a single entity name against Wikidata.

    Returns:
        {
            'valid': bool,          # Should this be kept as a tag?
            'name': str,            # Canonical name (may be corrected)
            'type': str,            # product, company, person, technology, health, concept
            'wikidata_id': str,     # Wikidata Q-number if matched
            'description': str,     # Wikidata description
            'hierarchy': list,      # Parent chain from Wikidata
            'significance': float,  # 0.0-1.0 score
            'source': str,          # 'wikidata', 'ner', 'domain'
        }
    """
    name_lower = name.lower().strip()

    # Skip noise words
    if name_lower in NOISE_WORDS or len(name) < 3:
        return {'valid': False, 'name': name, 'reason': 'noise'}

    # Skip pure numbers
    if name.replace(',', '').replace('.', '').replace(' ', '').isdigit():
        return {'valid': False, 'name': name, 'reason': 'number'}

    nlp = get_nlp()

    # Run through spaCy to get NER + entity linking
    # Use entity name in a simple sentence for better linking
    probe_text = f"{name} is notable."
    if context_text:
        probe_text = f"{name}. {context_text[:200]}"

    doc = nlp(probe_text)

    # Check if entity linker found a Wikidata match
    linked = doc._.linkedEntities
    if linked and len(linked) > 0:
        # Find the best match for our entity name
        best_match = None
        for le in linked:
            span_text = le.get_span().text.lower()
            # Match if the linked span overlaps with our entity name
            if span_text in name_lower or name_lower in span_text:
                best_match = le
                break

        if not best_match and len(linked) > 0:
            # Take first match as fallback
            best_match = linked[0]

        if best_match:
            wikidata_id = f"Q{best_match.get_id()}"
            canonical_name = best_match.get_label()
            description = best_match.get_description()
            supers = best_match.get_super_entities(limit=10)

            # Check if Wikidata matched the WRONG entity (disambiguation failure)
            # If canonical name is very different from input, it's probably wrong
            if (canonical_name.lower() not in name_lower and
                    name_lower not in canonical_name.lower() and
                    len(set(name_lower.split()) & set(canonical_name.lower().split())) == 0):
                # Complete mismatch — treat as domain entity instead
                return {
                    'valid': True,
                    'name': name,
                    'type': 'concept',
                    'wikidata_id': None,
                    'description': None,
                    'hierarchy': [],
                    'significance': 0.4,
                    'source': 'domain'
                }

            # Classify from Wikidata hierarchy
            tag_type = classify_from_wikidata(supers) or 'concept'

            # Check domain relevance — skip generic objects/places/everyday items
            IRRELEVANT_CATEGORIES = frozenset([
                'room', 'building', 'furniture', 'clothing', 'food',
                'vehicle', 'animal', 'plant', 'color', 'shape',
                'body part', 'kinship', 'family', 'affinity',
                'geographic region', 'landform', 'body of water',
                'fictional character', 'mythological character',
                'musical group', 'album', 'song', 'film', 'television series',
            ])
            super_labels = {se.get_label().lower() for se in supers}
            if super_labels & IRRELEVANT_CATEGORIES and tag_type == 'concept':
                return {'valid': False, 'name': name, 'reason': 'irrelevant_category'}

            # Build hierarchy chain
            hierarchy = []
            for s in supers[:5]:
                hierarchy.append({
                    'name': s.get_label(),
                    'wikidata_id': f"Q{s.get_id()}"
                })

            return {
                'valid': True,
                'name': canonical_name if len(canonical_name) > 2 else name,
                'type': tag_type,
                'wikidata_id': wikidata_id,
                'description': description,
                'hierarchy': hierarchy,
                'significance': 0.9,
                'source': 'wikidata'
            }

    # No Wikidata match — check spaCy NER
    for ent in doc.ents:
        if ent.text.lower() in name_lower or name_lower in ent.text.lower():
            ner_type_map = {
                'PERSON': 'person', 'ORG': 'company', 'GPE': 'concept',
                'PRODUCT': 'product', 'WORK_OF_ART': 'concept',
                'LAW': 'concept', 'LANGUAGE': 'technology',
                'NORP': 'concept', 'FAC': 'concept',
            }
            tag_type = ner_type_map.get(ent.label_, 'concept')
            return {
                'valid': True,
                'name': name,
                'type': tag_type,
                'wikidata_id': None,
                'description': None,
                'hierarchy': [],
                'significance': 0.6,
                'source': 'ner'
            }

    # Not in Wikidata, not in NER — might be a domain-specific term
    # Check if it looks like a proper noun (capitalized) or technical term
    words = name.split()
    is_proper = any(w[0].isupper() for w in words if w)
    is_technical = any(c in name for c in ['-', '_', '.']) or len(words) >= 2

    if is_proper or is_technical:
        return {
            'valid': True,
            'name': name,
            'type': 'concept',
            'wikidata_id': None,
            'description': None,
            'hierarchy': [],
            'significance': 0.4,
            'source': 'domain'
        }

    # Generic common word — skip
    return {'valid': False, 'name': name, 'reason': 'generic'}


def validate_entities(entities: list, context_text: str = '') -> list:
    """Validate a batch of entity names. Returns only valid ones with metadata."""
    results = []
    for name in entities:
        result = validate_entity(name, context_text)
        if result.get('valid'):
            results.append(result)
    return results


if __name__ == '__main__':
    # Test with sample entities
    test_entities = [
        'Claude Code', 'Anthropic', 'Docker', 'Kubernetes',
        'intermittent fasting', 'autophagy', 'Andrew Huberman',
        'TDD', 'bathroom', 'wife', 'he', 'features', 'next one',
        'MCP servers', 'vibe coding', 'RAG', 'Stanford',
    ]

    print("Validating entities against Wikidata...\n")
    for name in test_entities:
        result = validate_entity(name)
        if result.get('valid'):
            print(f"  KEEP [{result['type']:12s}] {result['name']:25s} "
                  f"(sig={result['significance']:.1f}, src={result['source']}"
                  f"{', wd=' + result['wikidata_id'] if result.get('wikidata_id') else ''})")
            if result.get('hierarchy'):
                chain = ' -> '.join(h['name'] for h in result['hierarchy'][:3])
                print(f"       hierarchy: {chain}")
        else:
            print(f"  SKIP {name:30s} ({result.get('reason', '?')})")
