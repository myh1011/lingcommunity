
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('create-page-form');
  const listEl = document.getElementById('page-list');

  async function loadPages() {
    try {
      const res = await fetch('/api/v1/pages');
      if (!res.ok) return;
      const pages = await res.json();

      listEl.innerHTML = pages.map(p => {
        // 显示头像，如果没有则显示占位符
        const avatarHtml = p.avatar_url 
          ? `<img src="${escapeAttr(p.avatar_url)}" alt="${escapeHtml(p.title)} 头像">`
          : `<div class="avatar-placeholder"><i class="fas fa-user-circle"></i></div>`;
        
        // 检查当前登录用户是否是上传者
        const currentUser = localStorage.getItem('auth_user');
        const isOwner = currentUser && p.uploader && currentUser === p.uploader;
        
        // 格式化日期
        const createdDate = p.created_at ? new Date(p.created_at).toLocaleDateString('zh-CN') : '未知';
        
        // 渲染标签
        const tagsHtml = p.tags && p.tags.length > 0 ? 
          `<div class="page-tags" style="margin: 8px 0; display: flex; flex-wrap: wrap; gap: 4px;">
            ${p.tags.map(tag => `
              <span style="background: var(--surface); padding: 2px 8px; border-radius: 12px; font-size: 12px; color: var(--muted);">
                ${escapeHtml(tag)}
              </span>
            `).join('')}
          </div>` : '';
        
        return `
          <li class="page-card-list-item">
            <article class="card">
              <div class="page-card-with-avatar">
                <div class="avatar-container">
                  <div class="avatar-image">
                    ${avatarHtml}
                  </div>
                </div>
                <div class="page-card-content">
                  <h3 class="card-title"><a href="/page/${encodeURIComponent(p.uid)}">${escapeHtml(p.title)}</a></h3>
                  ${tagsHtml}
                  <div class="card-meta">
                    <a class="meta-link" href="${escapeAttr(p.url)}" target="_blank" rel="noopener">
                      <i class="fas fa-download"></i> 下载链接
                    </a>
                    <div class="uploader-info">
                      <i class="fas fa-user"></i>
                      ${p.uploader ? `上传者: ${escapeHtml(p.uploader)}` : '匿名用户'}
                    </div>
                    <div class="uploader-info">
                      <i class="fas fa-calendar"></i>
                      ${createdDate}
                    </div>
                  </div>
                  ${isOwner ? `
                    <div class="page-actions" style="margin-top: 12px;">
                      <button class="btn btn-danger small delete-btn" data-uid="${p.uid}">
                        <i class="fas fa-trash"></i> 删除角色
                      </button>
                    </div>
                  ` : ''}
                </div>
              </div>
            </article>
          </li>`;
      }).join('');

      // 为删除按钮添加事件监听器
      document.querySelectorAll('.delete-btn').forEach(button => {
        button.addEventListener('click', async (e) => {
          e.preventDefault();
          const uid = button.getAttribute('data-uid');
          await deletePage(uid);
        });
      });

    } catch (err) {
      console.error('load pages failed', err);
    }
  }

  // 删除角色函数
  async function deletePage(uid) {
    const currentUser = localStorage.getItem('auth_user');
    if (!currentUser) {
      alert('请先登录');
      window.location.href = '/login';
      return;
    }

    if (!confirm('确定要删除这个角色吗？此操作不可撤销。')) {
      return;
    }

    try {
      const res = await fetch(`/api/v1/pages/${uid}`, {
        method: 'DELETE',
        headers: { 
          'Content-Type': 'application/json',
          'X-User': currentUser  // 发送当前用户名用于权限验证
        }
      });

      if (!res.ok) {
        const err = await res.json().catch(() => null);
        alert('删除失败: ' + (err?.detail ?? res.status));
        return;
      }

      alert('删除成功');
      loadPages(); // 重新加载角色列表
    } catch (err) {
      console.error('Error deleting page:', err);
      alert('删除时出错');
    }
  }

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      // 要求已登录
      const uploader = localStorage.getItem('auth_user');
      if (!uploader) {
        alert('请先登录后再创建角色');
        window.location.href = '/login';
        return;
      }

      const title = document.getElementById('title').value.trim();
      const body = document.getElementById('body').value.trim();
      const url = document.getElementById('url').value.trim();
      const tags = document.getElementById('tags').value.trim();
      const avatarFile = document.getElementById('avatar').files[0];

      // 创建 FormData 以支持文件上传
      const formData = new FormData();
      formData.append('title', title);
      formData.append('body', body);
      formData.append('url', url);
      formData.append('uploader', uploader);
      formData.append('tags', tags);
      
      if (avatarFile) {
        formData.append('avatar', avatarFile);
      }

      try {
        const res = await fetch('/api/v1/pages/', {
          method: 'POST',
          body: formData
        });

        if (!res.ok) {
          const err = await res.json().catch(() => null);
          alert('创建失败: ' + (err?.detail ?? res.status));
          return;
        }

        const data = await res.json();
        window.location.href = `/page/${encodeURIComponent(data.uid)}`;
      } catch (err) {
        console.error('Error creating page:', err);
        alert('创建时出错');
      }
    });
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, s => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[s]));
  }
  
  function escapeAttr(str) {
    return String(str).replace(/["']/g, s => (s === '"' ? '&quot;' : '&#39;'));
  }

  // 加载 Font Awesome（如果角色还没有）
  if (!document.querySelector('link[href*="font-awesome"]')) {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css';
    document.head.appendChild(link);
  }

  // 只有在首页才加载页面列表
  if (window.location.pathname === '/' || window.location.pathname === '/pages') {
    loadPages();
  }
});
