"""Batch transcribe audio/video files under `files/` and save text to `extracted_text/`.

Behavior mirrors the style of `extract_text_from_downloads.py`: for each media file
under `files/` create `extracted_text/<ext>/safe__path.txt` containing the transcription.
"""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
import traceback

load_dotenv()
elevenlabs = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

# Use same layout as extract_text_from_downloads: ROOT is the container directory for this script
ROOT = Path(__file__).resolve().parents[1]
FILES = ROOT / 'files'
OUTDIR = ROOT / 'extracted_text'

MEDIA_EXT = {
    '.mp4', '.mkv', '.mov', '.avi', '.wmv', '.flv', '.webm',
    '.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg'
}

def ensure_out(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

def normalize_transcription(transcription) -> str:
    if isinstance(transcription, bytes):
        return transcription.decode('utf-8', errors='replace')
    if isinstance(transcription, str):
        return transcription
    if isinstance(transcription, dict):
        return transcription.get('text') or transcription.get('transcription') or str(transcription)
    if hasattr(transcription, 'text'):
        return getattr(transcription, 'text')
    return str(transcription)

def process_media_file(path: Path, out_root: Path) -> tuple[bool, str]:
    """Transcribe a single media file and write out a .txt file.

    Returns (ok, message) where message is output path on success, or reason on failure.
    """
    ext = path.suffix.lower()
    rel = path.relative_to(FILES)
    safe_name = str(rel).replace(os.sep, '__')
    out_dir = out_root / (ext.lstrip('.') or 'other')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (safe_name + '.txt')

    if ext not in MEDIA_EXT:
        return False, f'skipped-unhandled-ext({ext})'

    try:
        # skip empty files
        if path.stat().st_size == 0:
            return False, 'skipped-empty-file'

        with path.open('rb') as audio_file:
            transcription = elevenlabs.speech_to_text.convert(
                file=audio_file,
                model_id='scribe_v1',
                tag_audio_events=True,
                language_code='eng',
                diarize=True,
            )

        text = normalize_transcription(transcription) or ''
        ensure_out(out_path)
        out_path.write_text(text, encoding='utf-8')
        return True, str(out_path)
    except Exception as e:
        return False, f'error:{e}\n{traceback.format_exc()}'

def main() -> None:
    if not FILES.exists():
        print('No files/ directory found; nothing to do')
        return

    out_root = OUTDIR
    out_root.mkdir(parents=True, exist_ok=True)

    total = 0
    ok = 0
    failed = 0

    for root, _, files in os.walk(FILES):
        for f in files:
            p = Path(root) / f
            if p.suffix.lower() not in MEDIA_EXT:
                continue
            total += 1
            success, msg = process_media_file(p, out_root)
            if success:
                ok += 1
                print('OK:', msg)
            else:
                failed += 1
                print('SKIP/FAIL:', f'{p} -> {msg}')

    print('Done. total=%d ok=%d failed=%d' % (total, ok, failed))


if __name__ == '__main__':
    main()
