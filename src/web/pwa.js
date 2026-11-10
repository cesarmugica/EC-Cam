/* ============================================================
   EC-Cam — App instalable (PWA)
   - Registra el service worker (sw.js, junto a este archivo).
   - Los elementos con [data-instalar] (ocultos al inicio con
     style="display:none") se muestran cuando el navegador permite
     instalar la app; en iPhone/iPad muestran cómo agregarla a la
     pantalla de inicio (texto en data-instalar-ios).
   ============================================================ */
(function () {
    var yo = document.currentScript && document.currentScript.src;
    if ('serviceWorker' in navigator && yo) {
        window.addEventListener('load', function () {
            navigator.serviceWorker.register(yo.replace(/pwa\.js(\?.*)?$/, 'sw.js')).catch(function () { });
        });
    }

    var instalada = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
    var ios = /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    // Para que el botón no aparezca siempre: en iPhone/iPad se oculta después de mostrar la
    // instrucción una vez; si en Android/PC se rechaza la instalación, no vuelve a salir en 30 días.
    var CLAVE = 'pwa_instalar_oculto';
    function oculto() {
        try { var v = +localStorage.getItem(CLAVE); return v > 0 && (v === 1 || Date.now() < v); } catch (e) { return false; }
    }
    function ocultar(dias) {
        try { localStorage.setItem(CLAVE, dias ? String(Date.now() + dias * 864e5) : '1'); } catch (e) { }
    }
    if (instalada) ocultar(0);
    var aviso = null, diferido = null;

    function botones() { return document.querySelectorAll('[data-instalar]'); }
    function mostrar(si) { botones().forEach(function (b) { b.style.display = si ? '' : 'none'; }); }

    function avisoIos(texto) {
        if (aviso) aviso.remove();
        aviso = document.createElement('div');
        aviso.setAttribute('role', 'status');
        aviso.textContent = texto;
        aviso.style.cssText = 'position:fixed;left:50%;bottom:22px;transform:translateX(-50%);z-index:99999;max-width:min(92vw,420px);' +
            'padding:13px 18px;border-radius:10px;background:#121614;color:#fff;font:15px/1.45 system-ui,-apple-system,"Segoe UI",Arial,sans-serif;' +
            'box-shadow:0 12px 30px rgba(0,0,0,.35);border-left:4px solid #F07C1E;text-align:left';
        document.body.appendChild(aviso);
        setTimeout(function () { if (aviso) { aviso.remove(); aviso = null; } }, 7000);
    }

    window.addEventListener('beforeinstallprompt', function (e) {
        e.preventDefault();
        diferido = e;
        if (!instalada && !oculto()) mostrar(true);
    });
    window.addEventListener('appinstalled', function () { diferido = null; mostrar(false); });

    document.addEventListener('DOMContentLoaded', function () {
        if (!instalada && ios && !oculto()) mostrar(true);
        botones().forEach(function (b) {
            b.addEventListener('click', function (e) {
                e.preventDefault();
                if (diferido) {
                    diferido.prompt();
                    diferido.userChoice.then(function (r) { if (!r || r.outcome !== 'accepted') ocultar(30); })
                        .finally(function () { diferido = null; mostrar(false); });
                } else if (ios) {
                    avisoIos(b.getAttribute('data-instalar-ios') || '');
                    ocultar(0);
                    mostrar(false);
                }
            });
        });
    });
})();
