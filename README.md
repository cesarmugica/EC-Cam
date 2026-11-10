# EC-Cam

Ver tus cámaras **Tapo** en vivo desde cualquier lugar, en una página web que se instala como app (PWA), igual que DGPOS / DGPOSR.

- Video en vivo (baja latencia), audio, mover la cámara (pan/tilt), modo privacidad.
- Grabaciones de la memoria SD: línea de tiempo, reproducir y descargar en MP4.
- Login propio de EC-Cam, con usuarios **Administrador** y **Visor**.
- Se instala en el celular o la PC con el botón **Instalar** (Android, Chrome/Edge) o «Agregar a pantalla de inicio» (iPhone).
- No necesitas RTSP, abrir puertos ni VPN: el servidor habla con la nube de Tapo.

El motor de video viene de [Topo 0.1.7](https://github.com/filirnd/topo) (licencia MIT, ver `LICENSE-TOPO.txt`).

## Video ligero

- El mosaico va en **SD** (ligero); al abrir una cámara en pantalla completa cambia a **HD** y las demás se pausan. En el mosaico puedes elegir «Mosaico en HD».
- Solo se transmiten las cámaras que están en pantalla. Abriendo EC-Cam directo en la PC servidor (sin túnel) el navegador solo permite 6 conexiones, así que se ven 4 en vivo a la vez; las demás muestran «En pausa · toca para ver en vivo». Por el túnel de Cloudflare se ven hasta 12.
- Si la app pasa a segundo plano o se bloquea el celular, el video se detiene y no consume datos.
- Un visor nuevo entra al instante en el último cuadro clave, sin cortar el video de los demás.
- Si el video se congela, la página se reconecta sola; si la red es muy lenta, salta al punto en vivo en vez de acumular atraso.
- Si nadie ve una cámara durante 20 s, el servidor cierra su conexión con Tapo.

## Cómo funciona

```
Celular / PC  ──HTTPS──▶  Cloudflare Tunnel  ──▶  PC servidor (EC-Cam :8790)  ──▶  Nube Tapo  ──▶  Cámaras
```

Una PC de la casa u oficina corre el **servidor EC-Cam** (sin ventana, arranca con Windows). Esa PC guarda la sesión de Tapo y convierte el video con FFmpeg. Cloudflare Tunnel publica el servidor en internet con HTTPS, sin abrir puertos en el módem.

## Instalar en la PC servidor

1. Ejecuta `EC-Cam-Setup-x.y.z.exe`. No pide permisos de administrador.
   - Si Windows muestra «Windows protegió tu PC»: **Más información → Ejecutar de todas formas** (el instalador no está firmado).
   - Si el Firewall de Windows pregunta, permite **redes privadas** (sirve para entrar desde otros equipos de la misma red).
2. Al terminar se abre `http://127.0.0.1:8790/setup`: crea el **usuario administrador** de EC-Cam.
   (La configuración inicial solo funciona en la propia PC servidor, nunca a través de internet).
3. Conecta tu **cuenta Tapo** (correo y contraseña de Tapo + verificación en dos pasos si la pide). La contraseña de Tapo no se guarda; solo la sesión.
4. Publica el servidor en internet: ver [docs/TUNEL.md](docs/TUNEL.md).
5. Desde tu celular abre `https://camaras.tudominio.com`, entra y toca **Instalar**.

En el menú Inicio quedan: **EC-Cam** (inicia y abre), **Detener servidor EC-Cam** y **Carpeta de datos de EC-Cam**.

## Usuarios

| | Visor | Administrador |
|---|:---:|:---:|
| Ver en vivo, audio, pantalla completa | ✓ | ✓ |
| Mover la cámara | ✓ | ✓ |
| Grabaciones de la SD (ver/descargar) | ✓ | ✓ |
| Activar / quitar privacidad | | ✓ |
| Conectar / desconectar la cuenta Tapo | | ✓ |
| Administrar usuarios | | ✓ |

Se administran desde **👥 Usuarios** en la página. Cada quien cambia su contraseña en **⚙ Cuenta**.

Si se pierde la contraseña del administrador, en la PC servidor:

```bat
"%LOCALAPPDATA%\Programs\EC-Cam\eccam-server.exe" --reset-password NOMBRE
"%LOCALAPPDATA%\Programs\EC-Cam\eccam-server.exe" --add-user NOMBRE --role admin
"%LOCALAPPDATA%\Programs\EC-Cam\eccam-server.exe" --list-users
```

## Seguridad

- Contraseñas de EC-Cam con PBKDF2-SHA256 (310 000 iteraciones); nunca en texto plano.
- Sesión en cookie `HttpOnly`, `SameSite=Lax` y `Secure` cuando llega por HTTPS; dura 30 días y se renueva con el uso. En disco solo se guarda el hash del token.
- Bloqueo de 15 minutos tras 5 intentos fallidos desde la misma IP (o 20 contra el mismo usuario).
- Protección CSRF: todas las acciones exigen JSON y mismo origen.
- El reproductor nativo de Topo (abre ventanas en la PC) está desactivado.
- Trata la carpeta de datos como una llave: contiene la sesión de Tapo.

## Datos y configuración

Carpeta: `%LOCALAPPDATA%\EC-Cam\`

| Archivo | Qué es |
|---|---|
| `config.json` | `host`, `port` (8790), `trust_local_proxy`, `open_browser_on_start` |
| `users.json` | usuarios de EC-Cam (hash de contraseñas) |
| `sessions.json` | sesiones abiertas (hash del token) |
| `state\session.json` | sesión de la cuenta Tapo |
| `logs\eccam.log` | registro del servidor |

Para cambiar el puerto, edita `config.json` y reinicia el servidor.

## Compilar el instalador

En una PC con Windows, **Python 3.12** e **Inno Setup 6**:

```powershell
cd D:\XX-Software\Z-Propio\ECCAM\eccam
powershell -ExecutionPolicy Bypass -File .\windows\build.ps1
```

Resultado: `windows\out\EC-Cam-Setup-<versión>.exe`. El script descarga FFmpeg la primera vez y lo mete dentro del instalador.

Para probar sin instalar (necesita FFmpeg en el PATH): `windows\ejecutar-desarrollo.bat`.

## Estructura

```
eccam_server.py        servidor EC-Cam (login, roles, PWA, rutas)
eccam_auth.py          usuarios, contraseñas, sesiones, límite de intentos
tapo_cloud_app.py      motor de Topo: video, audio, PTZ, grabaciones
tapo_cloud_probe.py    motor de Topo: API de la nube Tapo y MFA
certs/                 certificados raíz de TP-Link
web/                   index.html, login.html, manifest.json, sw.js, pwa.js, offline.html, img/
windows/               build.ps1, eccam.iss (Inno Setup), .bat de ayuda
tools/                 make_icons.py y build_index.py (regenera web/index.html desde el de Topo)
```

Si actualizas Topo a una versión nueva: reemplaza `tapo_cloud_app.py`, `tapo_cloud_probe.py` y `web/index.topo.html`, vuelve a aplicar los cambios de rutas de `session_path()` y corre `python tools/build_index.py`. El script avisa qué textos ya no encontró.

## Limitaciones

- Usa endpoints no documentados de la nube Tapo (los de la app de Android); si TP-Link los cambia, puede dejar de funcionar hasta que se actualice el motor.
- La PC servidor debe estar encendida y con internet.
- Probado por Topo en Tapo C200; otros modelos deberían funcionar, pero el pan/tilt depende del modelo.
- El audio en vivo requiere un toque en **Activar audio** (los navegadores bloquean el sonido automático).
