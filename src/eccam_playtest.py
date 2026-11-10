"""EC-Cam: diagnóstico de la reproducción de grabaciones de la SD.

Prueba varias formas de la petición de reproducción (playback) por el relay de
Tapo y reporta qué contesta la cámara y si llega video. Solo lectura.
"""

from __future__ import annotations

import json
import socket
import time
import uuid
from urllib.parse import urlsplit

from tapo_cloud_probe import APP_NAME, APP_VERSION, error_code, result_of


def _frame(body: dict, extra: dict | None = None) -> bytes:
    raw = json.dumps(body, separators=(",", ":")).encode()
    head = ["----client-stream-boundary--", "Content-Type: application/json", f"Content-Length: {len(raw)}"]
    head += [f"{k}: {v}" for k, v in (extra or {}).items()]
    return ("\r\n".join(head) + "\r\n\r\n").encode() + raw + b"\r\n"


def _attempt(state, device: dict, client_id: int, start: int, end: int, variant: dict) -> dict:
    client = state.client
    client.discover_cipc_url(state.base_url)
    device_id = str(device.get("deviceId") or "")
    player_id = str(uuid.uuid4())
    track_id = f"eccam-playback-{device_id}-{start}"
    param = {
        "cloudType": 2,
        "customParams": '{"audio_config":{"encode_type":"G711ulaw","sample_rate":"16"}}',
        "dataTimeoutCount": 0,
        "deviceId": device_id,
        "deviceType": device.get("deviceType") or "SMART.IPCAMERA",
        "playerId": player_id,
        "preConnection": 0,
        "resolution": "HD",
        "rootCaVer": "1",
        "streamType": 1,
        "trackId": track_id,
    }
    response = client.post_cipc("/v2/relay/request", param, player_id)
    info = result_of(response)
    report: dict = {"cloud_code": error_code(response)}
    if error_code(response) != 0 or not info.get("relayUrl"):
        return report
    parsed = urlsplit(str(info["relayUrl"]))
    host = parsed.hostname or ""
    path = (parsed.path or "/") + ("?" + parsed.query + "&" if parsed.query else "?") + "retryTime=0"
    headers = {
        "Host": host,
        "User-Agent": f"Client={APP_NAME} Android {APP_VERSION}/1.3",
        "Accept": "*/*",
        "Keep-Relay": "3600",
        "Content-Type": "multipart/mixed;boundary=--client-stream-boundary--",
        "Content-Length": "9223372036854775807",
        "X-token": str(info.get("relayToken") or ""),
        "X-Client-Model": variant.get("model", "OnTapo"),
        "X-Client-UUID": player_id,
        "X-Track-Id": track_id,
        "X-Redirect-Times": "0",
        "X-Pull-Mode": "2",
        "X-Version": "2.0",
        "X-Arrive-Latency": "200",
        "Connection": "Keep-alive",
    }
    if variant.get("compete", True):
        headers["X-Compete"] = "1"
    if info.get("elbCookie"):
        headers["Cookie"] = str(info["elbCookie"])
    raw_head = (f"POST {path} HTTP/1.1\r\n" + "".join(f"{k}: {v}\r\n" for k, v in headers.items()) + "\r\n").encode()

    playback: dict = {"client_id": client_id, "channels": variant.get("channels", [0, 1])}
    if variant.get("scale", True):
        playback["scale"] = "1/1"
    if variant.get("int_times"):
        playback["start_time"], playback["end_time"] = start, end
    else:
        playback["start_time"], playback["end_time"] = str(start), str(end)
    if variant.get("event_type", True):
        playback["event_type"] = [1, 2]
    seq = variant.get("seq", 1)
    request = {"type": "request", "seq": seq, "params": {"playback": playback, "method": "get"}}
    report["request"] = request["params"]["playback"] | {"seq": seq}

    buffer = bytearray()
    video_bytes = 0
    responses = []
    started = time.monotonic()
    try:
        with socket.create_connection((host, parsed.port or 443), timeout=15) as plain:
            with client.verify_context.wrap_socket(plain, server_hostname=host) as sock:
                sock.settimeout(3)
                sock.sendall(raw_head + _frame(request, {"X-Data-Window-Size": "40"}))
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline and video_bytes < 200_000:
                    try:
                        chunk = sock.recv(65536)
                    except (socket.timeout, TimeoutError):
                        continue
                    if not chunk:
                        report["closed"] = True
                        break
                    buffer.extend(chunk)
                    while True:
                        head_end = buffer.find(b"\r\n\r\n")
                        if head_end < 0:
                            break
                        head = bytes(buffer[:head_end]).decode("latin1", "replace")
                        if head.startswith("HTTP/"):
                            report["status_line"] = head.split("\r\n", 1)[0]
                            del buffer[: head_end + 4]
                            continue
                        fields = {}
                        for line in head.split("\r\n"):
                            key, _, value = line.partition(":")
                            fields[key.strip().lower()] = value.strip()
                        length = int(fields.get("content-length", "0") or 0)
                        if len(buffer) < head_end + 4 + length:
                            break
                        body = bytes(buffer[head_end + 4 : head_end + 4 + length])
                        del buffer[: head_end + 4 + length]
                        if "json" in fields.get("content-type", ""):
                            responses.append(body.decode("utf-8", "replace")[:200])
                        elif "video" in fields.get("content-type", ""):
                            video_bytes += len(body)
                stop = {"type": "request", "seq": seq + 1, "params": {"playback": {"client_id": client_id, "channels": playback["channels"]}, "method": "stop"}}
                try:
                    sock.sendall(_frame(stop))
                except OSError:
                    pass
    except OSError as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
    report["camera_json"] = responses[:3]
    report["video_bytes"] = video_bytes
    report["seconds"] = round(time.monotonic() - started, 1)
    return report


def run(state, index: int, start: int, end: int) -> dict:
    device = state.devices[index]
    state.reset_worker(index)  # sin en vivo de esa cámara
    time.sleep(2.5)
    users = state.client.services_sync(
        state.base_url, device, [{"method": "getUserID", "params": {"system": {"get_user_id": "null"}}}], fresh_connection=True
    )
    client_id = int((users[0].get("result") or {}).get("user_id") or 0) if users else 0
    end = min(end, start + 30)
    variants = [
        ("como Topo (seq 1000+)", {"seq": 1000 + start % 20000}),
        ("seq 1", {"seq": 1}),
        ("seq 1, canal [0]", {"seq": 1, "channels": [0]}),
        ("seq 1, canal [0], horas numéricas", {"seq": 1, "channels": [0], "int_times": True}),
        ("seq 1, canal [0], sin event_type ni scale", {"seq": 1, "channels": [0], "event_type": False, "scale": False}),
        ("seq 1, X-Client-Model de la cámara, sin X-Compete", {"seq": 1, "model": str(device.get("deviceModel") or "C200"), "compete": False}),
    ]
    results = []
    for label, variant in variants:
        try:
            outcome = _attempt(state, device, client_id, start, end, variant)
        except Exception as exc:  # noqa: BLE001 - diagnóstico
            outcome = {"error": f"{type(exc).__name__}: {exc}"}
        results.append({"variant": label, **outcome})
        time.sleep(3)  # liberar la ranura de reproducción de la cámara
    return {"camera": device.get("alias"), "firmware": device.get("fwVer"), "client_id": client_id, "start": start, "end": end, "results": results}
