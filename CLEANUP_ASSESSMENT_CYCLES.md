# Circular Dependency Assessment

Branch: `worktree-agent-a8533bcf`
Date: 2026-04-21

## Scope

Static analysis across two Python packages (`backend/app`, `backend/wonderwall`) and
the frontend (`frontend/src`, Vue 3 + Vite).

## Tools Run

1. `pycycle --here` inside `backend/` and `backend/wonderwall/` — no cycles reported.
2. Custom AST-based cycle detector (top-level imports + deferred/in-function imports,
   handling relative imports). Detected one self-import false positive
   (`wonderwall.clock` package importing its own `clock.py` submodule — that's the
   standard `from .clock import Clock` idiom, not a real cycle).
3. `npx madge --circular --extensions js src/` on the frontend: **No circular
   dependency found** for JS. Madge cannot parse this project's `.vue` SFC blocks
   (it tries Babel on the whole `<template>`), so `.vue` files were cross-checked
   manually via `grep`. Every `.vue` file imports only from `api/`, `store/`,
   `utils/`, and other components with a clear hierarchy (views → components → api);
   no back-edges.
4. Grep for `TYPE_CHECKING` imports, `importlib.import_module`, and function-local
   `from ..` imports.

## Cycles Found

### CYCLE-1: `wonderwall.social_agent` package self-import loop — **HIGH CONFIDENCE FIX**

Graph:

```
wonderwall.social_agent (__init__.py)
  ├─ imports SocialAgent from .agent        (line 14)
  ├─ imports AgentGraph  from .agent_graph  (line 15)
  └─ imports agents_generator               (line 16)
         └─ from wonderwall.social_agent import AgentGraph, SocialAgent  (line 28)
               └─ RE-ENTERS wonderwall.social_agent.__init__ (partially-loaded)
```

This works today only because `__init__.py` imports `SocialAgent` and `AgentGraph`
**before** it imports `agents_generator`. If anyone reorders `__init__.py` the
whole package breaks. Classic fragile "it works by luck of ordering" cycle.

**Fix (implemented):** in `agents_generator.py`, import directly from the sibling
submodules:

```python
from wonderwall.social_agent.agent import SocialAgent
from wonderwall.social_agent.agent_graph import AgentGraph
```

This removes the re-entry into the package's `__init__.py` and makes the
dependency order explicit.

Confidence: **HIGH** — pure mechanical rewrite, preserves public API
(`wonderwall.social_agent.generate_*` still exposes the same symbols), no behavior
change.

### CYCLE-2: `wonderwall.social_agent.agent` ↔ `wonderwall.social_agent.agent_graph` — **LEGITIMATE, KEEP TYPE_CHECKING GUARD**

Graph:

```
wonderwall.social_agent.agent
  └─ TYPE_CHECKING: from wonderwall.social_agent import AgentGraph
wonderwall.social_agent.agent_graph
  └─ from wonderwall.social_agent.agent import SocialAgent  (runtime)
```

`SocialAgent` only needs `AgentGraph` as a type annotation. The `TYPE_CHECKING`
guard is already the correct fix for this pattern. Left as-is (this is the
textbook solution for mutual type dependencies).

Confidence: **HIGH** — leave it.

## Deferred / function-local imports that are NOT cycles

These lazy imports were inspected and confirmed not to be breaking a cycle; they
are either (a) optional providers, (b) Flask factory pattern, or (c) just a
redundant re-import that duplicates a module-level import. Not fixed to minimize
unrelated churn, but noted for future cleanup:

| Location | Status |
| --- | --- |
| `app/__init__.py` — inner imports inside `create_app()` | Flask factory idiom, keep |
| `app/utils/llm_client.py` — `from .claude_code_client import ClaudeCodeClient` | Optional provider; `claude_code_client` does not import back |
| `app/utils/llm_client.py` line 249 — `from .trace_context import TraceContext` | Redundant; already imported at module top (line 17). No cycle. |
| `app/services/graph_tools.py` — `from .simulation_runner import SimulationRunner` | `simulation_runner` does not import `graph_tools`. No cycle. |
| `app/storage/neo4j_storage.py` — `from .reasoning_trace import ReasoningTraceRecorder` | `reasoning_trace` has zero internal deps. No cycle. |
| `app/api/report.py` lines 821, 870 — `from ..services.graph_tools import GraphToolsService` | Redundant; imported at module top (line 14). No cycle. |
| `app/api/settings.py` line 103 — `from ..utils.llm_client import LLMClient` | No cycle. |
| `app/api/observability.py` lines 47/145/177/253 — `from ..utils.event_logger import LOG_DIR` | Redundant; already imported at line 21. No cycle. |
| `app/api/simulation.py` — `from ..services.push_notification_service import …` (x3), `from ..models.task import TaskManager` (x3), `from ..config import Config` (x3) | Redundant at best, but `push_notification_service` imports from multiple places and these are inside request handlers — likely started as lazy-for-test-fixture. No cycle. |
| `app/services/report_agent.py` — `from ..utils.run_summary import generate_run_summary` | `run_summary` is leaf. No cycle. |
| `app/services/simulation_runner.py` — `from .push_notification_service import …` | No cycle. |
| `wonderwall.social_agent.agent` TYPE_CHECKING | See CYCLE-2, keep |

## Frontend

No circular dependencies detected. Frontend dependency graph is strictly layered:

```
main.js → router → views/*.vue → components/*.vue → api/*.js → api/index.js
                                                 ↘ utils/markdown.js
                                                 ↘ store/pendingUpload.js
```

`components` never import `views`, `api` never imports `components`, `store`
never imports anything else. Clean hierarchy.

## Summary

- **1 real cycle found** (`CYCLE-1`) and **fixed** with a 3-line change to one file.
- **1 TYPE_CHECKING-guarded mutual type reference** (`CYCLE-2`) — correct as-is,
  no change.
- **Frontend** — no cycles.
- Many in-function imports exist across the backend; the ones inspected are not
  breaking cycles and are either Flask factory idiom, optional-provider lazy
  loading, or plain redundancy. Flagged above for human review but NOT touched.
