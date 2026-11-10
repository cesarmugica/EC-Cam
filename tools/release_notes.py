"""Actualiza el título y las notas de cada Release a partir de CHANGELOG.md.

Lo corre .github/workflows/release-notes.yml cuando cambia CHANGELOG.md
(necesita GH_TOKEN con permiso contents: write y GITHUB_REPOSITORY).
"""
import json
import os
import re
import subprocess
from pathlib import Path

repo = os.environ["GITHUB_REPOSITORY"]
changelog = (Path(__file__).resolve().parent.parent / "CHANGELOG.md").read_text(encoding="utf-8")
link = f"https://github.com/{repo}/blob/main/CHANGELOG.md"

notes: dict[str, tuple[str, bool]] = {}
# Versiones con sección propia: "## 2.0.1 — Título"
for match in re.finditer(r"(?ms)^## (\d+\.\d+\.\d+)\b.*?(?=^## |\Z)", changelog):
    notes[match.group(1)] = (match.group(0).strip(), False)
# Versiones dentro de un grupo: "- **1.2.2:** texto"
for match in re.finditer(r"^- \*\*(\d+\.\d+\.\d+)( ⚠️ defectuosa)?:\*\* (.+)$", changelog, re.M):
    notes.setdefault(match.group(1), (match.group(3), bool(match.group(2))))

releases = json.loads(subprocess.check_output(["gh", "api", f"repos/{repo}/releases?per_page=100"]))
for release in releases:
    version = release["tag_name"].lstrip("v")
    if version not in notes:
        print("sin notas en CHANGELOG:", release["tag_name"])
        continue
    text, broken = notes[version]
    warning = "⚠️ **Versión defectuosa: no arranca. Usa la 1.1.10 o posterior.**\n\n" if broken else ""
    body = f"{warning}{text}\n\n---\nInstalador: **EC-Cam-Setup-{version}.exe** · [Historial completo]({link})"
    title = f"EC-Cam {release['tag_name']}" + (" ⚠️ defectuosa" if broken else "")
    if release.get("body") == body and release.get("name") == title:
        continue
    subprocess.run(
        ["gh", "api", "-X", "PATCH", f"repos/{repo}/releases/{release['id']}", "-f", f"body={body}", "-f", f"name={title}"],
        check=True, capture_output=True,
    )
    print("actualizada:", release["tag_name"])
