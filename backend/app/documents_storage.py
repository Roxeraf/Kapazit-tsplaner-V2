import mimetypes
import os
import uuid
from pathlib import Path

from fastapi import UploadFile

DOCUMENTS_DIR = Path(os.environ.get("DOCUMENTS_DIR", "./data/documents"))


def _sanitize_filename(name: str) -> str:
    """Nur den Dateinamen behalten (kein Pfadanteil) — verhindert Path-Traversal über
    manipulierte Upload-Dateinamen wie "../../etc/passwd"."""
    return Path(name).name or "datei"


def save_upload(project_id: int, upload: UploadFile) -> tuple[str, int, str | None]:
    """Speichert eine hochgeladene Datei unter DOCUMENTS_DIR/{project_id}/{uuid}_{name}.

    Gibt (speicherpfad relativ zu DOCUMENTS_DIR, Größe in Bytes, Mimetype) zurück.
    Mimetype: bevorzugt der vom Browser mitgeschickte content_type, sonst ein Fallback über
    mimetypes.guess_type() (z.B. für .eml-Dateien, die Browser oft nicht korrekt setzen) —
    damit eine spätere strukturierte E-Mail-Vorschau nicht zusätzlich erschwert wird
    (siehe CONCEPT.md Abschnitt 10).
    """
    project_dir = DOCUMENTS_DIR / str(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)

    safe_name = _sanitize_filename(upload.filename or "datei")
    stored_name = f"{uuid.uuid4().hex}_{safe_name}"
    target = project_dir / stored_name

    content = upload.file.read()
    target.write_bytes(content)

    mimetype = upload.content_type
    if not mimetype or mimetype == "application/octet-stream":
        guessed, _ = mimetypes.guess_type(safe_name)
        mimetype = guessed or mimetype

    speicherpfad = f"{project_id}/{stored_name}"
    return speicherpfad, len(content), mimetype


def resolve_path(speicherpfad: str) -> Path:
    return DOCUMENTS_DIR / speicherpfad


def delete_file(speicherpfad: str) -> None:
    resolve_path(speicherpfad).unlink(missing_ok=True)
