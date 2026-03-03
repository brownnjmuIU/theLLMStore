import json
import os
import shutil
import subprocess
import tempfile


def extract_text_from_video(file_bytes: bytes) -> dict:
    """
    Extract video metadata from video bytes.
    Transcript support can be added later (optional Whisper path).

    Returns dict with text and page_count for compatibility with existing pipeline.
    """
    lines = ["Video File"]
    lines.append(f"File Size (bytes): {len(file_bytes)}")

    ffprobe_path = shutil.which("ffprobe")
    if ffprobe_path is None:
        lines.append("")
        lines.append("Metadata:")
        lines.append("[ffprobe not installed - metadata extraction unavailable in this build]")
        lines.append("")
        lines.append("Transcript:")
        lines.append("[Transcript not enabled in this build yet]")
        return {"text": "\n".join(lines).strip(), "page_count": None}

    temp_path = None
    try:
        # Start with mp4 suffix for probing; actual bytes determine parse success
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp.write(file_bytes)
            temp_path = tmp.name

        cmd = [
            ffprobe_path,
            "-v", "error",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            temp_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            lines.append("")
            lines.append("Metadata:")
            lines.append(f"[ffprobe failed] {result.stderr.strip() or 'Unknown error'}")
            lines.append("")
            lines.append("Transcript:")
            lines.append("[Transcript not enabled in this build yet]")
            return {"text": "\n".join(lines).strip(), "page_count": None}

        data = json.loads(result.stdout)

        lines.append("")
        lines.append("Format Metadata:")
        fmt = data.get("format", {})
        for key in ["format_name", "duration", "size", "bit_rate"]:
            if key in fmt:
                lines.append(f"{key}: {fmt[key]}")

        video_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
        audio_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]

        if video_streams:
            v = video_streams[0]
            lines.append("")
            lines.append("Video Stream:")
            for key in ["codec_name", "width", "height", "avg_frame_rate", "pix_fmt"]:
                if key in v:
                    lines.append(f"{key}: {v[key]}")

        if audio_streams:
            a = audio_streams[0]
            lines.append("")
            lines.append("Audio Stream:")
            for key in ["codec_name", "sample_rate", "channels"]:
                if key in a:
                    lines.append(f"{key}: {a[key]}")

        lines.append("")
        lines.append("Transcript:")
        lines.append("[Transcript not enabled in this build yet]")

    except Exception as exc:
        lines.append("")
        lines.append("Metadata:")
        lines.append(f"[video metadata extraction error] {exc}")
        lines.append("")
        lines.append("Transcript:")
        lines.append("[Transcript not enabled in this build yet]")
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

    return {"text": "\n".join(lines).strip(), "page_count": None}
