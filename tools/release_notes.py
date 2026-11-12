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
# Versiones que no pasaron la prueba: "## 2.3.0 — ⚠️ ..." → sin instalador y fuera de "Última versión".
failed: set[str] = set()
# Versiones con sección propia: "## 2.0.1 — Título"
for match in re.finditer(r"(?ms)^## (\d+\.\d+\.\d+)\b.*?(?=^## |\Z)", changelog):
    notes[match.group(1)] = (match.group(0).strip(), False)
    if "⚠️" in match.group(0).splitlines()[0]:
        failed.add(match.group(1))
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
    if version in failed:
        title = f"EC-Cam {release['tag_name']} ⚠️ no superó la prueba"
        body = f"⚠️ **Esta versión se publicó pero no superó la prueba; se quitó su instalador.**\n\n{text}\n\n---\n[Historial completo]({link})"
        for asset in release.get("assets", []):
            subprocess.run(["gh", "api", "-X", "DELETE", f"repos/{repo}/releases/assets/{asset['id']}"], check=True, capture_output=True)
            print("instalador quitado:", release["tag_name"], asset["name"])
        if release.get("body") != body or release.get("name") != title or not release.get("prerelease"):
            subprocess.run(["gh", "api", "-X", "PATCH", f"repos/{repo}/releases/{release['id']}", "-f", f"body={body}",
                            "-f", f"name={title}", "-F", "prerelease=true", "-f", "make_latest=false"], check=True, capture_output=True)
            print("marcada como no superada:", release["tag_name"])
        continue
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

# "Última versión" = la más nueva que sí funciona.
def _key(tag: str) -> tuple[int, ...]:
    return tuple(int(x) for x in tag.lstrip("v").split("."))


good = [r for r in releases if r["tag_name"].lstrip("v") not in failed and not r.get("draft")
        and r["tag_name"].lstrip("v") in notes and not notes[r["tag_name"].lstrip("v")][1]]
if good:
    newest = max(good, key=lambda r: _key(r["tag_name"]))
    subprocess.run(["gh", "api", "-X", "PATCH", f"repos/{repo}/releases/{newest['id']}", "-f", "make_latest=true"],
                   check=True, capture_output=True)
    print("última versión:", newest["tag_name"])
