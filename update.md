# MiroShark — Session Update (2026-03-26)

## What we did

Started from a deep dive on how MiroShark works, then systematically improved every layer of the simulation engine across a single session.

### 1. Cross-Platform Round Memory

Built `round_memory.py` — a sliding-window context system that gives every agent awareness of what happened across all 3 platforms.

- **Old rounds** get LLM-compacted into 2-3 sentence summaries (background thread, non-blocking)
- **Previous round** shown in full detail (every action, every post)
- **Current round** shows partial data (platforms that already stepped)
- When individual summaries pile up (6+), they get batch-compacted into a narrative paragraph

This means a Polymarket trader in round 8 sees a compressed history of rounds 1-5, full detail of round 7, and live data from Twitter/Reddit in round 8.

### 2. All 3 Platforms Run Simultaneously

Restructured the simulation loop so Twitter, Reddit, and Polymarket execute in parallel via `asyncio.gather()` instead of Polymarket waiting for social media to finish. Each platform sees previous-round context from all others. Reduced per-round time by ~40%.

### 3. Polymarket Overhaul

**Before**: Agents created random markets, all started at 50/50, commented instead of trading, never sold, traded in isolation from social media.

**After**:
- Single LLM-generated prediction market that captures the core question of the simulation
- Non-50/50 initial pricing via constant-product AMM (LLM sets the starting probability)
- Agents can only buy, sell, or do nothing — no comments, no market creation
- Traders see actual Twitter/Reddit posts in their observation prompt (not just sentiment numbers)
- P&L tracking with sell signals ("PRICE NEAR MAX — consider taking profit")
- Social media context injected directly into the trading observation, not buried in system message

**Tested result**: 18 trades on one market, price moved from $0.35 to $0.27, agents bought both YES and NO, profit-taking and loss-cutting both occurred naturally. Best trader made +$558 by going contrarian.

### 4. Performance Optimizations

| What | Before | After |
|---|---|---|
| Neo4j entity/relation writes | 1 transaction each | Batched UNWIND queries (~10x) |
| Graph chunk processing | Sequential | ThreadPoolExecutor parallel (~3x) |
| Config batch generation | Sequential LLM calls | 3 concurrent batches (~3x) |
| Platform execution | Twitter+Reddit parallel, then Polymarket | All 3 parallel (~40% faster per round) |
| Memory compaction | Blocks the round loop | Background thread (zero latency) |

### 5. Prompt Rewrites (every platform)

**Twitter**: Added decision heuristics ("DO_NOTHING is your default — you must have a specific reason to do anything else"), platform culture ("punchy, not formal"), content authenticity ("write like a real person, not an AI"), context priority ordering.

**Reddit**: Differentiated from Twitter — "write in paragraph form, cite sources, upvote = quality not agreement, be willing to change your mind."

**Polymarket**: Position sizing heuristics (small edge = small bet), contrarian psychology ("trade on YOUR beliefs, not the crowd"), explicit social media signal usage section.

**DO_NOTHING tool description**: Changed from "Perform no action" to a compelling 5-line description explaining when and why to skip. Achieved 36% DO_NOTHING rate on Twitter (up from 0%).

### 6. NER Extraction Improvements

- Added 2 few-shot examples showing correct extraction from realistic text
- Added rejection rules: fragments ("NYU dropout"), too-short names ("CO"), descriptive phrases ("a large company"), co-reference duplicates ("Hanson" vs "Robin Hanson")
- Added rule 12: extract a factual summary sentence, not just "Name (Type)"
- Programmatic validation in `_validate_and_clean`: rejects names <=2 chars, single lowercase words, article-prefixed names, descriptive suffixes
- Neo4j now stores NER-extracted summaries instead of "Name (Type)" placeholders

### 7. Persona Generation Improvements

- **Individual vs group detection**: Added keyword matching (`INDIVIDUAL_TYPE_KEYWORDS`) so custom ontology types like "CryptoFounder" and "ElectionForecaster" automatically get the individual template. Unknown types default to individual (safer assumption).
- **Rewrote both prompts**: Individual prompt asks for blind spots, what would change their mind, online behavior specifics. Group prompt asks for controversy handling, red lines, content strategy.
- **Removed numeric fields** (karma, follower_count) from LLM generation — already computed from graph structure.
- **Entity interleaving**: Round-robin by type so individuals come before organizations in generation order.
- **MBTI diversity**: Group prompt explicitly says "not all orgs are ISTJ" with 5 examples.
- **Risk tolerance**: Domain-aware inference (prediction markets = high, stablecoins = low, hash-based variation for generic orgs).

### 8. Web Enrichment

Built `web_enrichment.py` — uses the existing LLM client to research entities when the graph context is thin or the entity is a notable figure.

- Triggers automatically for politicians, CEOs, founders, organizations, etc.
- Configurable: `WEB_SEARCH_MODEL=perplexity/sonar-pro` for grounded web search via OpenRouter
- Caches results per entity name (no duplicate LLM calls)
- Prompt tells the LLM to add NEW information, not repeat what's already in the graph
- Falls back gracefully if LLM is unavailable

### 9. Config Generation Improvements

- **Market generation**: New LLM step generates exactly 1 prediction market from the simulation requirement with an initial probability and reasoning
- **System prompts**: Replaced one-liners with concrete heuristics (timing: "breaking news = short rounds", events: "first poster should be whoever would realistically learn about this first", agents: "institutions post rarely with high influence, activists post heavily")
- **Parallel batch generation**: Up to 3 agent config batches generated concurrently

### 10. Report Agent — Simulation Data Access

**Before**: The report only searched the Neo4j knowledge graph (from the PDF). It had zero access to simulation output — no posts, no comments, no trades, no market prices.

**After**: Two new tools:
- `simulation_feed`: Reads actual posts, comments, and trades from all platforms. Supports filtering by platform, keyword, and round number. Returns agent names, action types, and content.
- `market_state`: Returns Polymarket final state — market prices, complete trade history, trader portfolios with P&L.

Updated the section generation prompt: "START with simulation_feed — this is your PRIMARY data source. QUOTE actual agent posts/comments."

**Tested result**: Report now cites actual trades ("Agent_5 initially sold NO shares at $0.030, then bought 782 NO shares at $0.192") and quotes agent posts ("Augur was designed to be the last one standing").

### 11. Belief Tracking

Replaced naive keyword extraction (`extract_topics_from_requirement`) with an LLM call that produces 2-4 clean debate topics. Before: `["Twitter Reddit", "Polymarket", "Polymarket's", "Focus"]`. After: `["crypto regulation", "prediction market legitimacy", "Polymarket transparency", "media influence on markets"]`.

### 12. Documentation

- `run.md`: Complete reference of all 22 LLM call sites — exact prompts, context fed, temperature, model routing, purpose
- `README.md`: Updated architecture section with cross-platform diagram, performance table, web enrichment docs

---

## Test Results

Ran the full pipeline on a Polymarket article PDF:

| Phase | Time | Output |
|---|---|---|
| PDF parse | <1s | 21K chars |
| Ontology | 15s | 10 entity types, 8 edge types |
| Graph (8 chunks, parallel) | 181s | 21 nodes, 20 edges |
| Profiles (5 entities + web enrichment) | 506s | Rich personas with real-world research |
| Config generation | 28-47s | Smart stances, relevant initial posts, 1 market |
| 3-platform simulation (8 rounds, 6 agents) | 230s | 148 Twitter + 155 Reddit + 64 Polymarket actions |
| Report generation | 263s | 16K chars, 4 sections, cites actual simulation data |

Key metrics from the simulation:
- Twitter DO_NOTHING rate: 36-39%
- Polymarket: 34 buys + 22 sells on single market, price $0.72 → $0.92
- Reddit: 37+ substantive comments with threaded discussion
- Belief tracking: all 4 topics showed convergence or polarization
- Report quotes actual agent posts and trade data

---

## Next Steps

### High Priority

1. **Scheduled events mid-simulation** — The `event_config.scheduled_events` field exists in the config but is never injected during rounds. Adding timed events ("CFTC announces investigation at round 5") would create narrative turning points instead of agents reacting to the same initial posts for 20 rounds. The LLM already generates these during config — they just need to be injected.

2. **Front-end validation** — None of the new features (round memory, single market, improved prompts, web enrichment) have been tested through the Vue UI. The Flask API endpoints may need updates to pass new parameters (simulation_requirement to the profile generator, initial_markets to the simulation runner).

3. **Full end-to-end test via API** — We tested phases separately via scripts. A single run from POST `/api/graph/ontology/generate` through to GET `/api/report/{id}` would validate the integration.

### Medium Priority

4. **Interview tool fix** — The report agent's `interview_agents` tool fails because it looks for profiles in `uploads/simulations/{id}/` but test simulations save elsewhere. In production this works, but a fallback path resolution would make it robust.

5. **Longer simulation stress test (20+ rounds)** — Needed to validate: memory compaction triggering and quality, belief drift over time, sell behavior emerging from price movement, and whether the report agent can handle a larger simulation dataset.

6. **NER re-test** — The rejection rules and summary extraction were built but never re-run on a fresh graph build. Need to verify "NYU dropout", "CO", and "Hanson" duplicates get filtered.

7. **Individual persona diversity** — All tests used a crypto article that produced mostly organization entities. Testing with a political article or policy document would generate more individual personas (politicians, activists, journalists) with very different simulation dynamics.

### Lower Priority

8. **Report charts** — Belief trajectory and market price data exist as JSON. Embedding sparklines or ASCII charts in the report markdown would make it more visual.

9. **Polymarket DO_NOTHING** — Currently 0% on Polymarket (traders always trade). The `activity_level` pre-filter handles this in production, but the prompt could be tuned further for pure LLM-driven inaction.

10. **Cost optimization** — Agent action decisions dominate cost (~98% of LLM calls). Batching multiple agents into one LLM call, or using a cheaper model for "DO_NOTHING likely" rounds, could reduce costs significantly.
