/**
 * Глобальные настройки пользователя
 * Применяются на всех страницах проекта
 */

// Функция для показа уведомлений
function showNotification(message, type = 'info') {
  // Создаем элемент уведомления
  const notification = document.createElement('div');
  notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
  notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
  notification.innerHTML = `
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
  `;
  
  // Добавляем на страницу
  document.body.appendChild(notification);
  
  // Автоматически убираем через 3 секунды
  setTimeout(() => {
    if (notification.parentNode) {
      notification.remove();
    }
  }, 3000);
}

// Загружаем настройки при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
  loadAndApplySettings();
});

/**
 * Загружает настройки из localStorage и применяет их
 */
function loadAndApplySettings() {
  const settings = JSON.parse(localStorage.getItem('userSettings') || '{}');
  
  // Применяем настройки
  applyGlobalSettings(settings);
  
  // Применяем размер страницы по умолчанию
  applyDefaultPageSize(settings.defaultPageSize);
}

/**
 * Применяет глобальные настройки
 */
function applyGlobalSettings(settings) {
  // Применяем темную тему
  if (settings.darkTheme) {
    document.body.classList.add('dark');
    document.documentElement.setAttribute('data-theme', 'dark');
  } else {
    document.body.classList.remove('dark');
    document.documentElement.setAttribute('data-theme', 'light');
  }
  
  // Применяем компактный режим
  if (settings.compactMode) {
    document.body.classList.add('compact-mode');
  } else {
    document.body.classList.remove('compact-mode');
  }
  
  // Применяем цветные строки заказов
  if (settings.coloredOrderRows !== false) { // по умолчанию включено
    document.body.classList.add('colored-order-rows');
  } else {
    document.body.classList.remove('colored-order-rows');
  }
}

/**
 * Применяет размер страницы по умолчанию
 */
function applyDefaultPageSize(pageSize) {
  if (pageSize && pageSize !== '10') {
    // Если текущая страница имеет пагинацию, применяем размер страницы
    const perPageSelect = document.querySelector('select[name="per_page"]');
    if (perPageSelect) {
      perPageSelect.value = pageSize;
      // Автоматически перезагружаем страницу с новым размером
      const url = new URL(window.location);
      url.searchParams.set('per_page', pageSize);
      window.location.href = url.toString();
    }
  }
}

/**
 * Сохраняет настройки в localStorage
 */
function saveSettings(settings) {
  localStorage.setItem('userSettings', JSON.stringify(settings));
  applyGlobalSettings(settings);
  
  // Показываем уведомление
  showNotification('Настройки сохранены', 'success');
}

/**
 * Сбрасывает настройки к умолчанию
 */
function resetSettings() {
  if (confirm('Вы уверены, что хотите сбросить все настройки?')) {
    localStorage.removeItem('userSettings');
    localStorage.removeItem('defaultPageSize');
    
    // Убираем примененные стили
    document.body.classList.remove('dark', 'compact-mode', 'colored-order-rows');
    document.documentElement.setAttribute('data-theme', 'light');
    
    // Перезагружаем страницу для сброса размера страницы
    window.location.reload();
    
    showNotification('Настройки сброшены', 'success');
  }
}

/**
 * Экспортирует настройки пользователя
 */
function exportUserData() {
  const settings = JSON.parse(localStorage.getItem('userSettings') || '{}');
  const dataStr = JSON.stringify(settings, null, 2);
  const dataBlob = new Blob([dataStr], {type: 'application/json'});
  
  const link = document.createElement('a');
  link.href = URL.createObjectURL(dataBlob);
  link.download = 'user_settings.json';
  link.click();
  
  showNotification('Данные экспортированы', 'success');
}

/**
 * Очищает кэш браузера
 */
function clearCache() {
  if (confirm('Очистить кэш браузера? Это может замедлить загрузку страниц.')) {
    // Очищаем localStorage (кроме настроек)
    const settings = localStorage.getItem('userSettings');
    localStorage.clear();
    if (settings) {
      localStorage.setItem('userSettings', settings);
    }
    
    showNotification('Кэш очищен', 'success');
  }
}

// Экспортируем функции для использования в других скриптах
window.UserSettings = {
  loadAndApplySettings,
  applyGlobalSettings,
  applyDefaultPageSize,
  saveSettings,
  resetSettings,
  exportUserData,
  clearCache
};
