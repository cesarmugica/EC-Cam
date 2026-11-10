# Cómo se conecta EC-Cam con la nube de Tapo

TP-Link **no tiene una API oficial** para ver cámaras Tapo desde la nube. EC-Cam imita a la app oficial de Android (Tapo 3.21.114), usando lo que descifraron [Topo](https://github.com/filirnd/topo) y [tapo-view](https://github.com/tothi/tapo-view), más lo que se comprobó con cámaras reales. Este documento explica cada paso, dónde está en el código y qué revisar si TP-Link cambia algo.

> Los valores secretos (llaves de la app, tokens) no se copian aquí: viven en el código o se generan al iniciar sesión.

## Mapa general

```
                 ┌─────────────── 1. Login + MFA ───────────────┐
EC-Cam (tu PC) ──┤  n-wap-gw.tplinkcloud.com  /api/v2/account/…  │──► token de sesión
                 └───────────────────────────────────────────────┘
        │  2. Lista de cámaras ........ /api/v2/common/getDeviceListByPage
        │  3. Descubrir servicios ..... /api/v2/common/getAppServiceUrl
        │        ├─ cipc.api.cloud ............ (video: pide el relay)
        │        └─ nbu.iot-app-server.app .... (control: privacidad, PTZ, SD)
        │
        ├─ 4. Control ──► {iot-app-server}/v2/things/{deviceId}/services-sync
        │
        └─ 5. Video ───► {cipc}/v2/relay/request ──► relayUrl + relayToken
                              │
                              ▼
              TLS a *.dcipc.i.tplinkcloud.com:443  (POST multipart en ambos sentidos)
                 cliente → cámara: petición de vista previa, confirmaciones, latido
                 cámara → cliente: respuesta JSON + partes video/mp2t (MPEG-TS H.264)
```

## Dónde está en el código

| Paso | Archivo | Función |
|---|---|---|
| Firma de peticiones | `tapo_cloud_probe.py` | `TapoCloud._headers`, `post` |
| Login, región, MFA | `tapo_cloud_probe.py` | `login`, `request_mfa`, `verify_mfa` |
| Sesión guardada | `tapo_cloud_probe.py` | `save_session`, `load_session`, `terminal_uuid_path` |
| Lista de cámaras | `tapo_cloud_probe.py` | `list_cameras` |
| Descubrir servicios | `tapo_cloud_probe.py` | `discover_cipc_url`, `discover_iot_app_server` |
| Control de la cámara | `tapo_cloud_probe.py` | `services_sync` (+ `get/set_privacy_mode`, `move_motor`, `ptz_supported`) |
| Video en vivo | `tapo_cloud_app.py` | `CloudMediaWorker._relay_once`, `client_part` |
| Pre-conexión | `tapo_cloud_probe.py` | `probe_cipc_preconnection` (botón «Probar conexión») |
| Grabaciones SD | `tapo_cloud_probe.py` | `recording_dates`, `recordings_for_day`, `download_recording` |
| Certificados de TP-Link | `certs/tapo-cloud-roots.pem` | `create_verify_context` |
| Pruebas de diagnóstico | `eccam_relaytest.py`, `eccam_server.py` | `/api/app/relaytest`, `/api/app/diag` |

## 1. Firma de las peticiones (API de cuenta)

Todas las llamadas a `https://n-wap-gw.tplinkcloud.com` (o a la URL regional) son `POST` con JSON compacto y estas cabeceras:

| Cabecera | Valor |
|---|---|
| `Content-Type` | `application/json; charset=UTF-8` |
| `Content-MD5` | Base64 del MD5 del cuerpo |
| `X-Authorization` | `Timestamp=9999999999, Nonce=<uuid>, AccessKey=<ACCESS_KEY>, Signature=<firma>` |
| `User-Agent` | `okhttp/3.12.13` |

`firma = HMAC-SHA1(ACCESS_SECRET, Content-MD5 + "\n" + Timestamp + "\n" + Nonce + "\n" + endpoint)` en hexadecimal. `ACCESS_KEY` y `ACCESS_SECRET` son las llaves **de la app Android** (no de tu cuenta) y están al inicio de `tapo_cloud_probe.py`. Después del login, el token va como parámetro `?token=…` en la URL.

**Si TP-Link cambia las llaves de la app**, el login empieza a fallar con un código de error de firma: hay que conseguir las nuevas (revisar Topo, tapo-view u otros proyectos) y actualizarlas junto con `APP_VERSION`.

## 2. Login y verificación en dos pasos

`POST /api/v2/account/login` con `appType` (`TP-Link_Tapo_Android`), `appVersion`, `cloudUserName`, `cloudPassword`, `platform`, `terminalName`, `terminalUUID` y `terminalMeta: "1"`.

- **Región:** si la respuesta trae el código `-20212` y un `appServerUrl`, la cuenta es de otra región: se repite el login en esa URL y se usa como base en adelante.
- **Verificación en dos pasos:** si llega `MFAProcessId`, se pide el código con `getPushVC4TerminalMFA` (notificación en la app, tipo 1) o `getEmailVC4TerminalMFA` (correo, tipo 2) y se confirma con `checkMFACodeAndLogin` (`code`, `MFAProcessId`, `MFAType`, `terminalBindEnabled: true`).
- **`terminalUUID`** identifica a esta PC ante Tapo y se guarda en `state\terminal_uuid`. Si se conserva, Tapo puede no volver a pedir la verificación. Al cerrar sesión se borra a propósito.
- Se guarda `token` y `base_url` en `state\session.json`; al abrir EC-Cam se reutilizan sin volver a pedir la contraseña.

## 3. Cámaras y servicios

- `POST /api/v2/common/getDeviceListByPage` con `{"deviceTypeList":["SMART.IPCAMERA"],"index":0,"limit":20}`. Campos útiles de cada cámara: `deviceId`, `alias`, `deviceModel`, `fwVer`, `deviceType`, `appServerUrl`. **Ojo:** `status` vale 0 aunque la cámara funcione; no sirve para saber si está en línea.
- `POST /api/v2/common/getAppServiceUrl` con `{"serviceIds":["cipc.api.cloud"]}` y `["nbu.iot-app-server.app"]` devuelve las URL de video y de control.

> Limitación conocida: la lista pide 20 cámaras (`limit: 20`). Con más de 20 habría que paginar.

## 4. Control de la cámara (privacidad, PTZ, SD)

`POST {iot-app-server}/v2/things/{deviceId}/services-sync` (si responde 404/405/501, se usa `v1`). Cabeceras: `Authorization: ut|<token>`, `app-cid: app:TP-Link_Tapo_Android:<terminalUUID>`, `x-app-name`, `x-app-version`, `x-term-id`.

Cuerpo:
```json
{"serviceId":"passthrough","inputParams":{"requestData":{"method":"multipleRequest","params":{"requests":[ … ]}}}}
```

| Función | Método de la cámara | Parámetros |
|---|---|---|
| Leer privacidad | `getLensMaskConfig` | `{"lens_mask":{"name":["lens_mask_info"]}}` |
| Cambiar privacidad | `setLensMaskConfig` | `{"lens_mask":{"lens_mask_info":{"enabled":"on"\|"off"}}}` |
| ¿Tiene PTZ? | `getAppComponentList` | busca el componente `ptz` |
| Mover | `motorMove` | `{"motor":{"move":{"x_coord":"10","y_coord":"0"}}}` |
| Zona horaria | `getTimezone` | `{"system":{"name":"basic"}}` |
| Estado de la SD | `getSdCardStatus` | `{"harddisk_manage":{"table":["hd_info"]}}` |
| Días con grabación | `searchDateWithVideo` | `playback.search_year_utility` |
| Usuario de reproducción | `getUserID` | `{"system":{"get_user_id":"null"}}` |
| Clips de un día | `searchVideoOfDay` | `playback.search_video_utility` |

## 5. Video en vivo (la parte más delicada)

### 5.1 Pedir el relay

`POST {cipc}/v2/relay/request` con cabeceras `Authorization: <token>` (sin `ut|`), `X-Client-Id: <playerId>`, `X-Source: tapo-app`, `X-Brand: TPLINK`, `X-Ca-Type: cloud-self`, `X-Request-Signature: <10 hex al azar>`.

```json
{"deviceId":"…","dataTimeoutCount":0,"cloudType":2,"deviceType":"SMART.IPCAMERA",
 "playerId":"<uuid>","rootCaVer":"1","streamType":0,"preConnection":0,"resolution":"HD"}
```
- `cloudType` 2 = nube IoT actual (1 es la vieja y contesta «device offline»).
- `streamType` 0 = en vivo; 1 = grabación de la SD.
- `resolution` `HD` o `SD` (EC-Cam usa HD y, si la cámara rechaza SD, cambia a HD sola).

La respuesta trae `relayUrl`, `relayToken`, `relayBusinessUrl`, `cdnUrl`, `elbCookie`, `relayIp`, `quicEnable` y `concurrentType` (`cdn_quic`, `node_https`, `cdn_https`). EC-Cam usa `relayUrl` por HTTPS. La app oficial puede probar varias rutas a la vez, entre ellas QUIC; si algún día `relayUrl` deja de servir, la prueba de diagnóstico ya intenta `relayBusinessUrl` y `cdnUrl`.

### 5.2 Abrir el relay

TLS a `relayUrl` (puerto 443) y un único `POST` que nunca termina:

```
POST /relayservice?…&retryTime=0 HTTP/1.1
Host: use1-relay-i-….dcipc.i.tplinkcloud.com
User-Agent: Client=TP-Link_Tapo_Android Android 3.21.114/1.3
Keep-Relay: 3600
Content-Type: multipart/mixed;boundary=--client-stream-boundary--
Content-Length: 9223372036854775807
X-token: <relayToken>
X-Client-UUID: <playerId>
X-Redirect-Times: 0
X-Pull-Mode: 2
X-Version: 2.0
X-Arrive-Latency: 0
Cookie: <elbCookie>                (solo si viene)
X-Client-SessionID: <sessionToken> (solo si viene y es distinto del relayToken)
```

El relay responde `HTTP/1.1 200 OK` con `Content-Type: multipart/mixed; boundary=--device-stream-boundary--` y la cabecera `pre_connection: 0|1`.

### 5.3 Conversación por el relay (imprescindible desde los firmwares nuevos)

Cada parte que manda el cliente:
```
----client-stream-boundary--\r\n
Content-Type: application/json\r\n
Content-Length: <bytes>\r\n
[cabeceras extra]\r\n
\r\n
<json>\r\n
```

| Cuándo | JSON | Cabeceras extra |
|---|---|---|
| Al conectar | `{"type":"request","seq":1,"params":{"method":"get","preview":{"channels":[0],"resolutions":["HD"],"audio":["default"]}}}` | `X-Data-Window-Size: 50` |
| Cada 25 partes de video | `{"type":"notification","params":{"event_type":"stream_sequence"}}` | `X-Data-Received: <n>`, `X-Session-Id: <id>` |
| Cada 20 s | `{"type":"notification","params":{"event_type":"heartbeat"}}` | — |

La cámara contesta:
- Una parte `application/json`: `{"type":"response","seq":1,"params":{"error_code":0,"session_id":"171"}}`.
- Partes `video/mp2t` con `X-Data-Sequence` y `X-Session-Id`: MPEG-TS con video H.264 y audio G.711 µ-law a 16 kHz.

**Por qué importa:** los firmwares viejos mandan video aunque nadie lo pida. El **C200 1.3.17 build 58281** no manda nada hasta recibir la petición de vista previa: abre la conexión y se queda callado. Antes de EC-Cam 1.0.6 esas cámaras solo se veían si la app oficial las estaba viendo al mismo tiempo. La ventana de 50 sin confirmaciones también puede detener el video a medio camino.

### 5.4 Cómo lo procesa EC-Cam

FFmpeg toma el MPEG-TS y lo reempaqueta **sin recodificar** a MP4 fragmentado (`-c:v copy`, un fragmento por cuadro). EC-Cam reparte solo fragmentos completos, guarda desde el último cuadro clave para que un visor nuevo entre al instante, desconecta a los visores demasiado lentos y cierra el relay si nadie mira durante 20 s. El audio se extrae del TS y se convierte a MP3 solo cuando alguien lo activa.

### 5.5 Respuestas conocidas del relay

| Lo que se ve | Significado | Mensaje en EC-Cam |
|---|---|---|
| `500` + `{"errorCode":-1007,"closeReason":"device offline"}` | La cámara no está conectada a la nube | «Cámara sin conexión (según Tapo)» |
| `200` y luego nada por 20 s | La cámara no envía video (antes: faltaba la petición de vista previa) | «La cámara no está enviando video» |
| Parte con `X-If-Encrypt: 1` | Video cifrado; EC-Cam no sabe descifrarlo | error «relay video is encrypted» en el log |
| JSON con `error_code` ≠ 0 | La cámara rechazó la vista previa | error «camera rejected preview» en el log |
| `500` + `{"errorCode":-52207,"closeReason":"passthrough fail"}` | El relay no pudo pasarle la petición a la cámara (p. ej. ya está ocupada con otro relay) | se reintenta |

## 6. Pre-conexión

`POST {cipc}/v2/relay/preConnectionBatchRequest` con `{"playerId":…,"requestList":[{…igual que relay/request…, "preConnection":1}]}`. Devuelve `preConnRespInfoList[0].relayAccessInfo` con los mismos campos del relay y `preConnIdleTime: 300`. EC-Cam lo usa solo para el botón «Probar conexión»; con las cámaras probadas no hizo falta para el video.

## 7. Grabaciones de la SD

1. `getSdCardStatus` + `searchDateWithVideo` → días con grabaciones.
2. `getUserID` → `user_id`; `searchVideoOfDay` → clips del día.
3. `relay/request` con `streamType: 1`, `trackId` y `customParams: {"audio_config":{"encode_type":"G711ulaw","sample_rate":"16"}}`. Al abrir el relay cambian las cabeceras: `X-Client-Model: OnTapo`, `X-Track-Id`, `X-Compete: 1`, `X-Arrive-Latency: 200`.
4. **Antes, apagar el en vivo de esa cámara.** La C200 no da en vivo y grabación a la vez: si hay un relay en vivo abierto, el de reproducción responde `500` con `{"errorCode":-52207,"closeReason":"passthrough fail"}`. EC-Cam cierra el en vivo, espera 2.5 s y reintenta hasta 3 veces si sigue ocupada; mientras tanto no deja abrir el en vivo de esa cámara.
> **Compatibilidad comprobada (2026-11-09) con `/api/app/playtest`:** C200 1.9.1 ✓ reproduce; C200 1.3.17 build 58281 ✗ `-52402` con todas las variantes. Si la cámara no entiende la petición (horas como número, sin `event_type`/`scale`), no contesta nada.

5. Por el relay se manda `{"type":"request","seq":N,"params":{"playback":{…"start_time","end_time","event_type":[1,2]…},"method":"get"}}` y al terminar el mismo con `"method":"stop"`, porque la cámara solo atiende **una reproducción a la vez**. También aquí hay que confirmar lo recibido (`stream_sequence`; ventana de 40). Topo pedía `"channels":[0,1]`; si la cámara lo rechaza, EC-Cam reintenta con `[0]`.

> **Pedir los clips por páginas.** Con `end_index: 999999999` (todo el día de una vez) y muchos clips, la nube de Tapo devuelve `{"outputParams":{}}` vacío: la respuesta es demasiado grande. EC-Cam pide páginas de 50 (`start_index` 0–49, 50–99, …) hasta que una trae menos de 50. `id` debe ser el número de `getUserID`: como texto o sin él, la cámara responde `-71112`. Cada clip trae `startTime`, `endTime` (segundos Unix) y `vedio_type` (así, con la errata; `"1"` = continua, `"2"` = movimiento).

## 8. Si deja de funcionar

**Primero, ubicar dónde se rompió:**

| Síntoma | Paso probable | Dónde mirar |
|---|---|---|
| No deja iniciar sesión | 1–2 (firma, llaves, login) | código de error en pantalla y en `logs\eccam.log` |
| Entra pero no salen cámaras | 3 (lista o servicios) | `logs\eccam.log` |
| Cámaras listadas, pero privacidad o PTZ fallan | 4 (`services-sync`) | mensaje «cloud control rejected» |
| Ninguna cámara da video | 5.1–5.2 | `http://127.0.0.1:8790/api/app/diag` |
| Solo algunas cámaras dan video | 5.3 (firmware) | `diag` y `relaytest` de esa cámara; anotar `fwVer` |

**Herramientas de diagnóstico** (abrirlas en el navegador de la PC donde corre EC-Cam):
- `http://127.0.0.1:8790/api/app/diag`: estado de cada cámara (firmware, si hay relay abierto, último error, hace cuánto llegaron datos).
- `http://127.0.0.1:8790/api/app/relaytest?cam=N`: prueba la cámara N con varias rutas (`relayUrl`, `relayBusinessUrl`, `cdnUrl`, con y sin `customParams`) y muestra qué contesta el relay, sin tokens. Tarda alrededor de un minuto.
- `%LOCALAPPDATA%\EC-Cam\logs\eccam.log`: cada falla de cámara queda como `EC-Cam: <cámara> [HD] falla #n: <motivo>`.

**Una pista muy útil:** si una cámara no se ve en EC-Cam pero sí aparece **mientras la app oficial la está viendo**, el relay y la cuenta funcionan, y lo que falta es algo que la app manda por el relay (así se descubrió el punto 5.3).

**Dónde buscar cambios:**
1. Los proyectos de referencia: [filirnd/topo](https://github.com/filirnd/topo) y [tothi/tapo-view](https://github.com/tothi/tapo-view). Comparar sus últimos cambios con `tapo_cloud_probe.py` y `tapo_cloud_app.py`.
2. Subir `APP_VERSION` (versión de la app Android que se imita) si TP-Link empieza a rechazar versiones viejas.
3. Si cambian los certificados del relay, actualizar `certs/tapo-cloud-roots.pem`.

## Historial de cambios del protocolo

| Fecha | Qué pasó | Arreglo |
|---|---|---|
| 2026-11-09 | El C200 1.3.17 build 58281 abre el relay pero no manda video | EC-Cam 1.0.6: petición de vista previa, confirmaciones y latido (5.3) |
| 2026-11-09 | Topo trataba las respuestas JSON de la cámara como video | EC-Cam 1.0.6: se separan por `Content-Type` |
| 2026-11-09 | Días con muchos clips: la búsqueda de grabaciones regresaba vacía | EC-Cam 1.1.2: búsqueda por páginas de 50 (punto 7) |
| 2026-11-09 | Reproducir una grabación con el en vivo abierto: `-52207 passthrough fail` | EC-Cam 1.1.5: se apaga el en vivo antes de reproducir (punto 7) |
| 2026-11-09 | C200 1.3.17 build 58281: la reproducción responde `{"error_code":-52402}` con cualquier variante (seq, canales, horas numéricas, sin `event_type`/`scale`, otro `X-Client-Model`); el C200 1.9.1 acepta la misma petición y manda video | **Sin resolver.** EC-Cam 1.1.7 muestra un mensaje claro. Pista: la app oficial debe usar otra petición para ese firmware |

## Fuentes

- [Topo](https://github.com/filirnd/topo), licencia MIT: login, firma, relay, control y grabaciones.
- [tapo-view](https://github.com/tothi/tapo-view): protocolo multipart de vista previa, confirmaciones y latido.
- Pruebas con cámaras reales (C200 firmwares 1.3.17 y 1.9.1, C500 1.3.5) en noviembre de 2026.
