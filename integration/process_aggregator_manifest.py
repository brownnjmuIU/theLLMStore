import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# --- Permission layer (optional: only active if PPLLM-main is present) ---
_PERMISSION_LAYER_PATH = REPO_ROOT / "PPLLM-main" / "permission_layer"
_pm = None
_AccessRequest = None

if _PERMISSION_LAYER_PATH.exists():
    sys.path.insert(0, str(_PERMISSION_LAYER_PATH.parent))
    try:
        from permission_layer.permissions import AccessRequest as _AccessRequest
        from permission_layer.permissions import PermissionManager
        _pm = PermissionManager(
            config_path=str(_PERMISSION_LAYER_PATH / "permissions_config.json"),
            db_path=str(_PERMISSION_LAYER_PATH / "access_log.db"),
        )
        print("[permissions] Permission layer loaded.")
    except Exception as _e:
        print(f"[permissions] WARNING: Could not load permission layer: {_e}")
else:
    print("[permissions] WARNING: PPLLM-main not found — running without permission checks.")

from extractors.browser_extractor import (
    extract_text_from_browser_cookies,
    extract_text_from_browser_history,
)
from extractors.docs_extractor import extract_text_from_docx
from extractors.image_extractor import extract_text_from_image
from extractors.pdf_extractor import extract_text_from_pdf
from extractors.platform_extractor import extract_text_from_platform_export
from extractors.pptx_extractor import extract_text_from_pptx
from extractors.video_extractor import extract_text_from_video
from processing.pipeline import process_document
from storage.json_store import save_artifact


IMAGE_TYPES = {"jpg", "jpeg", "png"}
VIDEO_TYPES = {"mp4", "mov"}
DATABASE_TYPES = {"sqlite", "db"}

SENSITIVE_KEYWORDS = {"private", "secret", "password", "bank", "ssn", "confidential"}


def _is_sensitive(filename: str) -> bool:
    name_lower = filename.lower()
    return any(kw in name_lower for kw in SENSITIVE_KEYWORDS)


def _extract_from_path(file_path: Path) -> tuple[str, dict]:
    file_type = file_path.suffix.lower().lstrip(".")
    file_bytes = file_path.read_bytes()

    if file_type == "pdf":
        result = extract_text_from_pdf(file_bytes)
    elif file_type == "docx":
        result = extract_text_from_docx(file_bytes)
    elif file_type == "pptx":
        result = extract_text_from_pptx(file_bytes)
    elif file_type in IMAGE_TYPES:
        result = extract_text_from_image(file_bytes)
    elif file_type in VIDEO_TYPES:
        result = extract_text_from_video(file_bytes)
    elif file_type == "json":
        result = extract_text_from_platform_export(file_bytes)
    elif file_type in DATABASE_TYPES:
        if "cookie" in file_path.name.lower():
            result = extract_text_from_browser_cookies(file_bytes)
        else:
            result = extract_text_from_browser_history(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {file_type or '[no extension]'}")

    return file_type, result


def process_manifest(
    manifest_path: str,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
    process_chunks: bool = True,
) -> dict:
    manifest_file = Path(manifest_path)
    with manifest_file.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    files = manifest.get("files", [])
    results = []

    for entry in files:
        source_path = Path(entry["path"])
        item_result = {
            "source_path": str(source_path),
            "status": "pending",
        }

        try:
            if not source_path.exists() or not source_path.is_file():
                raise FileNotFoundError(f"Source file not found: {source_path}")

            # --- Sensitive file warning ---
            if _is_sensitive(source_path.name):
                print(f"\n[WARNING] '{source_path.name}' looks like it may contain sensitive data.")
                answer = input("  Do you want to process this file? (yes/no): ").strip().lower()
                if answer != "yes":
                    print(f"[permissions] DENIED by user: {source_path.name}")
                    if _pm is not None and _AccessRequest is not None:
                        req = _AccessRequest(
                            agent_id="extractor_tool",
                            action="read",
                            resource_type="sensitive_file",
                            resource_id=str(source_path),
                            metadata={"stage": "extraction", "reason": "user_denied_at_prompt"},
                        )
                        _pm._log_access(req, "deny", "user_denied_at_prompt")
                    item_result["status"] = "denied_by_user"
                    results.append(item_result)
                    continue

            # --- Permission check ---
            if _pm is not None and _AccessRequest is not None:
                request = _AccessRequest(
                    agent_id="extractor_tool",
                    action="read",
                    resource_type="raw_file",
                    resource_id=str(source_path),
                    metadata={"stage": "extraction", "manifest": str(manifest_file)},
                )
                if not _pm.check_access(request):
                    print(f"[permissions] DENIED: {source_path.name}")
                    item_result["status"] = "permission_denied"
                    results.append(item_result)
                    continue
                print(f"[permissions] ALLOWED: {source_path.name}")

            file_type, extracted = _extract_from_path(source_path)
            doc_id, raw_artifact_path = save_artifact(
                filename=source_path.name,
                file_type=file_type,
                text=extracted["text"],
                page_count=extracted.get("page_count"),
            )

            item_result.update(
                {
                    "status": "ingested",
                    "doc_id": doc_id,
                    "raw_artifact_path": raw_artifact_path,
                    "text_length": len(extracted["text"]),
                }
            )

            if process_chunks:
                chunk_result = process_document(
                    file_path=raw_artifact_path,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
                item_result.update(
                    {
                        "status": "chunked",
                        "chunk_output_path": chunk_result["output_path"],
                        "total_chunks": chunk_result["total_chunks"],
                    }
                )
        except Exception as exc:
            item_result.update(
                {
                    "status": "error",
                    "error": str(exc),
                }
            )

        results.append(item_result)

    return {
        "manifest_path": str(manifest_file),
        "total_files": len(files),
        "processed_files": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process a file-selection manifest exported by the aggregator tool."
    )
    parser.add_argument("manifest_path", help="Path to aggregator exported JSON manifest")
    parser.add_argument("--chunk-size", type=int, default=800, help="Chunk size in characters")
    parser.add_argument("--chunk-overlap", type=int, default=100, help="Chunk overlap in characters")
    parser.add_argument(
        "--no-chunk",
        action="store_true",
        help="Only ingest and save raw artifacts without running the chunking pipeline",
    )
    args = parser.parse_args()

    summary = process_manifest(
        manifest_path=args.manifest_path,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        process_chunks=not args.no_chunk,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
