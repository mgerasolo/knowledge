---
project_name: 'knowledge'
user_name: 'Matt'
date: '2026-01-31'
sections_completed: ['technology_stack', 'language_specific', 'framework_specific', 'testing', 'code_quality', 'development_workflow', 'critical_rules']
status: 'complete'
rule_count: 102
optimized_for_llm: true
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

### Core Platform (Adopted — Speakr)
- **Speakr** — Python 3.11 / Flask 2.3.3 + Vue.js 3 (pre-built static) — AGPL-3.0
- **PostgreSQL** — relational DB (shared with Speakr, psycopg2-binary ≥2.9.0)
- **FFmpeg** — system dependency for audio processing
- **sentence-transformers 2.7.0** — Speakr's built-in embedding/search

### KnowledgeStack Intelligence Overlay
- **n8n** — ingestion orchestration (YouTube RSS → Speakr REST API `/api/v1/upload`)
- **Qdrant** — vector DB (self-hosted Docker) — semantic search enrichment layer
- **LiteLLM proxy** — AI model routing (10.0.0.27:2764)
- **Qwen3 8B** — local LLM for bulk processing
- **nomic-embed-text-v1.5** — embedding model
- **Frontend (overlay)** — TBD (Speakr = Vue.js 3 as-is; overlay UI framework is open)

### Dev Tooling
- TypeScript ^5.9.3 | Node.js 20+ LTS
- ESLint ^9.39.2 | Prettier ^3.8.1
- Vitest ^4.0.18 (unit/integration) | Playwright ^1.58.0 (e2e)

### Infrastructure
- Docker Compose → Banner (10.0.0.33) dev / Hulk (10.0.0.32) prod
- Traefik reverse proxy → knowledge.nextlevelguild.com
- Authentik (Helicarrier) for auth | Loki+Prometheus → Grafana (Coulson)

## Critical Implementation Rules

### Language-Specific Rules

#### TypeScript (KnowledgeStack Overlay)
- ES modules (`"type": "module"`)
- Strict mode enabled — no `any` escape hatches without justification
- Async/await preferred over raw Promises
- Explicit return types on exported functions

#### Python (Speakr Extensions)
- Follow Speakr's existing patterns when extending — do not introduce new conventions
- Flask route decorators and Blueprint structure as established in Speakr `src/api/`
- Speakr uses `psycopg2-binary` — do not switch to `asyncpg` without migration plan
- Respect Speakr's SQLAlchemy model patterns (Flask-SQLAlchemy, not raw SQLAlchemy)

#### Cross-Language
- All API contracts between TypeScript overlay and Speakr/n8n use JSON over REST
- ISO 8601 for all datetime serialization
- UUIDv5 for deterministic content identifiers (per deduplication strategy)

### Framework-Specific Rules

#### 5-Product Architecture (KnowledgeStack Platform)
Agents must understand the product boundaries — each product owns a pipeline stage:

| Product | Tier | Owns | Tech | UI |
|---------|------|------|------|----|
| **KnowledgeEnroll** | 1 — Ingestion | RSS monitoring, download, dedup, metadata, channel subs | n8n, yt-dlp, YouTube API | Web portal (Sunflower UI) |
| **KnowledgeLecture** | 2 — Lecture Hall | Listen to/watch transcribed expert lectures, search, per-recording chat, tags, multi-user | Speakr (adopted, unmodified) | Speakr Vue.js 3 (as-is) |
| **KnowledgeCollege** | 3 — Intelligence | Vector embeddings, semantic search, entity/topic/speaker enrichment | Qdrant, LiteLLM | Headless (backend only) |
| **KnowledgeGraduate** | 4 — Distribution | REST API + MCP server for external apps/AI tools | Express/Flask, MCP | Headless (API only) |
| **KnowledgeOps** | Cross-cutting | Pipeline monitoring, Slack alerts, status digests, admin, DevOps | n8n, Slack, Grafana, Loki | Web portal (Sunflower UI) |

#### Speakr (KnowledgeLecture — DO NOT MODIFY without reason)
- Speakr is an adopted upstream project — treat it like a dependency
- Bug fixes and extensions OK; refactoring Speakr internals is not
- Speakr's Vue.js 3 frontend ships as pre-built static files — no build step
- Speakr REST API is the integration boundary (`/api/v1/...`)
- AGPL-3.0: any modifications to Speakr code must remain open-source

#### n8n (KnowledgeEnroll + KnowledgeOps)
- Configuration-first — prefer workflow JSON over custom code nodes
- Custom code nodes only when n8n's built-in nodes can't handle the task
- 4-workflow architecture (per research): RSS monitor, ingestion, enrichment, maintenance
- Sidecar yt-dlp pattern for audio download (not n8n's built-in HTTP node)

#### KnowledgeEnroll Web Portal
- Channel subscription management, ingestion monitoring, channel scoring (Authority × Relevance)
- Frontend framework TBD (overlay UI framework is open)
- Sunflower UI kit (NLF custom) from MVP

#### KnowledgeOps Web Portal
- Pipeline monitoring dashboard, failed item management, admin tooling
- Frontend framework TBD (overlay UI framework is open)
- Sunflower UI kit (NLF custom) from MVP

#### Qdrant (KnowledgeCollege)
- API-only integration — no plugins/extensions (Qdrant doesn't support them)
- JS client (`@qdrant/js-client-rest`) lacks Python's `upload_collection` bulk method — custom batching required (batch size 100-256, `wait: false` for throughput)
- Hybrid search (dense + sparse vectors) for quality results

#### Key Integration Rules
- Data flows: Enroll → Library → College → Graduate (pipeline, not circular)
- Never duplicate what Speakr already provides — check Library before building in College/Graduate

### Testing Rules

#### Test Framework Assignment
- **Vitest** — unit tests, integration tests, API contract tests, property-based tests (fast-check)
- **Playwright** — e2e UI workflow tests ONLY for KnowledgeEnroll portal and KnowledgeOps portal
- **supertest** — HTTP endpoint testing (Express/Flask routes) without browser overhead
- **zod** — runtime schema validation doubles as contract test (define schemas before tests)
- **Stryker** — mutation testing to verify test quality (run periodically, not every commit)
- Speakr has its own `tests/` directory — do not mix our tests into Speakr's test suite

#### 6-Layer Verification Architecture (Playwright is LAST, not first)
1. **Container health** — Docker HEALTHCHECK + Uptime Kuma ping
2. **Service availability** — HTTP 200 on version/health endpoints (supertest)
3. **API contract integrity** — zod schema validation on request/response boundaries
4. **Pipeline data integrity** — Vitest: dedup logic, batching edge cases, state transitions
5. **Production smoke** — automated post-deploy script verifies version endpoint returns expected commit SHA
6. **UI workflows** — Playwright for critical user flows only (after layers 1-5 pass)

#### Deploy Verification Gate (MUST pass before human review)
- Every deployable service exposes `GET /health` (200 OK) and `GET /version` (returns `{ commit, version, built }`)
- Post-deploy script: hit version endpoint, compare commit SHA to expected, fail loudly if mismatch
- If deploy verification fails → auto-reject, no human review triggered
- This eliminates the "not even deployed" false-positive review cycle

#### Variant Testing Matrix (KnowledgeEnroll + KnowledgeOps only)
- **Playwright projects config:** 3 viewports × 2 color schemes = 6 combinations
  - Mobile (375×667), Tablet (768×1024), Desktop (1280×800)
  - Light mode, Dark mode (`colorScheme` context option)
- **Full matrix:** Only for flows tagged `@variant-test` (critical user journeys)
- **Default:** Desktop-light for all other e2e tests
- **Visual regression:** `toHaveScreenshot()` with per-variant baselines
- Speakr UI variants are Speakr's responsibility — do not variant-test Speakr pages

#### Test Organization
- Unit/integration tests co-located with source or in `tests/` at project root
- Playwright e2e tests in `tests/e2e/` (existing config: `testDir: './tests'`)
- Contract schemas in `packages/contracts/src/` — shared between tests and runtime validation
- n8n workflow tests: validate workflow JSON structure + mock execution results

#### What to Test
- API contract boundaries between products (Enroll → Library, College → Graduate)
- Deduplication logic (UUIDv5 deterministic IDs — critical for data integrity)
- n8n webhook/trigger endpoints (mock n8n, test our handlers)
- Qdrant batching logic (edge cases around batch boundaries)
- Pipeline state machine transitions (11 states per dedup strategy)
- Config validation on startup (FR114 — fail fast on bad config)
- Health/version endpoints (every deployable service)

#### What NOT to Test
- Speakr internals — that's Speakr's responsibility
- n8n's built-in node behavior — test our workflows, not n8n itself
- LiteLLM proxy routing — test our prompts/responses, not the proxy
- Sunflower component internals (test at page integration level)

#### Contract-First Development
- Define zod schemas/TypeScript types BEFORE writing tests or implementation
- Schemas live in `packages/contracts/src/` and are imported by both test and production code
- API boundaries between products are the highest-priority contracts

#### Red-Green-Mutate Cycle
- Write failing tests FIRST (verify they actually fail — WF Phase 3 gate)
- Implement until green
- Run Stryker periodically to verify tests catch mutations (test quality check)
- Property-based tests (fast-check) for dedup logic and batch boundary edge cases

### Code Quality & Style Rules

#### Project Structure (Monorepo)
```
knowledge/
├── packages/
│   ├── enroll/              # KnowledgeEnroll — n8n workflows, RSS handlers, dedup
│   │   ├── package.json     # Own dependencies, scripts
│   │   ├── src/
│   │   └── tests/
│   ├── college/             # KnowledgeCollege — Qdrant, embeddings, enrichment
│   ├── graduate/            # KnowledgeGraduate — REST API, MCP server
│   ├── ops/                 # KnowledgeOps — monitoring, admin, Slack alerts
│   ├── contracts/           # Shared zod schemas, TypeScript types
│   │   └── src/
│   │       ├── enroll-channel.schema.ts
│   │       ├── enroll-recording.schema.ts
│   │       ├── college-embedding.schema.ts
│   │       └── index.ts     # Barrel export
│   └── shared/              # Shared utilities (logging, config, health endpoint)
├── n8n-workflows/           # Version-controlled n8n workflow definitions
│   ├── enroll-rss-monitor/
│   │   ├── workflow.json
│   │   ├── README.md
│   │   └── metadata.json    # { n8nWorkflowId, lastDeployedCommit }
│   ├── enroll-ingestion/
│   ├── college-enrichment/
│   └── ops-maintenance/
├── speakr/                  # Adopted upstream — git submodule or Docker-only
├── tests/
│   └── e2e/                 # Playwright e2e tests (cross-product flows)
├── docs/
│   ├── ACTIVE-WORK.md       # Parallel conversation registry
│   └── INTEGRATION-STATUS.md # Cross-product dependency tracking
├── CURRENT-STATE.md         # Living baton — updated at end of every conversation
└── CLAUDE.md                # AI agent instructions
```

#### Naming Conventions

**Files & Directories:**
- `kebab-case` for all files and directories (`channel-scoring.ts`, `rss-monitor/`)
- Contract schemas: `{product}-{entity}.schema.ts` (e.g., `enroll-channel.schema.ts`)
- Test files: `{name}.test.ts` for unit tests; `issue-[NUMBER]-[slug].spec.ts` for issue-driven tests
- n8n workflows: `{product}-{purpose}/` (e.g., `enroll-rss-monitor/`)
- Config files: `{tool}.config.ts` (e.g., `vitest.config.ts`, `playwright.config.ts`)

**TypeScript Code:**
- `PascalCase` for interfaces, types, classes, enums, components (`ChannelScore`, `RecordingState`)
- `camelCase` for functions, variables, properties (`getChannelScore`, `isProcessed`)
- `SCREAMING_SNAKE_CASE` for constants and enum values (`MAX_BATCH_SIZE`, `PROCESSING_FAILED`)
- Interfaces: prefix with `I` only if needed to disambiguate from class (`IChannelConfig` vs `ChannelConfig` class) — prefer no prefix
- Enums: singular name (`RecordingState`, not `RecordingStates`), values are `SCREAMING_SNAKE`
- Boolean variables/properties: prefix with `is`, `has`, `should`, `can` (`isProcessed`, `hasTranscript`)

**Products (always capitalize):**
- KnowledgeEnroll, KnowledgeLecture, KnowledgeCollege, KnowledgeGraduate, KnowledgeOps
- In code: import paths use lowercase package names (`@knowledge/enroll`, `@knowledge/contracts`)
- In prose/docs: always full capitalized name

**Reserved terms:**
- "Expert" — reserved for future authority profiles feature
- "Forge" and "Foundry" — off limits (used elsewhere in NLF)

**Environment Variables:**
- Convention: `KS_{PRODUCT}_{PURPOSE}` (e.g., `KS_ENROLL_RSS_INTERVAL`, `KS_COLLEGE_QDRANT_URL`)
- Shared infra: `KS_SHARED_{PURPOSE}` (e.g., `KS_SHARED_POSTGRES_URL`, `KS_SHARED_LITELLM_URL`)
- Never hardcode — always read from env with validation on startup

**Database:**
- Table names: `snake_case`, plural (`channels`, `recordings`, `pipeline_states`)
- Column names: `snake_case` (`created_at`, `channel_id`, `authority_score`)
- Indexes: `idx_{table}_{columns}` (e.g., `idx_recordings_channel_id`)

**API Endpoints:**
- REST: `/{product}/api/v1/{resource}` (e.g., `/enroll/api/v1/channels`)
- kebab-case for multi-word resources (`/pipeline-states`)
- Speakr endpoints unchanged: `/api/v1/...` (Speakr's existing routes)

**Docker Services:**
- `knowledge-{product}` (e.g., `knowledge-enroll`, `knowledge-college`)
- `knowledge-{infra}` for shared services (e.g., `knowledge-qdrant`, `knowledge-n8n`)

**Git:**
- Branch names: `feature/{issue-number}-{kebab-slug}` (e.g., `feature/42-rss-monitor`)
- Conventional Commits with product scope: `feat(enroll): add RSS polling interval config`
- Scopes: `enroll`, `library`, `college`, `graduate`, `ops`, `contracts`, `shared`, `infra`, `docs`

#### Versioning Strategy (Per-Product)

Each product is versioned independently using semver (`MAJOR.MINOR.PATCH`):

| Package | Version Source | Notes |
|---------|---------------|-------|
| `@knowledge/enroll` | `packages/enroll/package.json` | Starts at 0.1.0 (pre-1.0 until MVP-1 complete) |
| `@knowledge/college` | `packages/college/package.json` | Starts at 0.1.0 |
| `@knowledge/graduate` | `packages/graduate/package.json` | Starts at 0.1.0 |
| `@knowledge/ops` | `packages/ops/package.json` | Starts at 0.1.0 |
| `@knowledge/contracts` | `packages/contracts/package.json` | **Breaking change = MAJOR bump — all consumers must update** |
| `@knowledge/shared` | `packages/shared/package.json` | Starts at 0.1.0 |
| KnowledgeLecture | Speakr upstream version | Track in `speakr/VERSION` or Docker image tag |

**Version rules:**
- **No umbrella version** — products version independently
- **contracts is the coordination point** — a MAJOR bump in contracts means all consuming products must be updated in the same PR or coordinated sprint
- **Pre-1.0** (`0.x.y`): breaking changes bump MINOR, features bump PATCH — move fast
- **Post-1.0** (`1.x.y+`): standard semver — breaking = MAJOR, features = MINOR, fixes = PATCH
- **Docker image tags:** `knowledge-{product}:{version}` (e.g., `knowledge-enroll:0.3.1`)
- **n8n workflows:** versioned via `metadata.json` commit SHA, not semver (workflows don't have consumers)
- **Speakr:** pinned to a specific upstream version/commit — document in CURRENT-STATE.md when upgrading

**When to bump:**
- Bump version in `package.json` as part of the PR (not a separate commit)
- Conventional Commits drive the bump type: `feat()` = MINOR, `fix()` = PATCH, `feat()!` or `BREAKING CHANGE:` = MAJOR
- Use `npm version {major|minor|patch} --no-git-tag-force` or edit manually — no automated release tooling in MVP

**Cross-product version coordination:**
- When `@knowledge/contracts` has a breaking change, the PR must update ALL consuming products
- `docs/INTEGRATION-STATUS.md` tracks which contract version each product depends on
- Deploy order matters: contracts → shared → products (Enroll, College, Graduate, Ops)

#### Linting & Formatting
- ESLint ^9.39.2 flat config — run on all TypeScript overlay code
- Prettier ^3.8.1 — format on save, no debates on style
- Do NOT lint Speakr's Python code — Speakr has its own standards
- n8n workflow JSON is not linted — validate structure via tests instead
- Import boundaries enforced: packages cannot import from sibling packages except through `@knowledge/contracts` and `@knowledge/shared`

#### Code Organization
- Product boundaries = directory boundaries — never mix KnowledgeEnroll code into KnowledgeCollege directories
- Shared types/contracts only in `packages/contracts/`
- Shared utilities only in `packages/shared/`
- Speakr extensions (if any) in a clearly marked directory — never in Speakr's own source tree
- No barrel exports (`index.ts`) from packages except `contracts` — import specific files

#### Error Handling Pattern
```typescript
// Product boundary errors — always wrap with context
throw new KnowledgeError('ENROLL_RSS_FETCH_FAILED', {
  channelId,
  feedUrl,
  cause: originalError,
});
```
- Product-prefixed error codes: `ENROLL_*`, `COLLEGE_*`, `GRADUATE_*`, `OPS_*`
- Never swallow errors silently — log + rethrow or log + handle
- Config validation errors on startup = fatal (process.exit(1))

#### Documentation Standards
- n8n workflows include inline comments explaining business logic
- Contract schemas are self-documenting (zod `.describe()` on every field)
- No JSDoc on obvious code — only comment non-obvious decisions
- Every package has a `README.md` with: purpose, dependencies, key files, how to run/test

### Development Workflow & Conversation Discipline

#### PR-Scoped Conversations (CRITICAL)
- **One branch → one PR → one Claude Code conversation → one concern**
- When the PR merges, the conversation is done — start fresh for next work
- Conversation naming: `#{issue-number}-{kebab-slug}` (e.g., `#42-rss-monitor`)
- This defeats context window exhaustion — conversations never grow beyond one feature's scope

#### Git Worktrees (Parallel Development)
- Each active conversation gets its own git worktree (physical directory)
- Window/terminal title = feature name for visual identification
- Create worktree: `git worktree add ../knowledge-{slug} feature/{issue}-{slug}`
- Clean up after PR merge: `git worktree remove ../knowledge-{slug}`

#### State Files (Context Chain)
Three files maintain context continuity across PR-scoped conversations:

1. **`CURRENT-STATE.md`** (project root) — living baton passed between conversations
   - What's implemented (with PR references)
   - Recent history (last 3-5 PRs with key decisions)
   - Known issues / deferred items
   - Dependencies between products
   - What's next
   - Updated as the LAST act before closing a conversation

2. **`docs/INTEGRATION-STATUS.md`** — cross-product dependency tracking
   - Per-product readiness status
   - Cross-product contract status (which schemas are stable)
   - Shared infrastructure status (what's available)
   - Blocking dependencies

3. **`docs/ACTIVE-WORK.md`** — parallel conversation registry
   ```markdown
   | Issue | Product | Branch | Worktree | Started |
   |-------|---------|--------|----------|---------|
   | #42 | enroll | feature/42-rss | knowledge-rss-42 | 2026-02-15 |
   | #44 | ops | feature/44-health | knowledge-health-44 | 2026-02-15 |
   ```
   - Register on conversation startup, deregister on shutdown
   - If another conversation is modifying the same product → warn before proceeding

#### Conversation Startup Ritual
Every implementation conversation begins with:
1. Read `CURRENT-STATE.md` — understand where the project stands
2. Read `docs/ACTIVE-WORK.md` — check for parallel work conflicts
3. Read `docs/INTEGRATION-STATUS.md` — understand cross-product state
4. Establish scope anchor (see below)
5. Register in `ACTIVE-WORK.md`

#### Conversation Shutdown Ritual
Every conversation ends with:
1. Commit all work
2. Update `CURRENT-STATE.md` with what was accomplished, decisions made, what's next
3. Deregister from `docs/ACTIVE-WORK.md`
4. If PR is ready, create it

#### Scope Anchoring (Per-Conversation)
At conversation start, establish an immutable scope anchor:
```
SCOPE ANCHOR:
- Issue: #42 — KnowledgeEnroll RSS Monitor
- Product: KnowledgeEnroll
- Branch: feature/42-rss-monitor
- Authorized directories: packages/enroll/, packages/contracts/, n8n-workflows/enroll-*
- Acceptance Criteria: [list from issue]
```
- The scope anchor is SET ONCE and does not change
- Every proposed change is evaluated against this anchor

#### Scope Drift Detection
When the AI detects work outside the scope anchor (touching unauthorized directories, implementing features not in the ACs, or addressing a different issue):

```
⚠️ SCOPE CHECK: This sounds outside this conversation's scope.
This conversation: #42 — KnowledgeEnroll RSS Monitor
Proposed work: packages/ops/

Options:
1. [Handoff] — Update state files, generate handoff summary for new conversation
2. [Backlog] — Create GitHub issue, stay focused on current work
3. [Route to active] — Another conversation is working on that area. Add there?
4. [Continue] — Override, proceed but log scope expansion
```

- Scope check is **per-conversation**, not per-project
- Five conversations may run simultaneously — each guards its own boundaries
- "While we're at it" is a drift trigger

#### Commit Guardrails
AI prompts for commits at natural checkpoints (non-blocking):
- After completing a logical unit (function, schema, test passing)
- Before switching concerns within an issue
- Before running test suite
- Before any destructive operation (file deletion, DB migration)
- After ~15 minutes of active work without a commit
- Auto-suggested message using Conventional Commits: `feat(enroll): add RSS polling interval config`

#### n8n Workflow Version Control
n8n workflows are version-controlled in repo and deployed via REST API:
```
n8n-workflows/{product}-{purpose}/
  workflow.json       # The actual workflow definition
  README.md           # What it does, triggers, dependencies
  metadata.json       # { n8nWorkflowId, lastDeployedCommit, lastDeployedAt }
```
- Deploy via n8n REST API: `PUT /api/v1/workflows/:id`
- Claude Code calls the deploy script directly — no manual copy/import
- `metadata.json` tracks deployed version — compare against HEAD to detect drift
- Deploy verification checks `metadata.json` commit against running workflow version

#### Response Format

**Implementation conversations** use a response footer at the BOTTOM of every response (max 8 lines):
```
---
📍 #42 KnowledgeEnroll RSS Monitor | feature/42-rss
✅ This response: [what was completed]
⏭️ Next: [immediate next step]
📊 Context: ~XX% used
```

**Conversation checkpoint** (on demand via `status` or every ~5 responses):
- Progress against each acceptance criterion
- Files modified this conversation
- Branch/commit status
- Time active

**Context % as break signal:** At 60%+ context usage, append warning to wrap up. At 75%+, begin shutdown ritual.

### Critical Don't-Miss Rules

#### Principles
- **Every human review rejection is a system failure.** If automation could have caught it, add a test so it does next time.
- **Every compaction is a documentation failure.** If you needed that context, it should have been in a state file.
- **Every scope drift is a conversation discipline failure.** Build guardrails, not willpower.
- **Product boundaries are hard boundaries.** Do not cross-pollinate code between packages.
- **Speakr is a dependency, not our code.** Treat it like a third-party library.

#### Absolute Rules
- Never deploy to Stark or localhost — containers go to Banner (10.0.0.33) or Hulk (10.0.0.32)
- Never use `localhost` or `127.0.0.1` in URLs — use domain or VM IP
- Never skip deploy verification gate — no human review without health check passing
- Never advance from Phase 3 (tests) without verifying tests actually FAIL
- Never commit secrets or API keys — use env vars from shared location
- Never modify Speakr source without clear justification and AGPL compliance note
- Never import directly between sibling packages — go through `@knowledge/contracts` or `@knowledge/shared`
- Scope anchor is immutable — once set, it does not change within a conversation

#### Cross-Project Learning
When this project discovers improvements to workflow, conventions, or tooling:
1. Capture the lesson in the herding protocol input format (problem → solution → applies-to → files-to-update)
2. Create portable prompts for other projects when the improvement is workflow-related
3. The Infrastructure project's herding protocol propagates lessons across all NLF projects

---

## Usage Guidelines

**For AI Agents:**
- Read this file before implementing any code
- Follow ALL rules exactly as documented
- When in doubt, prefer the more restrictive option
- Read state files (CURRENT-STATE.md, ACTIVE-WORK.md, INTEGRATION-STATUS.md) on conversation startup
- Establish scope anchor before writing any code

**For Humans:**
- Keep this file lean and focused on agent needs
- Update when technology stack changes or new conventions are established
- Review periodically for outdated rules
- Remove rules that become obvious over time

Last Updated: 2026-01-31
