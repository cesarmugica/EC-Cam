    // ---------- EC-Cam: visor de una cámara + mosaico sin video ----------
    // Solo transmite la cámara elegida. El mosaico muestra nombre y la última
    // imagen vista (foto fija, no video). Flechas, deslizar o teclado para
    // pasar a la siguiente; la anterior se apaga al cambiar.
    const viewerCard = document.querySelector('#viewerCard'), viewerName = document.querySelector('#viewerName'), viewerCount = document.querySelector('#viewerCount'), viewerSection = document.querySelector('#viewer');
    const viewerState = {cameras: [], index: -1, thumbs: new Map()};
    function savedCamera() { try { return localStorage.getItem('eccam_camera') || ''; } catch (_) { return ''; } }
    function rememberCamera(id) { try { localStorage.setItem('eccam_camera', String(id)); } catch (_) {} }
    function tileThumb(camera) {
      const thumb = viewerState.thumbs.get(String(camera.id));
      if (camera.privacy === true) return '<span class="tile-thumb">🔒</span>';
      return thumb ? `<span class="tile-thumb" style="background-image:url('${thumb}')"></span>` : '<span class="tile-thumb">📷</span>';
    }
    function renderTiles() {
      grid.innerHTML = viewerState.cameras.map((camera, index) => `<button class="tile${index === viewerState.index ? ' active' : ''}" type="button" data-index="${index}" aria-label="Ver ${esc(camera.name)}">${tileThumb(camera)}<span class="tile-name">${esc(camera.name)}</span><span class="tile-meta">${camera.privacy === true ? 'Privacidad activada' : esc(camera.model || 'Cámara')}</span></button>`).join('');
      grid.querySelectorAll('.tile').forEach(tile => tile.addEventListener('click', () => {
        selectCamera(Number(tile.dataset.index));
        const top = viewerSection.getBoundingClientRect().top;
        if (top < 0 || top > window.innerHeight * 0.5) viewerSection.scrollIntoView({behavior: 'smooth', block: 'start'});
      }));
    }
    function selectCamera(index) {
      const total = viewerState.cameras.length;
      if (!total) return;
      index = ((index % total) + total) % total;
      if (fullscreenElement()) { try { (document.exitFullscreen || document.webkitExitFullscreen)?.call(document); } catch (_) {} }
      viewerState.index = index;
      const camera = viewerState.cameras[index];
      viewerCard.innerHTML = cardMarkup(camera);
      const card = viewerCard.firstElementChild;
      if (card) bindCard(card);
      liveVideo.refresh();
      viewerName.textContent = camera.name;
      viewerCount.textContent = `${index + 1} de ${total}`;
      grid.querySelectorAll('.tile').forEach(tile => tile.classList.toggle('active', Number(tile.dataset.index) === index));
      rememberCamera(camera.id);
    }
    async function load() {
      grid.innerHTML = '<div class="empty-state">Cargando cámaras…</div>'; viewerCard.innerHTML = ''; viewerName.textContent = ''; viewerCount.textContent = '';
      cameraSummary.textContent = 'Conectando con la nube Tapo…'; setState('Actualizando…');
      try {
        const data = await api('/api/cameras');
        if (!data.cameras?.length) { grid.innerHTML = '<div class="empty-state">No hay cámaras en esta cuenta.</div>'; viewerSection.classList.add('hidden'); cameraSummary.textContent = 'Sin cámaras'; setState('Sin cámaras', 'bad'); return; }
        viewerSection.classList.remove('hidden');
        viewerState.cameras = data.cameras;
        const saved = savedCamera();
        let start = viewerState.cameras.findIndex(camera => String(camera.id) === saved);
        if (start < 0) start = Math.max(0, viewerState.cameras.findIndex(camera => camera.privacy !== true));
        viewerState.index = start;
        renderTiles();
        selectCamera(start);
        cameraSummary.textContent = `${data.cameras.length} ${data.cameras.length === 1 ? 'cámara' : 'cámaras'} · toca una para verla`;
        setState('En línea', 'ok');
      } catch (error) {
        viewerSection.classList.add('hidden');
        grid.innerHTML = `<div class="empty-state"><strong>No se pudieron cargar las cámaras</strong><div class="meta">${esc(error.message)}</div><button id="loadRetryButton" type="button">Reintentar</button></div>`;
        grid.querySelector('#loadRetryButton')?.addEventListener('click', load);
        cameraSummary.textContent = 'Error de conexión';
        setState(error.message === 'login required' ? 'Tapo sin conectar' : 'Nube no disponible', 'bad');
        if (error.message === 'login required') showLogin();
      }
    }
    document.querySelector('#prevCam').addEventListener('click', () => selectCamera(viewerState.index - 1));
    document.querySelector('#nextCam').addEventListener('click', () => selectCamera(viewerState.index + 1));
    document.addEventListener('keydown', event => {
      if (!recordingsModal.classList.contains('hidden') || event.target.closest('input, select, textarea') || document.querySelector('.app-modal:not(.hidden)')) return;
      if (event.key === 'ArrowLeft') selectCamera(viewerState.index - 1);
      if (event.key === 'ArrowRight') selectCamera(viewerState.index + 1);
    });
    (() => {
      let startX = 0, startY = 0, tracking = false;
      viewerCard.addEventListener('touchstart', event => { if (event.target.closest('button, input, select, .movement-panel')) { tracking = false; return; } const touch = event.touches[0]; startX = touch.clientX; startY = touch.clientY; tracking = true; }, {passive: true});
      viewerCard.addEventListener('touchend', event => { if (!tracking) return; tracking = false; const touch = event.changedTouches[0], dx = touch.clientX - startX, dy = touch.clientY - startY; if (Math.abs(dx) > 60 && Math.abs(dy) < 50) selectCamera(viewerState.index + (dx < 0 ? 1 : -1)); }, {passive: true});
    })();
    // Foto fija para el mosaico: la última imagen vista de cada cámara.
    const thumbCanvas = document.createElement('canvas');
    setInterval(() => {
      const video = viewerCard.querySelector('video'), camera = viewerState.cameras[viewerState.index];
      if (!video || !camera || video.readyState < 2 || !video.videoWidth) return;
      thumbCanvas.width = 320; thumbCanvas.height = Math.round(320 * video.videoHeight / video.videoWidth);
      try {
        thumbCanvas.getContext('2d').drawImage(video, 0, 0, thumbCanvas.width, thumbCanvas.height);
        const url = thumbCanvas.toDataURL('image/jpeg', 0.6);
        viewerState.thumbs.set(String(camera.id), url);
        const thumb = grid.querySelector(`.tile[data-index="${viewerState.index}"] .tile-thumb`);
        if (thumb) { thumb.textContent = ''; thumb.style.backgroundImage = `url('${url}')`; }
      } catch (_) {}
    }, 5000);
