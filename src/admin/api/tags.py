"""Tag browsing and management API endpoints."""
import re

import requests
from flask import Blueprint, jsonify, request
from config import Config

tags_bp = Blueprint('tags', __name__)

SURREAL_URL = Config.SURREAL_URL
SURREAL_NS = Config.SURREAL_NS
SURREAL_DB = Config.SURREAL_DB
SURREAL_AUTH = (Config.SURREAL_USER, Config.SURREAL_PASS)


class SurrealError(RuntimeError):
    """A SurrealDB statement was rejected, or the server was unreachable."""


def q(text: str) -> str:
    """Escape user input for a single-quoted SurrealQL literal."""
    if not text:
        return ""
    out = text.replace("\\", "\\\\").replace("'", "\\'")
    return "".join(c for c in out if ord(c) >= 32)


def surreal_query(query: str):
    """Execute a SurrealDB query, returning the raw statement payload.

    Raises SurrealError when a statement is rejected. Previously this returned
    the payload regardless, and on failure SurrealDB puts an error STRING where
    the rows belong — so `results[0]['result']` handed callers that string,
    which they serialised into a 200 response. Consumers checking only the
    status code could not tell a failure from real data.
    """
    try:
        response = requests.post(
            f"{SURREAL_URL}/sql",
            headers={
                "Content-Type": "text/plain",
                "Accept": "application/json",
                "surreal-ns": SURREAL_NS,
                "surreal-db": SURREAL_DB,
            },
            auth=SURREAL_AUTH,
            data=query.encode("utf-8"),
            timeout=30
        )
    except Exception as e:
        raise SurrealError(f"SurrealDB unreachable: {e}") from e

    if not response.ok:
        raise SurrealError(f"SurrealDB returned HTTP {response.status_code}")

    try:
        payload = response.json()
    except ValueError as e:
        raise SurrealError("SurrealDB response was not JSON") from e

    if not isinstance(payload, list):
        raise SurrealError("unexpected response shape from SurrealDB")

    for statement in payload:
        if isinstance(statement, dict) and statement.get('status') != 'OK':
            raise SurrealError(str(statement.get('result', 'unknown SurrealDB error')))

    return payload


@tags_bp.errorhandler(SurrealError)
def _handle_surreal_error(err):
    """Report a datastore failure honestly — never as a 200 with an error inside.

    "Table does not exist" is separated out deliberately. Tagging was never
    built: these endpoints query a `tag` table that no schema defines and no
    writer populates. That is a missing feature (501), not an outage (503), and
    conflating the two would have monitors paging about a service that is
    working exactly as built.
    """
    message = str(err)
    if 'does not exist' in message and 'table' in message.lower():
        return jsonify({
            'error': 'Tagging is not implemented — no tag data has ever been written.',
            'detail': message,
            'source': 'knowledgestack',
        }), 501
    return jsonify({'error': message, 'source': 'surrealdb'}), 503


@tags_bp.route('/api/list')
def list_tags():
    """List tags with filtering and sorting."""
    tag_type = request.args.get('type', '')
    sort = request.args.get('sort', 'mentions')
    limit = min(int(request.args.get('limit', 100)), 500)
    search = request.args.get('q', '')
    min_mentions = int(request.args.get('min_mentions', 1))

    where_clauses = [f"mention_count >= {min_mentions}"]
    if tag_type:
        where_clauses.append(f"type = '{q(tag_type)}'")
    if search:
        safe_search = search.replace("'", "\\'")
        where_clauses.append(f"string::lowercase(name) CONTAINS '{safe_search.lower()}'")

    where = " AND ".join(where_clauses)

    sort_map = {
        'mentions': 'mention_count DESC',
        'name': 'name ASC',
        'recent': 'created_at DESC',
    }
    order = sort_map.get(sort, 'mention_count DESC')

    results = surreal_query(f"""
        SELECT id, name, slug, type, description, wikidata_id, mention_count, created_at
        FROM tag WHERE {where}
        ORDER {order} LIMIT {limit};
    """)

    tags = results[0]['result'] if results and results[0].get('result') else []

    return jsonify({'tags': tags, 'count': len(tags)})


@tags_bp.route('/api/stats')
def tag_stats():
    """Get tag statistics."""
    results = surreal_query("""
        SELECT count() as total FROM tag GROUP ALL;
        SELECT type, count() as c FROM tag GROUP BY type ORDER c DESC;
        SELECT count() as c FROM tagged_segment GROUP ALL;
        SELECT count() as c FROM tagged_video GROUP ALL;
        SELECT count() as c FROM child_of GROUP ALL;
        SELECT count() as c FROM related_to GROUP ALL;
    """)

    total = results[0]['result'][0]['total'] if results and results[0].get('result') else 0
    by_type = results[1]['result'] if len(results) > 1 and results[1].get('result') else []
    segment_links = results[2]['result'][0]['c'] if len(results) > 2 and results[2].get('result') else 0
    video_links = results[3]['result'][0]['c'] if len(results) > 3 and results[3].get('result') else 0
    hierarchies = results[4]['result'][0]['c'] if len(results) > 4 and results[4].get('result') else 0
    relations = results[5]['result'][0]['c'] if len(results) > 5 and results[5].get('result') else 0

    return jsonify({
        'total_tags': total,
        'by_type': by_type,
        'segment_links': segment_links,
        'video_links': video_links,
        'hierarchies': hierarchies,
        'relations': relations,
    })


@tags_bp.route('/api/<tag_id>')
def get_tag(tag_id):
    """Get tag detail with hierarchy and linked content."""
    # tag_id lands directly in a record identifier, where quote-escaping does not
    # help — `foo; DELETE video` would run as its own statement. Restrict it to
    # the characters a real tag id uses and reject anything else outright.
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", tag_id or ""):
        return jsonify({'error': 'Invalid tag id'}), 400

    safe_id = f"tag:{tag_id}"

    # Get tag details
    results = surreal_query(f"SELECT * FROM {safe_id};")
    if not results or not results[0].get('result'):
        return jsonify({'error': 'Tag not found'}), 404

    tag = results[0]['result'][0]

    # Get parent tags (this tag is child_of -> parent)
    parents = surreal_query(f"""
        SELECT out.name as name, out.id as id, out.type as type, out.wikidata_id as wd
        FROM child_of WHERE in = {safe_id};
    """)
    tag['parents'] = parents[0]['result'] if parents and parents[0].get('result') else []

    # Get child tags (children -> child_of -> this tag)
    children = surreal_query(f"""
        SELECT in.name as name, in.id as id, in.type as type, in.mention_count as mentions
        FROM child_of WHERE out = {safe_id} ORDER in.mention_count DESC;
    """)
    tag['children'] = children[0]['result'] if children and children[0].get('result') else []

    # Get synonyms
    synonyms = surreal_query(f"""
        SELECT in.name as name, in.id as id FROM synonym_of WHERE out = {safe_id};
    """)
    tag['synonyms'] = synonyms[0]['result'] if synonyms and synonyms[0].get('result') else []

    # Get related tags via related_to
    related = surreal_query(f"""
        SELECT out.name as name, out.id as id, out.type as type, predicate
        FROM related_to WHERE in = {safe_id} LIMIT 20;
    """)
    tag['related'] = related[0]['result'] if related and related[0].get('result') else []

    # Get videos that have this tag
    videos = surreal_query(f"""
        SELECT in.youtube_id as youtube_id, in.title as title, in.domain as domain, segment_count
        FROM tagged_video WHERE out = {safe_id}
        ORDER segment_count DESC LIMIT 20;
    """)
    tag['videos'] = videos[0]['result'] if videos and videos[0].get('result') else []

    # Get sample segments with this tag
    segments = surreal_query(f"""
        SELECT in.text as text, in.start_time as start_time, in.video_youtube_id as video_id, confidence
        FROM tagged_segment WHERE out = {safe_id}
        LIMIT 10;
    """)
    tag['segments'] = segments[0]['result'] if segments and segments[0].get('result') else []

    return jsonify(tag)


@tags_bp.route('/api/hierarchy')
def get_hierarchy():
    """Get tag hierarchy as tree structure for visualization."""
    # Get root tags (tags that are parents but not children)
    results = surreal_query("""
        SELECT out as parent FROM child_of GROUP BY out;
    """)
    parent_ids = set()
    if results and results[0].get('result'):
        parent_ids = {str(r['parent']) for r in results[0]['result']}

    child_results = surreal_query("""
        SELECT in as child FROM child_of GROUP BY in;
    """)
    child_ids = set()
    if child_results and child_results[0].get('result'):
        child_ids = {str(r['child']) for r in child_results[0]['result']}

    # Root tags: are parents but not children of anything
    root_ids = parent_ids - child_ids

    # Get all hierarchy edges
    edges = surreal_query("SELECT in as child, out as parent FROM child_of;")
    edge_list = edges[0]['result'] if edges and edges[0].get('result') else []

    # Get all tag names
    tag_results = surreal_query("""
        SELECT id, name, type, mention_count, wikidata_id FROM tag
        WHERE mention_count >= 1
        ORDER mention_count DESC;
    """)
    tags = {str(t['id']): t for t in (tag_results[0]['result'] if tag_results and tag_results[0].get('result') else [])}

    # Build tree
    children_map = {}
    for edge in edge_list:
        parent = str(edge['parent'])
        child = str(edge['child'])
        if parent not in children_map:
            children_map[parent] = []
        children_map[parent].append(child)

    def build_node(tag_id, depth=0):
        if depth > 5:
            return None
        tag = tags.get(tag_id, {})
        if not tag:
            return None
        node = {
            'id': tag_id,
            'name': tag.get('name', '?'),
            'type': tag.get('type', 'concept'),
            'mentions': tag.get('mention_count', 0),
            'wikidata_id': tag.get('wikidata_id'),
            'children': []
        }
        for child_id in children_map.get(tag_id, []):
            child_node = build_node(child_id, depth + 1)
            if child_node:
                node['children'].append(child_node)
        node['children'].sort(key=lambda x: x.get('mentions', 0), reverse=True)
        return node

    tree = []
    for root_id in sorted(root_ids, key=lambda x: tags.get(x, {}).get('mention_count', 0), reverse=True):
        node = build_node(root_id)
        if node:
            tree.append(node)

    return jsonify({'roots': tree, 'total_nodes': len(tags), 'total_edges': len(edge_list)})


@tags_bp.route('/api/graph')
def get_graph():
    """Get tag relationship graph for force-directed visualization."""
    limit = min(int(request.args.get('limit', 100)), 300)
    min_mentions = int(request.args.get('min_mentions', 2))

    # Get significant tags
    tag_results = surreal_query(f"""
        SELECT id, name, type, mention_count, wikidata_id
        FROM tag WHERE mention_count >= {min_mentions}
        ORDER mention_count DESC LIMIT {limit};
    """)
    tags = tag_results[0]['result'] if tag_results and tag_results[0].get('result') else []
    tag_ids = {str(t['id']) for t in tags}

    # Get edges between these tags
    edges = surreal_query(f"""
        SELECT in as source, out as target, 'child_of' as type FROM child_of
        WHERE string::is::record(in) AND string::is::record(out);
    """)
    child_edges = edges[0]['result'] if edges and edges[0].get('result') else []

    rel_edges = surreal_query(f"""
        SELECT in as source, out as target, predicate as type FROM related_to;
    """)
    related_edges = rel_edges[0]['result'] if rel_edges and rel_edges[0].get('result') else []

    # Filter edges to only include tags in our node set
    all_edges = child_edges + related_edges
    filtered_edges = []
    for e in all_edges:
        src = str(e.get('source', ''))
        tgt = str(e.get('target', ''))
        if src in tag_ids and tgt in tag_ids:
            filtered_edges.append({
                'source': src,
                'target': tgt,
                'type': e.get('type', 'related')
            })

    # Format nodes
    nodes = [{
        'id': str(t['id']),
        'name': t['name'],
        'type': t['type'],
        'mentions': t['mention_count'],
        'wikidata': t.get('wikidata_id'),
    } for t in tags]

    return jsonify({
        'nodes': nodes,
        'edges': filtered_edges,
    })
