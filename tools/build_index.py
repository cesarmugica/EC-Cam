"""Genera web/index.html a partir del index de Topo (web/index.topo.html)."""
from pathlib import Path
import re, sys
base = Path(__file__).resolve().parent.parent / "web"
s = (base / "index.topo.html").read_text(encoding="utf-8")
missing = []
def R(old, new, count=1):
    global s
    n = s.count(old)
    if n == 0 or (count and n != count):
        missing.append((old[:70], n)); return
    s = s.replace(old, new)

# ---------- head / tema ----------
R('<html lang="en">', '<html lang="es">')
R('<title>Topo - desktop app for Tapo camera</title>', '''<title>EC-Cam</title>
  <link rel="manifest" href="/manifest.json">
  <link rel="icon" href="/img/favicon.png">
  <link rel="apple-touch-icon" href="/img/pwa-192.png">
  <meta name="theme-color" content="#121614">
  <meta name="mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black">
  <meta name="apple-mobile-web-app-title" content="EC-Cam Web">
  <script src="/pwa.js?v=1" defer></script>''')
R('''      color-scheme: light;''', '''      color-scheme: dark;''')
R('''      --bg: #edede9; --surface: #f5ebe0; --surface-2: #e3d5ca; --surface-3: #d6ccc2;
      --border: #d5bdaf; --muted: #756961; --text: #3f3834;
      --accent: #d5bdaf; --accent-strong: #e3d5ca; --success: #756961;
      --warning: #75604f; --danger: #b58f7e; --shadow: 0 14px 30px rgba(63, 56, 52, .16);''',
'''      --bg: #121614; --surface: #1b201d; --surface-2: #252c28; --surface-3: #313a35;
      --border: #2e3732; --muted: #9aa6a0; --text: #f3f5f4;
      --accent: #F07C1E; --accent-strong: #ff9a45; --success: #6fcf97;
      --warning: #f2c94c; --danger: #8e2f25; --shadow: 0 14px 30px rgba(0, 0, 0, .35);''')
R('button:hover:not(:disabled) { background: var(--text); color: var(--bg); transform: translateY(-1px); }',
  'button:hover:not(:disabled) { filter: brightness(1.12); transform: translateY(-1px); }')
R('button { border: 0; border-radius: 10px; padding: 10px 13px; background: var(--accent); color: var(--text);',
  'button { border: 0; border-radius: 10px; padding: 10px 13px; background: var(--accent); color: #fff; font-weight: 600;')
R('button.danger { background: var(--danger); border: 1px solid var(--accent); color: var(--text); } button.danger:hover:not(:disabled) { background: var(--surface-2); }',
  'button.danger { background: var(--danger); border: 1px solid var(--danger); color: #fff; }')
R('.ptz button:hover:not(:disabled) { background: var(--accent); color: var(--text); }', '.ptz button:hover:not(:disabled) { background: var(--accent); color: #fff; }')
R('background: rgba(63, 56, 52, .42); }', 'background: rgba(0, 0, 0, .65); }')
R('.timeline-segment.event:hover:not(:disabled) { background: var(--accent-strong); color: var(--text); }', '.timeline-segment.event:hover:not(:disabled) { background: var(--accent-strong); }')
R('    @keyframes spin', '''    .header-actions button.icon-only { min-width: 38px; }
    .preview .audio-controls { top: 12px; bottom: auto; }
    .movement-panel { right: auto; left: 0; }
    .user-chip { color: var(--muted); font-size: .82rem; white-space: nowrap; } .user-chip strong { color: var(--text); }
    .viewer-note { padding: 14px; border-radius: 12px; background: var(--bg); color: var(--muted); line-height: 1.5; }
    .app-modal { position: fixed; inset: 0; z-index: 60; display: flex; align-items: flex-start; justify-content: center; padding: clamp(12px, 6vh, 70px) 16px; overflow-y: auto; background: rgba(0, 0, 0, .65); }
    .app-modal-panel { width: min(560px, 100%); border: 1px solid var(--border); border-radius: 18px; background: var(--surface); box-shadow: var(--shadow); }
    .app-modal-panel header { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 16px 20px; border-bottom: 1px solid var(--border); } .app-modal-panel h2 { font-size: 1.1rem; }
    .app-modal-body { padding: 18px 20px 22px; } .app-modal-body form { display: grid; gap: 8px; } .app-modal-body label { margin: 6px 0 0; }
    .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; } .form-row label { margin-top: 6px; }
    .user-list { display: grid; gap: 8px; margin-bottom: 18px; } .user-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 10px 12px; border: 1px solid var(--border); border-radius: 10px; background: var(--bg); }
    .user-row .who { min-width: 0; overflow: hidden; text-overflow: ellipsis; } .user-row .who small { display: block; color: var(--muted); }
    .user-row .row-actions { display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end; } .user-row .row-actions button { padding: 6px 9px; font-size: .78rem; }
    .form-msg { min-height: 1.3em; margin-top: 8px; font-size: .86rem; } .form-msg.bad { color: #ff8a7a; } .form-msg.ok { color: var(--success); }
    .app-footer { padding: 0 16px 28px; color: var(--muted); font-size: .75rem; text-align: center; } .app-footer a { color: var(--muted); }
    @media (max-width: 520px) { .form-row { grid-template-columns: 1fr; } }
    @keyframes spin''')

# ---------- encabezado ----------
R('''<div class="brand"><img class="brand-icon" src="/assets/topo.png" alt="Topo"><div class="brand-copy"><h1>Topo - desktop app for Tapo camera</h1><div class="brand-subtitle">Cloud control for your cameras</div></div></div>''',
  '''<div class="brand"><img class="brand-icon" src="/img/pwa-192.png" alt=""><div class="brand-copy"><h1>EC-Cam</h1><div class="brand-subtitle">Tus cámaras Tapo en vivo</div></div></div>''')
R('''<div id="account"><div id="state" aria-live="polite">Login required</div><div class="header-actions"><button id="infoButton" class="ghost" type="button" title="Open the Topo website" aria-label="Open the Topo website">Info</button><button id="refreshButton" class="ghost hidden" type="button" title="Refresh cameras" aria-label="Refresh cameras">↻</button><button id="logoutButton" class="danger hidden" type="button">Log out</button></div></div>''',
  '''<div id="account"><div id="state" aria-live="polite">Conectando…</div><div class="header-actions"><button class="ghost" type="button" data-instalar style="display:none" title="Instalar «EC-Cam Web» como app con su propia ventana">⤓ Instalar app</button><button id="refreshButton" class="ghost icon-only hidden" type="button" title="Actualizar cámaras" aria-label="Actualizar cámaras">↻</button></div></div>''')

# ---------- login de Tapo ----------
R('''<img class="login-brand" src="/assets/topo.png" alt="Topo"><div id="credentialsView"><h2>Log in to Tapo</h2><p>Use your Tapo account credentials. Your password is not saved.</p>''',
  '''<img class="login-brand" src="/img/pwa-192.png" alt=""><div id="credentialsView"><h2>Conectar cuenta Tapo</h2><p>Entra con el correo y la contraseña de tu cuenta Tapo (la misma de la app del celular). La contraseña no se guarda: EC-Cam guarda solo la sesión en esta PC.</p>''')
R('<label for="username">Tapo email/account</label>', '<label for="username">Correo de la cuenta Tapo</label>')
R('<label for="password">Password</label>', '<label for="password">Contraseña de Tapo</label>')
R('<button id="loginButton" type="submit">Log in</button>', '<button id="loginButton" type="submit">Conectar</button>')
R('<h2>MFA verification</h2><p>Complete the verification requested by your Tapo account.</p><label for="mfaType">Verification method</label>',
  '<h2>Verificación en dos pasos</h2><p>Completa la verificación que pide tu cuenta Tapo.</p><label for="mfaType">Método de verificación</label>')
R('<button id="requestMfaButton" type="button">Send code</button><label for="mfaCode">MFA code</label>', '<button id="requestMfaButton" type="button">Enviar código</button><label for="mfaCode">Código de verificación</label>')
R('<button id="verifyMfaButton" type="button" disabled>Verify code</button><button id="backLoginButton" class="secondary" type="button">Back to login</button>',
  '<button id="verifyMfaButton" type="button" disabled>Verificar código</button><button id="backLoginButton" class="secondary" type="button">Volver</button>')

# ---------- vista principal ----------
R('<h2>Your cameras</h2><p id="cameraSummary">Loading cameras…</p></div><div class="toolbar-actions"><button id="refreshMainButton" class="secondary" type="button">↻ Refresh</button></div>',
  '<h2>Tus cámaras</h2><p id="cameraSummary">Cargando cámaras…</p></div><div class="toolbar-actions"><button id="refreshMainButton" class="secondary" type="button">↻ Actualizar</button><button id="logoutButton" class="danger hidden" type="button" title="Cerrar la sesión de Tapo en esta PC">Cerrar sesión de Tapo</button></div>')
R('<div id="grid" class="grid" aria-live="polite"></div></main>', '''<div id="grid" class="grid" aria-live="polite"></div></main>
  <footer class="app-footer">EC-Cam · motor de video basado en <a href="https://github.com/filirnd/topo" target="_blank" rel="noopener">Topo</a> (licencia MIT)</footer>''')

# ---------- grabaciones (HTML) ----------
for a, b in [
  ('<h2 id="recordingsTitle">Recordings</h2><p id="recordingsSubtitle">SD card timeline</p>', '<h2 id="recordingsTitle">Grabaciones</h2><p id="recordingsSubtitle">Línea de tiempo de la memoria SD</p>'),
  ('<button id="closeRecordingsButton" class="ghost" type="button">Close</button>', '<button id="closeRecordingsButton" class="ghost" type="button">Cerrar</button>'),
  ('<h3>Available days</h3><p>Times are shown in the camera timezone.</p>', '<h3>Días disponibles</h3><p>Las horas están en la zona horaria de la cámara.</p>'),
  ('<button id="refreshRecordingsButton" class="secondary" type="button">↻ Refresh</button>', '<button id="refreshRecordingsButton" class="secondary" type="button">↻ Actualizar</button>'),
  ('aria-live="polite">Loading recordings…</div>', 'aria-live="polite">Cargando grabaciones…</div>'),
  ('aria-live="polite">Loading timeline…</div>', 'aria-live="polite">Cargando línea de tiempo…</div>'),
  ('<strong id="timelineDate">Timeline</strong>', '<strong id="timelineDate">Línea de tiempo</strong>'),
  ('<span>Motion / event</span><span class="continuous">Continuous recording</span>', '<span>Movimiento / evento</span><span class="continuous">Grabación continua</span>'),
  ('<strong>Recording segments</strong><span>Use the list when segments are close together.</span>', '<strong>Segmentos grabados</strong><span>Usa la lista cuando los segmentos están muy juntos.</span>'),
  ('class="recording-selection">Select a segment to inspect its time and duration.</div>', 'class="recording-selection">Elige un segmento para ver su hora y duración.</div>'),
]: R(a, b)

# Modales nuevos (usuarios y cuenta)


# ---------- JS ----------
R("const PROJECT_WEBSITE = 'https://filirnd.github.io/topo/';", "let appUser = {user: 'local', role: 'admin'}; const isAdmin = () => true;")
R(", infoButton = document.querySelector('#infoButton')", "")
R("function methodName(value) { return Number(value) === 1 ? 'Tapo app notification' : 'Email'; }", "function methodName(value) { return Number(value) === 1 ? 'Notificación en la app Tapo' : 'Correo electrónico'; }")
R("async function api(path, options = {}) { const response = await fetch(path, options); let data = {}; try { data = await response.json(); } catch (_) {} if (!response.ok) throw new Error(data.error || `HTTP error ${response.status}`); return data; }",
  "async function api(path, options = {}) { const opts = {credentials: 'same-origin', ...options}; if ((opts.method || 'GET').toUpperCase() === 'POST') { opts.headers = {'Content-Type': 'application/json', ...(opts.headers || {})}; if (opts.body === undefined) opts.body = '{}'; } const response = await fetch(path, opts); let data = {}; try { data = await response.json(); } catch (_) {} if (response.status === 401 && data.app_auth === false) { location.replace('/login'); throw new Error('Sesión de EC-Cam terminada.'); } if (!response.ok) throw new Error(translateError(data.error) || `Error HTTP ${response.status}`); return data; }\n    function translateError(message) { const map = {'login required': 'login required', 'email and password are required': 'Escribe el correo y la contraseña.', 'no pending MFA login': 'No hay una verificación pendiente; vuelve a iniciar sesión.', 'request the MFA code first': 'Primero solicita el código.', 'MFA method is not available': 'Ese método de verificación no está disponible.', 'invalid camera': 'Cámara inválida.', 'camera did not provide a video frame': 'La cámara no envió video.'}; return map[message] || message; }")
R("function showLogin() { loginView.classList.remove('hidden'); appView.classList.add('hidden'); logoutButton.classList.add('hidden'); refreshButton.classList.add('hidden'); setState('Login required'); grid.innerHTML = ''; closeRecordings?.(); }",
  "function showLogin() { loginView.classList.remove('hidden'); appView.classList.add('hidden'); logoutButton.classList.add('hidden'); refreshButton.classList.add('hidden'); setState('Tapo sin conectar', 'bad'); grid.innerHTML = ''; closeRecordings?.(); }")
R("mfaInfo.textContent = 'Choose a method and request verification.';", "mfaInfo.textContent = 'Elige un método y solicita la verificación.';")
R("function showApp() { loginView.classList.add('hidden'); appView.classList.remove('hidden'); logoutButton.classList.remove('hidden'); refreshButton.classList.remove('hidden'); }",
  "function showApp() { loginView.classList.add('hidden'); appView.classList.remove('hidden'); logoutButton.classList.toggle('hidden', !isAdmin()); refreshButton.classList.remove('hidden'); }")
R("""<span class="badge privacy">Privacy</span>""", """<span class="badge privacy">Privacidad</span>""")
R("""<span class="badge">Cloud</span>""", """<span class="badge">En vivo</span>""")
R("<strong>Privacy mode enabled</strong><span>Video and audio are paused</span>", "<strong>Modo privacidad activado</strong><span>Video y audio en pausa</span>")
R('aria-label="Live ${esc(camera.name)}"', 'aria-label="En vivo ${esc(camera.name)}"')
R('aria-label="Live audio volume"><button class="audio-toggle" type="button" aria-pressed="false">Enable audio</button>', 'aria-label="Volumen del audio"><button class="audio-toggle" type="button" aria-pressed="false">🔈 Activar audio</button>')
R('<div class="preview-status loading">Connecting to low-latency stream…</div><div class="preview-status error hidden">Stream unavailable <button class="retry-button" type="button">Retry</button></div>',
  '<div class="preview-status loading">Conectando con la cámara…</div><div class="preview-status error hidden">Video no disponible <button class="retry-button" type="button">Reintentar</button></div>')
R("esc(camera.ptz_error || 'Pan & tilt unavailable.')", "esc(camera.ptz_error ? 'Movimiento no disponible.' : 'Esta cámara no se mueve.')")
R('aria-controls="${panelId}">Pan & tilt</button>', 'aria-controls="${panelId}">✥ Mover</button>')
R('<span class="meta">Movement step</span><select class="step-select" aria-label="Movement step">', '<span class="meta">Paso</span><select class="step-select" aria-label="Paso del movimiento">')
R('aria-label="Pan and tilt controls"', 'aria-label="Controles de movimiento"')
R('title="Tilt up" aria-label="Tilt up"', 'title="Arriba" aria-label="Arriba"')
R('title="Pan left" aria-label="Pan left"', 'title="Izquierda" aria-label="Izquierda"')
R('title="Current position" aria-label="Current position"', 'title="Posición actual" aria-label="Posición actual"')
R('title="Pan right" aria-label="Pan right"', 'title="Derecha" aria-label="Derecha"')
R('title="Tilt down" aria-label="Tilt down"', 'title="Abajo" aria-label="Abajo"')
R('aria-live="polite">Pan & tilt ready · step 10°</div>', 'aria-live="polite">Listo · paso 10°</div>')
R("const privacyText = camera.privacy === true ? 'Privacy enabled.' : (camera.privacy === false ? 'Privacy disabled.' : (camera.privacy_error || 'Privacy status unavailable.'));",
  "const privacyText = camera.privacy === true ? 'Privacidad activada.' : (camera.privacy === false ? 'Privacidad desactivada.' : 'Estado de privacidad no disponible.');")
R("const privacyDisabled = camera.privacy === null ? 'disabled' : '';", "const privacyDisabled = camera.privacy === null ? 'disabled' : ''; const privacyHidden = isAdmin() ? '' : ' hidden';")
R('aria-label="Open ${esc(camera.name)} fullscreen"', 'aria-label="Abrir ${esc(camera.name)} en pantalla completa"')
R("${esc(camera.model || 'Camera')} · account ${esc(camera.account_status ?? 'n/a')} · cloud-only", "${esc(camera.model || 'Cámara')} · vía nube Tapo")
R('aria-live="polite">Ready</div>', 'aria-live="polite">Lista</div>')
R('<button class="relay-button" type="button" data-id="${esc(camera.id)}">Check connection</button>', '<button class="relay-button" type="button" data-id="${esc(camera.id)}">Probar conexión</button>')
R('<button class="secondary privacy-button" type="button"', '<button class="secondary privacy-button${privacyHidden}" type="button"')
R("${camera.privacy === true ? 'Disable privacy' : 'Enable privacy'}</button><button class=\"secondary fullscreen-button\" type=\"button\">Fullscreen</button>",
  "${camera.privacy === true ? 'Quitar privacidad' : 'Activar privacidad'}</button><button class=\"secondary fullscreen-button\" type=\"button\">⛶ Pantalla completa</button>")
R('data-name="${esc(camera.name)}">Recordings</button>', 'data-name="${esc(camera.name)}">▶ Grabaciones</button>')
R('<button class="commands-handle" type="button" aria-expanded="false">Controls</button>', '<button class="commands-handle" type="button" aria-expanded="false">Controles</button>')
R("scheduleReconnect('Stream interrupted. Reconnecting…')", "scheduleReconnect('Video interrumpido. Reconectando…')")
R("scheduleReconnect('Stream ended. Reconnecting…')", "scheduleReconnect('El video terminó. Reconectando…')")
R("scheduleReconnect('Retrying stream…')", "scheduleReconnect('Reintentando…')")
s = s.replace("audioButton.textContent = 'Enable audio';", "audioButton.textContent = '🔈 Activar audio';")
R("audioButton.textContent = 'Connecting audio…';", "audioButton.textContent = 'Conectando audio…';")
R("audioButton.textContent = 'Mute audio';", "audioButton.textContent = '🔇 Silenciar';")
R("const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];", "const monthNames = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];")
R("return match ? match[1] : 'Unknown time';", "return match ? match[1] : 'Hora desconocida';")
R("return Number(value) === 1 ? 'Continuous recording' : 'Motion / event';", "return Number(value) === 1 ? 'Grabación continua' : 'Movimiento / evento';")
R("<small>Open timeline</small>", "<small>Ver línea de tiempo</small>")
R("'<div class=\"empty-state\">No recordings were found in the selected range.</div>'", "'<div class=\"empty-state\">No hay grabaciones en estos días.</div>'")
R("anchor.download = `topo-recording-", "anchor.download = `eccam-grabacion-")
R("recordingsStatus.textContent = 'Download started. Choose the destination in the save dialog.';", "recordingsStatus.textContent = 'Descarga iniciada.';")
R('<button type="button" class="recording-action play-recording-button">Play clip</button><button type="button" class="recording-action secondary download-recording-button">Download clip</button>',
  '<button type="button" class="recording-action play-recording-button">▶ Reproducir</button><button type="button" class="recording-action secondary download-recording-button">⤓ Descargar</button>')
R("${data.timezone || 'camera time'}`;\n", "${data.timezone || 'hora de la cámara'}`;\n")
R("${clips.length === 1 ? 'segment' : 'segments'}", "${clips.length === 1 ? 'segmento' : 'segmentos'}")
s = s.replace("recordingSelection.textContent = 'Select a segment to inspect its time and duration.';", "recordingSelection.textContent = 'Elige un segmento para ver su hora y duración.';")
R("'<div class=\"timeline-empty\">No segments for this day.</div>'", "'<div class=\"timeline-empty\">No hay segmentos este día.</div>'")
R("'<div class=\"meta\">No recording segments available.</div>'", "'<div class=\"meta\">No hay segmentos grabados.</div>'")
s = s.replace("recordingsStatus.textContent = 'Recording ready.';", "recordingsStatus.textContent = 'Grabación lista.';")
R("button.textContent = isDownload ? 'Download clip' : 'Play clip';", "button.textContent = isDownload ? '⤓ Descargar' : '▶ Reproducir';")
R("button.textContent = `Preparing… ${progress}%`;", "button.textContent = `Preparando… ${progress}%`;")
R("(isDownload ? 'Preparing recording download…' : 'Preparing recording…')} ${progress}%`;", "(isDownload ? 'Preparando descarga…' : 'Preparando grabación…')} ${progress}%`;")
R("button.textContent = 'Preparing… 1%';", "button.textContent = 'Preparando… 1%';")
R("recordingsStatus.textContent = isDownload ? 'Preparing recording download… 1%' : 'Preparing recording… 1%';", "recordingsStatus.textContent = isDownload ? 'Preparando descarga… 1%' : 'Preparando grabación… 1%';")
R("throw new Error(job?.error || 'Recording preparation timed out.');", "throw new Error(job?.error || 'Se agotó el tiempo al preparar la grabación.');")
R("(isDownload ? 'Unable to download recording.' : 'Unable to prepare recording playback.');", "(isDownload ? 'No se pudo descargar la grabación.' : 'No se pudo preparar la grabación.');")
R("recordingsStatus.textContent = `Loading ${displayDate(date)} timeline…`;", "recordingsStatus.textContent = `Cargando ${displayDate(date)}…`;")
R("recordingsStatus.textContent = `${data.clips?.length || 0} segments found · ${data.timezone || 'camera time'}`;", "recordingsStatus.textContent = `${data.clips?.length || 0} segmentos · ${data.timezone || 'hora de la cámara'}`;")
s = s.replace("recordingsStatus.textContent = error.message || 'Unable to load recordings.';", "recordingsStatus.textContent = error.message || 'No se pudieron cargar las grabaciones.';")
R("recordingsStatus.textContent = 'Loading available recording days…';", "recordingsStatus.textContent = 'Buscando días con grabaciones…';")
R("data.sd_available ? 'The SD card is available, but no recordings were found.' : 'No SD card was detected.';", "data.sd_available ? 'La memoria SD está bien, pero no tiene grabaciones.' : 'No se detectó memoria SD.';")
R("recordingsTitle.textContent = `${name} recordings`; recordingsSubtitle.textContent = 'SD card timeline · camera local time';", "recordingsTitle.textContent = `Grabaciones · ${name}`; recordingsSubtitle.textContent = 'Memoria SD · hora local de la cámara';")
R("result.textContent = `Pan & tilt ready · step ${STEP_VALUES[select.value]}`;", "result.textContent = `Listo · paso ${STEP_VALUES[select.value]}°`;")
R("if (!data.camera) throw new Error('Camera state is unavailable.');", "if (!data.camera) throw new Error('No hay estado de la cámara.');")
R("if (!replacement) throw new Error('Camera card could not be rebuilt.');", "if (!replacement) throw new Error('No se pudo actualizar la tarjeta.');")
R("grid.innerHTML = '<div class=\"empty-state\">Loading cameras…</div>'; cameraSummary.textContent = 'Connecting to Tapo cloud…'; setState('Refreshing…');",
  "grid.innerHTML = '<div class=\"empty-state\">Cargando cámaras…</div>'; cameraSummary.textContent = 'Conectando con la nube Tapo…'; setState('Actualizando…');")
R("grid.innerHTML = '<div class=\"empty-state\">No cameras available.</div>'; cameraSummary.textContent = 'No cameras found'; setState('No cameras', 'bad');",
  "grid.innerHTML = '<div class=\"empty-state\">No hay cámaras en esta cuenta.</div>'; cameraSummary.textContent = 'Sin cámaras'; setState('Sin cámaras', 'bad');")
R("cameraSummary.textContent = `${data.cameras.length} ${data.cameras.length === 1 ? 'camera available' : 'cameras available'}`; setState(`${data.cameras.length} cameras from cloud`, 'ok');",
  "cameraSummary.textContent = `${data.cameras.length} ${data.cameras.length === 1 ? 'cámara disponible' : 'cámaras disponibles'}`; setState('En línea', 'ok');")
R("<strong>Unable to load cameras</strong>", "<strong>No se pudieron cargar las cámaras</strong>")
R('<button id="loadRetryButton" type="button">Retry</button>', '<button id="loadRetryButton" type="button">Reintentar</button>')
R("cameraSummary.textContent = 'Connection error'; setState(error.message === 'login required' ? 'Login required' : 'Cloud unavailable', 'bad');",
  "cameraSummary.textContent = 'Error de conexión'; setState(error.message === 'login required' ? 'Tapo sin conectar' : 'Nube no disponible', 'bad');")
s = s.replace("handle.textContent = 'Controls';", "handle.textContent = 'Controles';")
R("button.textContent = button.closest('.card') === active ? 'Exit fullscreen' : 'Fullscreen';", "button.textContent = button.closest('.card') === active ? '⛶ Salir de pantalla completa' : '⛶ Pantalla completa';")
R("button.textContent = open ? 'Close controls' : 'Controls';", "button.textContent = open ? 'Cerrar controles' : 'Controles';")
R("throw new Error('Fullscreen is not supported by this version');", "throw new Error('Este navegador no permite pantalla completa');")
R("result.textContent = 'Checking cloud relay…';", "result.textContent = 'Probando conexión…';")
R("result.textContent = data.ok ? 'Cloud relay available.' : (data.error || 'Relay unavailable');", "result.textContent = data.ok ? 'Conexión con la nube OK.' : (data.error || 'Sin conexión con la nube');")
R("button.textContent = enabled ? 'Enabling…' : 'Disabling…'; result.textContent = enabled ? 'Enabling privacy…' : 'Disabling privacy…';", "button.textContent = enabled ? 'Activando…' : 'Desactivando…'; result.textContent = enabled ? 'Activando privacidad…' : 'Quitando privacidad…';")
R("throw new Error('The camera returned an invalid privacy state.');", "throw new Error('La cámara respondió un estado inválido.');")
R("throw new Error('Camera preview is unavailable.');", "throw new Error('Vista previa no disponible.');")
R("button.textContent = isOn ? 'Disable privacy' : 'Enable privacy'; result.textContent = isOn ? 'Privacy enabled: video and audio paused.' : 'Privacy disabled.';",
  "button.textContent = isOn ? 'Quitar privacidad' : 'Activar privacidad'; result.textContent = isOn ? 'Privacidad activada: video y audio en pausa.' : 'Privacidad desactivada.';")
R("result.textContent = timedOut ? 'Privacy request timed out. Try again.' : (error.message || 'Privacy request failed.');", "result.textContent = timedOut ? 'La cámara tardó demasiado. Intenta de nuevo.' : (error.message || 'No se pudo cambiar la privacidad.');")
R("result.textContent = 'Moving…';", "result.textContent = 'Moviendo…';")
R("result.textContent = `Move sent · step ${step}°.`;", "result.textContent = `Movimiento enviado · ${step}°.`;")
R("loginError.textContent = 'Logging in…';", "loginError.textContent = 'Conectando con Tapo…';")
R("mfaInfo.textContent = 'Requesting verification…';", "mfaInfo.textContent = 'Solicitando verificación…';")
R("mfaInfo.textContent = data.mfa_type === 1 ? 'Check the notification in the Tapo app.' : 'Check the code sent by email.';", "mfaInfo.textContent = data.mfa_type === 1 ? 'Revisa la notificación en la app Tapo.' : 'Revisa el código que llegó a tu correo.';")
R("mfaInfo.textContent = 'Verifying…';", "mfaInfo.textContent = 'Verificando…';")
R("async function logout() { logoutButton.disabled = true; try { await api('/api/logout', {method: 'POST'}); showCredentials(); showLogin(); }",
  "async function logout() { if (!confirm('¿Cerrar la sesión de Tapo en esta PC? Tendrás que volver a entrar con tu cuenta Tapo para ver las cámaras.')) return; logoutButton.disabled = true; try { await api('/api/logout', {method: 'POST'}); showCredentials(); showLogin(); }")
R("infoButton.addEventListener('click', () => { window.location.href = PROJECT_WEBSITE; }); ", "")
R("(async function init() { try { const data = await api('/api/session'); if (data.authenticated) { showApp(); await load(); } else if (data.mfa_pending) showMfa(data.mfa_types); else showLogin(); } catch (_) { showLogin(); } })();",
  (base.parent / "tools" / "index_extra.js").read_text(encoding="utf-8").strip())

# ---------- EC-Cam: video ligero ----------
R('<video class="live-native-video" autoplay muted playsinline preload="auto" src="/stream/${encodeURIComponent(camera.id)}.mp4?native=${Date.now()}"',
  '<video class="live-native-video" muted playsinline preload="none"')
start = s.find('    function bindStream(card) {')
end = s.find("    document.addEventListener('click', event => { const button = event.target.closest('.audio-toggle');")
if start < 0 or end < start:
    missing.append(('bindStream block', 0))
else:
    s = s[:start] + (base.parent / "tools" / "stream_client.js").read_text(encoding="utf-8") + s[end:]
R('<div class="toolbar-actions"><button id="refreshMainButton"',
  '<div class="toolbar-actions"><select id="qualitySelect" class="quality-select" title="Calidad del mosaico" aria-label="Calidad del mosaico"><option value="sd">Mosaico ligero (SD)</option><option value="hd">Mosaico en HD</option></select><button id="refreshMainButton"')
R('    @keyframes spin', """    .preview-status.paused { cursor: pointer; border-color: var(--accent); background: rgba(18, 22, 20, .88); color: var(--text); font-weight: 600; }
    .preview-status.paused:hover:not(:disabled) { transform: none; filter: none; background: rgba(240, 124, 30, .25); }
    .quality-select { width: auto; padding: 9px 10px; border-radius: 10px; background: var(--surface-2); font-size: .85rem; }
    @keyframes spin""")
R("    (async function init() {", """    const qualitySelect = document.querySelector('#qualitySelect'); qualitySelect.value = liveVideo.quality(); qualitySelect.addEventListener('change', () => liveVideo.setGridQuality(qualitySelect.value));
    (async function init() {""")

# ---------- EC-Cam: visor de una cámara + mosaico sin video ----------
R('<div id="grid" class="grid" aria-live="polite"></div>',
  '<div class="stage"><section id="viewer" class="viewer"><div class="viewer-bar"><button id="prevCam" class="nav-btn" type="button" aria-label="Cámara anterior" title="Cámara anterior (←)">◀</button><div class="viewer-title"><strong id="viewerName"></strong><span id="viewerCount"></span></div><button id="nextCam" class="nav-btn" type="button" aria-label="Cámara siguiente" title="Cámara siguiente (→)">▶</button></div><div id="viewerCard"></div></section><aside class="tiles-wrap"><h3 class="tiles-title">Todas las cámaras</h3><div id="grid" class="tiles" aria-live="polite"></div></aside></div>')
load_start = s.find('    async function load() {')
load_end = s.find('\n', load_start)
if load_start < 0:
    missing.append(('load()', 0))
else:
    s = s[:load_start] + (base.parent / "tools" / "viewer.js").read_text(encoding="utf-8").rstrip('\n') + s[load_end:]
R('<option value="sd">Mosaico ligero (SD)</option><option value="hd">Mosaico en HD</option>', '<option value="hd">Calidad HD</option><option value="sd">Calidad ligera (SD)</option>')
R('title="Calidad del mosaico" aria-label="Calidad del mosaico"', 'title="Calidad del video" aria-label="Calidad del video"')
R('    @keyframes spin', """    .viewer { width: min(1100px, 100%); margin: 0 auto 28px; }
    .viewer-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
    .nav-btn { flex: 0 0 auto; width: 52px; height: 52px; padding: 0; border-radius: 50%; background: var(--surface-2); color: var(--text); font-size: 1.15rem; }
    .nav-btn:hover:not(:disabled) { background: var(--accent); color: #fff; }
    .viewer-title { flex: 1; min-width: 0; text-align: center; } .viewer-title strong { display: block; overflow: hidden; font-size: 1.2rem; text-overflow: ellipsis; white-space: nowrap; } .viewer-title span { color: var(--muted); font-size: .82rem; }
    .viewer .card .name { display: none; }
    .tiles-title { margin: 0 0 12px; color: var(--muted); font-size: .95rem; font-weight: 650; }
    .tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 12px; }
    .tile { display: flex; flex-direction: column; align-items: stretch; padding: 0; overflow: hidden; border: 1px solid var(--border); border-radius: 14px; background: var(--surface); color: var(--text); text-align: left; }
    .tile:hover:not(:disabled) { border-color: var(--muted); }
    .tile.active { border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent); }
    .tile-thumb { display: grid; place-items: center; aspect-ratio: 16 / 9; background: #0b0e0c center / cover no-repeat; color: var(--muted); font-size: 1.6rem; }
    .tile-thumb .cctv-icon { width: 56px; height: auto; opacity: .85; }
    .tile-name { padding: 9px 11px 0; overflow: hidden; font-size: .9rem; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }
    .tile-meta { padding: 2px 11px 11px; color: var(--muted); font-size: .75rem; font-weight: 500; }
    @media (max-width: 520px) { .tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; } .nav-btn { width: 46px; height: 46px; } }
    .viewer { scroll-margin-top: 96px; }
    .viewer .preview { max-height: calc(100vh - 250px); }
    @media (max-width: 720px) { .viewer { scroll-margin-top: 175px; } }
    .viewer .preview video { max-height: calc(100vh - 250px); aspect-ratio: 16 / 9; }
    @media (min-width: 1100px) {
      .stage { display: grid; grid-template-columns: minmax(0, 1fr) 290px; gap: 26px; align-items: start; }
      .viewer { width: 100%; margin: 0; }
      .tiles-wrap { position: sticky; top: 96px; max-height: calc(100vh - 116px); overflow-y: auto; padding-right: 4px; }
      .tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
      .tile-name { font-size: .82rem; }
    }
    @media (max-width: 720px) { .toolbar-actions { flex-wrap: wrap; } .toolbar-actions .quality-select { flex: 1 1 100%; } .toolbar-actions button { min-width: 0; } }
    @keyframes spin""")

# ---------- EC-Cam: grabaciones — reproducir mientras descarga y cancelar al salir ----------
R("const created = await api(`/api/cameras/${encodeURIComponent(recordingsState.id)}/recordings/play`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({start: Number(clip.start), end})});",
  "const created = await api(`/api/cameras/${encodeURIComponent(recordingsState.id)}/recordings/play`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({start: Number(clip.start), end})});\n        recordingsState.jobId = created.job_id;\n        if (!isDownload) { recordingPlayer.src = `/recordings/${encodeURIComponent(created.job_id)}/stream.mp4`; recordingPlayerWrap.classList.remove('hidden'); recordingPlayer.load(); recordingPlayer.play().catch(() => {}); }")
R("""        if (!job || job.status !== 'ready') throw new Error(job?.error || 'Se agotó el tiempo al preparar la grabación.');""",
  """        if (recordingsState.jobId === created.job_id) recordingsState.jobId = '';
        if (!job || job.status !== 'ready') throw new Error(job?.error || 'Se agotó el tiempo al preparar la grabación.');""")
R("""        } else {
          recordingPlayer.src = job.video_url;
          recordingPlayerWrap.classList.remove('hidden');
          recordingPlayer.load();
          recordingsStatus.className = 'recordings-status';
          recordingsStatus.textContent = 'Grabación lista.';
          recordingPlayer.play().catch(() => {});
        }""", """        } else if (recordingPlayer.currentSrc.includes('/stream.mp4') && !recordingPlayer.error && recordingPlayer.currentTime > 0) {
          // Ya se está viendo mientras descargaba: no reiniciar el video.
          recordingsStatus.className = 'recordings-status';
          recordingsStatus.textContent = 'Grabación completa. «Descargar» la guarda con audio.';
        } else {
          recordingPlayer.src = job.video_url;
          recordingPlayerWrap.classList.remove('hidden');
          recordingPlayer.load();
          recordingsStatus.className = 'recordings-status';
          recordingsStatus.textContent = 'Grabación lista.';
          recordingPlayer.play().catch(() => {});
        }""")
R("""      } catch (error) {
        recordingsStatus.className = 'recordings-status bad';
        recordingsState.preparedClipKey = '';""", """      } catch (error) {
        if (error.message === 'cancelled') return; // se cerró Grabaciones o se eligió otro clip
        recordingsStatus.className = 'recordings-status bad';
        recordingsState.preparedClipKey = '';""")
R("function closeRecordings() {", "function cancelRecordingJob() { const id = recordingsState.jobId; recordingsState.jobId = ''; if (id) fetch(`/api/recording-jobs/${encodeURIComponent(id)}/cancel`, {method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json'}, body: '{}'}).catch(() => {}); }\n    function closeRecordings() { cancelRecordingJob();")
R("function selectRecording(clip, segment, listItem) {", "function selectRecording(clip, segment, listItem) {\n      cancelRecordingJob(); recordingPlayer.pause(); recordingPlayer.removeAttribute('src'); recordingPlayer.load();")
R("    window.addEventListener('resize', repositionOpenMovementPanels);", "    window.addEventListener('pagehide', () => cancelRecordingJob());\n    window.addEventListener('resize', repositionOpenMovementPanels);")

if missing:
    print("NO ENCONTRADOS:"); [print(" ", m) for m in missing]; sys.exit(1)
(base / "index.html").write_text(s, encoding="utf-8")
print("web/index.html generado")
