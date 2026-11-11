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
      // ---------- Reproductor MSE (Media Source Extensions) ----------
      // El MP4 en vivo no tiene fin; como descarga progresiva, el reproductor de
      // Edge a veces deja de pintar a los pocos segundos. Con MSE EC-Cam le da
      // los fragmentos uno por uno, se mantiene en el borde del en vivo y borra
      // lo ya visto. Si el navegador no tiene MSE, se usa la descarga normal.
      const MSE_OK = typeof MediaSource !== 'undefined' && typeof MediaSource.isTypeSupported === 'function';
      const u32 = (b, o) => ((b[o] << 24) >>> 0) + (b[o + 1] << 16) + (b[o + 2] << 8) + b[o + 3];
      const boxType = (b, o) => String.fromCharCode(b[o + 4], b[o + 5], b[o + 6], b[o + 7]);
      function codecFromInit(init) {
        for (let i = 4; i + 8 < init.length; i++) {
          if (init[i] === 0x61 && init[i + 1] === 0x76 && init[i + 2] === 0x63 && init[i + 3] === 0x43) { // avcC
            const hex = n => n.toString(16).padStart(2, '0');
            return `avc1.${hex(init[i + 5])}${hex(init[i + 6])}${hex(init[i + 7])}`;
          }
        }
        return 'avc1.640028';
      }
      function startMse(entry, url) {
        const video = entry.video, mediaSource = new MediaSource(), controller = new AbortController();
        const session = {controller, mediaSource, objectUrl: URL.createObjectURL(mediaSource), closed: false};
        entry.mse = session;
        video.src = session.objectUrl;
        const fail = reason => { if (session.closed || entry.mse !== session) return; restart(entry, reason || 'Video interrumpido. Reconectando…'); };
        mediaSource.addEventListener('sourceopen', async () => {
          let sourceBuffer = null, pending = [], pendingBytes = 0, carry = new Uint8Array(0), init = [], lastTrim = 0;
          const pump = () => {
            if (!sourceBuffer || sourceBuffer.updating || session.closed || mediaSource.readyState !== 'open') return;
            const end = video.buffered.length ? video.buffered.end(video.buffered.length - 1) : 0;
            // Borrar lo ya visto (deja 8 s atrás) para no llenar la memoria.
            if (video.buffered.length && video.currentTime - video.buffered.start(0) > 20 && Date.now() - lastTrim > 5000) {
              lastTrim = Date.now();
              try { sourceBuffer.remove(video.buffered.start(0), Math.max(video.buffered.start(0), video.currentTime - 8)); return; } catch (_) {}
            }
            if (!pending.length) return;
            const chunk = new Uint8Array(pendingBytes); let offset = 0;
            for (const part of pending) { chunk.set(part, offset); offset += part.length; }
            pending = []; pendingBytes = 0;
            try { sourceBuffer.appendBuffer(chunk); }
            catch (error) { if (error && error.name === 'QuotaExceededError' && end) { try { sourceBuffer.remove(0, Math.max(0, video.currentTime - 2)); } catch (_) {} pending.unshift(chunk); pendingBytes += chunk.length; } else fail(); }
          };
          const afterAppend = () => {
            if (!video.buffered.length) return;
            const start = video.buffered.start(0), end = video.buffered.end(video.buffered.length - 1);
            // El primer fragmento no empieza en 0 (se entra desde el último cuadro clave).
            if (video.currentTime < start || video.currentTime > end) video.currentTime = Math.max(start, end - 0.5);
            if (video.paused && !document.hidden) { const playback = video.play(); if (playback) playback.catch(() => {}); }
            pump();
          };
          try {
            const response = await fetch(url, {signal: controller.signal, credentials: 'same-origin', cache: 'no-store'});
            if (!response.ok || !response.body) { fail(); return; }
            const reader = response.body.getReader();
            while (!session.closed) {
              const {done, value} = await reader.read();
              if (done) break;
              let data = value;
              if (carry.length) { data = new Uint8Array(carry.length + value.length); data.set(carry); data.set(value, carry.length); }
              let offset = 0;
              while (data.length - offset >= 8) {
                const size = u32(data, offset);
                if (size < 8) { fail(); return; }
                if (data.length - offset < size) break;
                const box = data.subarray(offset, offset + size), type = boxType(data, offset);
                offset += size;
                if (!sourceBuffer) {
                  init.push(box.slice());
                  if (type !== 'moov') continue;
                  const initBytes = new Uint8Array(init.reduce((n, part) => n + part.length, 0)); let o = 0;
                  for (const part of init) { initBytes.set(part, o); o += part.length; }
                  const mime = `video/mp4; codecs="${codecFromInit(initBytes)}"`;
                  if (!MediaSource.isTypeSupported(mime)) { entry.noMse = true; fail('Cambiando de reproductor…'); return; }
                  sourceBuffer = mediaSource.addSourceBuffer(mime);
                  sourceBuffer.mode = 'segments';
                  sourceBuffer.addEventListener('updateend', afterAppend);
                  sourceBuffer.addEventListener('error', () => fail());
                  pending.push(initBytes); pendingBytes += initBytes.length;
                } else { pending.push(box.slice()); pendingBytes += box.length; }
              }
              carry = data.slice(offset);
              pump();
            }
            fail();
          } catch (error) {
            if (!session.closed) fail();
          }
        }, {once: true});
      }
      function closeMse(entry) {
        const session = entry.mse; if (!session) return;
        session.closed = true; entry.mse = null;
        try { session.controller.abort(); } catch (_) {}
        try { if (session.mediaSource.readyState === 'open') session.mediaSource.endOfStream(); } catch (_) {}
        setTimeout(() => URL.revokeObjectURL(session.objectUrl), 1000);
      }
      function start(entry, quality) {
        clearTimeout(entry.retryTimer); entry.retryTimer = null;
        closeMse(entry);
        entry.quality = quality; entry.running = true; entry.played = false;
        entry.lastTime = -1; entry.lastProgress = Date.now(); entry.lastFrameAt = Date.now();
        if (MSE_OK && !entry.noMse) startMse(entry, streamUrl(entry, quality));
        else entry.video.src = streamUrl(entry, quality);
        setOverlay(entry, 'loading', quality === 'hd' ? 'Conectando en HD…' : 'Conectando con la cámara…');
        const playback = entry.video.play(); if (playback) playback.catch(() => {});
      }
      function stop(entry) {
        clearTimeout(entry.retryTimer); entry.retryTimer = null;
        entry.running = false;
        closeMse(entry);
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
          else if (now - entry.lastProgress > (entry.played ? 5000 : 25000)) { restart(entry, 'Video congelado. Reconectando…'); continue; }
          // EC-Cam: imagen congelada aunque el tiempo avance (el navegador deja
          // de pintar cuadros, p. ej. si el video llega dañado): reconectar.
          if (entry.frameWatch && entry.played && now - entry.lastFrameAt > 5000) { restart(entry, 'Video congelado. Reconectando…'); continue; }
          if (video.buffered.length) {
            const behind = video.buffered.end(video.buffered.length - 1) - video.currentTime;
            // Colchón de ~1 s detrás del en vivo: aguanta pausas cortas de
            // internet sin detenerse. Se ajusta con la velocidad (±5 %).
            if (behind > 4) video.currentTime = video.buffered.end(video.buffered.length - 1) - 1.2;
            else video.playbackRate = behind > 2 ? 1.05 : (behind < 0.7 && entry.played ? 0.95 : 1);
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
        video.addEventListener('error', () => { if (entry.running) { if (entry.mse && video.error && video.error.code === 4) entry.noMse = true; restart(entry, 'Video interrumpido. Reconectando…'); } });
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
