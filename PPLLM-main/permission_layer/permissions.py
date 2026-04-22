import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, Optional


DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "access_log.db")
DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "permissions_config.json")


@dataclass
class AccessRequest:
    agent_id: str
    action: str
    resource_type: str
    resource_id: str
    metadata: Optional[Dict[str, Any]] = None


class PermissionManager:
    """
    Minimal permission + logging layer for a personalized LLM stack.

    - Permissions are defined in a JSON config file.
    - All access attempts are logged in a SQLite database.
    - Can be used via explicit `check_access` calls or decorators.
    """

    def __init__(
        self,
        config_path: str = DEFAULT_CONFIG_PATH,
        db_path: str = DEFAULT_DB_PATH,
    ) -> None:
        self.config_path = config_path
        self.db_path = db_path
        self._config = self._load_config()
        self._init_db()

    # ----------------------
    # Config handling
    # ----------------------
    def _load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            # Minimal default config; user is expected to edit the JSON file.
            default = {
                "agents": {},
                "default_policy": "deny",
            }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(default, f, indent=2)
            return default

        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def reload_config(self) -> None:
        """Reload permissions from disk."""
        self._config = self._load_config()

    # ----------------------
    # DB handling
    # ----------------------
    def _init_db(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS access_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_utc TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    metadata_json TEXT
                )
                """
            )
            conn.commit()

    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    # ----------------------
    # Core permission logic
    # ----------------------
    def check_access(self, request: AccessRequest) -> bool:
        """
        Check whether an agent is allowed to perform an action on a resource.
        Also logs the decision.
        """
        decision, reason = self._evaluate_policy(request)
        self._log_access(request, decision, reason)
        return decision == "allow"

    def _evaluate_policy(self, request: AccessRequest) -> (str, str):
        agents_cfg = self._config.get("agents", {})
        agent_cfg = agents_cfg.get(request.agent_id)

        if not agent_cfg:
            return "deny", "unknown_agent"

        resources_cfg = agent_cfg.get("resources", {})
        resource_type_cfg = resources_cfg.get(request.resource_type, {})

        allowed_actions_cfg = resource_type_cfg.get("actions", {})
        allowed_resources = allowed_actions_cfg.get(request.action, [])

        if "*" in allowed_resources:
            return "allow", "wildcard_resource"

        if request.resource_id in allowed_resources:
            return "allow", "explicit_resource"

        # Fallback to agent-level default if present
        agent_default = agent_cfg.get("default_policy")
        if agent_default in ("allow", "deny"):
            return agent_default, "agent_default_policy"

        # Global default
        global_default = self._config.get("default_policy", "deny")
        return global_default, "global_default_policy"

    def _log_access(self, request: AccessRequest, decision: str, reason: str) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        metadata_json = (
            json.dumps(request.metadata, default=str) if request.metadata else None
        )

        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO access_log (
                    ts_utc,
                    agent_id,
                    action,
                    resource_type,
                    resource_id,
                    decision,
                    reason,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ts,
                    request.agent_id,
                    request.action,
                    request.resource_type,
                    request.resource_id,
                    decision,
                    reason,
                    metadata_json,
                ),
            )
            conn.commit()

    # ----------------------
    # Decorator helpers
    # ----------------------
    def require_permission(
        self,
        agent_id: str,
        action: str,
        resource_type: str,
        resource_id_getter: Optional[Callable[..., str]] = None,
        metadata_getter: Optional[Callable[..., Dict[str, Any]]] = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Decorator to guard a function with a permission check.

        Parameters
        ----------
        agent_id:
            Logical ID of the calling agent (e.g. "file_aggregator", "extractor", "chatgpt_client").
        action:
            Logical operation, e.g. "read", "write", "embed", "serve_to_llm".
        resource_type:
            Category of resource, e.g. "file_json", "embedding", "raw_file".
        resource_id_getter:
            Optional function that receives (*args, **kwargs) and returns the concrete
            resource_id string for this call. If omitted, the decorator expects a
            `resource_id` keyword argument when the function is called.
        metadata_getter:
            Optional function that receives (*args, **kwargs) and returns a metadata
            dict to be logged together with the access attempt.
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                if resource_id_getter is not None:
                    resource_id = resource_id_getter(*args, **kwargs)
                else:
                    resource_id = kwargs.get("resource_id")
                    if resource_id is None:
                        raise ValueError(
                            "resource_id must be provided as a keyword argument "
                            "or via resource_id_getter."
                        )

                metadata = metadata_getter(*args, **kwargs) if metadata_getter else None

                request = AccessRequest(
                    agent_id=agent_id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=str(resource_id),
                    metadata=metadata,
                )

                if not self.check_access(request):
                    raise PermissionError(
                        f"Access denied for agent '{agent_id}' on "
                        f"{resource_type}:{resource_id} for action '{action}'."
                    )

                return func(*args, **kwargs)

            return wrapper

        return decorator


# ----------------------
# Example usage helpers
# ----------------------
def demo_example() -> None:
    """
    Simple end-to-end demo showing how the PermissionManager could be used
    between:
      - a file aggregator
      - an extraction / embedding tool
      - an LLM consumer

    Run this module directly to see it in action:
      python -m permission_layer.permissions
    """

    pm = PermissionManager()

    @pm.require_permission(
        agent_id="file_aggregator",
        action="read",
        resource_type="raw_file",
        resource_id_getter=lambda path: path,
        metadata_getter=lambda path: {"stage": "aggregation"},
    )
    def aggregate_file(path: str) -> str:
        return f"aggregated:{path}"

    @pm.require_permission(
        agent_id="extractor_tool",
        action="embed",
        resource_type="file_json",
        resource_id_getter=lambda json_path: json_path,
        metadata_getter=lambda json_path: {"stage": "extraction"},
    )
    def extract_embeddings(json_path: str) -> str:
        return f"embeddings_for:{json_path}"

    @pm.require_permission(
        agent_id="chatgpt_client",
        action="serve_to_llm",
        resource_type="embedding",
        resource_id_getter=lambda embedding_id: embedding_id,
        metadata_getter=lambda embedding_id: {"stage": "llm_consumption"},
    )
    def serve_to_llm(embedding_id: str) -> str:
        return f"served:{embedding_id}"

    # Example pipeline
    aggregated = aggregate_file("/data/user123/file1.pdf")
    embeddings = extract_embeddings("/data/user123/file1.json")
    _served = serve_to_llm(f"embedding:{aggregated}:{embeddings}")

    print("Demo pipeline executed. Check the SQLite log at:", DEFAULT_DB_PATH)


if __name__ == "__main__":
    demo_example()

