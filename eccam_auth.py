"""EC-Cam: usuarios y sesiones propias de la página web.

La sesión de Tapo vive en el servidor, así que cualquiera que llegue a la URL
podría ver las cámaras. Este módulo pone un login propio de EC-Cam delante:

- Usuarios en ``users.json`` con contraseña PBKDF2-SHA256 (nunca en claro).
- Sesiones con token aleatorio en cookie HttpOnly; en disco solo se guarda el
  SHA-256 del token, así que copiar ``sessions.json`` no da acceso.
- Límite de intentos fallidos por IP y por usuario.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import tempfile
import threading
import time
from pathlib import Path

PBKDF2_ITERATIONS = 310_000
SESSION_TTL = 30 * 24 * 3600          # 30 días, se renueva con el uso
SESSION_TOUCH_INTERVAL = 3600         # guardar "último uso" como máximo cada hora
MAX_FAILURES = 5                      # intentos fallidos permitidos por IP...
MAX_FAILURES_PER_USER = 20            # ...y por usuario (más alto, para que nadie
                                      # pueda bloquear tu cuenta a propósito)
FAILURE_WINDOW = 15 * 60              # ...en esta ventana
LOCKOUT_SECONDS = 15 * 60
USERNAME_RE = re.compile(r"^[A-Za-z0-9._@-]{3,40}$")
ROLES = ("admin", "viewer")


def eccam_home() -> Path:
    override = os.environ.get("ECCAM_HOME")
    if override:
        return Path(override)
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        return (Path(base) if base else Path.home() / "AppData" / "Local") / "EC-Cam"
    base = os.environ.get("XDG_STATE_HOME")
    return (Path(base) if base else Path.home() / ".local" / "state") / "eccam"


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if os.name == "nt":
        # En Windows os.replace falla a veces por el antivirus; escribir directo.
        path.write_text(text, encoding="utf-8")
        return
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, path)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


# Hash de relleno para que un usuario inexistente tarde lo mismo en responder.
_DUMMY_HASH = hash_password(secrets.token_hex(8))


def validate_password(password: str) -> None:
    if not isinstance(password, str) or len(password) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")
    if len(password) > 200:
        raise ValueError("La contraseña es demasiado larga.")


def validate_username(username: str) -> str:
    username = (username or "").strip()
    if not USERNAME_RE.match(username):
        raise ValueError("El usuario debe tener de 3 a 40 caracteres: letras, números, punto, guion, @ o _.")
    return username


class AuthStore:
    def __init__(self, home: Path | None = None):
        self.home = home or eccam_home()
        self.users_path = self.home / "users.json"
        self.sessions_path = self.home / "sessions.json"
        self.lock = threading.RLock()
        self.users: dict[str, dict] = _read_json(self.users_path).get("users", {}) or {}
        raw_sessions = _read_json(self.sessions_path).get("sessions", {}) or {}
        now = time.time()
        self.sessions: dict[str, dict] = {
            key: value
            for key, value in raw_sessions.items()
            if isinstance(value, dict)
            and value.get("expires", 0) > now
            and value.get("user") in self.users
        }
        self.failures: dict[str, list[float]] = {}

    # ---------- usuarios ----------
    def has_users(self) -> bool:
        with self.lock:
            return bool(self.users)

    def _save_users(self) -> None:
        _write_json(self.users_path, {"users": self.users})

    def _save_sessions(self) -> None:
        _write_json(self.sessions_path, {"sessions": self.sessions})

    def list_users(self) -> list[dict]:
        with self.lock:
            return [
                {"username": name, "role": data.get("role", "viewer"), "created": data.get("created")}
                for name, data in sorted(self.users.items(), key=lambda item: item[0].lower())
            ]

    def add_user(self, username: str, password: str, role: str = "viewer") -> None:
        username = validate_username(username)
        validate_password(password)
        if role not in ROLES:
            raise ValueError("Rol inválido.")
        with self.lock:
            if any(name.lower() == username.lower() for name in self.users):
                raise ValueError("Ese usuario ya existe.")
            self.users[username] = {"hash": hash_password(password), "role": role, "created": int(time.time())}
            self._save_users()

    def set_password(self, username: str, password: str) -> None:
        validate_password(password)
        with self.lock:
            if username not in self.users:
                raise ValueError("El usuario no existe.")
            self.users[username]["hash"] = hash_password(password)
            self._save_users()
            # Cerrar las demás sesiones de ese usuario.
            self.sessions = {k: v for k, v in self.sessions.items() if v.get("user") != username}
            self._save_sessions()

    def set_role(self, username: str, role: str) -> None:
        if role not in ROLES:
            raise ValueError("Rol inválido.")
        with self.lock:
            if username not in self.users:
                raise ValueError("El usuario no existe.")
            if role != "admin" and self._is_last_admin(username):
                raise ValueError("Debe quedar al menos un administrador.")
            self.users[username]["role"] = role
            self._save_users()

    def delete_user(self, username: str) -> None:
        with self.lock:
            if username not in self.users:
                raise ValueError("El usuario no existe.")
            if self._is_last_admin(username):
                raise ValueError("No puedes borrar al último administrador.")
            del self.users[username]
            self._save_users()
            self.sessions = {k: v for k, v in self.sessions.items() if v.get("user") != username}
            self._save_sessions()

    def _is_last_admin(self, username: str) -> bool:
        admins = [n for n, d in self.users.items() if d.get("role") == "admin"]
        return admins == [username]

    def role_of(self, username: str) -> str | None:
        with self.lock:
            user = self.users.get(username)
            return user.get("role", "viewer") if user else None

    # ---------- intentos fallidos ----------
    def _recent_failures(self, key: str, now: float) -> list[float]:
        items = [t for t in self.failures.get(key, []) if now - t < max(FAILURE_WINDOW, LOCKOUT_SECONDS)]
        self.failures[key] = items
        return items

    def locked_for(self, ip: str, username: str) -> int:
        """Segundos de bloqueo restantes (0 si puede intentar)."""
        now = time.time()
        with self.lock:
            wait = 0
            for key, limit in ((f"ip:{ip}", MAX_FAILURES), (f"user:{username.lower()}", MAX_FAILURES_PER_USER)):
                items = self._recent_failures(key, now)
                window = [t for t in items if now - t < FAILURE_WINDOW]
                if len(window) >= limit:
                    wait = max(wait, int(window[-1] + LOCKOUT_SECONDS - now) + 1)
            return wait

    def _register_failure(self, ip: str, username: str) -> None:
        now = time.time()
        with self.lock:
            for key in (f"ip:{ip}", f"user:{username.lower()}"):
                self._recent_failures(key, now).append(now)

    # ---------- sesiones ----------
    @staticmethod
    def _token_key(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def login(self, username: str, password: str, ip: str, agent: str = "") -> str:
        username = (username or "").strip()
        wait = self.locked_for(ip, username)
        if wait:
            minutes = max(1, (wait + 59) // 60)
            raise PermissionError(f"Demasiados intentos. Espera {minutes} min e inténtalo de nuevo.")
        with self.lock:
            match = next((n for n in self.users if n.lower() == username.lower()), None)
            stored = self.users[match]["hash"] if match else _DUMMY_HASH
        if not verify_password(password or "", stored) or not match:
            self._register_failure(ip, username)
            raise ValueError("Usuario o contraseña incorrectos.")
        token = secrets.token_urlsafe(32)
        now = time.time()
        with self.lock:
            self.failures.pop(f"ip:{ip}", None)
            self.failures.pop(f"user:{username.lower()}", None)
            self.sessions[self._token_key(token)] = {
                "user": match,
                "created": int(now),
                "last_seen": int(now),
                "expires": int(now + SESSION_TTL),
                "ip": ip,
                "agent": agent[:160],
            }
            self._save_sessions()
        return token

    def resolve(self, token: str | None) -> dict | None:
        if not token:
            return None
        key = self._token_key(token)
        now = time.time()
        with self.lock:
            session = self.sessions.get(key)
            if not session:
                return None
            if session.get("expires", 0) <= now or session.get("user") not in self.users:
                self.sessions.pop(key, None)
                self._save_sessions()
                return None
            if now - session.get("last_seen", 0) > SESSION_TOUCH_INTERVAL:
                session["last_seen"] = int(now)
                session["expires"] = int(now + SESSION_TTL)
                self._save_sessions()
            user = session["user"]
            return {"user": user, "role": self.users[user].get("role", "viewer")}

    def logout(self, token: str | None) -> None:
        if not token:
            return
        with self.lock:
            if self.sessions.pop(self._token_key(token), None) is not None:
                self._save_sessions()
