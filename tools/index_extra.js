    // ---------- EC-Cam: inicio ----------
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
