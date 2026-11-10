    // ---------- EC-Cam: inicio ----------
    // Mensajes que manda el servidor: el motor de Topo los da en inglés y los de
    // EC-Cam en español; se muestran en el idioma de la página.
    const SERVER_MESSAGES_ES = {'Starting recording preview…': 'Iniciando la grabación…', 'Connecting to playback relay…': 'Conectando con la cámara…', 'Starting camera playback…': 'Pidiendo la grabación a la cámara…', 'Downloading recording…': 'Descargando la grabación…', 'Preparing video…': 'Preparando el video…', 'Converting recording…': 'Convirtiendo la grabación…', 'Recording ready.': 'Grabación lista.', 'Recording preparation failed.': 'No se pudo preparar la grabación.'};
    const SERVER_MESSAGES = {};
    function localizeServerMessage(message) {
      if (!message) return message;
      const english = document.documentElement.lang === 'en';
      const map = english ? SERVER_MESSAGES : SERVER_MESSAGES_ES;
      if (map[message]) return map[message];
      const firmware = english && String(message).match(/^Esta cámara \(firmware (.+)\) no permite reproducir grabaciones desde EC-Cam todavía/);
      if (firmware) return `This camera (firmware ${firmware[1]}) cannot play recordings in EC-Cam yet. You can watch them in the Tapo app.`;
      return message;
    }
    const langSelect = document.querySelector('#langSelect');
    if (langSelect) {
      langSelect.value = document.documentElement.lang === 'en' ? 'en' : 'es';
      langSelect.addEventListener('change', () => {
        document.cookie = `eccam_lang=${langSelect.value}; Path=/; Max-Age=31536000; SameSite=Lax`;
        try { localStorage.setItem('eccam_lang', langSelect.value); } catch (_) {}
        location.reload();
      });
    }
    function formatBuildDate(value) { const m = String(value).match(/^(\d{4})-(\d{2})-(\d{2})(?: (\d{2}:\d{2}))?/); if (!m) return value; const months = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']; return `${Number(m[3])} ${months[Number(m[2]) - 1]} ${m[1]}${m[4] ? ', ' + m[4] : ''}`; }
    async function checkTapo() { try { const data = await api('/api/session'); if (data.authenticated) { showApp(); await load(); } else if (data.mfa_pending) showMfa(data.mfa_types); else showLogin(); } catch (_) { showLogin(); } }
    (async function init() {
      try {
        const session = await api('/api/app/session');
        const versionText = session.version ? `Versión ${session.version}${session.build_date ? ' · ' + formatBuildDate(session.build_date) : ''}` : '';
        const footer = document.querySelector('.app-footer'); if (footer && versionText) footer.insertAdjacentText('afterbegin', `${versionText} · `);
        const subtitle = document.querySelector('.brand-subtitle'); if (subtitle && versionText) { subtitle.textContent = versionText; subtitle.title = 'Versión instalada de EC-Cam'; }
      } catch (_) {}
      await checkTapo();
    })();
