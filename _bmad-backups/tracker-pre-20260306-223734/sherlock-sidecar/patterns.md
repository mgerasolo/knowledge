# Sherlock Pattern Database

Recurring issues extracted from case-log analysis.

## Pattern Categories

### Config Drift
<!-- Patterns where running config diverges from source of truth -->

### State Management
<!-- Patterns involving React state, Docker context, agent state -->

### Missing Enforcement
<!-- Patterns where process exists but isn't enforced -->

### Build/Deploy
<!-- Patterns in CI/CD, stale artifacts, wrong targets -->

### Timing/Race Conditions
<!-- Patterns involving async operations, batching, hooks -->

### External Service
<!-- Patterns with webhooks, APIs, third-party services -->

## Pattern Recognition Rules

When investigating, match symptoms against these patterns:

| Pattern Tag | Symptom Keywords | Typical Root Cause |
|-------------|------------------|-------------------|
| `dns-routing` | 404, domain, traefik, unreachable | DNS rewrite missing or misconfigured |
| `docker-context` | wrong containers, wrong host | Docker context not switched |
| `config-drift` | works in git, fails in prod | Server config diverged from repo |
| `stale-build` | old behavior, changes not applied | Dist files not rebuilt |
| `hook-race` | intermittent, timing-dependent | Async operation ordering |

<!-- Patterns added as they're identified -->
