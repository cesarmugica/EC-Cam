    // ---------- EC-Cam: Probar mis cámaras → Enviar reporte ----------
    // Prueba cada cámara (en vivo, lista de grabaciones, reproducir) y arma un
    // reporte de compatibilidad para GitHub con solo modelo, firmware, versión
    // y resultados: nunca el nombre de la cámara ni datos de la cuenta.
    const REPORT_URL = 'https://github.com/cesarmugica/EC-Cam/issues/new';
    const REPORT_OPTIONS = {ok: '✅ Funciona / Works', fail: '❌ No funciona / Doesn\u0027t work', untested: '⚪ No probado / Not tested', nosd: '— Sin memoria SD / No SD card', noptz: '— La cámara no se mueve / Camera has no pan/tilt'};
    const REPORT_NOTE = 'Prueba automática / Automatic test: EC-Cam 🧪';
    const TEST_ICONS = {ok: '✅', fail: '❌', untested: '⚪', nosd: '—', noptz: '—', running: '⏳', ptz: '✥'};
    const testModal = document.querySelector('#testModal'), testTable = document.querySelector('#testTable'), testRunButton = document.querySelector('#testRunButton'), testReports = document.querySelector('#testReports'), testStatus = document.querySelector('#testStatus');
    const testState = {cams: [], results: {}, running: false, cancelled: false, controller: null, jobId: ''};
    function testLabel(kind) { return {ok: 'Funciona', fail: 'No funciona', untested: 'No probado', nosd: 'Sin memoria SD', noptz: 'No se mueve', running: 'Probando…', ptz: 'Disponible (no se mueve sola durante la prueba)'}[kind] || ''; }
    function testCell(id, key) {
      const result = (testState.results[id] || {})[key];
      if (!result) return '<td class="test-cell">·</td>';
      return `<td class="test-cell ${result.kind}" title="${esc(testLabel(result.kind) + (result.error ? ' · ' + result.error : ''))}">${TEST_ICONS[result.kind] || '·'}</td>`;
    }
    function renderTestTable() {
      testTable.innerHTML = `<table><thead><tr><th></th><th>Cámara</th><th>Modelo</th><th>Firmware</th><th>En vivo</th><th>Lista SD</th><th>Reproducir</th><th>Mover</th></tr></thead><tbody>${testState.cams.map(camera => `<tr><td><input type="checkbox" class="test-pick" data-id="${esc(camera.id)}" ${camera.privacy === true ? '' : 'checked'} ${testState.running ? 'disabled' : ''} aria-label="Probar ${esc(camera.name)}"></td><td>${esc(camera.name)}${camera.privacy === true ? ' <small>(privacidad activada)</small>' : ''}</td><td>${esc(camera.model)}</td><td><small>${esc(camera.firmware || '?')}</small></td>${testCell(camera.id, 'live')}${testCell(camera.id, 'list')}${testCell(camera.id, 'play')}${testCell(camera.id, 'move')}</tr>`).join('')}</tbody></table>`;
    }
    function setResult(id, key, kind, error = '') { testState.results[id] = {...(testState.results[id] || {}), [key]: {kind, error}}; renderTestTable(); }
    const OFFLINE_TEXT = 'Cámara sin conexión (según Tapo)';
    const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
    async function streamReason(id) {
      try { const status = await api(`/api/app/stream-status?cam=${encodeURIComponent(id)}&q=SD`); return status.kind === 'offline' ? OFFLINE_TEXT : (status.error || ''); } catch (_) { return ''; }
    }
    // Una cámara apagada o sin internet no dice nada de la compatibilidad: queda «No probado».
    function liveFailure(reason) { return reason === OFFLINE_TEXT ? ['untested', reason] : ['fail', reason]; }
    async function testLive(id) {
      const controller = new AbortController(); testState.controller = controller;
      const timer = setTimeout(() => controller.abort(), 30000);
      let received = 0;
      try {
        const response = await fetch(`/stream/${encodeURIComponent(id)}.mp4?q=sd&t=${Date.now()}`, {signal: controller.signal, credentials: 'same-origin'});
        if (!response.ok) return liveFailure(localizeServerMessage((await response.json().catch(() => ({}))).error) || await streamReason(id));
        const reader = response.body.getReader();
        while (received < 20000) { const {done, value} = await reader.read(); if (done) break; received += value.length; }
        controller.abort();
        return received >= 20000 ? ['ok', ''] : liveFailure(await streamReason(id) || 'La cámara no envió video.');
      } catch (_) {
        return testState.cancelled ? ['untested', ''] : liveFailure(await streamReason(id) || 'La cámara no envió video en 30 s.');
      } finally { clearTimeout(timer); testState.controller = null; }
    }
    async function testRecordings(id) {
      let dates;
      try { dates = await api(`/api/cameras/${encodeURIComponent(id)}/recordings/dates?days=7`); } catch (error) { return {list: ['fail', error.message], play: ['untested', '']}; }
      if (!dates.sd_available) return {list: ['nosd', ''], play: ['nosd', '']};
      if (!dates.dates?.length) return {list: ['untested', 'La memoria SD no tiene grabaciones.'], play: ['untested', '']};
      let clips = [];
      for (const date of [...dates.dates].reverse().slice(0, 3)) {
        try { const day = await api(`/api/cameras/${encodeURIComponent(id)}/recordings?date=${encodeURIComponent(date)}`); clips = (day.clips || []).filter(clip => Number(clip.end) - Number(clip.start) >= 6); } catch (error) { return {list: ['fail', error.message], play: ['untested', '']}; }
        if (clips.length) break;
      }
      if (!clips.length) return {list: ['ok', ''], play: ['untested', 'No hubo un clip para probar.']};
      if (testState.cancelled) return {list: ['ok', ''], play: ['untested', '']};
      const clip = clips[Math.max(0, clips.length - 2)];
      let jobId = '';
      try {
        const created = await api(`/api/cameras/${encodeURIComponent(id)}/recordings/play`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({start: Number(clip.start), end: Number(clip.start) + 8})});
        jobId = testState.jobId = created.job_id;
        for (let i = 0; i < 120 && !testState.cancelled; i++) {
          await pause(500);
          const job = await api(`/api/recording-jobs/${encodeURIComponent(jobId)}`);
          if (job.status === 'error') return {list: ['ok', ''], play: ['fail', localizeServerMessage(job.error) || '']};
          if (job.status === 'ready' || Number(job.progress) >= 26) return {list: ['ok', ''], play: ['ok', '']};
        }
        return {list: ['ok', ''], play: [testState.cancelled ? 'untested' : 'fail', testState.cancelled ? '' : 'Se agotó el tiempo.']};
      } catch (error) {
        return {list: ['ok', ''], play: ['fail', error.message]};
      } finally {
        if (jobId) fetch(`/api/recording-jobs/${encodeURIComponent(jobId)}/cancel`, {method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json'}, body: '{}'}).catch(() => {});
        testState.jobId = '';
      }
    }
    function reportUrl(camera, result) {
      const pick = key => REPORT_OPTIONS[(result[key] || {}).kind] || REPORT_OPTIONS.untested;
      const errors = ['live', 'list', 'play'].filter(key => (result[key] || {}).kind === 'fail').map(key => result[key].error).filter(Boolean).join('\n');
      const version = (document.querySelector('.brand-subtitle')?.textContent.match(/\d+\.\d+\.\d+/) || [''])[0];
      const params = new URLSearchParams({template: 'compatibilidad.yml', title: ('[Compatibilidad] ' + (camera.model || '') + ' ' + (camera.firmware || '')).trim(), modelo: camera.model || '', hardware: camera.hardware || '', firmware: camera.firmware || '', version, envivo: pick('live'), lista: pick('list'), reproducir: pick('play'), mover: pick('move'), error: errors, notas: REPORT_NOTE});
      return REPORT_URL + '?' + params.toString();
    }
    // Varias cámaras del mismo modelo y firmware: un solo reporte con el mejor
    // resultado de cada prueba (si una funciona, el modelo funciona) y sus errores.
    const RESULT_RANK = {ok: 4, fail: 3, nosd: 2, noptz: 2, untested: 1};
    function mergeResults(a, b) {
      const merged = {};
      for (const key of ['live', 'list', 'play', 'move']) {
        const x = a[key] || {kind: 'untested', error: ''}, y = b[key] || {kind: 'untested', error: ''};
        const best = (RESULT_RANK[y.kind] || 0) > (RESULT_RANK[x.kind] || 0) ? y : x;
        const errors = best.kind === 'ok' ? '' : [...new Set([x.error, y.error].filter(Boolean))].join(' · ');
        merged[key] = {kind: best.kind, error: errors};
      }
      return merged;
    }
    function renderReports() {
      const groups = new Map();
      for (const camera of testState.cams) {
        const result = testState.results[camera.id];
        if (!result || !result.live) continue;
        const key = `${camera.model}|${camera.firmware}|${camera.hardware}`;
        const group = groups.get(key);
        groups.set(key, group ? {camera: group.camera, result: mergeResults(group.result, result)} : {camera, result});
      }
      if (!groups.size) { testReports.innerHTML = ''; return; }
      testReports.innerHTML = `<h3>Enviar reporte</h3><p class="meta">Un reporte por cada combinación de modelo y firmware. Se abre GitHub con el formulario ya llenado; revísalo y dale «Create».</p>${[...groups.values()].map(({camera, result}, index) => `<div class="test-report"><span><strong>${esc(camera.model)}</strong> <small>${esc(camera.firmware)}</small></span><button type="button" class="secondary" data-report="${index}">📤 Enviar reporte</button></div>`).join('')}`;
      const list = [...groups.values()];
      testReports.querySelectorAll('[data-report]').forEach(button => button.addEventListener('click', () => { const {camera, result} = list[Number(button.dataset.report)]; window.open(reportUrl(camera, result), '_blank', 'noopener'); }));
    }
    async function runCameraTest() {
      const picked = [...testTable.querySelectorAll('.test-pick:checked')].map(input => input.dataset.id);
      if (!picked.length) { testStatus.textContent = 'Elige al menos una cámara.'; return; }
      testState.running = true; testState.cancelled = false; testRunButton.disabled = true; testReports.innerHTML = '';
      for (const id of picked) testState.results[id] = {};
      for (const [position, id] of picked.entries()) {
        if (testState.cancelled) break;
        const camera = testState.cams.find(item => String(item.id) === String(id));
        testStatus.textContent = `Probando ${position + 1} de ${picked.length}: ${camera.name}…`;
        setResult(id, 'move', camera.ptz ? 'ptz' : 'noptz');
        setResult(id, 'live', 'running');
        const [liveKind, liveError] = await testLive(id);
        setResult(id, 'live', liveKind, liveError);
        if (testState.cancelled) break;
        setResult(id, 'list', 'running'); setResult(id, 'play', 'running');
        const recordings = await testRecordings(id);
        setResult(id, 'list', ...recordings.list); setResult(id, 'play', ...recordings.play);
      }
      for (const result of Object.values(testState.results)) if (result.move && result.move.kind === 'ptz') result.move = {kind: 'untested', error: ''};
      testState.running = false; testRunButton.disabled = false;
      testStatus.textContent = testState.cancelled ? 'Prueba detenida.' : 'Prueba terminada. Pasa el cursor sobre ❌ para ver el motivo.';
      renderTestTable(); renderReports();
    }
    async function openCameraTest() {
      testModal.classList.remove('hidden'); testStatus.textContent = 'Cargando cámaras…'; testReports.innerHTML = '';
      try { const data = await api('/api/cameras'); testState.cams = data.cameras || []; testStatus.textContent = 'Elige las cámaras y dale «Iniciar prueba». Tarda alrededor de un minuto por cámara; mientras tanto se pausa el video en vivo.'; }
      catch (error) { testState.cams = []; testStatus.textContent = error.message; }
      renderTestTable(); renderReports();
    }
    function closeCameraTest() {
      if (testState.running) { testState.cancelled = true; testState.controller?.abort(); }
      testModal.classList.add('hidden');
    }
    document.querySelector('#cameraTestButton')?.addEventListener('click', openCameraTest);
    testRunButton.addEventListener('click', runCameraTest);
    testModal.querySelector('[data-close-test]').addEventListener('click', closeCameraTest);
    testModal.addEventListener('click', event => { if (event.target === testModal) closeCameraTest(); });
