#!/usr/bin/env python3
"""EC-Cam — servidor web para ver las cámaras Tapo desde internet.

Usa el motor de Topo (tapo_cloud_app.py, MIT, https://github.com/filirnd/topo)
para hablar con la nube de Tapo, y le agrega:

- login propio de EC-Cam (usuarios admin / visor) delante de todo,
- página instalable (PWA), igual que DGPOS / DGPOSR,
- interfaz en español,
- modo servidor: escucha en la red para publicarse con Cloudflare Tunnel.

Uso:
    eccam-server                       inicia el servidor (puerto 8790)
    eccam-server --add-user NOMBRE     crea un usuario (pide la contraseña)
    eccam-server --list-users
    eccam-server --delete-user NOMBRE
    eccam-server --reset-password NOMBRE
"""

from __future__ import annotations

import argparse
import contextlib
import getpass
import ipaddress
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

APP_VERSION = "1.0.6"
ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
EXE_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else ROOT
WEB_ROOT = ROOT / "web"
COOKIE_NAME = "eccam_session"
DEFAULT_PORT = 8790

# ---------------------------------------------------------------------------
# Preparación del entorno (antes de importar el motor de Topo)
# ---------------------------------------------------------------------------
from eccam_auth import ROLES, SESSION_TTL, AuthStore, eccam_home  # noqa: E402

HOME = eccam_home()
os.environ.setdefault("ECCAM_HOME", str(HOME))


def _setup_logging() -> None:
    """Sin consola (exe de Windows) stdout es None: mandar todo a un log."""
    if sys.stdout is not None and not getattr(sys, "frozen", False):
        return
    log_dir = HOME / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "eccam.log"
    with contextlib.suppress(OSError):
        if log_path.exists() and log_path.stat().st_size > 5 * 1024 * 1024:
            log_path.replace(log_dir / "eccam.old.log")
    stream = open(log_path, "a", encoding="utf-8", buffering=1)  # noqa: SIM115
    if sys.stdout is None:
        sys.stdout = stream
    if sys.stderr is None:
        sys.stderr = stream
    if getattr(sys, "frozen", False):
        sys.stdout = sys.stderr = stream


def _hide_child_consoles() -> None:
    """En Windows, que FFmpeg no abra ventanas negras al correr sin consola."""
    if os.name != "nt":
        return
    flag = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    original_init = subprocess.Popen.__init__

    def patched_init(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        kwargs["creationflags"] = kwargs.get("creationflags", 0) | flag
        original_init(self, *args, **kwargs)

    subprocess.Popen.__init__ = patched_init  # type: ignore[method-assign]


def _locate_ffmpeg() -> None:
    if os.environ.get("TOPO_FFMPEG"):
        return
    name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    for candidate in (EXE_DIR / name, EXE_DIR / "ffmpeg" / name, ROOT / name):
        if candidate.is_file():
            os.environ["TOPO_FFMPEG"] = str(candidate)
            return
    found = shutil.which("ffmpeg")
    if found:
        os.environ["TOPO_FFMPEG"] = found


_setup_logging()
_hide_child_consoles()
_locate_ffmpeg()

import tapo_cloud_app as engine  # noqa: E402  (motor de Topo)

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
CONFIG_PATH = HOME / "config.json"
DEFAULT_CONFIG = {
    "host": "0.0.0.0",
    "port": DEFAULT_PORT,
    # Confiar en CF-Connecting-IP / X-Forwarded-For solo si la conexión llega
    # desde esta misma PC (cloudflared corre aquí).
    "trust_local_proxy": True,
    "open_browser_on_start": True,
}


def load_config() -> dict:
    config = dict(DEFAULT_CONFIG)
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            config.update({k: v for k, v in data.items() if k in DEFAULT_CONFIG})
    except FileNotFoundError:
        HOME.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError):
        print(f"AVISO: {CONFIG_PATH} no es válido; se usan valores por defecto.")
    return config


# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
PUBLIC_FILES = {
    "/login": "login.html",
    "/setup": "login.html",
    "/manifest.json": "manifest.json",
    "/sw.js": "sw.js",
    "/pwa.js": "pwa.js",
    "/offline.html": "offline.html",
    "/favicon.ico": "img/favicon.png",
    "/assets/topo.png": "img/pwa-192.png",
}
PUBLIC_PREFIXES = ("/img/",)
TAPO_ADMIN_POSTS = {"/api/login", "/api/mfa/request", "/api/mfa/verify", "/api/logout"}
PROXY_HEADERS = ("CF-Connecting-IP", "X-Forwarded-For", "X-Real-IP", "Forwarded", "CF-Ray")


class EcCamHandler(engine.Handler):
    auth: AuthStore
    trust_local_proxy: bool = True
    server_version = "EC-Cam"
    sys_version = ""
    # Si el navegador deja de recibir por 20 s (red muy lenta), se corta esa
    # conexión; la página se reconecta sola en el punto en vivo.
    timeout = 20

    # ---------- utilidades ----------
    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if self._is_https():
            self.send_header("Strict-Transport-Security", "max-age=15552000")
        super().end_headers()

    def _peer_is_loopback(self) -> bool:
        try:
            return ipaddress.ip_address(self.client_address[0]).is_loopback
        except ValueError:
            return False

    def _behind_proxy(self) -> bool:
        return any(self.headers.get(name) for name in PROXY_HEADERS)

    def client_ip(self) -> str:
        peer = self.client_address[0]
        if self.trust_local_proxy and self._peer_is_loopback():
            forwarded = self.headers.get("CF-Connecting-IP") or (
                self.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            )
            if forwarded:
                return forwarded
        return peer

    def is_direct_local(self) -> bool:
        """Petición hecha en la propia PC servidor (no a través del túnel)."""
        return self._peer_is_loopback() and not self._behind_proxy()

    def _is_https(self) -> bool:
        if self.headers.get("X-Forwarded-Proto", "").lower() == "https":
            return True
        return "https" in self.headers.get("CF-Visitor", "")

    def _cookie_token(self) -> str | None:
        raw = self.headers.get("Cookie", "")
        for part in raw.split(";"):
            name, _, value = part.strip().partition("=")
            if name == COOKIE_NAME and value:
                return value
        return None

    def _set_cookie(self, token: str, max_age: int) -> str:
        parts = [f"{COOKIE_NAME}={token}", "Path=/", "HttpOnly", "SameSite=Lax", f"Max-Age={max_age}"]
        if self._is_https():
            parts.append("Secure")
        return "; ".join(parts)

    def send_json_cookie(self, value: object, cookie: str, status: int = 200) -> None:
        body = engine.json_bytes(value)
        self.close_connection = True
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Set-Cookie", cookie)
        self.send_header("Connection", "close")
        self.end_headers()
        with contextlib.suppress(BrokenPipeError, ConnectionResetError, OSError):
            self.wfile.write(body)

    def redirect(self, location: str) -> None:
        self.close_connection = True
        self.send_response(302)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def serve_web(self, relative: str) -> None:
        path = (WEB_ROOT / relative).resolve()
        if WEB_ROOT.resolve() not in path.parents or not path.is_file():
            self.send_error(404)
            return
        self.send_file(path)

    def current_user(self) -> dict | None:
        return self.auth.resolve(self._cookie_token())

    def _same_origin_post(self) -> bool:
        """Defensa CSRF: JSON obligatorio y, si llega Origin, debe ser este sitio."""
        if not self.headers.get("Content-Type", "").lower().startswith("application/json"):
            return False
        origin = self.headers.get("Origin")
        if not origin:
            return True
        netloc = urlsplit(origin).netloc.lower()
        hosts = {
            (self.headers.get("Host") or "").lower(),
            (self.headers.get("X-Forwarded-Host") or "").split(",")[0].strip().lower(),
        }
        return netloc in hosts

    def _app_session_info(self, user: dict | None) -> dict:
        has_users = self.auth.has_users()
        return {
            "app_authenticated": user is not None,
            "user": user["user"] if user else None,
            "role": user["role"] if user else None,
            "needs_setup": not has_users,
            "setup_allowed": (not has_users) and self.is_direct_local(),
            "version": APP_VERSION,
        }

    def _deny(self, status: int, message: str) -> None:
        self.send_json({"ok": False, "error": message, "app_auth": status != 401}, status)

    # ---------- GET ----------
    def do_GET(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path

        if path in PUBLIC_FILES:
            if path == "/setup" and self.auth.has_users():
                self.redirect("/login")
                return
            if path == "/login" and self.current_user():
                self.redirect("/")
                return
            self.serve_web(PUBLIC_FILES[path])
            return
        if path.startswith(PUBLIC_PREFIXES) and ".." not in path:
            self.serve_web(path.lstrip("/"))
            return
        if path == "/api/app/session":
            self.send_json(self._app_session_info(self.current_user()))
            return

        user = self.current_user()
        if user is None:
            if path in ("/", "/index.html"):
                self.redirect("/setup" if not self.auth.has_users() else "/login")
            else:
                self._deny(401, "Inicia sesión en EC-Cam.")
            return

        if path in ("/", "/index.html"):
            self.serve_web("index.html")
            return
        if path == "/api/app/users":
            if user["role"] != "admin":
                self._deny(403, "Solo un administrador puede ver los usuarios.")
                return
            self.send_json({"ok": True, "users": self.auth.list_users()})
            return
        if path == "/api/app/stream-status":
            from urllib.parse import parse_qs
            query = parse_qs(urlsplit(self.path).query)
            state = self.context.current_state()
            message = ""
            try:
                index = int(query.get("cam", ["0"])[0])
                quality = query.get("q", ["SD"])[0].upper()
                if state is not None:
                    key = index if quality == engine.STREAM_RESOLUTION else (index, quality)
                    with state.workers_lock:
                        worker = state.workers.get(key)
                    if worker is not None:
                        message = worker.last_error
            except ValueError:
                pass
            kind = "ok"
            if "device offline" in message:
                kind = "offline"
            elif "timed out" in message:
                kind = "silent"
            elif message:
                kind = "error"
            self.send_json({"ok": True, "kind": kind, "error": message})
            return
        if path == "/api/app/diag":
            if user["role"] != "admin":
                self._deny(403, "Solo un administrador.")
                return
            state = self.context.current_state()
            workers = []
            if state is not None:
                with state.workers_lock:
                    items = list(state.workers.items())
                workers = [{"key": str(key), **worker.diagnostics()} for key, worker in items]
            self.send_json({"ok": True, "version": APP_VERSION, "ffmpeg": os.environ.get("TOPO_FFMPEG"), "workers": workers})
            return
        if path == "/api/app/relaytest":
            if user["role"] != "admin":
                self._deny(403, "Solo un administrador.")
                return
            state = self.context.current_state()
            if state is None:
                self._deny(409, "Conecta la cuenta Tapo primero.")
                return
            import eccam_relaytest
            from urllib.parse import parse_qs
            try:
                index = int(parse_qs(urlsplit(self.path).query).get("cam", ["0"])[0])
                state.devices[index]
            except (ValueError, IndexError):
                self._deny(400, "Cámara inválida.")
                return
            self.send_json({"ok": True, **eccam_relaytest.run(state, index)})
            return
        if path.endswith("/native-player"):
            # El reproductor nativo abriría ventanas en la PC servidor.
            self._deny(403, "No disponible en EC-Cam.")
            return
        super().do_GET()

    # ---------- POST ----------
    def do_POST(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if not self._same_origin_post():
            self._deny(403, "Solicitud rechazada.")
            return

        if path == "/api/app/login":
            try:
                payload = self.read_json_body()
                token = self.auth.login(
                    str(payload.get("username") or ""),
                    str(payload.get("password") or ""),
                    self.client_ip(),
                    self.headers.get("User-Agent", ""),
                )
            except PermissionError as exc:
                self.send_json({"ok": False, "error": str(exc)}, 429)
                return
            except ValueError as exc:
                time.sleep(0.4)
                self.send_json({"ok": False, "error": str(exc)}, 401)
                return
            print(f"EC-Cam: inicio de sesión de {payload.get('username')!r} desde {self.client_ip()}")
            self.send_json_cookie({"ok": True}, self._set_cookie(token, SESSION_TTL))
            return
        if path == "/api/app/setup":
            if self.auth.has_users():
                self._deny(403, "EC-Cam ya está configurado.")
                return
            if not self.is_direct_local():
                self._deny(403, "La configuración inicial solo se puede hacer en la PC servidor.")
                return
            try:
                payload = self.read_json_body()
                username = str(payload.get("username") or "")
                password = str(payload.get("password") or "")
                self.auth.add_user(username, password, "admin")
                token = self.auth.login(username, password, self.client_ip(), self.headers.get("User-Agent", ""))
            except (ValueError, PermissionError) as exc:
                self.send_json({"ok": False, "error": str(exc)}, 400)
                return
            self.send_json_cookie({"ok": True}, self._set_cookie(token, SESSION_TTL))
            return
        if path == "/api/app/logout":
            self.auth.logout(self._cookie_token())
            self.send_json_cookie({"ok": True}, self._set_cookie("", 0))
            return

        user = self.current_user()
        if user is None:
            self._deny(401, "Inicia sesión en EC-Cam.")
            return

        if path == "/api/app/me/password":
            try:
                payload = self.read_json_body()
                current = str(payload.get("current") or "")
                new = str(payload.get("new") or "")
                # Verificar la contraseña actual con el mismo límite de intentos.
                self.auth.login(user["user"], current, self.client_ip())
                self.auth.set_password(user["user"], new)
                token = self.auth.login(user["user"], new, self.client_ip(), self.headers.get("User-Agent", ""))
            except PermissionError as exc:
                self.send_json({"ok": False, "error": str(exc)}, 429)
                return
            except ValueError as exc:
                msg = str(exc)
                if "incorrectos" in msg:
                    msg = "La contraseña actual no es correcta."
                self.send_json({"ok": False, "error": msg}, 400)
                return
            self.send_json_cookie({"ok": True}, self._set_cookie(token, SESSION_TTL))
            return

        if path.startswith("/api/app/users"):
            if user["role"] != "admin":
                self._deny(403, "Solo un administrador puede administrar usuarios.")
                return
            try:
                payload = self.read_json_body()
                name = str(payload.get("username") or "")
                if path == "/api/app/users":
                    role = str(payload.get("role") or "viewer")
                    self.auth.add_user(name, str(payload.get("password") or ""), role)
                elif path == "/api/app/users/delete":
                    if name == user["user"]:
                        raise ValueError("No puedes borrar tu propio usuario.")
                    self.auth.delete_user(name)
                elif path == "/api/app/users/role":
                    if name == user["user"]:
                        raise ValueError("No puedes cambiar tu propio rol.")
                    self.auth.set_role(name, str(payload.get("role") or ""))
                elif path == "/api/app/users/password":
                    self.auth.set_password(name, str(payload.get("password") or ""))
                else:
                    self.send_error(404)
                    return
            except ValueError as exc:
                self.send_json({"ok": False, "error": str(exc)}, 400)
                return
            self.send_json({"ok": True, "users": self.auth.list_users()})
            return

        if path in TAPO_ADMIN_POSTS or path.endswith("/privacy"):
            if user["role"] != "admin":
                self._deny(403, "Solo un administrador puede hacer esto.")
                return
        if path.endswith("/native-player"):
            self._deny(403, "No disponible en EC-Cam.")
            return
        super().do_POST()


# ---------------------------------------------------------------------------
# Línea de comandos
# ---------------------------------------------------------------------------
def _ask_password(confirm: bool = True) -> str:
    password = getpass.getpass("Contraseña (mín. 8 caracteres): ")
    if confirm and getpass.getpass("Repite la contraseña: ") != password:
        raise SystemExit("Las contraseñas no coinciden.")
    return password


def _ensure_console() -> None:
    """El exe de Windows no tiene consola: abrir una para los comandos de usuarios."""
    if os.name != "nt" or not getattr(sys, "frozen", False):
        return
    import ctypes

    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    if not kernel32.AttachConsole(-1):  # consola del .bat / cmd que lo llamó
        kernel32.AllocConsole()
    sys.stdout = sys.stderr = open("CONOUT$", "w", encoding="utf-8", buffering=1)  # noqa: SIM115
    sys.stdin = open("CONIN$", encoding="utf-8")  # noqa: SIM115


def run_cli(args: argparse.Namespace, auth: AuthStore) -> int | None:
    if any((args.list_users, args.add_user, args.reset_password, args.delete_user)):
        _ensure_console()
    try:
        if args.list_users:
            users = auth.list_users()
            if not users:
                print("No hay usuarios. Crea uno con --add-user NOMBRE")
            for item in users:
                print(f"{item['username']:<30} {item['role']}")
            return 0
        if args.add_user:
            role = args.role or ("admin" if not auth.has_users() else "viewer")
            auth.add_user(args.add_user, _ask_password(), role)
            print(f"Usuario {args.add_user!r} creado con rol {role}.")
            return 0
        if args.reset_password:
            auth.set_password(args.reset_password, _ask_password())
            print("Contraseña actualizada; se cerraron sus sesiones.")
            return 0
        if args.delete_user:
            auth.delete_user(args.delete_user)
            print(f"Usuario {args.delete_user!r} borrado.")
            return 0
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=f"EC-Cam {APP_VERSION} — cámaras Tapo en la web")
    parser.add_argument("--host", help="dirección donde escuchar (por defecto 0.0.0.0)")
    parser.add_argument("--port", type=int, help=f"puerto (por defecto {DEFAULT_PORT})")
    parser.add_argument("--fresh-login", action="store_true", help="olvidar la sesión de Tapo guardada")
    parser.add_argument("--no-browser", action="store_true", help="no abrir el navegador al iniciar")
    parser.add_argument("--add-user", metavar="NOMBRE")
    parser.add_argument("--role", choices=ROLES)
    parser.add_argument("--reset-password", metavar="NOMBRE")
    parser.add_argument("--delete-user", metavar="NOMBRE")
    parser.add_argument("--list-users", action="store_true")
    parser.add_argument("--version", action="version", version=f"EC-Cam {APP_VERSION}")
    args = parser.parse_args()

    auth = AuthStore()
    result = run_cli(args, auth)
    if result is not None:
        return result

    config = load_config()
    host = args.host or str(config["host"])
    port = args.port if args.port is not None else int(config["port"])
    local_url = f"http://127.0.0.1:{port}/"

    handler_class = type(
        "EcCamRequestHandler",
        (EcCamHandler,),
        {"auth": auth, "trust_local_proxy": bool(config["trust_local_proxy"])},
    )
    try:
        server = ThreadingHTTPServer((host, port), handler_class)
    except OSError as exc:
        # Probablemente EC-Cam ya está corriendo: solo abrir la página.
        print(f"No se pudo abrir el puerto {port}: {exc}")
        if not args.no_browser:
            webbrowser.open(local_url)
        return 2
    server.daemon_threads = True

    try:
        context = engine.CloudAppContext(args.fresh_login)
    except (RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    handler_class.context = context

    print(f"EC-Cam {APP_VERSION} disponible en http://{host}:{port}", flush=True)
    print(f"Datos y configuración: {HOME}", flush=True)
    if not auth.has_users():
        print(f"Primera vez: abre {local_url}setup en esta PC para crear el administrador.", flush=True)
    if not os.environ.get("TOPO_FFMPEG"):
        print("AVISO: no se encontró FFmpeg; el video en vivo no funcionará.", flush=True)

    if config["open_browser_on_start"] and not args.no_browser:
        threading.Timer(1.0, webbrowser.open, args=(local_url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEC-Cam detenido.")
    finally:
        context.close()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
