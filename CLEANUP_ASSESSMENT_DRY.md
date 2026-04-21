# Deduplication / DRY Assessment

Worktree branch: `worktree-agent-a93ae49b`
Scope: `backend/app/{api,services,storage,utils,models}`, `backend/scripts/`, `backend/wonderwall/`, `frontend/src/`.

## Methodology

- Manual survey with Grep/Read across the backend (~700 py files) and frontend (~30 Vue/JS files).
- Looked for: helpers copy-pasted across files, near-identical blocks, repeated boilerplate in routes, identical small utilities.
- Validated baseline with `pytest --collect-only` (79 tests collected) and `vite build`.

---

## Findings

### HIGH CONFIDENCE (implemented)

1. **Three separate sliding-window per-IP rate limiters in `backend/app/api/simulation.py`**
   — `_scenario_rate_limited` (l.161), `_ask_rate_limited` (l.423), `_trending_rate_limited` (l.686).
   Near-line-for-line duplicates; only the module-level config (window, max-calls, hits-dict) varies.
   **Consolidated** into a single helper in a new local helper module, one call site each.
   Call sites: 3. Low risk — pure in-memory check with identical semantics.

2. **Two separate LRU caches (scenario, ask) in `backend/app/api/simulation.py`**
   — `_scenario_cache_get/put` (l.181-203), `_ask_cache_get/put` (l.440-461).
   Identical logic on distinct dicts + order lists. **Consolidated** into a small `LruCache`
   helper class; the trending TTL cache is left alone (different semantics — time-based eviction).
   Call sites: 2 distinct caches × (get + put) = 4.

3. **`client_ip` extraction block copied 3× in `simulation.py`**
   — same `X-Forwarded-For` + `remote_addr` fallback. **Consolidated** into `_client_ip()`.
   Call sites: 3.

4. **Frontend `truncateText` / `truncate` helpers duplicated in 4 components**
   — `HistoryDatabase.vue` (l.748), `Step4Report.vue` (l.1913), `Step3Simulation.vue::truncateContent`
   (l.1337), `ReplayView.vue::truncate` (l.443). All are `text.length > max ? text.slice(0,max)+'…' : text`.
   **Consolidated** into `frontend/src/utils/text.js::truncate()`. Replaced all 4 call sites.
   `Step2EnvSetup.vue::truncateBio` is a *different* function (trailing ellipsis + word boundary) — **left alone**.

### MEDIUM CONFIDENCE (left for human review)

1. **~220 `jsonify({"success": False, "error": ...}), 4xx/5xx` patterns across `api/*.py`.**
   Tempting, but each call site has slightly different contextual logging, status codes, and extra
   fields. A `_error(msg, code)` helper would shave boilerplate but would need careful mapping of
   error-code conventions. Recommend a focused pass by a human after consolidating error message
   conventions first.

2. **~66 `traceback.format_exc()` leaks in error bodies.**
   Many endpoints return the full traceback to clients — not just repetitive, but arguably a
   security smell. A helper `_server_error(exc)` that logs + returns a sanitized body would both
   DRY and fix the leak. Worth doing, but a behavior change (clients may rely on the traceback
   today).

3. **`validate_simulation_id` try/except boilerplate inside handlers.**
   Repeats in ~7 spots. A `@requires_simulation_id` decorator would centralize it. Only medium
   because the current `before_request` hook handles URL-path ids and the POST-body variants have
   slightly different shapes. Worth a dedicated refactor pass.

4. **`storage = current_app.extensions.get('neo4j_storage')` + null-check repeated ~13 times.**
   Could become a `@requires_neo4j_storage` decorator or a `get_neo4j_storage_or_503()` helper.
   Low-effort win but changes the function signature contract (injection vs. lookup) — needs an
   owner's sign-off.

5. **Front-end `formatTime` variants in 6+ components.**
   Nearly identical (`new Date(ts).toLocaleTimeString(...)`) but differ in format flags and
   error handling. Consolidating to `frontend/src/utils/time.js` is feasible but would require
   per-call-site review to preserve display differences. Not worth the risk in an automated pass.

6. **`LLMClient._emit_llm_event` caller-stack-walk logic duplicated inside `chat()` kwargs
   construction (l.240-247).**
   The "walk up the stack to find the first non-llm-client frame" block appears twice.
   A `_detect_caller()` helper would DRY it — low confidence because it touches hot LLM path.

### LOW CONFIDENCE (not worth it)

- **`formatDate` / `formatDateTime`** variants: deliberately different formats per surface.
  Unifying would harm UX consistency rather than help.
- **API client files (`frontend/src/api/*.js`)**: per-resource files are already thin; each
  endpoint function is 3-4 lines, already going through the shared `service` instance.
  Further abstraction would obscure, not clarify.
- **`RetryableAPIClient` + `retry_with_backoff` in `backend/app/utils/retry.py`**: three overlapping
  retry helpers, but each has meaningfully different ergonomics (decorator vs. class vs. async).
  Left alone.
- **Vue component base classes**: the `Step1–5` wizard steps have superficially similar structures
  but different concerns; a base component would impose a shape that fights the existing code.
- **Similar Neo4j query patterns in storage layer**: flagged by inspection but each query has
  non-trivial structural differences — attempting a generic `run_cypher_and_format()` would
  create a premature abstraction.

---

## Net impact of the implemented pass

- **Lines removed (net):** ~90 lines across `backend/app/api/simulation.py` and frontend components.
- **New files:** 1 — `frontend/src/utils/text.js`; new helpers added to existing simulation.py (private module-level, no new import surface).
- **Public API surface:** unchanged.
- **Tests:** `pytest --collect-only` still collects 79 tests; `vite build` succeeds.
