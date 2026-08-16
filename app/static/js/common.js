/* LingChat communitymods 公共前端工具
 * 认证（令牌）、API 封装、Toast、转义、日期格式化、统一导航渲染。
 */
(function () {
  'use strict';

  var LS_TOKEN = 'lc_token';
  var LS_USER = 'lc_user';

  function getUser() {
    try {
      return JSON.parse(localStorage.getItem(LS_USER) || 'null');
    } catch (e) {
      return null;
    }
  }
  function setUser(u) {
    if (u) localStorage.setItem(LS_USER, JSON.stringify(u));
    else localStorage.removeItem(LS_USER);
  }
  function getToken() { return localStorage.getItem(LS_TOKEN); }
  function setToken(t) {
    if (t) localStorage.setItem(LS_TOKEN, t);
    else localStorage.removeItem(LS_TOKEN);
  }
  function isAdmin() {
    var u = getUser();
    return !!u && (u.role === 'admin' || u.role === 'super_admin');
  }
  function logout() { setToken(null); setUser(null); }

  /** 统一 API 请求：自动附带 Bearer 令牌、JSON 序列化、错误抛出带 detail。 */
  async function api(path, opts) {
    opts = opts || {};
    var headers = Object.assign({}, opts.headers || {});
    var token = getToken();
    if (token) headers['Authorization'] = 'Bearer ' + token;
    if (opts.body && !(opts.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(opts.body);
    }
    var res;
    try {
      res = await fetch(path, Object.assign({}, opts, { headers: headers }));
    } catch (e) {
      throw new Error('网络错误，请检查网络连接');
    }
    var data = null;
    try { data = await res.json(); } catch (e) { /* 无 JSON 响应体 */ }
    if (!res.ok) {
      var err = new Error((data && data.detail) || ('请求失败 (HTTP ' + res.status + ')'));
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  }

  /** 轻量 toast 提示。 */
  function toast(msg, type) {
    type = type || 'info';
    var el = document.createElement('div');
    el.className = 'lc-toast lc-toast-' + type;
    el.textContent = msg;
    var box = document.getElementById('lc-toast-box');
    if (!box) {
      box = document.createElement('div');
      box.id = 'lc-toast-box';
      document.body.appendChild(box);
    }
    box.appendChild(el);
    setTimeout(function () { el.classList.add('show'); }, 10);
    setTimeout(function () {
      el.classList.remove('show');
      setTimeout(function () { el.remove(); }, 300);
    }, 3200);
  }

  function escapeHtml(str) {
    return String(str == null ? '' : str).replace(/[&<>"']/g, function (s) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[s];
    });
  }
  function escapeAttr(str) {
    return String(str == null ? '' : str).replace(/["']/g, function (s) {
      return s === '"' ? '&quot;' : '&#39;';
    });
  }
  function fmtDate(v) {
    if (!v) return '未知';
    var d = new Date(v);
    return isNaN(d.getTime()) ? String(v) : d.toLocaleDateString('zh-CN');
  }
  function fmtDateTime(v) {
    if (!v) return '未知';
    var d = new Date(v);
    return isNaN(d.getTime()) ? String(v) : d.toLocaleString('zh-CN', { hour12: false });
  }
  function qs(obj) {
    var params = new URLSearchParams();
    Object.keys(obj || {}).forEach(function (k) {
      var val = obj[k];
      if (val === undefined || val === null || val === '') return;
      params.append(k, val);
    });
    var s = params.toString();
    return s ? '?' + s : '';
  }

  /** 统一渲染头部登录状态。
   *  约定元素 id：auth-info / auth-link / admin-link / user-dropdown 可选。 */
  function renderAuth() {
    var user = getUser();
    var infoEl = document.getElementById('auth-info');
    var linkEl = document.getElementById('auth-link');
    var adminEl = document.getElementById('admin-link');
    if (infoEl) {
      infoEl.textContent = user ? '欢迎，' + user.username : '游客';
    }
    if (linkEl) {
      if (user) {
        linkEl.textContent = '登出';
        linkEl.setAttribute('href', '#');
        linkEl.onclick = function (e) {
          e.preventDefault();
          logout();
          window.location.href = '/';
        };
      } else {
        linkEl.textContent = '登录';
        linkEl.setAttribute('href', '/login');
        linkEl.onclick = null;
      }
    }
    if (adminEl) {
      adminEl.style.display = isAdmin() ? '' : 'none';
    }
  }

  /** 未登录时统一跳转登录页（带返回地址）。 */
  function requireLogin() {
    if (getToken()) return true;
    toast('请先登录', 'warning');
    setTimeout(function () {
      window.location.href = '/login?redirect=' + encodeURIComponent(window.location.pathname + window.location.search);
    }, 600);
    return false;
  }

  window.LC = {
    getUser: getUser,
    setUser: setUser,
    getToken: getToken,
    setToken: setToken,
    isAdmin: isAdmin,
    logout: logout,
    api: api,
    toast: toast,
    escapeHtml: escapeHtml,
    escapeAttr: escapeAttr,
    fmtDate: fmtDate,
    fmtDateTime: fmtDateTime,
    qs: qs,
    renderAuth: renderAuth,
    requireLogin: requireLogin,
  };

  document.addEventListener('DOMContentLoaded', renderAuth);
})();
