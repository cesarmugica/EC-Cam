    // ---------- EC-Cam: sesión propia, usuarios y cuenta ----------
    const usersModal = document.querySelector('#usersModal'), accountModal = document.querySelector('#accountModal'), userList = document.querySelector('#userList'), usersMsg = document.querySelector('#usersMsg'), accountMsg = document.querySelector('#accountMsg');
    function roleName(role) { return role === 'admin' ? 'Administrador' : 'Visor'; }
    function openModal(modal) { modal.classList.remove('hidden'); modal.querySelector('input, button')?.focus(); }
    function closeModal(modal) { modal.classList.add('hidden'); }
    document.querySelectorAll('[data-close-modal]').forEach(button => button.addEventListener('click', () => closeModal(button.closest('.app-modal'))));
    [usersModal, accountModal].forEach(modal => modal.addEventListener('click', event => { if (event.target === modal) closeModal(modal); }));
    document.addEventListener('keydown', event => { if (event.key === 'Escape') [usersModal, accountModal].forEach(closeModal); });
    function setMsg(node, text, tone = '') { node.textContent = text; node.className = `form-msg ${tone}`; }
    function renderUsers(users) {
      userList.innerHTML = users.map(u => { const me = u.username === appUser.user; return `<div class="user-row" data-user="${esc(u.username)}"><div class="who"><strong>${esc(u.username)}</strong>${me ? ' <small style="display:inline">(tú)</small>' : ''}<small>${roleName(u.role)}</small></div><div class="row-actions">${me ? '' : `<button class="ghost" type="button" data-act="role" data-role="${u.role === 'admin' ? 'viewer' : 'admin'}">Hacer ${u.role === 'admin' ? 'visor' : 'admin'}</button>`}<button class="ghost" type="button" data-act="password">Contraseña</button>${me ? '' : '<button class="danger" type="button" data-act="delete">Borrar</button>'}</div></div>`; }).join('');
    }
    async function loadUsers() { setMsg(usersMsg, ''); try { const data = await api('/api/app/users'); renderUsers(data.users); } catch (error) { setMsg(usersMsg, error.message, 'bad'); } }
    userList.addEventListener('click', async event => {
      const button = event.target.closest('button[data-act]'); if (!button) return;
      const username = button.closest('.user-row').dataset.user, act = button.dataset.act;
      try {
        let data;
        if (act === 'delete') { if (!confirm(`¿Borrar al usuario ${username}?`)) return; data = await api('/api/app/users/delete', {method: 'POST', body: JSON.stringify({username})}); setMsg(usersMsg, 'Usuario borrado.', 'ok'); }
        else if (act === 'role') { data = await api('/api/app/users/role', {method: 'POST', body: JSON.stringify({username, role: button.dataset.role})}); setMsg(usersMsg, 'Rol actualizado.', 'ok'); }
        else { const password = prompt(`Nueva contraseña para ${username} (mín. 8 caracteres):`); if (!password) return; data = await api('/api/app/users/password', {method: 'POST', body: JSON.stringify({username, password})}); setMsg(usersMsg, 'Contraseña cambiada; se cerraron sus sesiones.', 'ok'); }
        renderUsers(data.users);
      } catch (error) { setMsg(usersMsg, error.message, 'bad'); }
    });
    document.querySelector('#addUserForm').addEventListener('submit', async event => {
      event.preventDefault(); const form = event.currentTarget, submit = form.querySelector('button[type=submit]'); submit.disabled = true;
      try { const data = await api('/api/app/users', {method: 'POST', body: JSON.stringify({username: form.querySelector('#newUserName').value, password: form.querySelector('#newUserPass').value, role: form.querySelector('#newUserRole').value})}); renderUsers(data.users); form.reset(); setMsg(usersMsg, 'Usuario agregado.', 'ok'); }
      catch (error) { setMsg(usersMsg, error.message, 'bad'); } finally { submit.disabled = false; }
    });
    document.querySelector('#passwordForm').addEventListener('submit', async event => {
      event.preventDefault(); const form = event.currentTarget, submit = form.querySelector('button[type=submit]');
      const current = form.querySelector('#currentPass').value, next = form.querySelector('#newPass').value;
      if (next !== form.querySelector('#newPass2').value) { setMsg(accountMsg, 'Las contraseñas nuevas no coinciden.', 'bad'); return; }
      submit.disabled = true;
      try { await api('/api/app/me/password', {method: 'POST', body: JSON.stringify({current, new: next})}); form.reset(); setMsg(accountMsg, 'Contraseña cambiada. Se cerró la sesión en tus otros dispositivos.', 'ok'); }
      catch (error) { setMsg(accountMsg, error.message, 'bad'); } finally { submit.disabled = false; }
    });
    document.querySelector('#usersButton').addEventListener('click', () => { openModal(usersModal); loadUsers(); });
    document.querySelector('#accountButton').addEventListener('click', () => { document.querySelector('#accountInfo').textContent = `Usuario: ${appUser.user} · ${roleName(appUser.role)}`; document.querySelector('#accountUserHidden').value = appUser.user; setMsg(accountMsg, ''); openModal(accountModal); });
    document.querySelector('#appLogoutButton').addEventListener('click', async () => { try { await api('/api/app/logout', {method: 'POST'}); } catch (_) {} location.replace('/login'); });
    async function checkTapo() { try { const data = await api('/api/session'); if (data.authenticated) { showApp(); await load(); } else if (data.mfa_pending && isAdmin()) showMfa(data.mfa_types); else showLogin(); } catch (_) { showLogin(); } }
    document.querySelector('#viewerRetryButton').addEventListener('click', checkTapo);
    (async function init() {
      try {
        const session = await api('/api/app/session');
        if (!session.app_authenticated) { location.replace(session.needs_setup ? '/setup' : '/login'); return; }
        appUser = {user: session.user, role: session.role};
        const footer = document.querySelector('.app-footer'); if (footer && session.version) footer.insertAdjacentText('afterbegin', `Versión ${session.version} · `);
        document.querySelector('#userChip').innerHTML = `<strong>${esc(appUser.user)}</strong> · ${roleName(appUser.role)}`;
        document.querySelector('#usersButton').classList.toggle('hidden', !isAdmin());
      } catch (_) { location.replace('/login'); return; }
      await checkTapo();
    })();
