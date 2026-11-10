"""EC-Cam: prueba de diagnóstico de la conexión de video con la nube de Tapo.

Ensaya varias formas de abrir el relay de una cámara y reporta qué contesta
Tapo (sin mostrar tokens) y si llegan datos de video. Solo para administradores.
"""

from __future__ import annotations

import socket
import time
import uuid
from urllib.parse import urlsplit

from tapo_cloud_probe import error_code, result_of

SECRET_HEADERS = {"x-token", "cookie", "set-cookie", "authorization"}


def _relay_from_request(client, base_url: str, device: dict, pre: int, resolution: str, player_id: str) -> tuple[dict, dict]:
    client.discover_cipc_url(base_url)
    param = {
        "deviceId": str(device.get("deviceId") or ""),
        "dataTimeoutCount": 0,
        "cloudType": 2,
        "deviceType": device.get("deviceType") or "SMART.IPCAMERA",
        "playerId": player_id,
        "rootCaVer": "1",
        "streamType": 0,
        "preConnection": pre,
        "resolution": resolution,
    }
    response = client.post_cipc("/v2/relay/request", param, player_id)
    return response, result_of(response)


def _relay_from_preconnection(client, base_url: str, device: dict, resolution: str, player_id: str) -> tuple[dict, dict]:
    client.discover_cipc_url(base_url)
    param = {
        "deviceId": str(device.get("deviceId") or ""),
        "cloudType": 2,
        "deviceType": device.get("deviceType") or "SMART.IPCAMERA",
        "playerId": player_id,
        "rootCaVer": "1",
        "streamType": 0,
        "preConnection": 1,
        "resolution": resolution,
    }
    response = client.post_cipc(
        "/v2/relay/preConnectionBatchRequest", {"playerId": player_id, "requestList": [param]}, player_id
    )
    result = response.get("result") if isinstance(response.get("result"), dict) else response
    items = result.get("preConnRespInfoList") or []
    first = items[0] if isinstance(items, list) and items else {}
    info = first.get("relayAccessInfo") if isinstance(first, dict) else {}
    return response, info if isinstance(info, dict) else {}


def _describe(value: object) -> object:
    """Mostrar estructura sin secretos: llaves y valores cortos no sensibles."""
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(word in lowered for word in ("token", "cookie", "secret", "key", "url")):
                out[key] = f"<{type(item).__name__} {len(str(item))}>"
            else:
                out[key] = _describe(item)
        return out
    if isinstance(value, list):
        return [_describe(item) for item in value[:5]]
    return value


def _open_relay(client, device: dict, info: dict, player_id: str, pull_mode: str, seconds: float, redirects: int = 0) -> dict:
    relay_url = str(info.get("relayUrl") or info.get("url") or "")
    token = str(info.get("relayToken") or info.get("sessionToken") or info.get("token") or "")
    if not relay_url or not token:
        return {"error": "sin relayUrl o token", "info_keys": sorted(info)}
    parsed = urlsplit(relay_url if "://" in relay_url else "https://" + relay_url)
    host = parsed.hostname or ""
    path = (parsed.path or "/") + ("?" + parsed.query + "&retryTime=0" if parsed.query else "?retryTime=0")
    headers = {
        "Host": host,
        "User-Agent": "Client=TP-Link_Tapo_Android Android 3.21.114/1.3",
        "Keep-Relay": "3600",
        "Accept": "*/*",
        "Content-Type": "multipart/mixed;boundary=--client-stream-boundary--",
        "Content-Length": "9223372036854775807",
        "X-token": token,
        "X-Client-Model": str(device.get("deviceModel") or "C200"),
        "X-Client-UUID": player_id,
        "X-Redirect-Times": str(redirects),
        "X-Pull-Mode": pull_mode,
        "X-Version": "2.0",
        "X-Arrive-Latency": "0",
        "Connection": "Keep-alive",
    }
    if info.get("elbCookie"):
        headers["Cookie"] = str(info["elbCookie"])
    raw = (f"POST {path} HTTP/1.1\r\n" + "".join(f"{k}: {v}\r\n" for k, v in headers.items()) + "\r\n").encode()
    report: dict = {"host": host, "port": parsed.port or 443}
    started = time.monotonic()
    try:
        with socket.create_connection((host, parsed.port or 443), timeout=10) as plain:
            with client.verify_context.wrap_socket(plain, server_hostname=host) as tls:
                tls.settimeout(4)
                tls.sendall(raw)
                buffer = bytearray()
                while b"\r\n\r\n" not in buffer and len(buffer) < 65536:
                    chunk = tls.recv(8192)
                    if not chunk:
                        break
                    buffer.extend(chunk)
                head, _, rest = bytes(buffer).partition(b"\r\n\r\n")
                lines = head.decode("latin1", "replace").split("\r\n")
                report["status_line"] = lines[0] if lines else ""
                resp_headers = {}
                for line in lines[1:]:
                    key, _, value = line.partition(":")
                    resp_headers[key.strip()] = "<oculto>" if key.strip().lower() in SECRET_HEADERS else value.strip()[:160]
                report["headers"] = resp_headers
                report["headers_ms"] = round((time.monotonic() - started) * 1000)
                total = len(rest)
                first_data_ms = round((time.monotonic() - started) * 1000) if rest else None
                sample = rest[:300]
                deadline = time.monotonic() + seconds
                while time.monotonic() < deadline:
                    try:
                        chunk = tls.recv(65536)
                    except (socket.timeout, TimeoutError):
                        continue
                    if not chunk:
                        report["closed_by_relay"] = True
                        break
                    if first_data_ms is None:
                        first_data_ms = round((time.monotonic() - started) * 1000)
                    if len(sample) < 300:
                        sample += chunk[: 300 - len(sample)]
                    total += len(chunk)
                report["bytes"] = total
                report["first_data_ms"] = first_data_ms
                text = sample.decode("latin1", "replace").replace("\r\n", " | ")
                report["sample"] = "".join(c if 32 <= ord(c) < 127 else "." for c in text)[:140]
                # Seguir una redirección una vez, si Tapo la indica.
                location = next((v for k, v in resp_headers.items() if k.lower() in ("location", "x-redirect-url")), "")
                if location and redirects < 2 and location != "<oculto>":
                    report["redirect"] = _open_relay(
                        client, device, {**info, "relayUrl": location}, player_id, pull_mode, seconds, redirects + 1
                    )
    except OSError as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
    return report


def run(state, index: int, seconds: float = 8.0) -> dict:
    device = state.devices[index]
    client = state.client
    results = []
    plans = [
        ("request pre=0 HD pull=2", "request", 0, "HD", "2"),
        ("request pre=1 HD pull=2", "request", 1, "HD", "2"),
        ("preconnection HD pull=2", "preconn", 1, "HD", "2"),
        ("request pre=0 HD pull=1", "request", 0, "HD", "1"),
    ]
    for label, kind, pre, resolution, pull in plans:
        player_id = str(uuid.uuid4())
        entry: dict = {"plan": label}
        try:
            if kind == "request":
                response, info = _relay_from_request(client, state.base_url, device, pre, resolution, player_id)
            else:
                response, info = _relay_from_preconnection(client, state.base_url, device, resolution, player_id)
            entry["cloud_code"] = error_code(response)
            entry["relay_info"] = _describe(info)
            if info:
                entry["relay"] = _open_relay(client, device, info, player_id, pull, seconds)
        except Exception as exc:  # noqa: BLE001 - diagnóstico
            entry["error"] = f"{type(exc).__name__}: {exc}"
        results.append(entry)
    return {
        "camera": device.get("alias"),
        "model": device.get("deviceModel"),
        "firmware": device.get("fwVer"),
        "device": _describe({k: v for k, v in device.items() if k not in ("deviceId", "mac", "ip", "ssid")}),
        "results": results,
    }
