/**
 * Orders List JavaScript
 * Функциональность для страницы списка заказов
 */

// Глобальная функция для обработки кликов по стрелкам сортировки
function handleSortClick(arrow) {
  // Простая проверка
  if (!arrow) {
    alert('Ошибка: стрелка не найдена');
    return;
  }
  
  const direction = arrow.getAttribute('data-direction');
  const th = arrow.closest('th');
  const sortField = th.getAttribute('data-sort');
  
  if (!sortField) {
    alert('Ошибка: поле сортировки не найдено');
    return;
  }
  
  // Получаем текущие параметры URL
  const urlParams = new URLSearchParams(window.location.search);
  
  // Устанавливаем параметры сортировки
  urlParams.set('sort', sortField);
  urlParams.set('order', direction);
  
  // Обновляем URL и перезагружаем страницу
  const newUrl = `${window.location.pathname}?${urlParams.toString()}`;
  window.location.href = newUrl;
}

document.addEventListener('DOMContentLoaded', function() {
  // Принудительное отображение вертикальной прокрутки
  const tableContainer = document.querySelector('.table-responsive');
  if (tableContainer) {
    // Устанавливаем минимальную высоту для принудительного отображения прокрутки
    tableContainer.style.height = '70vh';
    tableContainer.style.maxHeight = '70vh';
    tableContainer.style.overflowY = 'scroll';
    
    // Проверяем, нужна ли прокрутка
    setTimeout(() => {
      if (tableContainer.scrollHeight > tableContainer.clientHeight) {
        tableContainer.style.overflowY = 'scroll';
      } else {
        tableContainer.style.overflowY = 'auto';
      }
    }, 100);
  }

  // Принудительное применение стилей для статусов
  const statusElements = document.querySelectorAll('h6.w-px-100');
  statusElements.forEach(element => {
    element.style.width = 'auto';
    element.style.minWidth = '150px';
    element.style.whiteSpace = 'normal';
    element.style.overflow = 'visible';
    element.style.lineHeight = '1.3';
    element.style.wordWrap = 'break-word';
    element.style.wordBreak = 'break-word';
    element.style.display = 'block';
  });

  // Принудительное применение стилей для ячеек статусов
  const statusCells = document.querySelectorAll('td:nth-child(3)');
  statusCells.forEach(cell => {
    cell.style.width = 'auto';
    cell.style.minWidth = '150px';
    cell.style.whiteSpace = 'normal';
    cell.style.overflow = 'visible';
    cell.style.verticalAlign = 'top';
    cell.style.padding = '0.5rem';
  });

  // Функциональность изменения размера столбцов
  const table = document.querySelector('.table');
  if (!table) return;

  // Загружаем сохраненные ширины столбцов
  const savedWidths = JSON.parse(localStorage.getItem('tableColumnWidths') || '{}');
  Object.keys(savedWidths).forEach(columnIndex => {
    const th = table.querySelector(`thead th:nth-child(${parseInt(columnIndex) + 1})`);
    if (th) {
      th.style.width = savedWidths[columnIndex] + 'px';
    }
  });

  // Добавляем обработчики для изменения размера столбцов
  const headers = table.querySelectorAll('thead th');
  headers.forEach((header, index) => {
    const resizeHandle = header.querySelector('.resize-handle');
    if (!resizeHandle) return;

    let isResizing = false;
    let startX = 0;
    let startWidth = 0;

    resizeHandle.addEventListener('mousedown', (e) => {
      isResizing = true;
      startX = e.clientX;
      startWidth = header.offsetWidth;
      
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      
      e.preventDefault();
    });

    function handleMouseMove(e) {
      if (!isResizing) return;
      
      const newWidth = startWidth + (e.clientX - startX);
      if (newWidth > 50) { // Минимальная ширина
        header.style.width = newWidth + 'px';
        
        // Сохраняем ширину в localStorage
        const widths = JSON.parse(localStorage.getItem('tableColumnWidths') || '{}');
        widths[index] = newWidth;
        localStorage.setItem('tableColumnWidths', JSON.stringify(widths));
      }
    }

    function handleMouseUp() {
      isResizing = false;
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    }
  });

  // Синхронизация горизонтальной прокрутки
  const scrollTop = document.querySelector('.table-scroll-top');
  const scrollContent = document.querySelector('.scroll-content');
  const tableWrapper = document.querySelector('.table-responsive');

  if (scrollTop && scrollContent && tableWrapper) {
    // Синхронизация прокрутки сверху с основной таблицей
    scrollTop.addEventListener('scroll', function() {
      tableWrapper.scrollLeft = scrollTop.scrollLeft;
    });

    // Синхронизация прокрутки основной таблицы с верхней
    tableWrapper.addEventListener('scroll', function() {
      scrollTop.scrollLeft = tableWrapper.scrollLeft;
    });

    // Обновление ширины контента при изменении размера окна
    function updateScrollContentWidth() {
      const tableWidth = tableWrapper.scrollWidth;
      scrollContent.style.width = tableWidth + 'px';
    }

    updateScrollContentWidth();
    window.addEventListener('resize', updateScrollContentWidth);
  }

  // Функциональность сортировки (используем только onclick в HTML)
  // initSorting(); // Отключено, используем onclick в HTML
  
  // Подсвечиваем активную сортировку
  highlightActiveSort();

  // Применяем настройки из глобального скрипта
  if (window.UserSettings && window.UserSettings.loadAndApplySettings) {
    window.UserSettings.loadAndApplySettings();
  } else {
    // Fallback: применяем настройки цветных строк
    applyColoredRowsSetting();
  }
});

// Функция для применения настройки цветных строк (fallback)
function applyColoredRowsSetting() {
  const settings = JSON.parse(localStorage.getItem('userSettings') || '{}');
  const coloredRowsEnabled = settings.coloredOrderRows !== false; // по умолчанию включено
  
  if (coloredRowsEnabled) {
    document.body.classList.add('colored-order-rows');
  } else {
    document.body.classList.remove('colored-order-rows');
    // Если цветные строки отключены, делаем все строки белыми
    const rows = document.querySelectorAll('.table tbody tr');
    rows.forEach(row => {
      row.style.backgroundColor = '#ffffff';
    });
  }
}

// Функция инициализации сортировки
function initSorting() {
  const sortArrows = document.querySelectorAll('.sort-arrow');
  
  sortArrows.forEach(arrow => {
    arrow.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      
      const direction = this.getAttribute('data-direction');
      const th = this.closest('th');
      const sortField = th.getAttribute('data-sort');
      
      if (!sortField) return;
      
      // Получаем текущие параметры URL
      const urlParams = new URLSearchParams(window.location.search);
      
      // Устанавливаем параметры сортировки
      urlParams.set('sort', sortField);
      urlParams.set('order', direction);
      
      // Обновляем URL и перезагружаем страницу
      const newUrl = `${window.location.pathname}?${urlParams.toString()}`;
      window.location.href = newUrl;
    });
  });
  
  // Подсвечиваем активную сортировку
  highlightActiveSort();
}

// Функция для подсветки активной сортировки
function highlightActiveSort() {
  const urlParams = new URLSearchParams(window.location.search);
  const currentSort = urlParams.get('sort');
  const currentOrder = urlParams.get('order');
  
  if (!currentSort) return;
  
  // Находим соответствующий заголовок
  const activeTh = document.querySelector(`th[data-sort="${currentSort}"]`);
  if (!activeTh) return;
  
  // Убираем подсветку со всех стрелок
  const allArrows = document.querySelectorAll('.sort-arrow');
  allArrows.forEach(arrow => {
    arrow.classList.remove('text-primary');
    arrow.classList.add('text-muted');
  });
  
  // Подсвечиваем активную стрелку
  const activeArrow = activeTh.querySelector(`.sort-arrow[data-direction="${currentOrder}"]`);
  if (activeArrow) {
    activeArrow.classList.remove('text-muted');
    activeArrow.classList.add('text-primary');
  }
}
