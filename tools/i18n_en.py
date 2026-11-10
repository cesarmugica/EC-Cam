"""EC-Cam: traducción al inglés de la interfaz.

build_index.py genera src/web/index.html en español y, con este diccionario,
src/web/index.en.html en inglés. Si agregas un texto en español a la interfaz,
agrégalo aquí también: `spanish_leftovers()` avisa de lo que quede sin traducir.
"""

from __future__ import annotations

import re

# (español, inglés). Se aplican de la más larga a la más corta.
PAIRS: list[tuple[str, str]] = [
    # --- documento y encabezado ---
    ('<html lang="es">', '<html lang="en">'),
    ('content="EC-Cam Web"', 'content="EC-Cam Web"'),
    ("Tus cámaras Tapo en vivo", "Your Tapo cameras, live"),
    ("Versión instalada de EC-Cam", "Installed EC-Cam version"),
    ("`Versión ${session.version}", "`Version ${session.version}"),
    ("Instalar «EC-Cam Web» como app con su propia ventana", "Install “EC-Cam Web” as an app with its own window"),
    ("⤓ Instalar app", "⤓ Install app"),
    ("Actualizar cámaras", "Refresh cameras"),
    ("Idioma / Language", "Language / Idioma"),
    ("EC-Cam · motor de video basado en", "EC-Cam · video engine based on"),
    ("(licencia MIT)", "(MIT license)"),
    # --- estado ---
    ("'Conectando…'", "'Connecting…'"),
    (">Conectando…<", ">Connecting…<"),
    ("'Tapo sin conectar'", "'Tapo not connected'"),
    ("'Nube no disponible'", "'Cloud unavailable'"),
    ("'Actualizando…'", "'Refreshing…'"),
    ("'En línea'", "'Online'"),
    ("'Sin cámaras'", "'No cameras'"),
    ("'Error de conexión'", "'Connection error'"),
    ("'Conectando con la nube Tapo…'", "'Connecting to the Tapo cloud…'"),
    # --- login de Tapo ---
    ("Conectar cuenta Tapo", "Connect your Tapo account"),
    ("Entra con el correo y la contraseña de tu cuenta Tapo (la misma de la app del celular). La contraseña no se guarda: EC-Cam guarda solo la sesión en esta PC.",
     "Sign in with your Tapo account email and password (the same as the phone app). The password is not stored: EC-Cam only keeps the session on this PC."),
    ("Correo de la cuenta Tapo", "Tapo account email"),
    ("Contraseña de Tapo", "Tapo password"),
    ('>Conectar</button>', '>Connect</button>'),
    ("Verificación en dos pasos", "Two-step verification"),
    ("Completa la verificación que pide tu cuenta Tapo.", "Complete the verification requested by your Tapo account."),
    ("Método de verificación", "Verification method"),
    ("Enviar código", "Send code"),
    ("Código de verificación", "Verification code"),
    ("Verificar código", "Verify code"),
    ('>Volver</button>', '>Back</button>'),
    ("'Notificación en la app Tapo'", "'Tapo app notification'"),
    ("'Correo electrónico'", "'Email'"),
    ("'Elige un método y solicita la verificación.'", "'Choose a method and request verification.'"),
    ("'Conectando con Tapo…'", "'Connecting to Tapo…'"),
    ("'Solicitando verificación…'", "'Requesting verification…'"),
    ("'Revisa la notificación en la app Tapo.'", "'Check the notification in the Tapo app.'"),
    ("'Revisa el código que llegó a tu correo.'", "'Check the code sent to your email.'"),
    ("'Verificando…'", "'Verifying…'"),
    ("'Escribe el correo y la contraseña.'", "'Enter your email and password.'"),
    ("'No hay una verificación pendiente; vuelve a iniciar sesión.'", "'No verification pending; sign in again.'"),
    ("'Primero solicita el código.'", "'Request the code first.'"),
    ("'Ese método de verificación no está disponible.'", "'That verification method is not available.'"),
    ("'Cámara inválida.'", "'Invalid camera.'"),
    ("'La cámara no envió video.'", "'The camera did not send video.'"),
    ("'Sesión de EC-Cam terminada.'", "'EC-Cam session ended.'"),
    ("`Error HTTP ${response.status}`", "`HTTP error ${response.status}`"),
    # --- barra de herramientas y visor ---
    (">Tus cámaras<", ">Your cameras<"),
    (">Cargando cámaras…<", ">Loading cameras…<"),
    ("Calidad del video", "Video quality"),
    (">Calidad HD<", ">HD quality<"),
    (">Calidad ligera (SD)<", ">Light quality (SD)<"),
    ("↻ Actualizar", "↻ Refresh"),
    ("Cerrar la sesión de Tapo en esta PC", "Sign out of Tapo on this PC"),
    ("Cerrar sesión de Tapo", "Sign out of Tapo"),
    ("¿Cerrar la sesión de Tapo en esta PC? Tendrás que volver a entrar con tu cuenta Tapo para ver las cámaras.",
     "Sign out of Tapo on this PC? You will need to sign in with your Tapo account again to see your cameras."),
    ("Cámara anterior (←)", "Previous camera (←)"),
    ("Cámara siguiente (→)", "Next camera (→)"),
    ("Cámara anterior", "Previous camera"),
    ("Cámara siguiente", "Next camera"),
    (">Todas las cámaras<", ">All cameras<"),
    ("`${index + 1} de ${total}`", "`${index + 1} of ${total}`"),
    ("'cámara' : 'cámaras'} · toca una para verla", "'camera' : 'cameras'} · click one to view it"),
    ('<div class="empty-state">Cargando cámaras…</div>', '<div class="empty-state">Loading cameras…</div>'),
    ('<div class="empty-state">No hay cámaras en esta cuenta.</div>', '<div class="empty-state">There are no cameras in this account.</div>'),
    ("<strong>No se pudieron cargar las cámaras</strong>", "<strong>Could not load the cameras</strong>"),
    ('aria-label="Ver ${esc(camera.name)}"', 'aria-label="View ${esc(camera.name)}"'),
    ("'Privacidad activada' : esc(camera.model || 'Cámara')", "'Privacy on' : esc(camera.model || 'Camera')"),
    # --- tarjeta de cámara ---
    ('<span class="badge privacy">Privacidad</span>', '<span class="badge privacy">Privacy</span>'),
    ('<span class="badge">En vivo</span>', '<span class="badge">Live</span>'),
    ("<strong>Modo privacidad activado</strong><span>Video y audio en pausa</span>", "<strong>Privacy mode on</strong><span>Video and audio paused</span>"),
    ('aria-label="En vivo ${esc(camera.name)}"', 'aria-label="Live ${esc(camera.name)}"'),
    ('aria-label="Volumen del audio"', 'aria-label="Audio volume"'),
    ("🔈 Activar audio", "🔈 Enable audio"),
    ("🔇 Silenciar", "🔇 Mute"),
    ("'Conectando audio…'", "'Connecting audio…'"),
    (">Conectando con la cámara…<", ">Connecting to the camera…<"),
    ("'Conectando con la cámara…'", "'Connecting to the camera…'"),
    ("'Conectando en HD…'", "'Connecting in HD…'"),
    ("Video no disponible", "Video unavailable"),
    (">Reintentar</button>", ">Retry</button>"),
    ("'Movimiento no disponible.' : 'Esta cámara no se mueve.'", "'Movement unavailable.' : 'This camera cannot move.'"),
    (">✥ Mover<", ">✥ Move<"),
    ('<span class="meta">Paso</span>', '<span class="meta">Step</span>'),
    ('aria-label="Paso del movimiento"', 'aria-label="Movement step"'),
    ('aria-label="Controles de movimiento"', 'aria-label="Movement controls"'),
    ('title="Arriba" aria-label="Arriba"', 'title="Up" aria-label="Up"'),
    ('title="Izquierda" aria-label="Izquierda"', 'title="Left" aria-label="Left"'),
    ('title="Posición actual" aria-label="Posición actual"', 'title="Current position" aria-label="Current position"'),
    ('title="Derecha" aria-label="Derecha"', 'title="Right" aria-label="Right"'),
    ('title="Abajo" aria-label="Abajo"', 'title="Down" aria-label="Down"'),
    (">Listo · paso 10°<", ">Ready · step 10°<"),
    ("`Listo · paso ${STEP_VALUES[select.value]}°`", "`Ready · step ${STEP_VALUES[select.value]}°`"),
    ("'Moviendo…'", "'Moving…'"),
    ("`Movimiento enviado · ${step}°.`", "`Move sent · ${step}°.`"),
    ("'Privacidad activada.' : (camera.privacy === false ? 'Privacidad desactivada.' : 'Estado de privacidad no disponible.')",
     "'Privacy on.' : (camera.privacy === false ? 'Privacy off.' : 'Privacy status unavailable.')"),
    ('aria-label="Abrir ${esc(camera.name)} en pantalla completa"', 'aria-label="Open ${esc(camera.name)} in full screen"'),
    ("· vía nube Tapo", "· via Tapo cloud"),
    ("${esc(camera.model || 'Cámara')}", "${esc(camera.model || 'Camera')}"),
    ("`eccam-grabacion-", "`eccam-recording-"),
    ('aria-live="polite">Lista</div>', 'aria-live="polite">Ready</div>'),
    (">Probar conexión<", ">Test connection<"),
    ("'Quitar privacidad' : 'Activar privacidad'", "'Turn privacy off' : 'Turn privacy on'"),
    ("⛶ Salir de pantalla completa", "⛶ Exit full screen"),
    ("⛶ Pantalla completa", "⛶ Full screen"),
    (">▶ Grabaciones<", ">▶ Recordings<"),
    ("'Cerrar controles' : 'Controles'", "'Close controls' : 'Controls'"),
    ("'Controles'", "'Controls'"),
    (">Controles<", ">Controls<"),
    ("'Este navegador no permite pantalla completa'", "'This browser does not support full screen'"),
    ("'Probando conexión…'", "'Testing connection…'"),
    ("'Conexión con la nube OK.'", "'Cloud connection OK.'"),
    ("'Sin conexión con la nube'", "'No cloud connection'"),
    ("'Activando…' : 'Desactivando…'", "'Turning on…' : 'Turning off…'"),
    ("'Activando privacidad…' : 'Quitando privacidad…'", "'Turning privacy on…' : 'Turning privacy off…'"),
    ("'La cámara respondió un estado inválido.'", "'The camera returned an invalid state.'"),
    ("'Vista previa no disponible.'", "'Preview unavailable.'"),
    ("'Privacidad activada: video y audio en pausa.' : 'Privacidad desactivada.'", "'Privacy on: video and audio paused.' : 'Privacy off.'"),
    ("'La cámara tardó demasiado. Intenta de nuevo.' : (error.message || 'No se pudo cambiar la privacidad.')",
     "'The camera took too long. Try again.' : (error.message || 'Could not change privacy.')"),
    ("'No hay estado de la cámara.'", "'No camera state available.'"),
    ("'No se pudo actualizar la tarjeta.'", "'Could not refresh the card.'"),
    # --- video en vivo ---
    ("▶ En pausa · toca para ver en vivo", "▶ Paused · click to watch live"),
    ("'Video congelado. Reconectando…'", "'Video frozen. Reconnecting…'"),
    ("'Video interrumpido. Reconectando…'", "'Video interrupted. Reconnecting…'"),
    ("'Cámara sin conexión (según Tapo). Reintento en 1 min.'", "'Camera offline (according to Tapo). Retrying in 1 min.'"),
    ("'La cámara no está enviando video. Reintento en 30 s.'", "'The camera is not sending video. Retrying in 30 s.'"),
    ("'La cámara está reproduciendo una grabación…'", "'The camera is playing back a recording…'"),
    # --- grabaciones ---
    ('<h2 id="recordingsTitle">Grabaciones</h2>', '<h2 id="recordingsTitle">Recordings</h2>'),
    ("Línea de tiempo de la memoria SD", "SD card timeline"),
    ('id="closeRecordingsButton" class="ghost" type="button">Cerrar<', 'id="closeRecordingsButton" class="ghost" type="button">Close<'),
    ("<h3>Días disponibles</h3><p>Las horas están en la zona horaria de la cámara.</p>", "<h3>Available days</h3><p>Times are shown in the camera's time zone.</p>"),
    (">Cargando grabaciones…<", ">Loading recordings…<"),
    (">Cargando línea de tiempo…<", ">Loading timeline…<"),
    ('<strong id="timelineDate">Línea de tiempo</strong>', '<strong id="timelineDate">Timeline</strong>'),
    ("<span>Movimiento / evento</span><span class=\"continuous\">Grabación continua</span>", "<span>Motion / event</span><span class=\"continuous\">Continuous recording</span>"),
    ("<strong>Segmentos grabados</strong><span>Usa la lista cuando los segmentos están muy juntos.</span>", "<strong>Recorded segments</strong><span>Use the list when segments are close together.</span>"),
    ("Elige un segmento para ver su hora y duración.", "Choose a segment to see its time and duration."),
    ("['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']", "['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']"),
    ("'Hora desconocida'", "'Unknown time'"),
    ("'Grabación continua' : 'Movimiento / evento'", "'Continuous recording' : 'Motion / event'"),
    ("<small>Ver línea de tiempo</small>", "<small>View timeline</small>"),
    ('<div class="empty-state">No hay grabaciones en estos días.</div>', '<div class="empty-state">No recordings in these days.</div>'),
    ("'Descarga iniciada.'", "'Download started.'"),
    (">▶ Reproducir</button>", ">▶ Play</button>"),
    (">⤓ Descargar</button>", ">⤓ Download</button>"),
    ("'⤓ Descargar' : '▶ Reproducir'", "'⤓ Download' : '▶ Play'"),
    ("${data.timezone || 'hora de la cámara'}", "${data.timezone || 'camera time'}"),
    ("'segmento' : 'segmentos'", "'segment' : 'segments'"),
    ('<div class="timeline-empty">No hay segmentos este día.</div>', '<div class="timeline-empty">No segments on this day.</div>'),
    ('<div class="meta">No hay segmentos grabados.</div>', '<div class="meta">No recorded segments.</div>'),
    ("'Grabación lista.'", "'Recording ready.'"),
    ("'Grabación completa. «Descargar» la guarda con audio.'", "'Recording complete. “Download” saves it with audio.'"),
    ("`Preparando… ${progress}%`", "`Preparing… ${progress}%`"),
    ("'Preparando descarga…' : 'Preparando grabación…'", "'Preparing download…' : 'Preparing recording…'"),
    ("'Preparando… 1%'", "'Preparing… 1%'"),
    ("'Preparando descarga… 1%' : 'Preparando grabación… 1%'", "'Preparing download… 1%' : 'Preparing recording… 1%'"),
    ("'Se agotó el tiempo al preparar la grabación.'", "'Timed out while preparing the recording.'"),
    ("'No se pudo descargar la grabación.' : 'No se pudo preparar la grabación.'", "'Could not download the recording.' : 'Could not prepare the recording.'"),
    ("`Cargando ${displayDate(date)}…`", "`Loading ${displayDate(date)}…`"),
    ("`${data.clips?.length || 0} segmentos · ", "`${data.clips?.length || 0} segments · "),
    ("'No se pudieron cargar las grabaciones.'", "'Could not load the recordings.'"),
    ("'Buscando días con grabaciones…'", "'Looking for days with recordings…'"),
    ("'La memoria SD está bien, pero no tiene grabaciones.' : 'No se detectó memoria SD.'", "'The SD card is fine but has no recordings.' : 'No SD card detected.'"),
    ("`Grabaciones · ${name}`", "`Recordings · ${name}`"),
    ("'Memoria SD · hora local de la cámara'", "'SD card · camera local time'"),
]

# Mensajes que llegan del servidor en español (se traducen en el navegador).
SERVER_MESSAGES_EN = {
    "Pausando el video en vivo…": "Pausing live video…",
    "La cámara está ocupada; reintentando…": "The camera is busy; retrying…",
    "Solicitud rechazada.": "Request rejected.",
    "No disponible en EC-Cam.": "Not available in EC-Cam.",
    "Conecta la cuenta Tapo primero.": "Connect your Tapo account first.",
    "Cámara inválida.": "Invalid camera.",
}

SPANISH_HINT = re.compile(
    r"[áéíóúñ¿¡ÁÉÍÓÚÑ]|\b(cámara|cámaras|grabaci\w*|privacidad|reintentar|conectando|preparando|actualizar|"
    r"descargar|reproducir|controles|verificaci\w*|contraseña|correo|segmentos?|línea|tiempo|"
    r"disponible|cerrar|activar|quitar|mover|paso|vivo|toca|nube|sesión)\b",
    re.I,
)


def to_english(html: str) -> str:
    for spanish, english in sorted(PAIRS, key=lambda pair: len(pair[0]), reverse=True):
        html = html.replace(spanish, english)
    return html


def spanish_leftovers(html: str) -> list[str]:
    """Textos que parecen español en la página en inglés (para avisar al generar)."""
    body = re.sub(r"<style>.*?</style>", "", html, flags=re.S)
    # Ignorar el diccionario de mensajes del servidor y nombres propios conocidos.
    body = re.sub(r"const SERVER_MESSAGES(?:_ES)? = \{.*?\};", "", body, flags=re.S)
    found = []
    for match in re.finditer(r">([^<>]{2,})<|'([^'\n]{2,})'|`([^`\n]{2,})`|(?:title|aria-label)=\"([^\"]{2,})\"", body):
        text = next(group for group in match.groups() if group)
        if SPANISH_HINT.search(text) and "español" not in text.lower():
            found.append(text.strip()[:120])
    return sorted(set(found))
