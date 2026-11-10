# EC-Cam

**Español** · [English](#english)

Ver tus cámaras **Tapo** en la PC, sin emulador de Android y sin la app del celular.

| | |
|---|---|
| ⬇️ **Descargar** | [Última versión](https://github.com/cesarmugica/EC-Cam/releases/latest) · [Historial de versiones](CHANGELOG.md) |
| 📖 **Documentación** | [Cómo se conecta con la nube de Tapo](docs/PROTOCOLO-TAPO.md) · [Reporte para el autor de Topo](docs/reporte-topo/) |

- Video en vivo, audio, mover la cámara (pan/tilt), modo privacidad y pantalla completa.
- Grabaciones de la memoria SD: línea de tiempo, reproducir y descargar en MP4.
- Funciona desde cualquier lugar con internet: se conecta por la nube de Tapo, igual que la app oficial. No hace falta estar en la misma red que las cámaras, abrir puertos ni usar VPN.
- Ligero: transmite solo la cámara que estás viendo.
- En **español o inglés**: se elige en la app (🌐) y en el instalador.

El motor de video viene de [Topo](https://github.com/filirnd/topo) (licencia MIT, ver `LICENSE-TOPO.txt`). El protocolo de vista previa para los firmwares nuevos está documentado por [tapo-view](https://github.com/tothi/tapo-view).

## Instalar

1. Descarga `EC-Cam-Setup-x.y.z.exe` de la [última versión](https://github.com/cesarmugica/EC-Cam/releases/latest) y ejecútalo. Elige el idioma. No pide permisos de administrador.
   - Si Windows muestra «Windows protegió tu PC»: **Más información → Ejecutar de todas formas** (el instalador no está firmado).
2. Se abre EC-Cam en su propia ventana. Entra con el **correo y la contraseña de tu cuenta Tapo** (los mismos de la app del celular) y completa la verificación en dos pasos si la pide.
3. Listo. La próxima vez entras directo: EC-Cam guarda la sesión de Tapo en tu PC (nunca la contraseña).

Opcional: con el botón **⤓ Instalar app** (Chrome o Edge) se instala **EC-Cam Web**, que abre en su propia ventana como un programa más. El acceso **EC-Cam** del escritorio es el del instalador: arranca el servicio y abre EC-Cam en su propia ventana (Edge o Chrome en modo aplicación, sin barra de direcciones).

En el escritorio queda **EC-Cam** y en el menú Inicio **Iniciar EC-Cam**, **Detener servicio EC-Cam** y **Carpeta de datos de EC-Cam**. Si marcaste la opción al instalar, el servicio arranca con Windows.

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

GitHub Actions compila el instalador en cada push a `main` y publica un Release cuando cambia `APP_VERSION` en `src/eccam_server.py`. Para compilar a mano en Windows (Python 3.12 + Inno Setup 6):

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\build.ps1
```

```
EC-Cam/
├── README.md                 este archivo
├── CHANGELOG.md              historial de versiones
├── LICENSE-TOPO.txt          licencia MIT de Topo
├── docs/
│   ├── PROTOCOLO-TAPO.md     cómo se conecta con la nube de Tapo y qué hacer si cambia
│   └── reporte-topo/         hallazgos para el autor de Topo (issue en inglés)
├── src/                      el programa
│   ├── eccam_server.py       servidor local (rutas, idioma, seguridad, diagnóstico)
│   ├── tapo_cloud_app.py     motor de Topo + mejoras: video, audio, PTZ, grabaciones
│   ├── tapo_cloud_probe.py   motor de Topo: API de la nube Tapo y verificación en dos pasos
│   ├── eccam_*test.py        pruebas de diagnóstico (relay, búsqueda y reproducción de la SD)
│   ├── certs/                certificados raíz de TP-Link
│   └── web/                  index.html (es), index.en.html (en), PWA, íconos
├── tools/
│   ├── build_index.py        genera index.html e index.en.html desde la plantilla de Topo
│   ├── i18n_en.py            diccionario español → inglés (avisa si falta algo)
│   ├── stream_client.js, viewer.js, index_extra.js   partes de EC-Cam que se insertan en la página
│   ├── make_icons.py         íconos
│   └── plantilla/            index.html original de Topo
└── windows/                  build.ps1, eccam.iss (Inno Setup) y ejecutar-desarrollo.bat
```

Si cambias la interfaz: edita `tools/` (no `src/web/index*.html`, que se generan) y corre `python tools/build_index.py`. Si agregas textos en español, agrégalos también en `tools/i18n_en.py`; el generador avisa de lo que quede sin traducir.

Diagnóstico: `http://127.0.0.1:8790/api/app/diag` muestra el estado de cada cámara.

**Cómo funciona la conexión con la nube de Tapo** (endpoints, protocolo del video y qué hacer si TP-Link cambia algo): [docs/PROTOCOLO-TAPO.md](docs/PROTOCOLO-TAPO.md).

## Limitaciones

- Usa endpoints no documentados de la nube Tapo; si TP-Link los cambia, puede dejar de funcionar hasta actualizarse (ver [docs/PROTOCOLO-TAPO.md](docs/PROTOCOLO-TAPO.md)).
- Probado con Tapo C200 (firmwares 1.3.17 y 1.9.1) y C500.
- Reproducir grabaciones de la SD no funciona con el C200 firmware 1.3.17 build 58281 (la cámara responde -52402); con el 1.9.1 sí. Ver [docs/PROTOCOLO-TAPO.md](docs/PROTOCOLO-TAPO.md).

---

## English

See your **Tapo** cameras on your Windows PC, without an Android emulator or the phone app.

- Live video, audio, pan/tilt, privacy mode and full screen; one camera at a time, so it stays light.
- SD card recordings: timeline, play while downloading, download as MP4.
- Works from anywhere: it connects through the Tapo cloud like the official app. No port forwarding or VPN.
- Spanish or English (🌐 selector in the app; also chosen in the installer).

**Install:** download `EC-Cam-Setup-x.y.z.exe` from the [latest release](https://github.com/cesarmugica/EC-Cam/releases/latest), run it (no admin needed; if SmartScreen warns, choose *More info → Run anyway*), and sign in with your Tapo account. EC-Cam only stores the session on your PC, never the password, and it only answers on `127.0.0.1`.

**Docs:** how the Tapo cloud connection works and what to check if TP-Link changes it: [docs/PROTOCOLO-TAPO.md](docs/PROTOCOLO-TAPO.md) (Spanish). Findings shared with the Topo author: [docs/reporte-topo/](docs/reporte-topo/) (English).

Video engine based on [Topo](https://github.com/filirnd/topo) (MIT). Preview protocol for newer firmware documented by [tapo-view](https://github.com/tothi/tapo-view).
