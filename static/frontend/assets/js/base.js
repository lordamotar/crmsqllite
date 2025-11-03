// Обработка сворачивания боковой панели
document.addEventListener('DOMContentLoaded', function() {
  const menuToggles = document.querySelectorAll('.layout-menu-toggle');
  const overlay = document.querySelector('.layout-overlay');
  const root = document.documentElement;
  const layoutMenu = document.querySelector('.layout-menu');
  const appBrand = document.querySelector('.app-brand');
  
  // Восстанавливаем состояние из localStorage
  const isCollapsed = localStorage.getItem('sidebar-collapsed') === 'true';
  if (isCollapsed) {
    root.classList.add('layout-menu-collapsed');
  }
  
  menuToggles.forEach(function(toggle) {
    toggle.addEventListener('click', function(e) {
      e.preventDefault();
      root.classList.toggle('layout-menu-collapsed');
      
      // Сохраняем состояние в localStorage
      const isNowCollapsed = root.classList.contains('layout-menu-collapsed');
      localStorage.setItem('sidebar-collapsed', isNowCollapsed.toString());
      
      // Показываем/скрываем overlay на мобильных устройствах
      if (window.innerWidth < 1200) {
        if (isNowCollapsed) {
          overlay.style.display = 'block';
          setTimeout(() => overlay.classList.add('show'), 10);
        } else {
          overlay.classList.remove('show');
          setTimeout(() => overlay.style.display = 'none', 300);
        }
      }
    });
  });
  
  // Обработка наведения на логотип/меню при свернутом состоянии (только на десктопе)
  let hoverTimeout = null;
  
  function setupMenuHover() {
    if (!layoutMenu || window.innerWidth < 1200) {
      return;
    }
    
    // При наведении на логотип/меню - раскрываем меню
    function handleMouseEnter(e) {
      if (root.classList.contains('layout-menu-collapsed')) {
        clearTimeout(hoverTimeout);
        hoverTimeout = null;
        root.classList.add('layout-menu-hover');
        if (layoutMenu) {
          layoutMenu.classList.add('menu-hover');
        }
      }
    }
    
    // При уходе курсора - закрываем меню с задержкой
    function handleMouseLeave(e) {
      if (root.classList.contains('layout-menu-collapsed')) {
        clearTimeout(hoverTimeout);
        hoverTimeout = setTimeout(function() {
          root.classList.remove('layout-menu-hover');
          if (layoutMenu) {
            layoutMenu.classList.remove('menu-hover');
          }
        }, 300); // Задержка 300мс для плавного перехода
      }
    }
    
    // Удаляем старые обработчики если есть
    const newLayoutMenu = document.querySelector('.layout-menu');
    if (newLayoutMenu) {
      newLayoutMenu.removeEventListener('mouseenter', handleMouseEnter);
      newLayoutMenu.removeEventListener('mouseleave', handleMouseLeave);
      newLayoutMenu.addEventListener('mouseenter', handleMouseEnter);
      newLayoutMenu.addEventListener('mouseleave', handleMouseLeave);
    }
  }
  
  // Инициализируем hover при загрузке
  setupMenuHover();
  
  // Закрытие меню при клике на overlay
  if (overlay) {
    overlay.addEventListener('click', function() {
      root.classList.remove('layout-menu-collapsed');
      root.classList.remove('layout-menu-hover');
      if (layoutMenu) {
        layoutMenu.classList.remove('menu-hover');
      }
      localStorage.setItem('sidebar-collapsed', 'false');
      overlay.classList.remove('show');
      setTimeout(() => overlay.style.display = 'none', 300);
    });
  }
  
  // Обработка изменения размера окна
  window.addEventListener('resize', function() {
    if (window.innerWidth >= 1200) {
      // На больших экранах убираем overlay
      if (overlay) {
        overlay.classList.remove('show');
        overlay.style.display = 'none';
      }
      
      // Включаем hover на десктопе
      setupMenuHover();
    } else {
      // На мобильных отключаем hover
      if (layoutMenu) {
        root.classList.remove('layout-menu-hover');
        layoutMenu.classList.remove('menu-hover');
      }
      
      // На мобильных устройствах показываем overlay если меню открыто
      if (root.classList.contains('layout-menu-collapsed') && overlay) {
        overlay.style.display = 'block';
        setTimeout(() => overlay.classList.add('show'), 10);
      }
    }
  });
});

// Обработка раскрывающегося меню
document.addEventListener('DOMContentLoaded', function() {
  // Инициализация меню - открываем активный пункт
  const currentPath = window.location.pathname;
  const menuLinks = document.querySelectorAll('.menu-link:not(.menu-toggle)');
  
  menuLinks.forEach(function(link) {
    const href = link.getAttribute('href');
    if (href && currentPath.startsWith(href) && href !== '/' && href !== 'javascript:void(0);') {
      const menuItem = link.closest('.menu-item');
      if (menuItem) {
        menuItem.classList.add('active');
        // Раскрываем родительское меню если есть
        const parentMenu = menuItem.closest('.menu-sub');
        if (parentMenu) {
          const parentItem = parentMenu.closest('.menu-item');
          if (parentItem) {
            parentItem.classList.add('open');
          }
        }
      }
    }
  });
  
  // Функция обработки клика на toggle
  function handleMenuToggle(e) {
    e.preventDefault();
    e.stopPropagation();
    
    const toggle = e.currentTarget;
    const menuItem = toggle.closest('.menu-item');
    if (!menuItem) {
      return;
    }
    
    const menuSub = menuItem.querySelector('.menu-sub');
    if (!menuSub) {
      return;
    }
    
    // Закрываем все другие открытые подменю на том же уровне
    const parentMenu = menuItem.parentElement;
    if (parentMenu) {
      if (parentMenu.classList.contains('menu-inner')) {
        // Закрываем все другие пункты первого уровня
        const allSiblings = parentMenu.querySelectorAll('.menu-item.open');
        allSiblings.forEach(function(item) {
          if (item !== menuItem) {
            item.classList.remove('open');
          }
        });
      } else {
        // Закрываем соседние пункты на том же уровне
        const siblings = Array.from(parentMenu.children);
        siblings.forEach(function(item) {
          if (item !== menuItem && item.classList.contains('menu-item') && item.classList.contains('open')) {
            item.classList.remove('open');
          }
        });
      }
    }
    
    // Переключаем текущее подменю
    menuItem.classList.toggle('open');
  }
  
  // Обработка кликов на пункты меню с подменю
  const menuToggles = document.querySelectorAll('.menu-toggle');
  menuToggles.forEach(function(toggle) {
    toggle.addEventListener('click', handleMenuToggle);
  });
  
  // Также добавляем обработчик через делегирование событий
  const menuInner = document.querySelector('.menu-inner');
  if (menuInner) {
    menuInner.addEventListener('click', function(e) {
      const toggle = e.target.closest('.menu-toggle');
      if (toggle && !toggle.hasAttribute('data-listener-added')) {
        toggle.setAttribute('data-listener-added', 'true');
        toggle.addEventListener('click', handleMenuToggle);
      }
    });
  }
  
  // Предотвращаем закрытие меню при клике на ссылку внутри подменю
  const menuSubLinks = document.querySelectorAll('.menu-sub .menu-link');
  menuSubLinks.forEach(function(link) {
    link.addEventListener('click', function(e) {
      e.stopPropagation();
    });
  });
});

// Функционал переключения тем
(function() {
  function getStoredTheme() {
    return localStorage.getItem('theme') || 'light';
  }

  function setStoredTheme(theme) {
    localStorage.setItem('theme', theme);
  }

  function getPreferredTheme() {
    const stored = getStoredTheme();
    if (stored !== 'system') {
      return stored;
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function setTheme(theme) {
    if (theme === 'system') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      document.documentElement.setAttribute('data-bs-theme', systemTheme);
      document.documentElement.setAttribute('data-theme', systemTheme);
    } else {
      document.documentElement.setAttribute('data-bs-theme', theme);
      document.documentElement.setAttribute('data-theme', theme);
    }
  }

  function showActiveTheme(theme, focus = false) {
    const themeToggle = document.querySelector('#nav-theme');
    const themeToggleText = document.querySelector('#nav-theme-text');
    const themeIcon = document.querySelector('.theme-icon-active');
    const themeButton = document.querySelector(`[data-bs-theme-value="${theme}"]`);
    
    if (themeButton) {
      const icon = themeButton.querySelector('i').getAttribute('data-icon');
      
      // Убираем активный класс со всех кнопок
      document.querySelectorAll('[data-bs-theme-value]').forEach(function(btn) {
        btn.classList.remove('active');
        btn.setAttribute('aria-pressed', 'false');
      });
      
      // Активируем выбранную кнопку
      themeButton.classList.add('active');
      themeButton.setAttribute('aria-pressed', 'true');
      
      // Обновляем иконку
      if (themeIcon) {
        const classes = Array.from(themeIcon.classList).filter(function(cls) {
          return !cls.startsWith('ri-');
        });
        themeIcon.setAttribute('class', `ri-${icon} ${classes.join(' ')}`);
      }
      
      // Обновляем aria-label
      if (themeToggle && themeToggleText) {
        const label = `${themeToggleText.textContent} (${theme})`;
        themeToggle.setAttribute('aria-label', label);
        if (focus) {
          themeToggle.focus();
        }
      }
    }
  }

  // Инициализация темы
  document.addEventListener('DOMContentLoaded', function() {
    const currentTheme = getPreferredTheme();
    setTheme(currentTheme);
    showActiveTheme(getStoredTheme());

    // Обработчики переключения тем
    document.querySelectorAll('[data-bs-theme-value]').forEach(function(button) {
      button.addEventListener('click', function() {
        const theme = this.getAttribute('data-bs-theme-value');
        setStoredTheme(theme);
        setTheme(theme);
        showActiveTheme(theme, true);
      });
    });

    // Слушаем изменения системной темы
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function() {
      const stored = getStoredTheme();
      if (stored === 'system') {
        setTheme('system');
      }
    });
  });
})();

// Система уведомлений в dropdown
function addNotificationToDropdown(message, type = 'success') {
  const notificationsList = document.querySelector('.dropdown-notifications-list ul');
  if (!notificationsList) return;

  // Определяем иконку и цвет в зависимости от типа
  let icon, bgClass, avatarText;
  switch(type) {
    case 'success':
      icon = 'ri-check-line';
      bgClass = 'bg-label-success';
      avatarText = '✓';
      break;
    case 'error':
      icon = 'ri-error-warning-line';
      bgClass = 'bg-label-danger';
      avatarText = '!';
      break;
    case 'warning':
      icon = 'ri-alert-line';
      bgClass = 'bg-label-warning';
      avatarText = '⚠';
      break;
    case 'info':
      icon = 'ri-information-line';
      bgClass = 'bg-label-info';
      avatarText = 'i';
      break;
    default:
      icon = 'ri-notification-line';
      bgClass = 'bg-label-primary';
      avatarText = 'N';
  }

  // Создаем HTML для нового уведомления
  const notificationHTML = `
    <li class="list-group-item list-group-item-action dropdown-notifications-item waves-effect">
      <div class="d-flex">
        <div class="flex-shrink-0 me-3">
          <div class="avatar">
            <span class="avatar-initial rounded-circle ${bgClass}">${avatarText}</span>
          </div>
        </div>
        <div class="flex-grow-1">
          <h6 class="small mb-50">Системное уведомление</h6>
          <small class="mb-1 d-block text-body">${message}</small>
          <small class="text-body-secondary">только что</small>
        </div>
        <div class="flex-shrink-0 dropdown-notifications-actions">
          <a href="javascript:void(0)" class="dropdown-notifications-read"> <span class="badge badge-dot"></span></a>
          <a href="javascript:void(0)" class="dropdown-notifications-archive"> <span class="icon-base ri ri-close-line"></span></a>
        </div>
      </div>
    </li>
  `;

  // Добавляем уведомление в начало списка
  notificationsList.insertAdjacentHTML('afterbegin', notificationHTML);

  // Обновляем счетчик новых уведомлений
  updateNotificationCount();

  // Добавляем обработчики для новых кнопок
  const newNotification = notificationsList.firstElementChild;
  addNotificationHandlers(newNotification);
}

// Функция обновления счетчика уведомлений
function updateNotificationCount() {
  const unreadNotifications = document.querySelectorAll('.dropdown-notifications-item:not(.marked-as-read)');
  const count = unreadNotifications.length;
  
  const badge = document.querySelector('.badge-notifications');
  if (badge) {
    badge.style.display = count > 0 ? 'block' : 'none';
  }
  
  const newBadge = document.querySelector('.badge.bg-label-primary');
  if (newBadge) {
    newBadge.textContent = count > 0 ? `${count} Новых` : '0 Новых';
  }
}

// Добавление обработчиков для новых уведомлений
function addNotificationHandlers(notificationElement) {
  // Отметить как прочитанное
  const readBtn = notificationElement.querySelector('.dropdown-notifications-read');
  if (readBtn) {
    readBtn.addEventListener('click', function() {
      if (!notificationElement.classList.contains('marked-as-read')) {
        notificationElement.classList.add('marked-as-read');
        updateNotificationCount();
      }
    });
  }

  // Удалить уведомление
  const archiveBtn = notificationElement.querySelector('.dropdown-notifications-archive');
  if (archiveBtn) {
    archiveBtn.addEventListener('click', function() {
      notificationElement.remove();
      updateNotificationCount();
    });
  }
}

// Глобальная функция для показа уведомлений
window.showNotification = addNotificationToDropdown;

// Обработка уведомлений
document.addEventListener('DOMContentLoaded', function() {
  // Отключаем автоматическое закрытие dropdown при клике вне их области
  document.addEventListener('click', function(e) {
    // Если клик не по dropdown элементу, не закрываем dropdown
    if (!e.target.closest('.dropdown')) {
      return;
    }
  });

  // Предотвращаем закрытие dropdown при открытии других dropdown
  const allDropdownToggles = document.querySelectorAll('[data-bs-toggle="dropdown"]');
  allDropdownToggles.forEach(function(toggle) {
    toggle.addEventListener('click', function(e) {
      e.stopPropagation();
    });
  });

  // Отключаем автоматическое закрытие dropdown при клике вне области
  document.addEventListener('click', function(e) {
    // Если клик по элементу навбара, не закрываем dropdown
    if (e.target.closest('.navbar')) {
      return;
    }
  });

  // Отметить все как прочитанные
  const markAllReadBtn = document.querySelector('.dropdown-notifications-all');
  if (markAllReadBtn) {
    markAllReadBtn.addEventListener('click', function() {
      const notifications = document.querySelectorAll('.dropdown-notifications-item');
      notifications.forEach(function(notification) {
        notification.classList.add('marked-as-read');
      });
      
      // Обновляем счетчик
      const badge = document.querySelector('.badge-notifications');
      if (badge) {
        badge.style.display = 'none';
      }
      
      const newBadge = document.querySelector('.badge.bg-label-primary');
      if (newBadge) {
        newBadge.textContent = '0 Новых';
      }
    });
  }

  // Добавляем обработчики для существующих уведомлений
  const existingNotifications = document.querySelectorAll('.dropdown-notifications-item');
  existingNotifications.forEach(function(notification) {
    addNotificationHandlers(notification);
  });
});

// Динамический навбар при прокрутке (как в Materio)
(function() {
  function handleScroll() {
    const layoutPage = document.querySelector('.layout-page');
    if (layoutPage) {
      if (window.scrollY > 0) {
        layoutPage.classList.add('window-scrolled');
      } else {
        layoutPage.classList.remove('window-scrolled');
      }
    }
  }
  
  // Проверяем сразу при загрузке (с небольшой задержкой для корректной работы)
  setTimeout(function() {
    handleScroll();
  }, 200);
  
  // Обрабатываем прокрутку
  window.addEventListener('scroll', handleScroll);
})();

