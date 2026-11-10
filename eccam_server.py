#!/usr/bin/env python3
"""EC-Cam — ver tus cámaras Tapo en la PC, sin emulador de Android.

Usa el motor de Topo (tapo_cloud_app.py, MIT, https://github.com/filirnd/topo)
para hablar con la nube de Tapo, y le agrega:

- visor de una cámara a la vez + mosaico sin video (ligero),
- protocolo de vista previa de la app oficial (firmwares nuevos),
- página instalable (PWA) e interfaz en español.

Cada persona instala EC-Cam en su PC y entra con su propia cuenta Tapo.
El servidor solo responde dentro de la propia PC (127.0.0.1).

Uso:
    eccam-server                 inicia EC-Cam (puerto 8790) y abre el navegador
    eccam-server --no-browser    inicia sin abrir el navegador
    eccam-server --fresh-login   olvida la sesión de Tapo guardada
"""

from __future__ import annotations

import argparse
import contextlib
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
from urllib.parse import parse_qs, urlsplit

APP_VERSION = "1.2.1"
try:  # fecha del instalador, la escribe windows/build.ps1
    from eccam_build import BUILD_DATE  # type: ignore[import-not-found]
except ImportError:
    BUILD_DATE = ""

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
EXE_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else ROOT
WEB_ROOT = ROOT / "web"
DEFAULT_PORT = 8790
LOCAL_HOSTS = {"127.0.0.1", "localhost", "[::1]", "::1"}


def eccam_home() -> Path:
    override = os.environ.get("ECCAM_HOME")
    if override:
        return Path(override)
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        return (Path(base) if base else Path.home() / "AppData" / "Local") / "EC-Cam"
    base = os.environ.get("XDG_STATE_HOME")
    return (Path(base) if base else Path.home() / ".local" / "state") / "eccam"


HOME = eccam_home()
os.environ.setdefault("ECCAM_HOME", str(HOME))


# ---------------------------------------------------------------------------
# Preparación del entorno (antes de importar el motor de Topo)
# ---------------------------------------------------------------------------
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

def _import_engine():
    """Importar el motor; si Windows tiene ocupado un archivo (el antivirus
    revisando lo recién instalado), esperar y reintentar en vez de cerrarse."""
    import time as _time

    last_error: Exception | None = None
    for attempt in range(10):
        try:
            # Import estático (no importlib) para que PyInstaller lo empaquete.
            import tapo_cloud_app

            return tapo_cloud_app
        except ImportError as exc:
            if "DLL load failed" not in str(exc):
                raise
            last_error = exc
            for name in [m for m in sys.modules if m in ("ssl", "_ssl", "tapo_cloud_app", "tapo_cloud_probe")]:
                sys.modules.pop(name, None)
            print(f"EC-Cam: archivo ocupado al iniciar ({exc}); reintento {attempt + 1}/10", flush=True)
            _time.sleep(2)
    raise last_error  # type: ignore[misc]


engine = _import_engine()  # motor de Topo

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
CONFIG_PATH = HOME / "config.json"
DEFAULT_CONFIG = {"port": DEFAULT_PORT, "open_browser_on_start": True}


def load_config() -> dict:
    config = dict(DEFAULT_CONFIG)
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            config.update({k: v for k, v in data.items() if k in DEFAULT_CONFIG})
    except FileNotFoundError:
        pass
    except (OSError, json.JSONDecodeError):
        print(f"AVISO: {CONFIG_PATH} no es válido; se usan valores por defecto.")
    # Guardar solo las opciones vigentes (limpia el "host" de versiones viejas).
    with contextlib.suppress(OSError):
        HOME.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return config


def _cleanup_old_login_files() -> None:
    """Las versiones 1.0.x tenían usuarios propios; ya no se usan."""
    for name in ("users.json", "sessions.json"):
        with contextlib.suppress(OSError):
            (HOME / name).unlink()


# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
STATIC_FILES = {
    "/": "index.html",
    "/index.html": "index.html",
    "/manifest.json": "manifest.json",
    "/sw.js": "sw.js",
    "/pwa.js": "pwa.js",
    "/offline.html": "offline.html",
    "/favicon.ico": "img/favicon.png",
    "/assets/topo.png": "img/pwa-192.png",
}


class EcCamHandler(engine.Handler):
    port: int = DEFAULT_PORT
    server_version = "EC-Cam"
    sys_version = ""
    # Si el navegador deja de recibir por 20 s, se corta esa conexión; la
    # página se reconecta sola en el punto en vivo.
    timeout = 20

    # ---------- seguridad de un servidor local sin contraseña ----------
    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        super().end_headers()

    def _local_request(self) -> bool:
        """Solo esta PC, y solo con Host 127.0.0.1/localhost.

        Revisar el Host evita el ataque de "DNS rebinding": una página web
        maliciosa no puede usar su propio dominio para leer EC-Cam.
        """
        try:
            if not ipaddress.ip_address(self.client_address[0]).is_loopback:
                return False
        except ValueError:
            return False
        host = urlsplit("//" + (self.headers.get("Host") or "")).hostname or ""
        return host.lower() in LOCAL_HOSTS or f"[{host}]" in LOCAL_HOSTS

    def _same_origin_post(self) -> bool:
        """Defensa CSRF: JSON obligatorio y, si llega Origin, debe ser EC-Cam."""
        if not self.headers.get("Content-Type", "").lower().startswith("application/json"):
            return False
        origin = self.headers.get("Origin")
        if not origin:
            return True
        parts = urlsplit(origin)
        return (parts.hostname or "").lower() in LOCAL_HOSTS and parts.port == self.port

    def _forbidden(self) -> None:
        self.send_json({"ok": False, "error": "Solicitud rechazada."}, 403)

    def serve_web(self, relative: str) -> None:
        path = (WEB_ROOT / relative).resolve()
        if WEB_ROOT.resolve() not in path.parents or not path.is_file():
            self.send_error(404)
            return
        self.send_file(path)

    def redirect(self, location: str) -> None:
        self.close_connection = True
        self.send_response(302)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    # ---------- GET ----------
    def do_GET(self) -> None:  # noqa: N802
        if not self._local_request():
            self._forbidden()
            return
        parsed = urlsplit(self.path)
        path = parsed.path
        if path in STATIC_FILES:
            self.serve_web(STATIC_FILES[path])
            return
        if path.startswith("/img/") and ".." not in path:
            self.serve_web(path.lstrip("/"))
            return
        if path in ("/login", "/setup"):
            self.redirect("/")
            return
        if path == "/api/app/session":
            self.send_json({
                "app_authenticated": True,
                "user": "local",
                "role": "admin",
                "version": APP_VERSION,
                "build_date": BUILD_DATE,
            })
            return
        if path == "/api/app/stream-status":
            self._stream_status(parse_qs(parsed.query))
            return
        if path == "/api/app/diag":
            self._diag()
            return
        if path == "/api/app/relaytest":
            self._relaytest(parse_qs(parsed.query))
            return
        if path == "/api/app/sdtest":
            self._sdtest(parse_qs(parsed.query))
            return
        if path == "/api/app/playtest":
            self._playtest(parse_qs(parsed.query))
            return
        if path.startswith("/recordings/") and path.endswith("/stream.mp4"):
            self._stream_recording(path[len("/recordings/"):-len("/stream.mp4")])
            return
        if path.endswith("/native-player"):
            # El reproductor nativo de Topo abriría ventanas aparte; no se usa.
            self.send_json({"ok": False, "error": "No disponible en EC-Cam."}, 403)
            return
        super().do_GET()

    # ---------- POST ----------
    def do_POST(self) -> None:  # noqa: N802
        if not self._local_request() or not self._same_origin_post():
            self._forbidden()
            return
        post_path = urlsplit(self.path).path
        if post_path.startswith("/api/recording-jobs/") and post_path.endswith("/cancel"):
            state = self.context.current_state()
            job_id = post_path[len("/api/recording-jobs/"):-len("/cancel")]
            cancelled = bool(state and job_id.isalnum() and state.cancel_recording(job_id))
            self.send_json({"ok": True, "cancelled": cancelled})
            return
        if urlsplit(self.path).path.endswith("/native-player"):
            self.send_json({"ok": False, "error": "No disponible en EC-Cam."}, 403)
            return
        super().do_POST()

    # ---------- reproducir mientras descarga ----------
    def _stream_recording(self, job_id: str) -> None:
        """Mandar al navegador la grabación mientras llega de la cámara.

        La cámara entrega las grabaciones a velocidad normal (1x); esperar el
        archivo completo hacía que un clip de 1.5 min tardara lo mismo o más
        en empezar. Aquí se reempaqueta el TS que se va escribiendo a MP4
        fragmentado (solo video; el audio va en el archivo final/Descargar).
        """
        state = self.context.current_state()
        source = state.recording_stream_source(job_id) if state and job_id.isalnum() else None
        if source is None:
            self.send_error(404)
            return
        ts_path, downloading = source
        deadline = time.monotonic() + 40
        while not (ts_path.is_file() and ts_path.stat().st_size > 64 * 1024):
            if not downloading() and not ts_path.is_file():
                self.send_json({"ok": False, "error": "La grabación no está disponible."}, 404)
                return
            if time.monotonic() > deadline or not downloading() and ts_path.is_file():
                break
            time.sleep(0.25)
        ffmpeg = subprocess.Popen(
            [
                os.environ.get("TOPO_FFMPEG") or "ffmpeg", "-hide_banner", "-loglevel", "error",
                "-probesize", "500000", "-analyzeduration", "1000000",
                "-f", "mpegts", "-i", "pipe:0", "-map", "0:v:0", "-c:v", "copy", "-an",
                "-movflags", "+empty_moov+default_base_moof+frag_keyframe", "-f", "mp4", "pipe:1",
            ],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0,
        )

        def feed() -> None:
            try:
                with open(ts_path, "rb") as handle:
                    while True:
                        data = handle.read(65536)
                        if data:
                            ffmpeg.stdin.write(data)
                        elif downloading():
                            time.sleep(0.2)
                        else:
                            break
            except (OSError, ValueError):
                pass
            finally:
                with contextlib.suppress(OSError):
                    ffmpeg.stdin.close()

        threading.Thread(target=feed, name=f"eccam-rec-{job_id[:8]}", daemon=True).start()
        try:
            self.close_connection = True
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            read1 = getattr(ffmpeg.stdout, "read1", ffmpeg.stdout.read)
            while True:
                chunk = read1(65536)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with contextlib.suppress(OSError):
                ffmpeg.kill()
            with contextlib.suppress(OSError, subprocess.TimeoutExpired):
                ffmpeg.wait(timeout=2)

    # ---------- diagnóstico ----------
    def _stream_status(self, query: dict) -> None:
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
        with contextlib.suppress(ValueError, AttributeError):
            if state is not None and state.playback_busy(int(query.get("cam", ["0"])[0])):
                message = "playback in progress"
        if message == "playback in progress":
            kind = "playback"
        elif "device offline" in message:
            kind = "offline"
        elif "timed out" in message:
            kind = "silent"
        elif message:
            kind = "error"
        self.send_json({"ok": True, "kind": kind, "error": message})

    def _diag(self) -> None:
        state = self.context.current_state()
        workers = []
        if state is not None:
            with state.workers_lock:
                items = list(state.workers.items())
            workers = [{"key": str(key), **worker.diagnostics()} for key, worker in items]
        self.send_json({
            "ok": True,
            "version": APP_VERSION,
            "build_date": BUILD_DATE,
            "ffmpeg": os.environ.get("TOPO_FFMPEG"),
            "workers": workers,
        })

    def _playtest(self, query: dict) -> None:
        state = self.context.current_state()
        if state is None:
            self.send_json({"ok": False, "error": "Conecta la cuenta Tapo primero."}, 409)
            return
        import eccam_playtest

        try:
            index = int(query.get("cam", ["0"])[0])
            state.devices[index]
            start = int(query.get("start", [""])[0])
            end = int(query.get("end", [""])[0])
        except (ValueError, IndexError):
            self.send_json({"ok": False, "error": "Usa ?cam=N&start=UNIX&end=UNIX"}, 400)
            return
        self.send_json({"ok": True, **eccam_playtest.run(state, index, start, end)})

    def _sdtest(self, query: dict) -> None:
        state = self.context.current_state()
        if state is None:
            self.send_json({"ok": False, "error": "Conecta la cuenta Tapo primero."}, 409)
            return
        import eccam_sdtest

        try:
            index = int(query.get("cam", ["0"])[0])
            state.devices[index]
            date = query.get("date", [""])[0]
            if not (len(date) == 8 and date.isdigit()):
                raise ValueError
        except (ValueError, IndexError):
            self.send_json({"ok": False, "error": "Usa ?cam=N&date=AAAAMMDD"}, 400)
            return
        self.send_json({"ok": True, **eccam_sdtest.run(state, index, date)})

    def _relaytest(self, query: dict) -> None:
        state = self.context.current_state()
        if state is None:
            self.send_json({"ok": False, "error": "Conecta la cuenta Tapo primero."}, 409)
            return
        import eccam_relaytest

        try:
            index = int(query.get("cam", ["0"])[0])
            state.devices[index]
        except (ValueError, IndexError):
            self.send_json({"ok": False, "error": "Cámara inválida."}, 400)
            return
        self.send_json({"ok": True, **eccam_relaytest.run(state, index)})


# ---------------------------------------------------------------------------
# Inicio
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=f"EC-Cam {APP_VERSION} — cámaras Tapo en la PC")
    parser.add_argument("--port", type=int, help=f"puerto (por defecto {DEFAULT_PORT})")
    parser.add_argument("--fresh-login", action="store_true", help="olvidar la sesión de Tapo guardada")
    parser.add_argument("--no-browser", action="store_true", help="no abrir el navegador al iniciar")
    parser.add_argument("--version", action="version", version=f"EC-Cam {APP_VERSION} {BUILD_DATE}".strip())
    args = parser.parse_args()

    config = load_config()
    _cleanup_old_login_files()
    port = args.port if args.port is not None else int(config["port"])
    local_url = f"http://127.0.0.1:{port}/"

    handler_class = type("EcCamRequestHandler", (EcCamHandler,), {"port": port})
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), handler_class)
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

    print(f"EC-Cam {APP_VERSION} ({BUILD_DATE or 'desarrollo'}) en {local_url}", flush=True)
    print(f"Datos: {HOME}", flush=True)
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
