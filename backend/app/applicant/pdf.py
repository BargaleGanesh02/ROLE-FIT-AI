"""DOCX -> PDF using headless LibreOffice (installed on the server machine)."""
import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

CONVERT_TIMEOUT = 120  # seconds (the very first run is slower: LibreOffice builds its profile)
_lock = threading.Lock()  # one conversion at a time keeps LibreOffice stable


class PdfError(Exception):
    """A problem we can explain to the user in plain words."""


def find_soffice():
    """Find soffice.exe / soffice. Order: SOFFICE_PATH setting, PATH, usual install folders."""
    env = os.environ.get("SOFFICE_PATH")
    if env and Path(env).exists():
        return env
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    for candidate in (
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        "/usr/bin/soffice",
        "/usr/local/bin/soffice",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ):
        if Path(candidate).exists():
            return candidate
    return None


def docx_to_pdf_bytes(docx_path, profile_dir):
    """Convert one .docx file and return the PDF as bytes."""
    exe = find_soffice()
    if not exe:
        raise PdfError(
            "LibreOffice was not found, so the PDF preview cannot be made. "
            "Install LibreOffice, or set the SOFFICE_PATH environment variable to soffice.exe."
        )
    profile_dir = Path(profile_dir).resolve()
    profile_dir.mkdir(parents=True, exist_ok=True)
    with _lock, tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "cv.docx"
        shutil.copyfile(docx_path, work)
        cmd = [
            exe,
            f"-env:UserInstallation={profile_dir.as_uri()}",
            "--headless", "--norestore", "--nologo",
            "--convert-to", "pdf",
            "--outdir", tmp,
            str(work),
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=CONVERT_TIMEOUT, check=False)
        except subprocess.TimeoutExpired:
            raise PdfError("The PDF conversion took too long. Please try again.")
        except OSError as err:
            raise PdfError(f"LibreOffice could not be started: {err}")
        result = Path(tmp) / "cv.pdf"
        if not result.exists():
            raise PdfError("LibreOffice ran but did not produce a PDF. Close any open LibreOffice window and try again.")
        return result.read_bytes()
