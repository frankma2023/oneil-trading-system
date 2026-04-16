/* 统一导航栏 - 自动注入 */
(function() {
  const NAV_LINKS = [
    { label: '个股RS', href: '/rs_dashboard.html' },
    { label: '行业RS', href: '/sector_rs_dashboard.html' },
    { label: '行业扫描', href: '/sector_scan_dashboard.html' },
    { label: '大盘方向', href: '/market_dashboard.html' },
    { label: '个股扫描', href: '/stock_screening_dashboard.html' },
    { label: 'CAN SLIM', href: '/canslim_dashboard.html' },
    { label: '形态分析', href: '/oneil_pattern.html' },
    { label: '持仓哨兵', href: '/sell_signal.html' },
    { label: '持仓总览', href: '/portfolio.html' },
  ];

  function injectNav() {
    const currentPath = window.location.pathname;

    // Inject CSS
    const css = document.createElement('link');
    css.rel = 'stylesheet';
    css.href = '/static/css/nav.css';
    document.head.appendChild(css);

    // Build nav
    const nav = document.createElement('nav');
    nav.className = 'unified-nav';

    const brand = document.createElement('a');
    brand.className = 'nav-brand';
    brand.href = '/rs_dashboard.html';
    brand.textContent = '欧奈尔投资策略';
    nav.appendChild(brand);

    const links = document.createElement('div');
    links.className = 'nav-links';

    const currentPage = currentPath.split('/').pop() || 'index.html';
    NAV_LINKS.forEach(item => {
      const a = document.createElement('a');
      a.className = 'nav-link';
      a.href = item.href;
      a.textContent = item.label;
      const itemPage = item.href.split('/').pop();
      if (currentPath === item.href || currentPage === itemPage) {
        a.classList.add('active');
      }
      links.appendChild(a);
    });

    nav.appendChild(links);

    // 添加控制区域（主题切换等）
    const controls = document.createElement('div');
    controls.className = 'nav-controls';
    nav.appendChild(controls);

    // Hide old nav-pill bars inside headers (keep the header itself visible)
    const oldPills = document.querySelector('.nav-pills');
    if (oldPills) oldPills.style.display = 'none';

    // Insert at body start
    document.body.insertBefore(nav, document.body.firstChild);
    
    // 动态加载主题切换管理器
    if (!window.InvestmentTheme) {
      const themeScript = document.createElement('script');
      themeScript.src = '/static/js/theme.js';
      themeScript.defer = true;
      document.head.appendChild(themeScript);
    }
  }

  // Wait for body to exist
  if (document.body) {
    injectNav();
  } else {
    document.addEventListener('DOMContentLoaded', injectNav);
  }
})();
