"""Tag enrichment pipeline using kg-gen for entity/relationship extraction.

Uses kg-gen (NeurIPS 2025) to extract entities and relationships from
transcript segments, then stores them as SurrealDB graph edges.

Pipeline:
1. kg-gen extracts entities + relationships from each segment
2. Entities become tags in the tag table
3. Relationships become graph edges (child_of, related_to, etc.)
4. Segment tags link via tagged_segment relation
5. Video tags roll up from segment tags via tagged_video relation
"""
import json
import os
import re
import time
import requests
from typing import Optional

from kg_gen import KGGen
from entity_linker import validate_entity

# Config
LITELLM_URL = os.getenv('LITELLM_URL', 'http://10.0.0.27:2764/v1')
LITELLM_API_KEY = os.getenv('LITELLM_API_KEY', 'sk-nlf-litellm-65cf74289dcc9be237bf6143')
SURREAL_URL = os.getenv('SURREAL_URL', 'http://10.0.0.33:5040')
SURREAL_USER = os.getenv('SURREAL_USER', 'root')
SURREAL_PASS = os.getenv('SURREAL_PASS', 'changeme')
SURREAL_NS = os.getenv('SURREAL_NS', 'knowledge')
SURREAL_DB = os.getenv('SURREAL_DB', 'transcripts')
ENRICH_MODEL = os.getenv('ENRICH_MODEL', 'openai/gpt-4o-mini')

# Initialize kg-gen
_kg = None


def get_kggen() -> KGGen:
    """Lazy-init kg-gen instance."""
    global _kg
    if _kg is None:
        _kg = KGGen(
            model=ENRICH_MODEL,
            api_base=LITELLM_URL,
            api_key=LITELLM_API_KEY,
            temperature=0.0
        )
    return _kg


def surreal_query(query: str) -> list:
    """Execute a SurrealDB query."""
    headers = {
        'Accept': 'application/json',
        'surreal-ns': SURREAL_NS,
        'surreal-db': SURREAL_DB,
    }
    try:
        resp = requests.post(
            f'{SURREAL_URL}/sql',
            auth=(SURREAL_USER, SURREAL_PASS),
            headers=headers,
            data=query,
            timeout=30
        )
        if resp.ok:
            return resp.json()
        print(f'SurrealDB error: {resp.status_code} {resp.text[:200]}')
    except Exception as e:
        print(f'SurrealDB connection error: {e}')
    return []


def slugify(name: str) -> str:
    """Convert a tag name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s-]+', '_', slug)
    slug = slug.strip('_')
    return slug[:100]  # Cap length


def escape_surreal(text: str) -> str:
    """Escape string for SurrealDB queries."""
    if not text:
        return ""
    return text.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')


def get_or_create_tag(name: str, tag_type: str = 'concept') -> Optional[str]:
    """Get existing tag by slug or create new one. Returns tag record ID."""
    slug = slugify(name)
    if not slug or len(slug) < 2:
        return None

    safe_name = escape_surreal(name)
    safe_slug = escape_surreal(slug)

    # Try to find existing
    results = surreal_query(f"SELECT id FROM tag WHERE slug = '{safe_slug}';")
    if results and results[0].get('result'):
        tag_id = str(results[0]['result'][0]['id'])
        # Bump mention count
        surreal_query(f"UPDATE {tag_id} SET mention_count += 1;")
        return tag_id

    # Create new tag
    results = surreal_query(
        f"CREATE tag SET name = '{safe_name}', slug = '{safe_slug}', "
        f"type = '{tag_type}', mention_count = 1;"
    )
    if results and results[0].get('result'):
        tag_id = str(results[0]['result'][0]['id'])
        print(f'  + tag: {name} ({tag_type})')
        return tag_id

    return None


def create_relation(from_id: str, relation: str, to_id: str, props: dict = None):
    """Create a SurrealDB relation edge."""
    props_str = ""
    if props:
        parts = []
        for k, v in props.items():
            if isinstance(v, (int, float)):
                parts.append(f"{k} = {v}")
            else:
                parts.append(f"{k} = '{escape_surreal(str(v))}'")
        props_str = " SET " + ", ".join(parts)
    result = surreal_query(f"RELATE {from_id}->{relation}->{to_id}{props_str};")
    if not result or (result and result[0].get('status') != 'OK'):
        print(f'  ! relation failed: {from_id}->{relation}->{to_id}')


def classify_entity(name: str, relations: list) -> str:
    """Classify entity type based on name and relationships."""
    name_lower = name.lower()

    # Person indicators
    if any(title in name_lower for title in ['dr.', 'mr.', 'mrs.', 'prof.']):
        return 'person'

    # Check relations for type hints
    for subj, pred, obj in relations:
        pred_lower = pred.lower()
        if subj.lower() == name_lower or obj.lower() == name_lower:
            if 'is a type of' in pred_lower or 'is a' in pred_lower:
                return 'concept'
            if 'developed by' in pred_lower or 'created by' in pred_lower:
                return 'product'
            if 'triggers' in pred_lower or 'reduces' in pred_lower or 'improves' in pred_lower:
                if any(h in name_lower for h in ['health', 'fasting', 'diet', 'exercise',
                        'anxiety', 'inflammation', 'autophagy', 'metabolic']):
                    return 'health'

    # Keyword-based fallback
    health_terms = ['fasting', 'health', 'diet', 'exercise', 'anxiety', 'stress',
                    'inflammation', 'autophagy', 'metabolic', 'sleep', 'hormone',
                    'cortisol', 'insulin', 'keto', 'mental health', 'heart']
    if any(h in name_lower for h in health_terms):
        return 'health'

    tech_terms = ['api', 'sdk', 'framework', 'algorithm', 'model', 'database',
                  'server', 'docker', 'kubernetes', 'python', 'javascript']
    if any(t in name_lower for t in tech_terms):
        return 'technology'

    return 'concept'


def enrich_segment(segment_id: str) -> dict:
    """Enrich a single segment with kg-gen extracted tags and relations."""
    # Check if already enriched
    existing = surreal_query(
        f"SELECT count() as c FROM tagged_segment WHERE in = {segment_id} GROUP ALL;"
    )
    if existing and existing[0].get('result') and existing[0]['result'][0].get('c', 0) > 0:
        return {'tags': 0, 'relations': 0, 'skipped': True}

    # Get segment text and linked video info
    results = surreal_query(
        f"SELECT text, video_youtube_id FROM {segment_id};"
    )
    if results and results[0].get('result'):
        vid_yt_id = results[0]['result'][0].get('video_youtube_id', '')
        if vid_yt_id:
            vid_results = surreal_query(
                f"SELECT title, domain FROM video WHERE youtube_id = '{escape_surreal(vid_yt_id)}' LIMIT 1;"
            )
            if vid_results and vid_results[0].get('result'):
                results[0]['result'][0]['title'] = vid_results[0]['result'][0].get('title', '')
                results[0]['result'][0]['domain'] = vid_results[0]['result'][0].get('domain', '')
    if not results or not results[0].get('result'):
        return {'tags': 0, 'relations': 0, 'error': 'not found'}

    seg = results[0]['result'][0]
    text = seg.get('text', '')
    title = seg.get('title', '') or ''
    domain = seg.get('domain', '') or ''

    if not text or len(text) < 30:
        return {'tags': 0, 'relations': 0, 'skipped': True}

    # Extract with kg-gen
    kg = get_kggen()
    context = f"YouTube video transcript about {domain}" if domain else "YouTube video transcript"
    if title:
        context += f". Video title: {title}"

    try:
        graph = kg.generate(input_data=text, context=context)
    except Exception as e:
        print(f'  kg-gen error on {segment_id}: {e}')
        return {'tags': 0, 'relations': 0, 'error': str(e)}

    if not graph.entities:
        return {'tags': 0, 'relations': 0}

    # Validate and create tags, link to segment
    tag_count = 0
    tag_ids = {}  # entity_name -> tag_id

    for entity_name in graph.entities:
        entity_name = entity_name.strip()
        if len(entity_name) < 3 or len(entity_name) > 100:
            continue

        # Validate entity against Wikidata + noise filter
        validation = validate_entity(entity_name, text[:200])
        if not validation.get('valid'):
            continue

        # Use validated name and type
        canonical_name = validation['name']
        tag_type = validation['type']
        significance = validation.get('significance', 0.5)
        wikidata_id = validation.get('wikidata_id')

        tag_id = get_or_create_tag(canonical_name, tag_type)
        if tag_id:
            # Store Wikidata ID if we have one
            if wikidata_id:
                surreal_query(
                    f"UPDATE {tag_id} SET wikidata_id = '{wikidata_id}', "
                    f"description = '{escape_surreal(validation.get('description', '') or '')}'"
                    f";"
                )

            # Link segment to tag with significance score
            create_relation(segment_id, 'tagged_segment', tag_id,
                            {'confidence': significance, 'source': validation['source']})
            tag_ids[entity_name.lower()] = tag_id
            tag_count += 1

            # Auto-create hierarchy from Wikidata
            if validation.get('hierarchy'):
                parent_id = tag_id
                for h in validation['hierarchy'][:3]:  # Max 3 levels deep
                    hier_tag_id = get_or_create_tag(h['name'], 'concept')
                    if hier_tag_id and hier_tag_id != parent_id:
                        if h.get('wikidata_id'):
                            surreal_query(
                                f"UPDATE {hier_tag_id} SET wikidata_id = '{h['wikidata_id']}';"
                            )
                        create_relation(parent_id, 'child_of', hier_tag_id)
                        parent_id = hier_tag_id

    # Store relationships between tags
    rel_count = 0
    for subj, pred, obj in graph.relations:
        subj_id = tag_ids.get(subj.lower())
        obj_id = tag_ids.get(obj.lower())
        if subj_id and obj_id and subj_id != obj_id:
            # Map kg-gen predicates to our relation types
            pred_lower = pred.lower()
            if 'type of' in pred_lower or 'subset of' in pred_lower:
                create_relation(subj_id, 'child_of', obj_id)
            else:
                # Store as a generic related_to with the predicate as label
                surreal_query(
                    f"RELATE {subj_id}->related_to->{obj_id} "
                    f"SET predicate = '{escape_surreal(pred)}', source = 'kggen';"
                )
            rel_count += 1

    return {'tags': tag_count, 'relations': rel_count}


def rollup_video_tags(video_id: str) -> int:
    """Roll up segment tags to video level with counts."""
    # Get youtube_id for this video
    vid_results = surreal_query(f"SELECT youtube_id FROM {video_id};")
    if not vid_results or not vid_results[0].get('result'):
        return 0
    yt_id = vid_results[0]['result'][0].get('youtube_id', '')

    # Get segment IDs for this video
    seg_results = surreal_query(
        f"SELECT id FROM segment WHERE video_youtube_id = '{escape_surreal(yt_id)}';"
    )
    if not seg_results or not seg_results[0].get('result'):
        return 0
    seg_ids = [str(s['id']) for s in seg_results[0]['result']]
    seg_id_list = ', '.join(seg_ids)

    # Get all tags from those segments with counts
    results = surreal_query(f"""
        SELECT out, count() as seg_count
        FROM tagged_segment
        WHERE in IN [{seg_id_list}]
        GROUP BY out;
    """)

    if not results or not results[0].get('result'):
        return 0

    count = 0
    for row in results[0]['result']:
        tag_id = str(row['out'])
        seg_count = row.get('seg_count', 1)

        # Delete existing rollup for this video+tag
        surreal_query(
            f"DELETE tagged_video WHERE in = {video_id} AND out = {tag_id};"
        )
        # Create fresh rollup
        surreal_query(
            f"RELATE {video_id}->tagged_video->{tag_id} "
            f"SET source = 'rollup', segment_count = {seg_count};"
        )
        count += 1

    return count


def enrich_video(video_id: str) -> dict:
    """Enrich all segments of a video, then roll up to video level."""
    # Get youtube_id for this video to find its segments
    vid_results = surreal_query(f"SELECT youtube_id FROM {video_id};")
    if not vid_results or not vid_results[0].get('result'):
        return {'segments_processed': 0, 'segments_total': 0, 'tags': 0, 'relations': 0, 'video_tags': 0}
    yt_id = vid_results[0]['result'][0].get('youtube_id', '')
    results = surreal_query(
        f"SELECT id FROM segment WHERE video_youtube_id = '{escape_surreal(yt_id)}';"
    )
    if not results or not results[0].get('result'):
        return {'segments': 0, 'tags': 0, 'relations': 0, 'video_tags': 0}

    segments = results[0]['result']
    total_tags = 0
    total_rels = 0
    processed = 0

    for seg in segments:
        seg_id = str(seg['id'])
        result = enrich_segment(seg_id)

        if result.get('skipped'):
            continue

        total_tags += result.get('tags', 0)
        total_rels += result.get('relations', 0)
        processed += 1

        # Rate limit LLM calls
        if result.get('tags', 0) > 0:
            time.sleep(0.3)

    # Roll up to video
    video_tags = rollup_video_tags(video_id)

    return {
        'segments_processed': processed,
        'segments_total': len(segments),
        'tags': total_tags,
        'relations': total_rels,
        'video_tags': video_tags
    }


def enrich_all(limit: int = 10) -> dict:
    """Find unenriched videos and process them."""
    # Get videos that have segments
    results = surreal_query(f"""
        SELECT id, title, youtube_id FROM video LIMIT {limit};
    """)

    if not results or not results[0].get('result'):
        return {'videos_processed': 0, 'total_tags': 0}

    # Filter to videos that actually have segments
    all_videos = results[0]['result']
    videos = []
    for v in all_videos:
        yt_id = v.get('youtube_id', '')
        seg_check = surreal_query(
            f"SELECT count() as c FROM segment WHERE video_youtube_id = '{escape_surreal(yt_id)}' GROUP ALL;"
        )
        if seg_check and seg_check[0].get('result') and seg_check[0]['result'][0].get('c', 0) > 0:
            videos.append(v)
    total_tags = 0
    total_rels = 0
    processed = 0

    for v in videos:
        vid = str(v['id'])
        title = v.get('title', 'Unknown')

        print(f'\n{"="*60}')
        print(f'Enriching: {title}')
        print(f'{"="*60}')

        result = enrich_video(vid)
        total_tags += result['tags']
        total_rels += result['relations']
        processed += 1

        print(f'  -> {result["tags"]} tags, {result["relations"]} relations, '
              f'{result["video_tags"]} rolled up to video')

    return {
        'videos_processed': processed,
        'total_tags': total_tags,
        'total_relations': total_rels
    }


if __name__ == '__main__':
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    print(f'Enriching up to {limit} videos...')
    print(f'Model: {ENRICH_MODEL}')
    print(f'LiteLLM: {LITELLM_URL}')
    print(f'SurrealDB: {SURREAL_URL}')
    result = enrich_all(limit=limit)
    print(f'\n{"="*60}')
    print(f'DONE: {result["videos_processed"]} videos, '
          f'{result["total_tags"]} tags, {result["total_relations"]} relations')
