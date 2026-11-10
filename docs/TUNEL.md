# Publicar EC-Cam en internet con Cloudflare Tunnel

Cloudflare Tunnel conecta la PC servidor con Cloudflare **desde adentro**, así que no hay que abrir puertos en el módem, y da HTTPS gratis (necesario para que la app se pueda instalar en el celular).

Necesitas una cuenta de Cloudflare (gratis) y un dominio administrado en Cloudflare (por ejemplo, el que ya uses para DGPOS).

## Prueba rápida (sin dominio, URL temporal)

En la PC servidor, con EC-Cam corriendo:

```bat
winget install --id Cloudflare.cloudflared
cloudflared tunnel --url http://localhost:8790
```

Muestra una dirección `https://algo-al-azar.trycloudflare.com`. Ábrela en el celular para probar. La dirección cambia cada vez, así que es solo para probar.

## Túnel permanente (recomendado)

1. Entra a [one.dash.cloudflare.com](https://one.dash.cloudflare.com) → **Networks → Tunnels** → **Create a tunnel** → tipo **Cloudflared**. Ponle de nombre `eccam`.
2. Elige **Windows** y copia el comando que te muestra; se ve así:
   ```bat
   cloudflared.exe service install eyJhIjoi...
   ```
   Ejecútalo en una terminal **como administrador** en la PC servidor. Queda instalado como servicio de Windows y arranca solo.
3. En **Public Hostname** agrega:
   - Subdominio: `camaras` · Dominio: `tudominio.com`
   - Tipo: **HTTP** · URL: `localhost:8790`
4. Guarda. En uno o dos minutos `https://camaras.tudominio.com` abre EC-Cam.

## Recomendaciones

- **No uses** «Disable chunked encoding» ni caché para este hostname: el video en vivo es un flujo continuo.
- Opcional, una capa extra: en **Access → Applications** puedes pedir un código por correo antes de llegar a EC-Cam. EC-Cam ya tiene su propio login, así que es opcional.
- `cloudflared` debe correr **en la misma PC** que EC-Cam. Así EC-Cam sabe la IP real de cada visitante (para el bloqueo por intentos fallidos) y nunca permite la configuración inicial desde internet.

## Si algo falla

| Síntoma | Revisa |
|---|---|
| Error 502 / 1033 de Cloudflare | Que EC-Cam esté corriendo (menú Inicio → EC-Cam) y que la URL del túnel sea `localhost:8790`. |
| Entra pero no se ve video | `%LOCALAPPDATA%\EC-Cam\logs\eccam.log`; con **Probar conexión** en la tarjeta de la cámara. |
| «Demasiados intentos» | Espera 15 minutos o reinicia el servidor EC-Cam. |
| No aparece el botón Instalar | Debe abrirse por `https://`. En iPhone: Safari → Compartir → Agregar a pantalla de inicio. |
