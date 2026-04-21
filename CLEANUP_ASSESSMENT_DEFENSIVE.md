# Cleanup Assessment: Defensive try/except

Scope: `backend/app/`, `backend/scripts/`, `backend/wonderwall/`, `backend/tests/`, `frontend/src/`.

Totals found:
- Python `try:` blocks: 563 across 68 files
- Python `except Exception` clauses: 393 across 61 files
- Python bare `except:` clauses: 4 (across 3 files)
- Frontend `try {` blocks: 107 across 30 files
- Frontend `.catch(() => {})` patterns: 3

This assessment only calls out non-trivial cases. The vast majority of try blocks in this codebase are legitimate boundary handling (HTTP calls, file I/O, LLM calls, DB queries, subprocess, JSON parsing of external input). The cleanup targets clearly defensive wrappers around internal logic that cannot raise or should not be swallowed.

---

## REMOVE / narrow (implemented)

### 1. `backend/app/api/simulation.py:2113-2117` — bare `except:` around string slicing
```python
try:
    created_date = sim_dict.get("created_at", "")[:10]
    sim_dict["created_date"] = created_date
except:
    sim_dict["created_date"] = ""
```
`dict.get("k", "")[:10]` cannot raise. `dict.get` with default returns either the value or `""`; `[:10]` works on any string. Worst case `created_at` is `None` and `None[:10]` would raise TypeError — but the default `""` protects that. Even if it raises, the behavior would be a bug. REMOVE.

### 2. `backend/app/api/simulation.py:4307-4311` — `except Exception` around string slicing
```python
created_date = ""
try:
    created_date = (state.created_at or "")[:10]
except Exception:
    pass
```
`(state.created_at or "")[:10]` cannot raise. REMOVE.

### 3. `backend/app/services/simulation_config_generator.py:553-562` — nested bare `except:` around `json.loads`
```python
try:
    return json.loads(json_str)
except:
    ...
    try:
        return json.loads(json_str)
    except:
        pass
```
`json.loads` can only raise `json.JSONDecodeError` (subclass of `ValueError`). NARROW to `json.JSONDecodeError`. Bare except would also swallow `KeyboardInterrupt`, `SystemExit`.

### 4. `backend/app/services/oasis_profile_generator.py:753-754` — bare `except:` around `json.loads`
Narrowed to `json.JSONDecodeError`.

### 5. `backend/app/utils/claude_code_client.py:113-115` — no file, moved on (this one is `self.client.close()` on a client — KEEP as boundary close).

---

## KEEP (boundary calls) — examples

These were reviewed and left alone:

- All `try` blocks wrapping `open()`, `json.load()`, `json.loads()` on external input, `subprocess.*`, DB cursor ops, HTTP requests, LLM/API calls.
- File handle `.close()` cleanup in `simulation_runner.py` (lines 665-675, 1449-1461).
- Process termination in `mcp_agent_bridge.py:209-210`.
- `resource_tracker._stop()` in `run_parallel_simulation.py:2910-2914` — a noisy internal multiprocessing hack; catching broadly is reasonable.
- Retry/fallback wrappers around LLM calls (all of `simulation_config_generator.py`, `oasis_profile_generator.py`, `web_enrichment.py`) — legitimate boundary handling with recovery logic.
- `except json.JSONDecodeError: continue` in JSONL readers (`observability.py`, `event_logger.py`) — genuine malformed-input handling.
- `socket.getaddrinfo`, `ipaddress.ip_address` calls in SSRF validator (`simulation.py:647-668`) — correctly scoped.
- Round analyzer DB queries (`round_analyzer.py:335, 359, 383, 405, 548`) — query-then-return-empty is defensible analyzer behavior; changing to propagate would alter contract. KEEP but flag as debatable (they hide SQL errors silently).

---

## FLAGGED — behavior-change candidates, not touched

These look suspect but altering them would change observable behavior; leaving them for manual review:

### Silent DB-query swallowing in analyzers
- `backend/wonderwall/social_agent/round_analyzer.py:335, 359, 383, 405, 548` — `except Exception: pass` / `return []`. DB failures silently produce empty results. If the DB is actually broken the analyzer would lie rather than fail.

### `run_parallel_simulation.py` silent lookups
- Lines 936-937, 971-972, 1017-1018 — helpers `_get_post_content`, `_get_user_name` return `None` on any exception. These are called during report generation; silencing DB errors here is questionable but long-standing behavior.
- Lines 1148-1150, 1154-1156, 1222-1224, 1344-1345, 1623-1624, 2281-2282 — agent setup/action injection errors swallowed. Could hide genuine init failures.

### `agent_graph.py:206-210` — `add_edge` errors swallowed
```python
def add_edge(self, agent_id_0, agent_id_1):
    try:
        self.graph.add_edge(agent_id_0, agent_id_1)
    except Exception:
        pass
```
This upstream file is from wonderwall (third-party-ish library). Risky to change; duplicate edges on some backends raise. Leaving.

### Script-level cleanup bypass
- `backend/scripts/director_events.py:120-123` — `_atomic_write_json` errors swallowed during consume-event flow. Could hide genuine disk-full / permission failures.
- `backend/app/services/oracle_seed.py:111-115` — `self.client.close()` failures swallowed. Close failures are usually inessential; leaving.

### Frontend `.catch(() => {})` — intentional optional-feature silencing
- `frontend/src/components/InfluenceLeaderboard.vue:324` — clipboard write fallback; legit.
- `frontend/src/components/Step3Simulation.vue:1526` — optional quality-score fetch; legit.
- `frontend/src/components/HistoryDatabase.vue:821` — optional quality-score fetch; legit.

All three handle genuinely optional features. KEEP.

---

## Summary

Removed/narrowed: 4 clear cases (2 useless wrappers + 3 bare-except narrowings).
Flagged for discussion: ~15 silent-DB-swallowing and silent-cleanup-swallowing cases that look wrong but are load-bearing in current behavior.
Kept (vast majority): boundary handling, LLM call retries, JSON parse of external input, file I/O, process/subprocess, cleanup close() calls.
