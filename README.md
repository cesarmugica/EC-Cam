# EC-Cam

Ver tus cámaras **Tapo** en la PC, sin emulador de Android y sin la app del celular.

- Video en vivo, audio, mover la cámara (pan/tilt), modo privacidad y pantalla completa.
- Grabaciones de la memoria SD: línea de tiempo, reproducir y descargar en MP4.
- Funciona desde cualquier lugar con internet: se conecta por la nube de Tapo, igual que la app oficial. No hace falta estar en la misma red que las cámaras, abrir puertos ni usar VPN.
- Ligero: transmite solo la cámara que estás viendo.

El motor de video viene de [Topo](https://github.com/filirnd/topo) (licencia MIT, ver `LICENSE-TOPO.txt`). El protocolo de vista previa para los firmwares nuevos está documentado por [tapo-view](https://github.com/tothi/tapo-view).

## Instalar

1. Descarga `EC-Cam-Setup-x.y.z.exe` de la sección **Releases** y ejecútalo. No pide permisos de administrador.
   - Si Windows muestra «Windows protegió tu PC»: **Más información → Ejecutar de todas formas** (el instalador no está firmado).
2. Se abre EC-Cam en el navegador. Entra con el **correo y la contraseña de tu cuenta Tapo** (los mismos de la app del celular) y completa la verificación en dos pasos si la pide.
3. Listo. La próxima vez entras directo: EC-Cam guarda la sesión de Tapo en tu PC (nunca la contraseña).

Opcional: con el botón **⤓ Instalar app** (Chrome o Edge) EC-Cam queda en su propia ventana, como un programa más.

En el menú Inicio quedan **Iniciar EC-Cam**, **Detener servicio EC-Cam** y **Carpeta de datos de EC-Cam**. Si marcaste la opción al instalar, el servicio arranca con Windows.

Si abres EC-Cam y el servicio está detenido, la página muestra **▶ Iniciar EC-Cam**: lo arranca con un clic y entra sola en cuanto está listo (la primera vez el navegador pregunta «¿Abrir EC-Cam?»).

## Uso

- **Visor:** muestra una cámara a la vez. Cambia con **◀ ▶**, con las flechas del teclado o haciendo clic en el mosaico de la derecha.
- **Mosaico:** todas tus cámaras, sin video, con la última imagen que viste de cada una.
- **Calidad:** HD por defecto; «Calidad ligera (SD)» gasta menos internet.
- **Pantalla completa:** doble clic sobre el video o el botón ⛶.
- Si una cámara está desconectada de la nube de Tapo, EC-Cam lo dice («Cámara sin conexión (según Tapo)») y reintenta cada minuto.

## Privacidad y seguridad

- EC-Cam corre en tu PC y solo responde dentro de ella (`127.0.0.1`); nadie más en tu red puede abrirlo.
- Rechaza peticiones de otras páginas web (protección contra *DNS rebinding* y CSRF).
- La contraseña de Tapo no se guarda; la sesión queda en `%LOCALAPPDATA%\EC-Cam\state\session.json`. Trátala como una llave: no la compartas.
- **Cerrar sesión de Tapo** borra esa sesión.

## Datos

Carpeta: `%LOCALAPPDATA%\EC-Cam\`

| Archivo | Qué es |
|---|---|
| `config.json` | `port` (8790) y `open_browser_on_start` |
| `state\session.json` | sesión de tu cuenta Tapo |
| `logs\eccam.log` | registro (útil si algo falla) |

## Problemas comunes

| Síntoma | Qué hacer |
|---|---|
| «Cámara sin conexión (según Tapo)» | La cámara no está conectada a internet: revisa su corriente y wifi. |
| «La cámara no está enviando video» | Prueba **Actualizar**; si sigue, revisa que la cámara se vea en la app Tapo. |
| El video se congela | Se reconecta solo; con internet lento usa «Calidad ligera (SD)». |
| «El servicio EC-Cam está detenido» | Botón **▶ Iniciar EC-Cam**, o menú Inicio → **Iniciar EC-Cam**. |

## Para desarrolladores

GitHub Actions compila el instalador en cada push a `main` y publica un Release cuando cambia `APP_VERSION` en `eccam_server.py`. Para compilar a mano en Windows (Python 3.12 + Inno Setup 6):

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\build.ps1
```

```
eccam_server.py        servidor local (rutas, seguridad, diagnóstico)
tapo_cloud_app.py      motor de Topo + mejoras: video, audio, PTZ, grabaciones
tapo_cloud_probe.py    motor de Topo: API de la nube Tapo y verificación en dos pasos
eccam_relaytest.py     prueba de conexión por cámara (/api/app/relaytest?cam=N)
web/                   index.html, manifest.json, sw.js, pwa.js, offline.html, img/
tools/                 build_index.py genera web/index.html desde el de Topo
windows/               build.ps1 e instalador (Inno Setup)
```

Diagnóstico: `http://127.0.0.1:8790/api/app/diag` muestra el estado de cada cámara.

**Cómo funciona la conexión con la nube de Tapo** (endpoints, protocolo del video y qué hacer si TP-Link cambia algo): [docs/PROTOCOLO-TAPO.md](docs/PROTOCOLO-TAPO.md).

## Limitaciones

- Usa endpoints no documentados de la nube Tapo; si TP-Link los cambia, puede dejar de funcionar hasta actualizarse (ver [docs/PROTOCOLO-TAPO.md](docs/PROTOCOLO-TAPO.md)).
- Probado con Tapo C200 (firmwares 1.3.17 y 1.9.1) y C500.
- Reproducir grabaciones de la SD no funciona con el C200 firmware 1.3.17 build 58281 (la cámara responde -52402); con el 1.9.1 sí. Ver [docs/PROTOCOLO-TAPO.md](docs/PROTOCOLO-TAPO.md).
