# Historial de versiones / Changelog

Cada versión tiene su instalador en [Releases](https://github.com/cesarmugica/EC-Cam/releases). La fecha y hora de cada compilación aparecen dentro de la app, debajo del nombre EC-Cam.

## 2.2.1
- El en vivo deja un colchón de ~1 segundo: las pausas cortas de internet ya casi no detienen la imagen (a cambio de ir ~1 s detrás del en vivo).

## 2.2.0 — Video más fluido
- **Nuevo reproductor del en vivo (Media Source Extensions):** EC-Cam le pasa el video a la ventana fragmento por fragmento, se mantiene pegado al en vivo y borra lo ya visto. Evita que la imagen se congele cada 20–60 segundos (pasaba sobre todo en la C500 con la ventana de Edge).
- Si el navegador no puede usar ese reproductor, EC-Cam vuelve solo al anterior.

## 2.1.3
- La reconexión automática de un video congelado ahora espera 5 segundos (antes 8 y 9).

## 2.1.2
- Si la imagen se queda congelada aunque el video siga «corriendo», EC-Cam ahora lo detecta (cuenta los cuadros que de verdad se pintan) y se reconecta solo en unos 8 segundos, sin tener que volver a elegir la cámara.

## 2.1.1
- Las cámaras **sin memoria SD** ahora salen como «— Sin memoria SD» en la prueba y en Grabaciones, en vez de marcarse como falla.

## 2.1.0 — Probar mis cámaras
- **🧪 Probar mis cámaras:** prueba en un clic el video en vivo, la lista de grabaciones de la SD y la reproducción de cada cámara, y muestra una tabla con ✅/❌ y el motivo de cada falla. No mueve las cámaras.
- **📤 Enviar reporte:** abre en GitHub el reporte de compatibilidad ya llenado, uno por cada modelo y firmware. Solo lleva modelo, firmware, versión de EC-Cam y resultados; nunca el nombre de tus cámaras ni datos de tu cuenta Tapo.
- La lista de cámaras ahora incluye firmware y versión de hardware.

## 2.0.1 — Idiomas y orden
- **Español / English:** selector de idioma en la app (🌐), que se recuerda. El instalador también es bilingüe, y el idioma que elijas al instalar es el idioma inicial de la app.
- Repositorio ordenado por carpetas: `src/`, `docs/`, `tools/`, `windows/`.
- Este historial y el reporte para el autor de Topo (`docs/HALLAZGOS-TOPO.md`).

## 1.2.x — Escritorio
- **1.2.2:** EC-Cam abre en **su propia ventana** (Edge o Chrome en modo aplicación, sin barra de direcciones).
- **1.2.1:** la app instalada desde el navegador se llama **EC-Cam Web**, para distinguirla del acceso **EC-Cam** del instalador.
- **1.2.0:** ícono de cámara de vigilancia en el mosaico; el acceso del escritorio se llama solo **EC-Cam**.

## 1.1.x — Grabaciones de la SD y arranque
- **1.1.10:** corrige la 1.1.9. La compilación ahora verifica que los módulos propios queden dentro del ejecutable.
- **1.1.9 ⚠️ defectuosa:** no arranca («No module named 'tapo_cloud_app'»). No la uses.
- **1.1.8:** las grabaciones **se ven mientras se descargan**; al cerrar Grabaciones o cambiar de clip se cancela la descarga y vuelve el en vivo.
- **1.1.7:** mensaje claro cuando el firmware no permite reproducir (C200 1.3.17 build 58281 → `-52402`).
- **1.1.6:** diagnóstico de reproducción (`/api/app/playtest`).
- **1.1.5:** se apaga el en vivo antes de reproducir una grabación (la cámara no puede hacer las dos cosas; `-52207 passthrough fail`).
- **1.1.4:** reproducción con confirmaciones de lo recibido; reintento con un solo canal.
- **1.1.3:** botón **▶ Iniciar EC-Cam** cuando el servicio está detenido (enlace `eccam://`); el instalador arranca el servicio al terminar.
- **1.1.2:** la búsqueda de grabaciones se hace por páginas de 50 (con días de muchos clips, la nube devolvía una respuesta vacía).
- **1.1.1:** diagnóstico de búsqueda de grabaciones (`/api/app/sdtest`).
- **1.1.0:** app local para cada PC, sin login propio: solo responde dentro de la PC, con protección contra DNS rebinding y CSRF.

## 1.0.x — Video en vivo estable
- **1.0.7:** versión y fecha de publicación visibles en la app.
- **1.0.6:** **protocolo de vista previa de la app oficial**: petición de video, confirmaciones y latido. Con esto funcionan los firmwares nuevos (C200 1.3.17 build 58281), que no mandaban video.
- **1.0.5:** visor de **una cámara a la vez**, con carrusel y mosaico sin video.
- **1.0.4:** mensajes claros por cámara («sin conexión», «no está enviando video») y reintentos espaciados.
- **1.0.3:** diagnóstico de conexión por cámara (`/api/app/relaytest`).
- **1.0.2:** diagnóstico de cámaras (`/api/app/diag`) y errores del relay en el registro.
- **1.0.1:** **video ligero y estable**: un visor nuevo ya no corta el video a los demás, se reparten fragmentos MP4 completos, el mosaico va en SD y solo se transmiten las cámaras visibles.
- **1.0.0:** primera versión, basada en el motor de [Topo 0.1.7](https://github.com/filirnd/topo): interfaz en español, app instalable e instalador de Windows.
