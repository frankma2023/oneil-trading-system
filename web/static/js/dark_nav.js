/* ====== 统一暗夜热力图导航系统 JavaScript ====== */
/* 处理导航交互、日期选择器、移动端菜单等功能 */

class DarkNavigation {
    constructor() {
        this.currentDate = new Date();
        this.selectedDate = new Date();
        this.init();
    }
    
    init() {
        this.initDatePicker();
        this.initMobileMenu();
        this.initNavLinks();
        this.updateDateTime();
        
        // 设置初始选中日期
        this.setDate(this.currentDate);
    }
    
    /* ====== 日期选择器功能 ====== */
    initDatePicker() {
        const datePickerBtn = document.getElementById('datePickerBtn');
        const datePickerDropdown = document.getElementById('datePickerDropdown');
        const prevMonthBtn = document.getElementById('prevMonthBtn');
        const nextMonthBtn = document.getElementById('nextMonthBtn');
        const currentMonthYear = document.getElementById('currentMonthYear');
        const datePickerGrid = document.getElementById('datePickerGrid');
        const quickToday = document.getElementById('quickToday');
        const quickYesterday = document.getElementById('quickYesterday');
        const quickWeekAgo = document.getElementById('quickWeekAgo');
        
        if (!datePickerBtn || !datePickerDropdown) return;
        
        // 切换日期选择器显示/隐藏
        datePickerBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            datePickerDropdown.classList.toggle('show');
            this.renderCalendar();
        });
        
        // 点击外部关闭日期选择器
        document.addEventListener('click', (e) => {
            if (!datePickerDropdown.contains(e.target) && !datePickerBtn.contains(e.target)) {
                datePickerDropdown.classList.remove('show');
            }
        });
        
        // 月份导航
        if (prevMonthBtn) {
            prevMonthBtn.addEventListener('click', () => {
                this.currentDate.setMonth(this.currentDate.getMonth() - 1);
                this.renderCalendar();
            });
        }
        
        if (nextMonthBtn) {
            nextMonthBtn.addEventListener('click', () => {
                this.currentDate.setMonth(this.currentDate.getMonth() + 1);
                this.renderCalendar();
            });
        }
        
        // 快速操作
        if (quickToday) {
            quickToday.addEventListener('click', () => {
                const today = new Date();
                this.setDate(today);
                this.currentDate = new Date(today);
                this.renderCalendar();
                datePickerDropdown.classList.remove('show');
            });
        }
        
        if (quickYesterday) {
            quickYesterday.addEventListener('click', () => {
                const yesterday = new Date();
                yesterday.setDate(yesterday.getDate() - 1);
                this.setDate(yesterday);
                this.currentDate = new Date(yesterday);
                this.renderCalendar();
                datePickerDropdown.classList.remove('show');
            });
        }
        
        if (quickWeekAgo) {
            quickWeekAgo.addEventListener('click', () => {
                const weekAgo = new Date();
                weekAgo.setDate(weekAgo.getDate() - 7);
                this.setDate(weekAgo);
                this.currentDate = new Date(weekAgo);
                this.renderCalendar();
                datePickerDropdown.classList.remove('show');
            });
        }
    }
    
    renderCalendar() {
        const currentMonthYear = document.getElementById('currentMonthYear');
        const datePickerGrid = document.getElementById('datePickerGrid');
        
        if (!currentMonthYear || !datePickerGrid) return;
        
        // 更新月份年份显示
        const monthNames = ['一月', '二月', '三月', '四月', '五月', '六月', 
                          '七月', '八月', '九月', '十月', '十一月', '十二月'];
        currentMonthYear.textContent = `${this.currentDate.getFullYear()}年 ${monthNames[this.currentDate.getMonth()]}`;
        
        // 清空日历网格
        datePickerGrid.innerHTML = '';
        
        // 添加星期标题
        const weekdays = ['日', '一', '二', '三', '四', '五', '六'];
        weekdays.forEach(day => {
            const weekdayEl = document.createElement('div');
            weekdayEl.className = 'date-picker-weekday';
            weekdayEl.textContent = day;
            datePickerGrid.appendChild(weekdayEl);
        });
        
        // 计算日历
        const year = this.currentDate.getFullYear();
        const month = this.currentDate.getMonth();
        
        // 当月第一天
        const firstDay = new Date(year, month, 1);
        // 当月最后一天
        const lastDay = new Date(year, month + 1, 0);
        // 当月天数
        const daysInMonth = lastDay.getDate();
        // 第一天是星期几（0=周日）
        const firstDayIndex = firstDay.getDay();
        
        // 添加上个月的最后几天
        const prevMonthLastDay = new Date(year, month, 0).getDate();
        for (let i = firstDayIndex - 1; i >= 0; i--) {
            const day = document.createElement('div');
            day.className = 'date-picker-day other-month';
            day.textContent = prevMonthLastDay - i;
            day.dataset.date = new Date(year, month - 1, prevMonthLastDay - i).toISOString().split('T')[0];
            datePickerGrid.appendChild(day);
        }
        
        // 添加当月天数
        const today = new Date();
        for (let i = 1; i <= daysInMonth; i++) {
            const day = document.createElement('div');
            const date = new Date(year, month, i);
            const dateStr = date.toISOString().split('T')[0];
            const selectedStr = this.selectedDate.toISOString().split('T')[0];
            const todayStr = today.toISOString().split('T')[0];
            
            day.className = 'date-picker-day';
            if (dateStr === selectedStr) {
                day.classList.add('selected');
            }
            if (dateStr === todayStr) {
                day.classList.add('today');
            }
            
            day.textContent = i;
            day.dataset.date = dateStr;
            
            day.addEventListener('click', () => {
                this.setDate(date);
                this.currentDate = new Date(date);
                this.renderCalendar();
                
                // 关闭下拉框
                const dropdown = document.getElementById('datePickerDropdown');
                if (dropdown) {
                    dropdown.classList.remove('show');
                }
            });
            
            datePickerGrid.appendChild(day);
        }
        
        // 添加下个月的前几天
        const nextMonthDays = 42 - (firstDayIndex + daysInMonth); // 6行 x 7列 = 42个格子
        for (let i = 1; i <= nextMonthDays; i++) {
            const day = document.createElement('div');
            day.className = 'date-picker-day other-month';
            day.textContent = i;
            day.dataset.date = new Date(year, month + 1, i).toISOString().split('T')[0];
            datePickerGrid.appendChild(day);
        }
    }
    
    setDate(date) {
        this.selectedDate = new Date(date);
        this.updateDateDisplay();
        this.onDateChange(this.selectedDate);
    }
    
    updateDateDisplay() {
        const dateDisplay = document.getElementById('dateDisplay');
        if (!dateDisplay) return;
        
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const selected = new Date(this.selectedDate.getFullYear(), this.selectedDate.getMonth(), this.selectedDate.getDate());
        
        if (selected.getTime() === today.getTime()) {
            dateDisplay.textContent = '今日';
        } else {
            const month = this.selectedDate.getMonth() + 1;
            const day = this.selectedDate.getDate();
            dateDisplay.textContent = `${month}月${day}日`;
        }
    }
    
    onDateChange(date) {
        console.log('日期更改为:', date.toLocaleDateString('zh-CN'));
        // 这里可以添加加载特定日期数据的逻辑
        // 例如: loadDataForDate(date);
        
        // 触发自定义事件
        const event = new CustomEvent('datechange', { detail: { date } });
        document.dispatchEvent(event);
    }
    
    /* ====== 移动端菜单功能 ====== */
    initMobileMenu() {
        const menuBtn = document.getElementById('navMenuBtn');
        const mobileMenu = document.getElementById('navMobileMenu');
        
        if (!menuBtn || !mobileMenu) return;
        
        menuBtn.addEventListener('click', () => {
            mobileMenu.classList.toggle('show');
        });
        
        // 点击菜单链接关闭菜单
        mobileMenu.addEventListener('click', (e) => {
            if (e.target.classList.contains('nav-mobile-link')) {
                mobileMenu.classList.remove('show');
            }
        });
        
        // 点击外部关闭菜单
        document.addEventListener('click', (e) => {
            if (!mobileMenu.contains(e.target) && !menuBtn.contains(e.target)) {
                mobileMenu.classList.remove('show');
            }
        });
    }
    
    /* ====== 导航链接功能 ====== */
    initNavLinks() {
        // 设置当前页面激活状态
        const currentPath = window.location.pathname;
        const pageName = currentPath.split('/').pop().replace('.html', '') || 'market';
        
        // 桌面端导航链接
        document.querySelectorAll('.nav-link').forEach(link => {
            const linkPage = link.getAttribute('data-page');
            if (linkPage === pageName) {
                link.classList.add('active');
            }
            
            link.addEventListener('click', (e) => {
                if (!link.getAttribute('href')) {
                    e.preventDefault();
                    this.setActiveNavLink(link);
                }
            });
        });
        
        // 移动端导航链接
        document.querySelectorAll('.nav-mobile-link').forEach(link => {
            const linkPage = link.getAttribute('data-page');
            if (linkPage === pageName) {
                link.classList.add('active');
            }
        });
    }
    
    setActiveNavLink(activeLink) {
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        document.querySelectorAll('.nav-mobile-link').forEach(link => {
            link.classList.remove('active');
        });
        
        activeLink.classList.add('active');
        
        // 同步移动端链接
        const linkPage = activeLink.getAttribute('data-page');
        const mobileLink = document.querySelector(`.nav-mobile-link[data-page="${linkPage}"]`);
        if (mobileLink) {
            mobileLink.classList.add('active');
        }
    }
    
    /* ====== 时间更新功能 ====== */
    updateDateTime() {
        const updateTime = () => {
            const now = new Date();
            const timeStr = now.toLocaleTimeString('zh-CN', {
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
            const dateStr = now.toLocaleDateString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit'
            });
            
            // 更新时间显示
            const timeElement = document.getElementById('currentTime');
            if (timeElement) {
                timeElement.textContent = timeStr;
            }
            
            // 更新日期显示（如果显示的是"今日"）
            const dateDisplay = document.getElementById('dateDisplay');
            if (dateDisplay && dateDisplay.textContent === '今日') {
                this.updateDateDisplay();
            }
        };
        
        // 立即更新一次
        updateTime();
        
        // 每秒更新一次
        setInterval(updateTime, 1000);
    }
    
    /* ====== 工具方法 ====== */
    formatDate(date) {
        return date.toISOString().split('T')[0];
    }
    
    formatDateChinese(date) {
        const year = date.getFullYear();
        const month = date.getMonth() + 1;
        const day = date.getDate();
        return `${year}年${month}月${day}日`;
    }
    
    isToday(date) {
        const today = new Date();
        return date.getDate() === today.getDate() &&
               date.getMonth() === today.getMonth() &&
               date.getFullYear() === today.getFullYear();
    }
}

/* ====== 页面加载后初始化 ====== */
document.addEventListener('DOMContentLoaded', () => {
    // 初始化导航系统
    window.darkNav = new DarkNavigation();
    
    // 添加键盘快捷键
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + D 打开日期选择器
        if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
            e.preventDefault();
            const datePickerBtn = document.getElementById('datePickerBtn');
            if (datePickerBtn) {
                datePickerBtn.click();
            }
        }
        
        // Esc 关闭所有下拉菜单
        if (e.key === 'Escape') {
            document.querySelectorAll('.date-picker-dropdown.show, .nav-mobile-menu.show').forEach(el => {
                el.classList.remove('show');
            });
        }
    });
    
    // 初始化页面特定的功能
    initPageSpecificFeatures();
});

/* ====== 页面特定功能 ====== */
function initPageSpecificFeatures() {
    // 这里可以添加每个页面特定的初始化代码
    
    // 示例：为所有卡片添加悬停效果
    document.querySelectorAll('.card, .stat-card, .panel-card').forEach(card => {
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-4px)';
        });
        card.addEventListener('mouseleave', () => {
            card.style.transform = '';
        });
    });
    
    // 示例：为所有按钮添加点击反馈
    document.querySelectorAll('.btn, .nav-action-btn, .date-picker-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = '';
            }, 200);
        });
    });
    
    // 示例：为搜索框添加实时搜索功能
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                console.log('搜索关键词:', this.value);
                // 这里可以添加实际的搜索逻辑
            }, 300);
        });
    }
}

/* ====== 数据加载工具函数 ====== */
async function loadDataForDate(date) {
    try {
        const dateStr = window.darkNav.formatDate(date);
        console.log('加载日期数据:', dateStr);
        
        // 这里可以添加实际的数据加载逻辑
        // 例如：const response = await fetch(`/api/data?date=${dateStr}`);
        // const data = await response.json();
        // updateUIWithData(data);
        
        return { success: true, date: dateStr };
    } catch (error) {
        console.error('加载数据失败:', error);
        return { success: false, error: error.message };
    }
}

/* ====== 导出函数供其他脚本使用 ====== */
window.DarkNavigation = DarkNavigation;
window.loadDataForDate = loadDataForDate;