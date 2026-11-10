"""EC-Cam: diagnóstico de la búsqueda de grabaciones en la SD.

Manda la búsqueda de clips de un día (searchVideoOfDay) de varias formas y
devuelve la respuesta de la nube tal cual (recortada), para ver qué cambia en
los firmwares nuevos. Solo lectura: no reproduce ni borra nada.
"""

from __future__ import annotations

import json
import time
from urllib.parse import quote

MAX_TEXT = 2500


def _raw_services_sync(client, base_url: str, device: dict, requests: list[dict]) -> dict:
    """Como TapoCloud.services_sync, pero devuelve el JSON completo."""
    if not client.iot_app_server:
        client.discover_iot_app_server(base_url)
    envelope = {
        "inputParams": {"requestData": {"method": "multipleRequest", "params": {"requests": requests}}},
        "serviceId": "passthrough",
    }
    body = client._body(envelope)
    url = (
        client.iot_app_server.rstrip("/")
        + f"/{client._services_sync_version}/things/"
        + quote(str(device.get("deviceId") or ""), safe="")
        + "/services-sync"
    )
    started = time.monotonic()
    status, raw = client._persistent_post(url, body, client._iot_headers(), reuse=False)
    elapsed = round((time.monotonic() - started) * 1000)
    text = raw.decode("utf-8", "replace")
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError:
        decoded = None
    return {"http": status, "ms": elapsed, "bytes": len(raw), "json": decoded, "text": None if decoded is not None else text[:MAX_TEXT]}


def _summarize(result: dict) -> dict:
    """Recortar listas largas para que el reporte sea legible."""
    def shrink(value, depth=0):
        if isinstance(value, dict):
            return {k: shrink(v, depth + 1) for k, v in value.items()}
        if isinstance(value, list):
            items = [shrink(v, depth + 1) for v in value[:3]]
            if len(value) > 3:
                items.append(f"… +{len(value) - 3} más (total {len(value)})")
            return items
        return value
    out = dict(result)
    out["json"] = shrink(result.get("json"))
    return out


def run(state, index: int, date: str) -> dict:
    client, base_url, device = state.client, state.base_url, state.devices[index]
    report: dict = {"camera": device.get("alias"), "model": device.get("deviceModel"), "firmware": device.get("fwVer"), "date": date}

    user = _raw_services_sync(client, base_url, device, [{"method": "getUserID", "params": {"system": {"get_user_id": "null"}}}])
    report["getUserID"] = _summarize(user)
    user_id = None
    try:
        responses = user["json"]["outputParams"]["responseData"]["result"]["responses"]
        user_id = responses[0]["result"]["user_id"]
    except (KeyError, IndexError, TypeError):
        pass

    def search(**utility) -> dict:
        params = {"playback": {"search_video_utility": utility}}
        return _summarize(_raw_services_sync(client, base_url, device, [{"method": "searchVideoOfDay", "params": params}]))

    variants = {
        "como Topo (0..999999999)": dict(channel=0, date=date, end_index=999999999, id=int(user_id or 0), start_index=0),
        "página chica (0..49)": dict(channel=0, date=date, end_index=49, id=int(user_id or 0), start_index=0),
        "página chica, id texto": dict(channel=0, date=date, end_index=49, id=str(user_id or 0), start_index=0),
        "sin id": dict(channel=0, date=date, end_index=49, start_index=0),
    }
    report["searchVideoOfDay"] = {}
    for label, utility in variants.items():
        try:
            report["searchVideoOfDay"][label] = search(**utility)
        except Exception as exc:  # noqa: BLE001 - diagnóstico
            report["searchVideoOfDay"][label] = {"error": f"{type(exc).__name__}: {exc}"}
    return report
