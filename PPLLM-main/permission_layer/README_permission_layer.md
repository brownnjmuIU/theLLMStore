## Permissioned Layer MVP for Personalized LLM Stack

This directory contains a minimal **permission + logging layer** that you can plug between:

- **File Aggregator** (your tool)
- **Extraction & Conversion Tool** (Manas’s tool)
- **LLM / Conversational Agent** (e.g. ChatGPT, Gemini client)

Its job is to:

- **Enforce**: check whether an agent is allowed to act on a resource.
- **Log**: record every access attempt (who, what, when, decision).
- **Stay simple**: JSON config + SQLite log, no heavy crypto.

Files:

- `permissions.py` – core logic, decorators, and a small demo pipeline.
- `permissions_config.json` – permission rules for agents.
- `access_log.db` – SQLite database (auto-created) storing access logs.

---

### 1. Conceptual Model

- **Agent**: any tool or external system that wants to access user data.
  - Examples: `file_aggregator`, `extractor_tool`, `chatgpt_client`.
- **Resource**: something to protect.
  - Examples: raw file paths, JSON outputs, embeddings.
- **Action**: what the agent wants to do.
  - Examples: `read`, `embed`, `serve_to_llm`.

The permission layer sits **between** stages:

1. User files → `file_aggregator`  
2. Aggregated JSON → `extractor_tool` (embeddings)  
3. Embeddings → `chatgpt_client` (LLM platform)  

Every such step is funneled through a **permission check**:

- If allowed → operation proceeds; decision is logged.
- If denied → operation is blocked with `PermissionError`; decision is logged.

---

### 2. Permission Config Structure (`permissions_config.json`)

High-level structure:

- **`default_policy`**: global fallback, `"allow"` or `"deny"` (MVP uses `"deny"`).
- **`agents`**: per-agent rules.
  - `default_policy` per agent (optional, overrides global default).
  - `resources` → `resource_type` → `actions` → list of allowed `resource_id`s.

Example (included in this repo):

- `file_aggregator`:
  - Can `read` specific `raw_file` paths.
- `extractor_tool`:
  - Can `embed` specific `file_json` paths.
- `chatgpt_client`:
  - Can `serve_to_llm` **any** `embedding` (via `"*"` wildcard).

You update this JSON file to add/remove agents or resources as your stack grows.

---

### 3. Core Python API (`permissions.py`)

#### 3.1. Key Types

- **`AccessRequest`**:
  - `agent_id` – logical name of the calling agent.
  - `action` – what it's trying to do (`"read"`, `"embed"`, etc.).
  - `resource_type` – category (`"raw_file"`, `"file_json"`, `"embedding"`).
  - `resource_id` – the specific item (e.g., file path, embedding ID).
  - `metadata` – optional dict (stage info, user ID, correlation IDs).

- **`PermissionManager`**:
  - Loads `permissions_config.json` (creates a default if missing).
  - Initializes a SQLite DB at `access_log.db`.
  - API:
    - `check_access(request: AccessRequest) -> bool` – returns `True`/`False` and logs the attempt.
    - `require_permission(...)` – decorator to guard functions.
    - `reload_config()` – hot-reload config from disk.

#### 3.2. How Decisions Are Made

Given an `AccessRequest`:

1. Look up `agent_id` in config:
   - If no entry → **deny** (`unknown_agent`).
2. Find `resource_type` and `action` for that agent.
3. Match `resource_id` against allowed list:
   - If exact match or `"*"` → **allow**.
4. If no explicit match:
   - Use agent's `default_policy` if set.
   - Else use global `default_policy`.

Every decision (allow or deny) is logged with a timestamp and reason.

---

### 4. Logging (`access_log.db`)

The first time you import `PermissionManager`, it creates a SQLite DB and a single table:

- Table: `access_log`
  - `ts_utc` – ISO timestamp in UTC.
  - `agent_id`, `action`, `resource_type`, `resource_id`.
  - `decision` – `"allow"` or `"deny"`.
  - `reason` – why the decision was made (`"explicit_resource"`, `"wildcard_resource"`, `"unknown_agent"`, etc.).
  - `metadata_json` – JSON-encoded metadata (can be `NULL`).

You can inspect logs with any SQLite viewer or via CLI:

```bash
cd permission_layer
python -c "import sqlite3; conn = sqlite3.connect('access_log.db'); \
for row in conn.execute('SELECT ts_utc, agent_id, action, resource_type, resource_id, decision, reason FROM access_log ORDER BY id DESC LIMIT 20'): print(row); conn.close()"
```

This gives you an **audit trail**: who accessed what, when, and whether it was allowed.

---

### 5. Using the Permission Layer in Your Stack

Assume your project structure contains this folder as `permission_layer/`.

#### 5.1. Basic Usage

```python
from permission_layer.permissions import PermissionManager, AccessRequest

pm = PermissionManager()

request = AccessRequest(
    agent_id="extractor_tool",
    action="embed",
    resource_type="file_json",
    resource_id="/data/user123/file1.json",
    metadata={"stage": "extraction", "user_id": "user123"},
)

if pm.check_access(request):
    # proceed with extraction
    ...
else:
    # block or raise
    raise PermissionError("Not allowed to embed this JSON")
```

#### 5.2. Using the Decorator (Recommended)

For cleaner integration, wrap sensitive functions:

```python
from permission_layer.permissions import PermissionManager

pm = PermissionManager()

@pm.require_permission(
    agent_id="extractor_tool",
    action="embed",
    resource_type="file_json",
    resource_id_getter=lambda json_path: json_path,
)
def extract_embeddings(json_path: str):
    # your existing embedding logic here
    ...
```

Now any call to `extract_embeddings("/data/user123/file1.json")` will:

1. Build an `AccessRequest`.
2. Evaluate against `permissions_config.json`.
3. Log the decision in `access_log.db`.
4. Either:
   - Proceed (if allowed), or
   - Raise `PermissionError` (if denied).

You can repeat the same pattern for:

- Aggregator reading raw files.
- LLM client fetching embeddings.

---

### 6. Example End-to-End Demo

`permissions.py` contains a `demo_example()` function that wires up:

- `aggregate_file` (simulated File Aggregator).
- `extract_embeddings` (simulated Extractor).
- `serve_to_llm` (simulated LLM client).

To run it:

```bash
cd permission_layer
python permissions.py
```

This will:

1. Use decorators to guard all three functions.
2. Execute a mini pipeline.
3. Log 3 access events in `access_log.db`.
4. Print a message pointing you to the SQLite log.

You can then query the DB to see the full trace.

---

### 7. How This Fits Your PPLLM Stack

- **Between Aggregator and Extractor**:
  - Protect JSON outputs; only approved extractor agents may read/convert them.
- **Between Extractor and LLM**:
  - Protect embeddings; only approved LLM clients may fetch them.
- **For Future Extensions**:
  - Add user-level scoping (e.g., `user_id` in metadata).
  - Add time-based rules (e.g., temporary tokens).
  - Replace JSON config with a more dynamic policy store.

In short, this MVP gives you a **permissioned layer** that is:

- Explicit (JSON rules).
- Auditable (SQLite logs).
- Pluggable (decorators around your existing functions).

