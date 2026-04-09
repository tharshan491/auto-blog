(function () {
  'use strict';

  // ── Dark / Light Mode ──
  const root = document.documentElement;
  const themeBtn = document.getElementById('theme-toggle');
  const savedTheme = localStorage.getItem('theme') || 'dark';

  function setTheme(t) {
    root.setAttribute('data-theme', t);
    localStorage.setItem('theme', t);
    if (themeBtn) themeBtn.textContent = t === 'dark' ? '☀️' : '🌙';
  }

  setTheme(savedTheme);
  if (themeBtn) {
    themeBtn.addEventListener('click', () => {
      setTheme(root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
    });
  }

  // ── Search ──
  const searchOverlay  = document.getElementById('search-overlay');
  const searchInput    = document.getElementById('search-input');
  const searchResults  = document.getElementById('search-results');
  const searchClose    = document.getElementById('search-close');
  const searchOpenBtn  = document.getElementById('search-open-btn');

  let allPosts = [];

  async function loadPosts() {
    try {
      const r = await fetch('/search.json');
      allPosts = await r.json();
    } catch {
      allPosts = [];
    }
  }

  function openSearch() {
    if (!allPosts.length) loadPosts();
    if (searchOverlay) searchOverlay.classList.add('active');
    setTimeout(() => searchInput && searchInput.focus(), 50);
  }

  function closeSearch() {
    if (searchOverlay) searchOverlay.classList.remove('active');
    if (searchInput)   searchInput.value = '';
    if (searchResults) searchResults.innerHTML = '';
  }

  if (searchOpenBtn) searchOpenBtn.addEventListener('click', openSearch);
  if (searchClose)   searchClose.addEventListener('click', closeSearch);

  if (searchOverlay) {
    searchOverlay.addEventListener('click', e => {
      if (e.target === searchOverlay) closeSearch();
    });
  }

  document.addEventListener('keydown', e => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      searchOverlay && searchOverlay.classList.contains('active')
        ? closeSearch() : openSearch();
    }
    if (e.key === 'Escape') closeSearch();
  });

  function highlight(text, query) {
    if (!query) return text;
    const re = new RegExp(
      '(' + query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi'
    );
    return text.replace(re, '<mark style="background:var(--accent);color:#000;border-radius:2px">$1</mark>');
  }

  if (searchInput) {
    searchInput.addEventListener('input', () => {
      const q = searchInput.value.trim().toLowerCase();
      if (!q) { searchResults.innerHTML = ''; return; }

      const matches = allPosts.filter(p =>
        (p.title   || '').toLowerCase().includes(q) ||
        (p.content || '').toLowerCase().includes(q) ||
        (p.tags    || []).some(t => t.toLowerCase().includes(q))
      ).slice(0, 8);

      if (!matches.length) {
        searchResults.innerHTML = `<div class="search-empty">No results for "<strong>${q}</strong>"</div>`;
        return;
      }

      searchResults.innerHTML = matches.map(p => `
        <a class="search-result-item" href="${p.url}">
          <div class="result-title">${highlight(p.title, q)}</div>
          <div class="result-meta">${p.date || ''} ${p.categories ? '· ' + p.categories : ''}</div>
        </a>`).join('');
    });
  }

  // ── Reading Progress ──
  const progressBar = document.getElementById('reading-progress');
  if (progressBar) {
    window.addEventListener('scroll', () => {
      const el  = document.documentElement;
      const pct = (el.scrollTop / (el.scrollHeight - el.clientHeight)) * 100;
      progressBar.style.width = Math.min(pct, 100) + '%';
    }, { passive: true });
  }

  // ── Back to Top ──
  const backTop = document.getElementById('back-to-top');
  if (backTop) {
    window.addEventListener('scroll', () => {
      backTop.classList.toggle('visible', window.scrollY > 400);
    }, { passive: true });
    backTop.addEventListener('click', () =>
      window.scrollTo({ top: 0, behavior: 'smooth' })
    );
  }

  // ── Copy Code Blocks ──
  document.querySelectorAll('pre').forEach(pre => {
    const btn = document.createElement('button');
    btn.textContent = 'copy';
    btn.style.cssText = 'position:absolute;top:0.5rem;right:0.75rem;background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:0.25rem 0.6rem;font-size:0.75rem;color:var(--text2);cursor:pointer;font-family:var(--font-code);transition:all 0.3s';
    pre.style.position = 'relative';
    pre.appendChild(btn);
    btn.addEventListener('click', () => {
      const code = pre.querySelector('code');
      navigator.clipboard.writeText(code ? code.innerText : pre.innerText).then(() => {
        btn.textContent = 'copied!';
        btn.style.color = 'var(--accent)';
        setTimeout(() => {
          btn.textContent = 'copy';
          btn.style.color = 'var(--text2)';
        }, 2000);
      });
    });
  });

  // ── Copy Link Button ──
  const copyLinkBtn = document.querySelector('.share-btn.copy');
  if (copyLinkBtn) {
    copyLinkBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(window.location.href).then(() => {
        const orig = copyLinkBtn.innerHTML;
        copyLinkBtn.innerHTML = '✅ Copied!';
        setTimeout(() => copyLinkBtn.innerHTML = orig, 2000);
      });
    });
  }

  // ── Newsletter Form ──
  const newsletterForm = document.querySelector('.newsletter-form');
  if (newsletterForm) {
    newsletterForm.addEventListener('submit', e => {
      e.preventDefault();
      const email = newsletterForm.querySelector('input[type="email"]').value;
      if (email) {
        newsletterForm.innerHTML = `<p style="color:var(--accent);font-weight:600">✅ Thanks! You're subscribed.</p>`;
      }
    });
  }

  // ── Animate cards on scroll ──
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity   = '1';
        entry.target.style.transform = 'translateY(0)';
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('.post-card, .sidebar-widget').forEach(el => {
    el.style.opacity    = '0';
    el.style.transform  = 'translateY(20px)';
    el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
    observer.observe(el);
  });

})();
