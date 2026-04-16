/* 主题切换管理器 */
(function() {
  const STORAGE_KEY = 'investment_theme';
  const THEMES = {
    DARK: 'dark',
    LIGHT: 'light'
  };
  
  // 默认主题
  const defaultTheme = THEMES.DARK;
  
  // 主题配置
  const themeConfig = {
    [THEMES.DARK]: {
      name: '暗色模式',
      icon: '🌙',
      cssClass: 'theme-dark'
    },
    [THEMES.LIGHT]: {
      name: '浅色模式',
      icon: '☀️',
      cssClass: 'theme-light'
    }
  };
  
  // 当前主题
  let currentTheme = defaultTheme;
  
  // 初始化
  function init() {
    loadTheme();
    applyTheme();
  }
  
  // 加载保存的主题
  function loadTheme() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && themeConfig[saved]) {
      currentTheme = saved;
    }
  }
  
  // 应用主题
  function applyTheme() {
    // 移除所有主题类
    document.body.classList.remove('theme-dark', 'theme-light');
    
    // 添加当前主题类
    const theme = themeConfig[currentTheme];
    if (theme) {
      document.body.classList.add(theme.cssClass);
    }
    
    // 保存到本地存储
    localStorage.setItem(STORAGE_KEY, currentTheme);
    
    // 更新主题切换按钮（如果存在）
    updateThemeToggle();
  }
  
  // 切换主题
  function toggleTheme() {
    currentTheme = currentTheme === THEMES.DARK ? THEMES.LIGHT : THEMES.DARK;
    applyTheme();
  }
  
  // 设置特定主题
  function setTheme(theme) {
    if (themeConfig[theme]) {
      currentTheme = theme;
      applyTheme();
    }
  }
  
  // 更新主题切换按钮
  function updateThemeToggle() {
    const toggleBtn = document.getElementById('themeToggleBtn');
    if (toggleBtn && themeConfig[currentTheme]) {
      const theme = themeConfig[currentTheme];
      toggleBtn.innerHTML = `${theme.icon} ${theme.name}`;
      toggleBtn.title = `点击切换到${currentTheme === THEMES.DARK ? '浅色' : '暗色'}模式`;
    }
  }
  
  // 创建主题切换按钮
  function createThemeToggle() {
    const container = document.createElement('div');
    container.className = 'nav-controls';
    
    const toggleBtn = document.createElement('button');
    toggleBtn.id = 'themeToggleBtn';
    toggleBtn.className = 'theme-toggle-btn';
    toggleBtn.addEventListener('click', toggleTheme);
    
    container.appendChild(toggleBtn);
    
    // 插入到导航栏
    const nav = document.querySelector('.unified-nav');
    if (nav) {
      nav.appendChild(container);
    }
    
    updateThemeToggle();
  }
  
  // 等待DOM加载完成
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      init();
      createThemeToggle();
    });
  } else {
    init();
    createThemeToggle();
  }
  
  // 导出API
  window.InvestmentTheme = {
    toggle: toggleTheme,
    set: setTheme,
    get: () => currentTheme,
    THEMES: THEMES
  };
})();