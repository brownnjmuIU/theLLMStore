import json
import os
import shutil
import subprocess
import tempfile

try:
    from faster_whisper import WhisperModel
except Exception:
    WhisperModel = None


def _transcribe_video(temp_video_path: str, duration_seconds: float | None) -> tuple[str, str | None]:
    """
    Return (transcript_text, transcript_error). Never raises.
    Keeps MVP fallback-safe by skipping long videos and missing dependencies.
    """
    if WhisperModel is None:
        return "", "faster-whisper not installed in current environment"

    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        return "", "ffmpeg not installed"

    if duration_seconds and duration_seconds > 900:
        return "", f"video too long for MVP local transcription ({duration_seconds:.1f}s > 900s)"

    temp_audio_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as audio_tmp:
            temp_audio_path = audio_tmp.name

        extract_audio_cmd = [
            ffmpeg_path,
            "-v",
            "error",
            "-y",
            "-i",
            temp_video_path,
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "wav",
            temp_audio_path,
        ]
        extract_result = subprocess.run(
            extract_audio_cmd, capture_output=True, text=True, check=False
        )
        if extract_result.returncode != 0:
            return "", f"ffmpeg audio extraction failed: {extract_result.stderr.strip() or 'Unknown error'}"

        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, _info = model.transcribe(temp_audio_path, vad_filter=True)
        transcript_text = " ".join((seg.text or "").strip() for seg in segments).strip()
        if not transcript_text:
            return "", "no speech text detected"
        return transcript_text, None
    except Exception as exc:
        return "", str(exc)
    finally:
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)


def extract_text_from_video(file_bytes: bytes) -> dict:
    """
    Extract video metadata from video bytes.
    Transcript support can be added later (optional Whisper path).

    Returns dict with text and page_count for compatibility with existing pipeline.
    """
    lines = ["Video File"]
    lines.append(f"File Size (bytes): {len(file_bytes)}")

    ffprobe_path = shutil.which("ffprobe")
    transcript_text = ""
    transcript_error = None

    if ffprobe_path is None:
        lines.append("")
        lines.append("Metadata:")
        lines.append("[ffprobe not installed - metadata extraction unavailable in this build]")
        lines.append("")
        lines.append("Transcript:")
        lines.append("[Transcript unavailable: ffprobe missing]")
        return {
            "text": "\n".join(lines).strip(),
            "page_count": None,
            "transcript_text": transcript_text,
        }

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
            lines.append("[Transcript unavailable: ffprobe failed]")
            return {
                "text": "\n".join(lines).strip(),
                "page_count": None,
                "transcript_text": transcript_text,
            }

        data = json.loads(result.stdout)
        duration_seconds = None
        try:
            duration_seconds = float(data.get("format", {}).get("duration", 0) or 0)
        except Exception:
            duration_seconds = None

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

        if not audio_streams:
            transcript_text = ""
            transcript_error = "no audio stream detected in video"
        else:
            transcript_text, transcript_error = _transcribe_video(temp_path, duration_seconds)

        lines.append("")
        lines.append("Transcript:")
        lines.append(transcript_text if transcript_text else "[No transcript text detected]")
        if transcript_error:
            lines.append(f"Transcript Error: {transcript_error}")

    except Exception as exc:
        lines.append("")
        lines.append("Metadata:")
        lines.append(f"[video metadata extraction error] {exc}")
        lines.append("")
        lines.append("Transcript:")
        lines.append("[Transcript unavailable due to extractor error]")
        transcript_error = str(exc)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

    return {
        "text": "\n".join(lines).strip(),
        "page_count": None,
        "transcript_text": transcript_text,
    }
