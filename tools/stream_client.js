    // ---------- EC-Cam: administrador de video ligero ----------
    // - Solo transmite las cámaras visibles en pantalla.
    // - Con HTTP/1.1 (abriendo la PC servidor directo) el navegador solo abre 6
    //   conexiones; se limita a 4 en vivo para no atorar las demás.
    // - Pausa todo si la app está en segundo plano.
    // - Mosaico en SD (ligero); pantalla completa en HD.
    // - Vigila congelados y se mantiene cerca del "en vivo".
    const liveVideo = (() => {
      const nav = (performance.getEntriesByType && performance.getEntriesByType('navigation')[0]) || {};
      const multiplexed = /^h[23]/i.test(nav.nextHopProtocol || '');
      const maxLive = multiplexed ? 12 : 4;
      const entries = new Map();
      let pinned = [];
      let timer = null;
      let gridQuality = 'hd';
      try { gridQuality = localStorage.getItem('eccam_quality2') === 'sd' ? 'sd' : 'hd'; } catch (_) {}
      const observer = 'IntersectionObserver' in window ? new IntersectionObserver(items => {
        items.forEach(item => { const entry = entries.get(item.target); if (entry) entry.visible = item.isIntersecting; });
        schedule();
      }, {threshold: 0.15}) : null;
      function schedule() { clearTimeout(timer); timer = setTimeout(refresh, 120); }
      function fullscreenCard() { return fullscreenElement() || document.querySelector('.card.is-fullscreen'); }
      function streamUrl(entry, quality) { return `/stream/${encodeURIComponent(entry.card.dataset.id)}.mp4?q=${quality}&t=${Date.now()}`; }
      function setOverlay(entry, state, text) {
        entry.loading.classList.toggle('hidden', state !== 'loading');
        entry.error.classList.toggle('hidden', state !== 'error');
        entry.paused.classList.toggle('hidden', state !== 'paused');
        if (state === 'loading' && text) entry.loading.textContent = text;
        if (state === 'error' && text) entry.errorText.textContent = text;
      }
      function start(entry, quality) {
        clearTimeout(entry.retryTimer); entry.retryTimer = null;
        entry.quality = quality; entry.running = true; entry.played = false;
        entry.lastTime = -1; entry.lastProgress = Date.now(); entry.lastFrameAt = Date.now();
        entry.video.src = streamUrl(entry, quality);
        setOverlay(entry, 'loading', quality === 'hd' ? 'Conectando en HD…' : 'Conectando con la cámara…');
        const playback = entry.video.play(); if (playback) playback.catch(() => {});
      }
      function stop(entry) {
        clearTimeout(entry.retryTimer); entry.retryTimer = null;
        entry.running = false;
        entry.video.pause(); entry.video.removeAttribute('src'); entry.video.load();
      }
      function restart(entry, reason) {
        if (!entry.running && entry.retryTimer) return;
        const quality = entry.quality || entry.wantedQuality;
        stop(entry);
        let delay = Math.min(1000 * (2 ** entry.attempts), 10000);
        entry.attempts = Math.min(entry.attempts + 1, 4);
        setOverlay(entry, 'error', reason);
        const schedule = ms => { clearTimeout(entry.retryTimer); entry.retryTimer = setTimeout(() => { entry.retryTimer = null; if (entry.wanted) start(entry, entry.wantedQuality); }, ms); };
        schedule(delay);
        // Preguntar al servidor el motivo: si la cámara está desconectada o no
        // manda video, avisarlo claro y esperar más antes de reintentar.
        fetch(`/api/app/stream-status?cam=${encodeURIComponent(entry.card.dataset.id)}&q=${quality}`, {credentials: 'same-origin'})
          .then(r => r.json()).then(status => {
            if (!entry.retryTimer) return;
            if (status.kind === 'offline') { setOverlay(entry, 'error', 'Cámara sin conexión (según Tapo). Reintento en 1 min.'); schedule(60000); }
            else if (status.kind === 'playback') { setOverlay(entry, 'error', 'La cámara está reproduciendo una grabación…'); schedule(8000); }
            else if (status.kind === 'silent') { setOverlay(entry, 'error', 'La cámara no está enviando video. Reintento en 30 s.'); schedule(30000); }
          }).catch(() => {});
      }
      function refresh() {
        clearTimeout(timer);
        for (const [card, entry] of entries) { if (!card.isConnected || !entry.video.isConnected) { stop(entry); observer?.unobserve(card); entries.delete(card); } }
        pinned = pinned.filter(card => entries.has(card));
        const fs = fullscreenCard();
        let want = [];
        // Con la ventana de Grabaciones abierta no se transmite en vivo: la
        // cámara no puede dar en vivo y grabación a la vez.
        // Igual mientras corre «Probar mis cámaras».
        const recordingsOpen = !recordingsModal.classList.contains('hidden') || !!document.querySelector('#testModal:not(.hidden)');
        if (!document.hidden && !recordingsOpen) {
          if (fs) want = entries.has(fs) ? [fs] : [];
          else {
            const visible = [...entries.values()].filter(entry => entry.visible).map(entry => entry.card);
            const ordered = [...pinned.filter(card => visible.includes(card)), ...visible.filter(card => !pinned.includes(card))];
            want = ordered.slice(0, maxLive);
          }
        }
        for (const entry of entries.values()) {
          const wanted = want.includes(entry.card), quality = entry.card === fs ? 'hd' : gridQuality;
          entry.wanted = wanted; entry.wantedQuality = quality;
          if (wanted && (!entry.running || entry.quality !== quality) && !entry.retryTimer) start(entry, quality);
          else if (!wanted && (entry.running || entry.retryTimer)) stop(entry);
          if (!wanted) setOverlay(entry, entry.visible && !document.hidden && !fs ? 'paused' : 'none');
        }
      }
      function watchdog() {
        const now = Date.now();
        for (const entry of entries.values()) {
          const video = entry.video;
          if (!entry.running) continue;
          if (video.currentTime > entry.lastTime + 0.05) { entry.lastTime = video.currentTime; entry.lastProgress = now; }
          else if (now - entry.lastProgress > (entry.played ? 9000 : 25000)) { restart(entry, 'Video congelado. Reconectando…'); continue; }
          // EC-Cam: imagen congelada aunque el tiempo avance (el navegador deja
          // de pintar cuadros, p. ej. si el video llega dañado): reconectar.
          if (entry.frameWatch && entry.played && now - entry.lastFrameAt > 8000) { restart(entry, 'Video congelado. Reconectando…'); continue; }
          if (video.buffered.length) {
            const behind = video.buffered.end(video.buffered.length - 1) - video.currentTime;
            if (behind > 3) video.currentTime = video.buffered.end(video.buffered.length - 1) - 0.4;
            else video.playbackRate = behind > 1.2 ? 1.08 : 1;
          }
          if (video.paused && entry.played && !document.hidden) { const playback = video.play(); if (playback) playback.catch(() => {}); }
        }
        if ([...entries.keys()].some(card => !card.isConnected)) refresh();
      }
      setInterval(watchdog, 2000);
      new MutationObserver(schedule).observe(recordingsModal, {attributes: true, attributeFilter: ['class']});
      const testModalEl = document.querySelector('#testModal'); if (testModalEl) new MutationObserver(schedule).observe(testModalEl, {attributes: true, attributeFilter: ['class']});
      document.addEventListener('visibilitychange', refresh);
      document.addEventListener('fullscreenchange', schedule); document.addEventListener('webkitfullscreenchange', schedule);
      window.addEventListener('online', refresh);
      function register(card, video, preview) {
        const old = entries.get(card); if (old) { stop(old); observer?.unobserve(card); }
        const entry = {card, video, visible: !observer, running: false, wanted: false, quality: '', wantedQuality: gridQuality, attempts: 0, retryTimer: null, lastTime: -1, lastProgress: 0, played: false,
          loading: preview.querySelector('.preview-status.loading'), error: preview.querySelector('.preview-status.error'), paused: document.createElement('button')};
        entry.errorText = entry.error.firstChild;
        entry.paused.type = 'button'; entry.paused.className = 'preview-status paused hidden'; entry.paused.textContent = '▶ En pausa · toca para ver en vivo';
        preview.appendChild(entry.paused);
        entry.paused.addEventListener('click', event => { event.stopPropagation(); pinned = [card, ...pinned.filter(item => item !== card)].slice(0, maxLive); refresh(); });
        const ready = () => { entry.played = true; entry.attempts = 0; entry.lastProgress = Date.now(); entry.lastFrameAt = Date.now(); setOverlay(entry, 'none'); };
        // Contar los cuadros que de verdad se pintan (Chrome y Edge).
        if ('requestVideoFrameCallback' in video) {
          entry.frameWatch = true;
          const onFrame = () => { entry.lastFrameAt = Date.now(); video.requestVideoFrameCallback(onFrame); };
          video.requestVideoFrameCallback(onFrame);
        }
        video.addEventListener('playing', ready);
        video.addEventListener('error', () => { if (entry.running) restart(entry, 'Video interrumpido. Reconectando…'); });
        video.addEventListener('ended', () => { if (entry.running) restart(entry, 'Video interrumpido. Reconectando…'); });
        entry.error.querySelector('.retry-button')?.addEventListener('click', event => { event.stopPropagation(); entry.attempts = 0; clearTimeout(entry.retryTimer); entry.retryTimer = null; if (entry.wanted) start(entry, entry.wantedQuality); else refresh(); });
        entries.set(card, entry);
        observer?.observe(card);
        schedule();
        return entry;
      }
      function setGridQuality(value) { gridQuality = value === 'hd' ? 'hd' : 'sd'; try { localStorage.setItem('eccam_quality2', gridQuality); } catch (_) {} refresh(); }
      return {register, refresh, setGridQuality, quality: () => gridQuality, qualityOf: card => entries.get(card)?.quality || gridQuality, maxLive};
    })();
    function bindStream(card) {
      const preview = card.querySelector('.preview'), video = preview.querySelector('.live-native-video'), audio = preview.querySelector('.live-audio'), audioControls = preview.querySelector('.audio-controls'), audioButton = preview.querySelector('.audio-toggle'), volume = preview.querySelector('.audio-volume');
      if (!video) return;
      video.removeAttribute('src'); video.removeAttribute('autoplay'); video.load();
      liveVideo.register(card, video, preview);
      if (audio && audioButton && audioControls && volume) { audio.volume = Number(volume.value); const stopAudio = () => { audio.pause(); audio.removeAttribute('src'); audio.load(); audioButton.dataset.audioOn = 'false'; audioButton.setAttribute('aria-pressed', 'false'); audioButton.classList.remove('active'); audioControls.classList.remove('active'); audioButton.disabled = false; audioButton.textContent = '🔈 Activar audio'; }; const startAudio = () => { audioButton.disabled = true; audioButton.textContent = 'Conectando audio…'; audio.volume = Number(volume.value); audio.src = `/audio/${encodeURIComponent(card.dataset.id)}.mp3?q=${liveVideo.qualityOf(card)}&stream=${Date.now()}`; audio.load(); const playback = audio.play(); if (playback) playback.catch(() => { stopAudio(); }); }; audioButton.addEventListener('click', event => { event.stopPropagation(); if (audioButton.dataset.audioOn === 'true') stopAudio(); else startAudio(); }); volume.addEventListener('click', event => event.stopPropagation()); volume.addEventListener('input', () => { audio.volume = Number(volume.value); }); audio.addEventListener('playing', () => { audioButton.disabled = false; audioButton.dataset.audioOn = 'true'; audioButton.setAttribute('aria-pressed', 'true'); audioButton.classList.add('active'); audioButton.textContent = '🔇 Silenciar'; }); audio.addEventListener('error', () => { if (audioButton.dataset.audioOn !== 'true') stopAudio(); }); }
    }
