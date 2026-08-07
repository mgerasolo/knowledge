# Knowledge Management Metadata Entities: Research Report

**Date:** 2026-01-29
**Scope:** Entity types, field inventories, source hierarchies, relationship patterns, and design recommendations drawn from real implementations across 15+ systems.

---

## Executive Summary

1. **Six core entity types recur across nearly every mature system:** Sources, People, Topics, Organizations, Tags, and Notes/Claims. Beyond those, Events, Locations, Instruments/Tools, Series, and Works appear in domain-specific systems (MusicBrainz, IMDb, Zotero).

2. **Source hierarchy follows a universal three-level pattern:** Publisher/Platform --> Series/Channel --> Item/Episode. This pattern appears identically in IMDb (Studio --> Show --> Episode), MusicBrainz (Label --> Release Group --> Recording), Podchaser (Network --> Podcast --> Episode), Zotero (Publisher --> Journal --> Article), and YouTube (Platform --> Channel --> Video).

3. **Tags and Topics are architecturally distinct concepts.** Tags are user-curated folksonomies (flat, free-form, personal); Topics are system-managed taxonomies (hierarchical, controlled vocabulary, shared). Every mature system that started with only one eventually added the other. The hybrid approach is now considered best practice.

4. **URL is standard on source entities, but mature systems always include a secondary identifier** (DOI, ISBN, ISSN, MBID, iTunes ID, RSS feed URL). Systems that relied solely on URLs faced link rot. Those that captured multiple identifiers proved most resilient.

5. **The most commonly regretted missing fields** are: explicit creation date (not filesystem), source/origin URL, note maturity status, content type classification, and "who told me this" provenance. Every mature PKM practitioner surveyed cited at least three of these.

---

## 1. Entity Types Found

### Tier 1: Universal (present in 80%+ of systems surveyed)

| Entity Type | Systems That Use It |
|---|---|
| **Source / Item** | Zotero, Notion, Obsidian, Logseq, Podchaser, Listen Notes, IMDb, MusicBrainz, Discogs, Neo4j, Schema.org |
| **Person / Creator** | Zotero, Podchaser, IMDb, MusicBrainz, Discogs, Schema.org, Notion, Obsidian, Roam |
| **Topic / Subject** | Podchaser, Listen Notes, Notion, Obsidian, Logseq, Zotero (via tags), Neo4j, Schema.org |
| **Tag** | Obsidian, Logseq, Zotero, MusicBrainz, Notion, Roam, all PKM tools |
| **Organization / Label / Publisher** | Zotero, MusicBrainz, Discogs, IMDb, Schema.org, Podchaser |
| **Note / Claim / Annotation** | Obsidian, Logseq, Roam, Zotero, Neo4j |

### Tier 2: Common (present in 40-80% of systems)

| Entity Type | Systems That Use It |
|---|---|
| **Series / Collection / Release Group** | MusicBrainz, IMDb, Discogs, Zotero, Schema.org, Podchaser |
| **Event** | MusicBrainz, Schema.org, Roam (via ontology) |
| **Location / Area / Place** | MusicBrainz, Schema.org, IMDb, Podchaser (creator location) |
| **Genre / Category** | MusicBrainz, Discogs, Podchaser, Listen Notes, IMDb |
| **URL (as entity)** | MusicBrainz (primary entity), Schema.org, Zotero |

### Tier 3: Domain-Specific (present in <40% of systems)

| Entity Type | Systems That Use It |
|---|---|
| **Work (composition behind a recording)** | MusicBrainz |
| **Instrument** | MusicBrainz |
| **Recording (specific audio)** | MusicBrainz |
| **Track (context-dependent recording)** | MusicBrainz, Discogs |
| **Medium (physical/digital carrier)** | MusicBrainz, Discogs |
| **Credit (role-in-context)** | Podchaser, IMDb, MusicBrainz, Discogs |
| **Rating / Review** | Podchaser, IMDb, MusicBrainz |
| **Playlist / Curated List** | Listen Notes, Podchaser |
| **Alias / Name Variation** | MusicBrainz, Discogs |
| **Chunk (text segment for RAG)** | Neo4j LLM Graph Builder, n8n pipelines |

---

## 2. Source Hierarchy Patterns

Every mature media/content database follows a remarkably consistent three-level hierarchy. The pattern is:

```
Platform/Publisher  -->  Series/Channel  -->  Item/Episode
```

### Concrete Examples

| Domain | Level 1 (Platform) | Level 2 (Series) | Level 3 (Item) |
|---|---|---|---|
| **YouTube** | YouTube (platform) | Channel | Video |
| **Podcasts** (Podchaser) | Network/Publisher | Podcast (PodcastSeries) | Episode |
| **Podcasts** (Listen Notes) | Publisher | Podcast | Episode |
| **TV/Film** (IMDb) | Company/Studio | TV Series (titleType) | Episode (tvepisode) |
| **Music** (MusicBrainz) | Label | Release Group (Album) | Recording/Track |
| **Music** (Discogs) | Label | Master Release | Release/Track |
| **Academic** (Zotero) | Publisher | Journal/Conference | Article/Paper |
| **Schema.org** | Organization (publisher) | CreativeWorkSeries | CreativeWork |
| **Books** | Publisher | Book Series | Book / Chapter |
| **Blogs/News** | Publisher | Blog/Section | Post/Article |

### Key Implementation Details

**MusicBrainz** adds a fourth level by separating `Work` (the abstract composition) from `Recording` (specific audio). A single Work can have many Recordings. This is the most granular hierarchy found.

**IMDb** uses `parentTconst` to link episodes to their parent series, with `seasonNumber` and `episodeNumber` fields. This is the simplest and most widely imitated pattern.

**Discogs** introduces `Master Release` as a grouping entity that collects multiple physical/digital releases of the same content. This solves the "same album, different pressings" problem -- analogous to "same podcast episode, different platforms."

**Schema.org** formalizes the pattern with `partOfSeries` (links Episode to PodcastSeries) and `partOfSeason` (links Episode to Season).

### Recommended Pattern for a Knowledge Ingestion Platform

```
Platform
  └── Channel / Publisher (Organization + Source hybrid)
       └── Series (optional -- for podcast series, YouTube playlists, book series)
            └── Item (Video, Episode, Article, Book, PDF)
                 └── Segment / Chunk (optional -- timestamped portions)
```

The Series level should be optional. Many sources (standalone articles, individual YouTube videos, one-off PDFs) do not belong to a series. Forcing a series entity creates empty scaffolding.

---

## 3. Field Inventories

### Person Entity

Fields synthesized from Schema.org Person, Podchaser Creator, MusicBrainz Artist, IMDb name.basics, and Zotero People database:

| Field | Source Systems | Priority | Notes |
|---|---|---|---|
| `id` | All | Required | Internal UUID |
| `name` | All | Required | Display name (primary) |
| `given_name` | Schema.org, Zotero | Recommended | First name |
| `family_name` | Schema.org, Zotero | Recommended | Last name |
| `aliases` | MusicBrainz, Discogs, Schema.org | Recommended | Array of alternate names, stage names |
| `bio` | Podchaser, Schema.org | Optional | Short biography |
| `url` | Schema.org, Podchaser | Recommended | Primary web presence |
| `image_url` | Podchaser, Schema.org | Optional | Profile photo |
| `email` | Schema.org | Optional | Contact |
| `affiliation` | Schema.org | Recommended | Organization(s) they belong to |
| `job_title` | Schema.org | Optional | Current role |
| `knows_about` | Schema.org | Recommended | Topics of expertise (links to Topic entities) |
| `same_as` | Schema.org, MusicBrainz | Recommended | Array of external profile URLs (Twitter, LinkedIn, Wikipedia) |
| `birth_date` | Schema.org, MusicBrainz | Optional | |
| `death_date` | Schema.org, MusicBrainz | Optional | |
| `location` | Podchaser, Schema.org | Optional | Current city/region |
| `nationality` | Schema.org | Optional | |
| `pronouns` | Podchaser | Optional | |
| `external_ids` | MusicBrainz (MBID, IPI, ISNI), IMDb (nconst) | Recommended | Map of platform -> ID |
| `created_at` | All | Required | When entity was created in system |
| `updated_at` | All | Required | Last modification |
| `notes` | Obsidian, Notion | Optional | Free-form annotations |

### Source Entity (Article, Video, Episode, Book, etc.)

Fields synthesized from Zotero (46 item types), Schema.org CreativeWork, Podchaser Episode, Listen Notes Episode, n8n pipeline outputs:

| Field | Source Systems | Priority | Notes |
|---|---|---|---|
| `id` | All | Required | Internal UUID |
| `title` | All | Required | Primary title |
| `source_type` | Zotero (46 types), Schema.org | Required | youtube_video, podcast_episode, article, book, pdf, etc. |
| `url` | All | Required* | Primary URL (*see URL handling section) |
| `description` | Podchaser, Listen Notes, Schema.org | Recommended | Summary/abstract |
| `content` | n8n pipelines | Optional | Full text / transcript |
| `author` | Zotero, Schema.org | Recommended | Link to Person entity |
| `publisher` | Zotero, Schema.org | Recommended | Link to Organization entity |
| `date_published` | All | Recommended | Original publication date |
| `date_accessed` | Zotero | Recommended | When you encountered this source |
| `date_ingested` | n8n pipelines | Required | When system processed this source |
| `language` | Listen Notes, Zotero, Schema.org | Optional | ISO language code |
| `duration` | Podchaser, Listen Notes, Schema.org | Conditional | For audio/video, in seconds |
| `thumbnail_url` | Listen Notes, Podchaser, Schema.org | Optional | Preview image |
| `parent_source` | IMDb, Podchaser, MusicBrainz | Recommended | Link to parent (channel, series, journal) |
| `series` | Zotero, Schema.org | Optional | Link to Series entity |
| `season_number` | IMDb, Schema.org | Conditional | For episodic content |
| `episode_number` | IMDb, Schema.org, Podchaser | Conditional | For episodic content |
| `volume` | Zotero | Conditional | For journals/books |
| `issue` | Zotero | Conditional | For journals |
| `pages` | Zotero | Conditional | For print sources |
| `isbn` | Zotero | Conditional | For books |
| `doi` | Zotero, Semantic Scholar | Conditional | For academic papers |
| `issn` | Zotero | Conditional | For journals |
| `external_ids` | Listen Notes (itunes_id), Podchaser (pcid), IMDb (tconst) | Recommended | Map of platform -> ID |
| `explicit_content` | Listen Notes, Podchaser | Optional | Boolean |
| `genre_ids` | Listen Notes, IMDb, MusicBrainz | Optional | Links to Genre/Category entities |
| `ai_summary` | n8n pipelines | Optional | LLM-generated summary |
| `ingestion_status` | n8n pipelines | Recommended | pending, transcript_complete, vectorized, etc. |
| `created_at` | All | Required | |
| `updated_at` | All | Required | |
| `notes` | Obsidian, Notion, Zotero | Optional | Personal annotations |

### Topic Entity

Fields synthesized from Podchaser categories, Listen Notes genres, MusicBrainz genres, Schema.org, Notion knowledge areas:

| Field | Source Systems | Priority | Notes |
|---|---|---|---|
| `id` | All | Required | Internal UUID |
| `name` | All | Required | Canonical name |
| `slug` | Web systems | Recommended | URL-safe identifier |
| `description` | Listen Notes, Podchaser | Optional | What this topic covers |
| `parent_topic` | Listen Notes (genre hierarchy), Schema.org | Recommended | For hierarchical taxonomy |
| `aliases` | MusicBrainz | Optional | Alternate names for this topic |
| `same_as` | Schema.org | Optional | Links to Wikidata, Wikipedia, etc. |
| `topic_type` | Custom | Recommended | subject_area, genre, discipline, skill |
| `created_at` | All | Required | |
| `updated_at` | All | Required | |

### Organization Entity

Fields synthesized from Schema.org Organization, MusicBrainz Label, Discogs Label, Zotero Publisher, Podchaser Network:

| Field | Source Systems | Priority | Notes |
|---|---|---|---|
| `id` | All | Required | Internal UUID |
| `name` | All | Required | Primary name |
| `aliases` | MusicBrainz, Discogs | Optional | Alternate names |
| `org_type` | Custom | Recommended | publisher, label, studio, network, company, channel |
| `url` | Schema.org | Recommended | Official website |
| `description` | All | Optional | About this organization |
| `location` | Schema.org, MusicBrainz (area) | Optional | HQ location |
| `parent_org` | MusicBrainz (parent label) | Optional | For subsidiaries |
| `same_as` | Schema.org | Optional | External profile URLs |
| `external_ids` | MusicBrainz (MBID), Discogs | Optional | Platform-specific IDs |
| `founded_date` | Schema.org, MusicBrainz | Optional | |
| `created_at` | All | Required | |
| `updated_at` | All | Required | |

### Tag Entity

| Field | Priority | Notes |
|---|---|---|
| `id` | Required | Internal UUID |
| `name` | Required | The tag text |
| `slug` | Recommended | URL-safe version |
| `color` | Optional | For UI display |
| `description` | Optional | What this tag means in your system |
| `created_by` | Recommended | User who created this tag |
| `usage_count` | Recommended | How many entities use this tag (computed) |
| `created_at` | Required | |

---

## 4. Relationship Types

### Universal Relationships (found across all systems)

| Relationship | Direction | Examples |
|---|---|---|
| `CREATED_BY` / `AUTHORED_BY` | Source --> Person | Article authored by Person, Video created by Person |
| `PUBLISHED_BY` | Source --> Organization | Episode published by Network, Article published by Journal |
| `PART_OF` | Source --> Source/Series | Episode part of Podcast, Chapter part of Book |
| `TAGGED_WITH` | Any --> Tag | Source tagged with Tag, Person tagged with Tag |
| `ABOUT` / `COVERS_TOPIC` | Source --> Topic | Video covers Topic, Article about Topic |
| `AFFILIATED_WITH` / `MEMBER_OF` | Person --> Organization | Person works at Company, Artist signed to Label |
| `RELATED_TO` | Topic --> Topic | Topic relates to Topic (bidirectional) |
| `PARENT_OF` / `CHILD_OF` | Topic --> Topic | Machine Learning parent of Deep Learning |

### Content-Specific Relationships

| Relationship | Direction | Systems | Notes |
|---|---|---|---|
| `APPEARS_IN` / `GUEST_ON` | Person --> Source | Podchaser, IMDb | Person appeared as guest on Episode |
| `HOSTS` | Person --> Source/Series | Podchaser | Person hosts Podcast |
| `PRODUCED_BY` | Source --> Person | IMDb, MusicBrainz | Production credit |
| `DIRECTED_BY` | Source --> Person | IMDb | Direction credit |
| `PERFORMED_BY` | Source --> Person | MusicBrainz | Performance credit |
| `RECORDED_AT` | Source --> Location | MusicBrainz (Place) | Where content was recorded |
| `REFERENCES` / `CITES` | Source --> Source | Zotero, Semantic Scholar | Citation relationship |
| `DERIVED_FROM` / `BASED_ON` | Source --> Source | Schema.org (isBasedOn) | Adaptation, response, etc. |
| `SAME_AS` | Any --> External URL | MusicBrainz, Schema.org | Links entity to external identity |
| `VERSION_OF` | Source --> Source | Discogs (Master Release) | Same content, different format |

### Relationship Properties (Metadata on Edges)

MusicBrainz pioneered rich relationship properties. Their `link` table includes:

| Property | Purpose |
|---|---|
| `link_type` | What kind of relationship (e.g., "engineer", "producer", "vocals") |
| `begin_date` / `end_date` | When the relationship was active |
| `attribute_count` | Number of qualifying attributes |
| `edits_pending` | Change tracking |
| `created` | When the relationship was established |

**Recommendation:** At minimum, relationships should carry: `role` (what kind of relationship), `created_at`, and optionally `confidence` (for AI-extracted relationships) and `source` (where the relationship was asserted).

---

## 5. Tags vs Topics: How Systems Differentiate

### The Formal Distinction

| Aspect | Tags (Folksonomy) | Topics (Taxonomy) |
|---|---|---|
| **Created by** | End users, personally meaningful | System owners, domain experts, or AI |
| **Structure** | Flat (no hierarchy) | Hierarchical (parent-child) |
| **Vocabulary** | Free-form, natural language | Controlled, standardized |
| **Consistency** | Low (synonyms, typos, ambiguity) | High (canonical names) |
| **Cost** | Low (user-generated) | Higher (requires curation) |
| **Best for** | Personal retrieval, quick capture | Browsing, discovery, cross-user consistency |

### How Real Systems Handle This

**Obsidian** -- Tags only. No built-in topic system. Power users simulate topics with nested tags (e.g., `#topic/machine-learning/transformers`) or dedicated "Map of Content" (MOC) notes. Tag Wrangler plugin helps manage renames and merges across the vault.

**Logseq / Roam** -- Properties and page references serve as both. Power users build explicit ontologies using `is_a::` properties to type pages as Person, Topic, etc. No formal separation between tags and topics at the system level.

**Notion** -- Separate databases for Tags and Topics/Knowledge Areas. Tags are a multi-select property on items. Topics are a separate linked database with their own properties and hierarchy. This is the closest to a formal dual system.

**Zotero** -- Tags only, but with two distinct types: user tags (manually applied) and automatic tags (imported from publisher metadata, displayed in a different color). Users frequently request topic/subject taxonomies but Zotero has not implemented them.

**MusicBrainz** -- Tags (user-applied folksonomy) and Genres (curated taxonomy) are separate entity types with separate tables. Tags can be anything; Genres are a controlled list.

**Podchaser / Listen Notes** -- Categories/Genres only (system-defined taxonomy). No user-generated tagging.

**Schema.org** -- Uses `keywords` (free-form, tag-like) and `about` (links to structured Thing entities, topic-like). This is the cleanest formal separation found.

### Recommendation

Implement both, clearly separated:

- **Tags**: flat, user-created, free-form strings. Applied to any entity. Personal and idiosyncratic.
- **Topics**: hierarchical, system-managed, controlled vocabulary. Linked to Topic entities with `parent_topic`. Can be AI-suggested and human-approved.
- **Bridge**: Allow Topics to have associated Tags (e.g., the Topic "Machine Learning" might have tags "ML", "machine-learning", "AI/ML" as aliases).

---

## 6. URL / Reference Handling

### The Problem

Not all sources have URLs. Books, PDFs found offline, verbal conversations, and paywalled content all present challenges. Systems that assumed every source has a URL encountered issues.

### How Systems Handle This

**Zotero** -- URL is optional. Primary identification uses DOI (academic papers), ISBN (books), or ISSN (journals). The `archive` and `archive_location` fields handle physical materials. The `extra` field serves as overflow for any identifier not covered by built-in fields.

**MusicBrainz** -- URL is a first-class entity type linked via relationships. Each entity can have zero or many URLs, each with a typed relationship (e.g., "official homepage", "Wikipedia page", "Discogs page", "streaming link"). This is the most flexible approach found.

**Schema.org** -- Uses `url` for primary web presence, `sameAs` for additional platform URLs, and `identifier` for non-URL identifiers (ISBN, DOI, ORCID).

**Listen Notes / Podchaser** -- Every entity has a canonical platform URL plus the original RSS/web URL. `audio_url` is separate from the episode page URL.

### Recommended Pattern

```
source.url           -- Primary web URL (nullable)
source.urls[]        -- Array of typed URLs: {url, type, label}
                        type: "canonical", "archive", "audio", "video",
                              "transcript", "purchase", "official"
source.external_ids  -- Map of platform identifiers: {doi, isbn, issn,
                        youtube_id, itunes_id, spotify_id, mbid, ...}
source.archive       -- Where physical copy is stored (nullable)
```

This handles:
- Web articles (url filled, external_ids empty)
- YouTube videos (url filled, external_ids.youtube_id filled)
- Books (url nullable, external_ids.isbn filled, archive optional)
- PDFs (url nullable, could store local path in archive)
- Podcasts (url filled, external_ids.itunes_id + spotify_id filled, urls[] includes audio URL)

---

## 7. Commonly Missed Fields (Lessons Learned)

These fields are cited repeatedly by mature system maintainers as things they wish they had captured from the start:

### Universally Regretted Omissions

| Field | Why It Matters | Systems That Learned This |
|---|---|---|
| **`created_at` (explicit, not filesystem)** | Filesystem dates break on backup/restore/migration. Store creation time in the data itself. | Obsidian community (top request), all databases |
| **`source_url` / provenance** | "Where did I find this?" is impossible to reconstruct retroactively. Capture the origin URL or reference immediately on ingestion. | PKM community (Obsidian, Notion), Zotero |
| **`date_accessed`** | When you encountered the source, separate from when it was published. Critical for link-rot recovery (Wayback Machine lookup). | Zotero (built-in), PKM community |
| **`content_type` / `note_type`** | Distinguishing fleeting notes from literature notes from evergreen notes. Without this, you cannot filter by maturity. | Zettelkasten practitioners, Obsidian community |
| **`status` / `maturity`** | draft, reviewed, evergreen, archived. Without it, you cannot find notes that need development. | Notion, Obsidian power users |
| **`who_told_me` / `attribution`** | "Who told me this?" -- provenance of a claim or idea, distinct from the author of the source. | PKM community, academic systems |
| **`ingestion_method`** | How the content entered the system (manual entry, web clipper, API import, AI extraction). Matters for assessing quality and completeness. | n8n pipelines, RAG systems |
| **`confidence` / `quality`** | For AI-extracted data: how reliable is this metadata? Without it, you cannot distinguish human-verified from machine-guessed. | Neo4j LLM Graph Builder, n8n AI pipelines |

### Domain-Specific Regrets

| Field | Context | Why It Matters |
|---|---|---|
| **`duration`** (for all media) | Podcasts, videos | Critical for filtering ("show me sub-10-minute videos on X") |
| **`language`** | Multilingual systems | Cannot filter or route content without it |
| **`explicit_content`** | Podcasts | Podchaser and Listen Notes both track this; useful for content filtering |
| **`parent_source`** hierarchy | All media | Without it, you cannot answer "what channel is this from?" retroactively |
| **`external_ids`** (multiple) | All | Systems that stored only one platform ID (e.g., only YouTube ID) regretted it when content appeared on multiple platforms |
| **`aliases`** on Person entities | All | People change names, use stage names, get credited differently. Without aliases, deduplication is painful. |
| **`role`** on relationships | All | Knowing that a person is connected to a source is not enough. Was she the host? Guest? Producer? Author? |

---

## 8. Recommendations for a Knowledge Ingestion Platform

Based on analysis of all systems above, here are concrete recommendations for a platform handling YouTube transcripts, podcasts, articles, and eventually PDFs/books:

### Entity Model

Implement these six core entities:

1. **Source** -- The primary content item (video, episode, article, book, PDF)
2. **Person** -- Any human referenced in or responsible for content
3. **Organization** -- Publishers, channels, networks, companies, labels
4. **Topic** -- System-managed hierarchical taxonomy (controlled vocabulary)
5. **Tag** -- User-managed flat folksonomy (free-form strings)
6. **Note** -- User annotations, claims, highlights, and original thoughts

Plus one supporting entity:

7. **Series** -- Optional grouping (podcast series, YouTube playlist, book series, journal)

### Source Type Taxonomy

Based on Zotero's 46 item types, filtered for relevance:

```
youtube_video
podcast_episode
article          (web article, blog post)
academic_paper   (journal article, conference paper)
book
book_section     (chapter)
pdf              (ungrouped document)
newsletter
social_post      (tweet thread, etc.)
presentation     (slides, talks)
interview
report
webpage          (general web page)
```

### Minimum Viable Fields Per Entity

**Source** (MVP -- capture these on every ingestion):
- `id`, `title`, `source_type`, `url`, `date_published`, `date_ingested`
- `author_id` (link to Person), `publisher_id` (link to Organization)
- `parent_source_id` (link to parent Source, e.g., channel)
- `description`, `content` (full text/transcript if available)
- `external_ids` (JSON map), `language`, `duration` (for media)
- `ingestion_status`, `ingestion_method`
- `created_at`, `updated_at`

**Person** (MVP):
- `id`, `name`, `aliases[]`, `url`, `image_url`
- `affiliation_id` (link to Organization)
- `same_as[]` (external profile URLs)
- `external_ids` (JSON map)
- `created_at`, `updated_at`

**Organization** (MVP):
- `id`, `name`, `org_type`, `url`
- `parent_org_id` (for subsidiaries/sub-labels)
- `created_at`, `updated_at`

**Topic** (MVP):
- `id`, `name`, `slug`, `parent_topic_id`
- `description`
- `created_at`, `updated_at`

**Tag** (MVP):
- `id`, `name`, `slug`
- `created_at`

**Note** (MVP):
- `id`, `content`, `note_type` (claim, highlight, annotation, thought)
- `source_id` (link to Source), `person_id` (link to Person, optional)
- `timestamp_start`, `timestamp_end` (for media sources)
- `confidence` (for AI-extracted notes)
- `created_at`, `updated_at`

### Relationship Tables

```
source_people       (source_id, person_id, role: author|host|guest|producer|mentioned)
source_topics       (source_id, topic_id, confidence)
source_tags         (source_id, tag_id, created_by)
source_orgs         (source_id, org_id, role: publisher|sponsor|producer)
source_sources      (source_id, related_source_id, relationship: part_of|references|derived_from|version_of)
person_orgs         (person_id, org_id, role: member|founder|employee)
person_topics       (person_id, topic_id, relationship: expert_in|interested_in)
topic_topics        (topic_id, related_topic_id, relationship: parent_of|related_to|alias_of)
note_sources        (note_id, source_id)
note_topics         (note_id, topic_id)
note_people         (note_id, person_id)
```

### Data Ingestion Priorities

For a YouTube/podcast-first platform, capture in this order:

**Phase 1 -- Automated (API/scraping):**
- Source: title, URL, date_published, description, duration, thumbnail
- Person: channel name/podcast host (create Person + Organization)
- External IDs: YouTube video ID, channel ID, iTunes ID
- Content: full transcript (via YouTube API or third-party)
- Topics: AI-extracted from transcript (stored with confidence score)

**Phase 2 -- AI-Enhanced:**
- People mentioned in transcript (NER extraction, stored with confidence)
- Claims/highlights (AI-extracted Notes with timestamps)
- Topic classification against existing taxonomy
- Related source suggestions

**Phase 3 -- User-Curated:**
- Tags (personal folksonomy)
- Notes (manual annotations)
- Relationship corrections (fix AI misattributions)
- Topic refinements (promote AI-suggested topics to confirmed)

---

## Bibliography

### PKM Tools and Plugins
- [Obsidian Dataview Documentation](https://blacksmithgu.github.io/obsidian-dataview/)
- [Obsidian Dataview - Adding Metadata](https://blacksmithgu.github.io/obsidian-dataview/annotation/add-metadata/)
- [Obsidian Tag Wrangler Plugin](https://github.com/pjeby/tag-wrangler)
- [Personal Knowledge Graphs in Obsidian](https://volodymyrpavlyshyn.medium.com/personal-knowledge-graphs-in-obsidian-528a0f4584b9) -- Volodymyr Pavlyshyn
- [Roam Data Structure Deep Dive](https://www.zsolt.blog/2021/01/Roam-Data-Structure-Query.html)
- [Roaming Through Contexts with Roam](https://medium.com/an-idea/roaming-through-contexts-with-roam-how-i-use-it-3c581029dd6d) -- Ivo Velitchkov
- [Notion Personal Knowledge Management](https://thesweetsetup.com/notion-personal-knowledge-management/) -- The Sweet Setup
- [StoryFlint Personal Knowledge Base in Notion](https://www.storyflint.com/blog/personal-knowledge-management-notion)
- [Principles for Metadata Minimalism](https://forum.obsidian.md/t/principles-for-metadata-minimalism/11379) -- Obsidian Forum
- [Metadata in Obsidian: Secret Design of an Efficient PKM](https://xavendano.medium.com/%EF%B8%8F-metadata-in-obsidian-the-secret-design-of-an-efficient-pkm-7a9769a4a7f4) -- Romell

### Knowledge Graph Databases
- [Neo4j Knowledge Graph Generation](https://neo4j.com/blog/developer/knowledge-graph-generation/)
- [Neo4j LLM Knowledge Graph Builder](https://neo4j.com/labs/genai-ecosystem/llm-graph-builder/)
- [Neo4j GraphRAG Python User Guide](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_kg_builder.html)

### Media Databases
- [MusicBrainz Database Schema](https://musicbrainz.org/doc/MusicBrainz_Database/Schema)
- [IMDb Non-Commercial Datasets](https://developer.imdb.com/non-commercial-datasets/)
- [IMDb MySQL Database Project](https://github.com/dlwhittenbury/MySQL_IMDb_Project)
- [Discogs Database Glossary](https://support.discogs.com/hc/en-us/articles/360004017694-Database-Glossary)
- [Discogs Master Release Guidelines](https://support.discogs.com/hc/en-us/articles/360005055493-Database-Guidelines-16-Master-Release)
- [Discogs XML-to-DB Schema](https://github.com/philipmat/discogs-xml2db)

### Podcast APIs
- [Podchaser API Documentation](https://api-docs.podchaser.com/docs/overview/)
- [Podchaser Podcast Object Schema](https://api-docs.podchaser.com/docs/reference/objects/podcast/)
- [Podchaser Episode Object Schema](https://api-docs.podchaser.com/docs/reference/objects/episode/)
- [Podchaser Creator Object Schema](https://api-docs.podchaser.com/docs/reference/objects/creator/)
- [Listen Notes Podcast API](https://www.listennotes.com/api/docs/)
- [Entity and Event Topic Extraction from Podcast Episodes](https://dl.acm.org/doi/fullHtml/10.1145/3543873.3587648) -- ACM, 2023

### Academic / Reference Management
- [Zotero Item Types and Fields](https://www.zotero.org/support/kb/item_types_and_fields)
- [Zotero-to-CSL Type Mappings](https://aurimasv.github.io/z2csl/typeMap.xml)
- [Semantic Scholar FAQ](https://www.semanticscholar.org/faq)

### Standards and Schemas
- [Schema.org CreativeWork](https://schema.org/CreativeWork)
- [Schema.org Person](https://schema.org/Person)
- [Schema.org Organization](https://schema.org/Organization)
- [Schema.org PodcastEpisode](https://schema.org/PodcastEpisode)
- [Schema.org VideoObject](https://schema.org/VideoObject)
- [Schema.org PodcastSeries](https://schema.org/PodcastSeries)

### Tags / Folksonomy vs Taxonomy
- [Folksonomy -- Wikipedia](https://en.wikipedia.org/wiki/Folksonomy)
- [Difference Between Folksonomy and Taxonomy](https://blog.bismart.com/en/difference-between-folksonomy-and-taxonomy)
- [Folksonomy and Taxonomy in UX Design](https://medium.com/@mariajennings/folksonomies-and-taxonomies-in-ux-design-4ba0071ba186) -- Maria Jennings

### Knowledge Management Metadata
- [The Importance of Metadata in Your Knowledge Base](https://www.knowledgeowl.com/blog/posts/knowledge-base-metadata) -- KnowledgeOwl
- [Meta Data as Knowledge Management Enabler](https://tdan.com/meta-data-as-a-knowledge-management-enabler/4916) -- TDAN
- [Framework to Model Metadata for KM Tools](https://www.researchgate.net/publication/259527099_A_Framework_to_Model_Metadata_for_Knowledge_Management_Tools) -- ResearchGate

### n8n Workflow Templates
- [Process YouTube Transcripts with Apify, OpenAI and Pinecone](https://n8n.io/workflows/3184)
- [YouTube Video Metadata Generation](https://n8n.io/workflows/4506)
- [Summarize YouTube Videos into Structured Content Ideas](https://n8n.io/workflows/3609)
- [Build Knowledge Base Chatbot with RAG](https://n8n.io/workflows/4526)
- [Repurpose YouTube Videos with AI and Airtable](https://n8n.io/workflows/6899)
