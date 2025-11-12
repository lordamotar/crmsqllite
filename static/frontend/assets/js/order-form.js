// Логика формы создания/редактирования заказа
// Версия: 2025-11-09 (исправлен URL для поиска товаров)
(function() {
  // Получаем данные из data-атрибутов контейнера
  const container = document.querySelector('.container-xxl');
  if (!container) {
    console.error('Container .container-xxl не найден!');
    return;
  }
  
  // Логирование для отладки
  console.log('Container found:', container);
  console.log('productSearchUrl attr:', container.dataset.productSearchUrl);
  console.log('All dataset:', container.dataset);
  
  const isEdit = container.dataset.isEdit === 'true';
  const steps = isEdit ? [1, 2, 3, 4] : [1, 2, 3];
  let current = 1;
  const items = [];

  // URLs из data-атрибутов с fallback
  const rawProductSearchUrl = container.dataset.productSearchUrl;
  const rawAddOrderUrl = container.dataset.addOrderUrl;
  
  // Функция для нормализации URL (убирает undefined и пустые значения)
  function normalizeUrl(url, fallback) {
    if (!url || url === 'undefined' || url === 'null' || url.includes('undefined')) {
      return fallback;
    }
    return url;
  }
  
  const urls = {
    productSearch: normalizeUrl(rawProductSearchUrl, '/orders/product-search/'),
    clientLookup: normalizeUrl(container.dataset.clientLookupUrl, '/orders/client-lookup/'),
    addOrder: normalizeUrl(rawAddOrderUrl, '/orders/add/'),
    editOrder: container.dataset.editOrderUrl || null,
    ordersList: normalizeUrl(container.dataset.ordersListUrl, '/orders/'),
    addClient: normalizeUrl(container.dataset.addClientUrl, '/clients/add/')
  };
  
  // Принудительная проверка и исправление критических URL
  if (!urls.productSearch || urls.productSearch === 'undefined' || urls.productSearch.includes('undefined')) {
    console.error('productSearch URL некорректен, принудительно устанавливаем fallback');
    urls.productSearch = '/orders/product-search/';
  }
  
  // Проверка всех URL
  console.log('Final URLs:', urls);
  console.log('productSearch URL:', urls.productSearch);

  // Загружаем данные заказа для редактирования
  let orderData = null;
  const orderDataEl = document.getElementById('order-data');
  if (orderDataEl) {
    try {
      orderData = JSON.parse(orderDataEl.textContent);
    } catch (e) {
      console.error('Failed to parse order data', e);
    }
  }

  // Элементы формы
  const priceInput = document.getElementById('productPrice');
  const qtyInput = document.getElementById('productQty');
  const priceLevelSelect = document.getElementById('priceLevelSelect');
  const itemsTableBody = document.querySelector('#itemsTable tbody');
  const totalCell = document.getElementById('totalCell');

  // Поиск товаров
  const productSearchInput = document.getElementById('productSearchInput');
  const productNameInput = document.getElementById('productNameInput');
  const productSeasonSelect = document.getElementById('productSeasonSelect');
  const productSearchCity = document.getElementById('productSearchCity');
  const productFindBtn = document.getElementById('productFindBtn');
  const productResultsWrapper = document.getElementById('productResultsWrapper');
  const productResultsTableBody = document.querySelector('#productResultsTable tbody');

  // Клиент
  const clientSelect = document.getElementById('clientSelect');
  const clientPhoneInput = document.getElementById('clientPhoneInput');
  const clientNameInput = document.getElementById('clientNameInput');
  const clientCityInput = document.getElementById('clientCityInput');
  const clientAddressComment = document.getElementById('clientAddressComment');

  // Параметры заказа
  const statusSelect = document.getElementById('statusSelect');
  const cancelReasonWrapper = document.getElementById('cancelReasonWrapper');
  const cancelReasonSelect = document.getElementById('cancelReasonSelect');
  const sourceSelect = document.getElementById('sourceSelect');
  const paymentSelect = document.getElementById('paymentSelect');
  const deliverySelect = document.getElementById('deliverySelect');
  const promoSwitch = document.getElementById('promoSwitch');
  const notesInput = document.getElementById('notesInput');

  // Доп. поля товара
  const productCitySelect = document.getElementById('productCitySelect');
  const productBranch = document.getElementById('productBranch');
  const productTireType = document.getElementById('productTireType');
  const productAssortmentGroup = document.getElementById('productAssortmentGroup');

  // Debounce helper
  function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  // Поиск товаров
  async function fetchProducts(params) {
    // Принудительно используем правильный URL
    let searchUrl = '/orders/product-search/'; // Fallback по умолчанию
    
    // Проверяем urls.productSearch
    if (urls.productSearch && 
        urls.productSearch !== 'undefined' && 
        !urls.productSearch.includes('undefined') &&
        urls.productSearch.startsWith('/')) {
      searchUrl = urls.productSearch;
    } else {
      console.warn('productSearch URL некорректен, используем fallback. Текущее значение:', urls.productSearch);
    }
    
    const qs = new URLSearchParams(params).toString();
    const fullUrl = `${searchUrl}?${qs}`;
    console.log('Fetching products from:', fullUrl);
    console.log('urls.productSearch value:', urls.productSearch);
    
    try {
      const res = await fetch(fullUrl, { 
        headers: { 'X-Requested-With': 'XMLHttpRequest' } 
      });
      if (!res.ok) {
        console.error('product fetch failed', res.status, fullUrl);
        return [];
      }
      const data = await res.json();
      console.log('Products fetched:', data.products?.length || 0);
      return data.products || [];
    } catch (e) {
      console.error('product fetch error', e, fullUrl);
      return [];
    }
  }

  async function doProductSearch() {
    const q = productSearchInput ? productSearchInput.value.trim() : '';
    const nameQuery = productNameInput ? productNameInput.value.trim() : '';
    const season = productSeasonSelect ? productSeasonSelect.value : '';
    const city = productSearchCity && productSearchCity.value ? productSearchCity.value : (productCitySelect ? productCitySelect.value : '');
    const priceLevel = priceLevelSelect ? priceLevelSelect.value : 'retail';

    const useNameOnly = !!nameQuery;
    const params = { q: (nameQuery || q), size: '', season, city, price_level: priceLevel };
    if (useNameOnly) params.search_field = 'name';

    productResultsWrapper.style.display = 'none';
    productResultsTableBody.innerHTML = `<tr><td colspan="7" class="text-center py-4">Поиск...</td></tr>`;

    const products = await fetchProducts(params);
    const filtered = season ? products.filter(p => matchesSeasonTag(p, season)) : products;
    renderProductResults(filtered);
  }

  function matchesSeasonTag(prod, selectedTag) {
    if (!selectedTag) return true;
    const normalizedSelected = normalizeTag(selectedTag);
    const endTag = detectEndTag((prod && (prod.name || '')) + ' ' + (prod && (prod.code || '')));
    if (endTag) {
      const normalizedEnd = normalizeTag(endTag);
      return normalizedEnd === normalizedSelected;
    }
    if (prod && prod.season) {
      return normalizeTag(prod.season) === normalizedSelected;
    }
    if (Array.isArray(prod?.season_tags)) {
      return prod.season_tags.some(t => normalizeTag(String(t)) === normalizedSelected);
    }
    return false;
  }

  function normalizeTag(tag) {
    const t = String(tag).trim();
    const upper = t.toUpperCase();
    if (upper.includes('БЕЗ') && upper.includes('РИСУНК')) return 'БЕЗ РИСУНКА';
    return upper;
  }

  function detectEndTag(text) {
    if (!text) return null;
    const s = String(text).trim();
    const reWithout = /(?:\s|\(|-|^)(Без\s+рисунка)\)?\s*$/i;
    const mWithout = s.match(reWithout);
    if (mWithout) return mWithout[1];
    
    const re = /(?:\s|\(|-|^)(ЗИМ|ШИП|ВС|ДР|ПП|УВ|РУО|ВДО|ПРО|КАР)\)?\s*$/i;
    const m = s.match(re);
    return m ? m[1] : null;
  }

  function renderProductResults(products) {
    productResultsTableBody.innerHTML = '';
    if (!products || !products.length) {
      productResultsTableBody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted">Ничего не найдено</td></tr>`;
      productResultsWrapper.style.display = 'block';
      return;
    }

    products.forEach(prod => {
      const tr = document.createElement('tr');
      const endTag = detectEndTag((prod && (prod.name || '')) + ' ' + (prod && (prod.code || '')));
      const seasonLabel = endTag || (prod.season_tags && prod.season_tags.join(', ')) || (prod.season || '—');
      const priceDisplay = (prod.price ? `₸${Number(prod.price).toLocaleString('ru-RU')}` : '—');
      const levels = [];
      if (prod.retail_price) levels.push('Розн');
      if (prod.promotional_price) levels.push('Акц');
      if (prod.wholesale_price) levels.push('Опт');

      tr.innerHTML = `
        <td>${prod.code || '—'}</td>
        <td>
          <strong>${prod.name}</strong><br>
          <small class="text-muted">${prod.assortment_group || ''} ${prod.tire_type ? '• ' + prod.tire_type : ''}</small>
        </td>
        <td>${seasonLabel}</td>
        <td>${prod.branch_city || '—'}</td>
        <td class="text-end">${priceDisplay}</td>
        <td class="text-center"><small class="text-muted">${levels.join(', ')}</small></td>
        <td class="text-center">
          <button class="btn btn-sm btn-success product-add-btn" data-product='${encodeURIComponent(JSON.stringify(prod))}'>Добавить</button>
        </td>
      `;
      productResultsTableBody.appendChild(tr);
    });

    productResultsWrapper.style.display = 'block';
  }

  // Добавление товара в корзину
  productResultsTableBody?.addEventListener('click', (e) => {
    const btn = e.target.closest('.product-add-btn');
    if (!btn) return;
    try {
      const prod = JSON.parse(decodeURIComponent(btn.getAttribute('data-product')));
      const chosenCity = (productSearchCity && productSearchCity.value) || (productCitySelect ? productCitySelect.value : '');
      const chosenPriceLevel = priceLevelSelect ? priceLevelSelect.value : '';

      if (!chosenCity) {
        alert('Выберите город перед добавлением товара');
        return;
      }
      if (!chosenPriceLevel) {
        alert('Выберите уровень цен перед добавлением товара');
        return;
      }
      const quantity = Math.max(0, parseInt(qtyInput && qtyInput.value ? qtyInput.value : '0', 10));
      if (!Number.isFinite(quantity) || quantity < 1) {
        alert('Укажите количество (минимум 1) перед добавлением товара');
        return;
      }

      let price = prod.price || 0;
      if (chosenPriceLevel === 'wholesale' && prod.wholesale_price) price = prod.wholesale_price;
      if (chosenPriceLevel === 'promotional' && prod.promotional_price) price = prod.promotional_price;
      if (chosenPriceLevel === 'retail' && (prod.retail_price || prod.price)) price = (prod.retail_price || prod.price);

      items.push({
        product_id: prod.id,
        name: prod.name,
        code: prod.code || '',
        price: Number(price),
        quantity,
        city: chosenCity
      });
      renderItems();
      document.querySelector('#itemsTable')?.scrollIntoView({ behavior: 'smooth' });
    } catch (err) {
      console.error('parse product', err);
    }
  });

  productFindBtn?.addEventListener('click', (e) => {
    e.preventDefault();
    doProductSearch();
  });
  productSearchInput?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      doProductSearch();
    }
  });

  // Навигация по шагам
  function switchStep(step) {
    steps.forEach(s => {
      document.getElementById(`step-${s}`).classList.toggle('d-none', s !== step);
      const btn = document.querySelector(`#stepsNav [data-step="${s}"]`);
      btn.classList.toggle('active', s === step);
    });
    current = step;
    document.getElementById('prevBtn').disabled = (current === 1);
  }

  document.getElementById('prevBtn').addEventListener('click', () => {
    if (current > 1) switchStep(current - 1);
  });
  document.getElementById('nextBtn').addEventListener('click', () => {
    const last = steps[steps.length - 1];
    if (current === 1 && items.length === 0) {
      alert('Добавьте хотя бы один товар');
      return;
    }
    if (current === 2 && !clientSelect.value) {
      alert('Выберите клиента или введите телефон для автоподбора');
      return;
    }
    if (current < last) switchStep(current + 1);
  });
  document.querySelectorAll('#stepsNav [data-step]').forEach(el => {
    el.addEventListener('click', () => switchStep(parseInt(el.dataset.step)));
  });

  // Логика причин отмены
  function isCancelReason(value) {
    return !!value && (value === 'refund' || value.startsWith('cancel_'));
  }

  function syncCancelUIFromStatus() {
    const val = statusSelect ? statusSelect.value : '';
    if (!statusSelect) return;
    if (val === 'cancelled') {
      if (cancelReasonWrapper) cancelReasonWrapper.classList.remove('d-none');
      if (cancelReasonSelect) cancelReasonSelect.value = '';
    } else if (isCancelReason(val)) {
      if (cancelReasonWrapper) cancelReasonWrapper.classList.remove('d-none');
      if (cancelReasonSelect) {
        const mapped = (val === 'cancelled_refund') ? 'refund' : val;
        cancelReasonSelect.value = mapped;
      }
    } else {
      if (cancelReasonWrapper) cancelReasonWrapper.classList.add('d-none');
      if (cancelReasonSelect) cancelReasonSelect.value = '';
    }
  }

  statusSelect?.addEventListener('change', () => {
    const val = statusSelect.value;
    if (val === 'cancelled') {
      if (cancelReasonWrapper) cancelReasonWrapper.classList.remove('d-none');
      if (cancelReasonSelect) cancelReasonSelect.value = '';
    } else if (isCancelReason(val)) {
      if (cancelReasonWrapper) cancelReasonWrapper.classList.remove('d-none');
      if (cancelReasonSelect) cancelReasonSelect.value = (val === 'cancelled_refund') ? 'refund' : val;
    } else {
      if (cancelReasonWrapper) cancelReasonWrapper.classList.add('d-none');
      if (cancelReasonSelect) cancelReasonSelect.value = '';
    }
  });

  cancelReasonSelect?.addEventListener('change', () => {
    if (statusSelect && statusSelect.value !== 'cancelled') {
      statusSelect.value = 'cancelled';
    }
  });

  syncCancelUIFromStatus();

  // Поиск клиента
  clientSelect?.addEventListener('change', async () => {
    const id = clientSelect.value;
    if (!id) return;
    try {
      const res = await fetch(`${urls.clientLookup}?id=` + encodeURIComponent(id), { 
        headers: { 'X-Requested-With': 'XMLHttpRequest' } 
      });
      if (!res.ok) return;
      const data = await res.json();
      if (data.status === 'success') {
        if (clientNameInput) clientNameInput.value = data.name || '';
        if (clientCityInput) clientCityInput.value = data.city || '';
        if (clientPhoneInput) clientPhoneInput.value = data.phone || '';
        if (clientAddressComment) clientAddressComment.value = [data.address, data.address_comment].filter(Boolean).join(' | ');
      }
    } catch (_) {}
  });

  const onPhoneInput = debounce(async () => {
    const raw = clientPhoneInput ? clientPhoneInput.value : '';
    if (!raw) return;
    try {
      const res = await fetch(`${urls.clientLookup}?phone=` + encodeURIComponent(raw), { 
        headers: { 'X-Requested-With': 'XMLHttpRequest' } 
      });
      if (!res.ok) return;
      const data = await res.json();
      if (data.status === 'success') {
        if (clientNameInput) clientNameInput.value = data.name || '';
        if (clientCityInput) clientCityInput.value = data.city || '';
        if (clientPhoneInput) clientPhoneInput.value = data.phone || '';
        if (clientAddressComment) clientAddressComment.value = [data.address, data.address_comment].filter(Boolean).join(' | ');
        const opt = document.querySelector(`#clientSelect option[value='${data.id}']`);
        if (opt) opt.selected = true;
      }
    } catch (_) {}
  }, 400);

  clientPhoneInput?.addEventListener('input', onPhoneInput);

  clientSelect?.addEventListener('change', () => {
    const opt = clientSelect.options[clientSelect.selectedIndex];
    const name = opt ? (opt.textContent || '').trim() : '';
    if (clientNameInput && name && !clientNameInput.value) {
      clientNameInput.value = name;
    }
  });

  // Форматирование
  function formatInt(num) {
    try {
      const n = Math.round(parseFloat(num || 0));
      return n.toLocaleString('ru-RU');
    } catch (_) { return num; }
  }

  function formatMoney(num) {
    try {
      const n = Math.round(parseFloat(num || 0));
      return n.toLocaleString('ru-RU');
    } catch (_) { return num; }
  }

  function renderItems() {
    itemsTableBody.innerHTML = '';
    let total = 0;
    items.forEach((it, idx) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${it.code || '—'}</td>
        <td>${it.name}</td>
        <td>${it.city || '—'}</td>
        <td class="text-end num">₸${formatMoney(it.price)}</td>
        <td class="text-center num">${formatInt(it.quantity)}</td>
        <td class="text-end num">₸${formatMoney(it.price * it.quantity)}</td>
        <td class="text-end">
          <button class="btn btn-sm btn-outline-danger" data-remove="${idx}" title="Удалить">
            <i class="ri-delete-bin-line"></i>
          </button>
        </td>
      `;
      itemsTableBody.appendChild(tr);
      total += it.price * it.quantity;
    });
    totalCell.innerHTML = `<strong class="num">₸${formatMoney(total)}</strong>`;
  }

  itemsTableBody.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-remove]');
    if (!btn) return;
    const idx = parseInt(btn.getAttribute('data-remove'));
    items.splice(idx, 1);
    renderItems();
  });

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  }

  async function submitOrder() {
    if (!items.length) {
      alert('Добавьте хотя бы один товар');
      switchStep(1);
      return;
    }
    if (!clientSelect.value) {
      alert('Выберите клиента');
      switchStep(2);
      return;
    }

    let statusValue = statusSelect.value;
    if (statusValue === 'cancelled' && cancelReasonSelect && cancelReasonSelect.value) {
      statusValue = (cancelReasonSelect.value === 'refund') ? 'refund' : cancelReasonSelect.value;
    }

    const payload = {
      client_id: clientSelect.value,
      status: statusValue,
      source: sourceSelect.value,
      payment_method: paymentSelect.value,
      delivery_method: deliverySelect.value,
      price_level: priceLevelSelect.value,
      is_promo: promoSwitch.checked,
      sale_number: '',
      notes: notesInput.value || '',
      client_phone: clientPhoneInput ? clientPhoneInput.value : '',
      client_name: clientNameInput ? clientNameInput.value : '',
      client_city: clientCityInput ? clientCityInput.value : '',
      client_address_comment: clientAddressComment ? clientAddressComment.value : '',
      items: items.map(it => ({ product_id: it.product_id, quantity: it.quantity, city: it.city }))
    };

    const postUrl = isEdit && urls.editOrder ? urls.editOrder : urls.addOrder;

    const res = await fetch(postUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: JSON.stringify(payload)
    });

    const data = await res.json().catch(() => ({}));
    
    // Обработка ошибки 403 - нет активной рабочей сессии
    if (res.status === 403) {
      alert(data.message || 'Для работы в системе необходимо начать рабочую сессию. Перейдите на страницу "Табель" и нажмите "Начать работу".');
      // Перенаправляем на страницу dashboard
      window.location.href = '/dashboard/';
      return;
    }
    
    if (res.ok && data.status === 'success') {
      window.location.href = urls.ordersList;
    } else {
      alert(data.message || 'Ошибка сохранения');
    }
  }

  document.getElementById('saveBtn').addEventListener('click', (e) => {
    e.preventDefault();
    submitOrder();
  });

  // Добавление нового клиента
  document.getElementById('saveNewClientBtn').addEventListener('click', async (e) => {
    e.preventDefault();
    
    const clientData = {
      client_type: document.getElementById('newClientType').value,
      phone: document.getElementById('newClientPhone').value,
      name: document.getElementById('newClientName').value,
      city: document.getElementById('newClientCity').value,
      address: document.getElementById('newClientAddress').value,
      address_comment: document.getElementById('newClientComment').value
    };

    try {
      const res = await fetch(urls.addClient, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
          'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(clientData)
      });

      const data = await res.json();
      
      if (res.ok && data.status === 'success') {
        const clientSelect = document.getElementById('clientSelect');
        const newOption = document.createElement('option');
        newOption.value = data.client_id;
        newOption.textContent = clientData.name;
        clientSelect.appendChild(newOption);
        
        clientSelect.value = data.client_id;
        
        if (clientPhoneInput) clientPhoneInput.value = clientData.phone;
        if (clientNameInput) clientNameInput.value = clientData.name;
        if (clientCityInput) clientCityInput.value = clientData.city;
        if (clientAddressComment) clientAddressComment.value = [clientData.address, clientData.address_comment].filter(Boolean).join(' | ');
        
        const modal = bootstrap.Modal.getInstance(document.getElementById('addClientModal'));
        modal.hide();
        
        document.getElementById('addClientForm').reset();
        
        if (window.showNotification) {
          window.showNotification('Клиент успешно добавлен!', 'success');
        }
      } else {
        alert(data.message || 'Ошибка при добавлении клиента');
      }
    } catch (error) {
      console.error('Error adding client:', error);
      alert('Ошибка при добавлении клиента');
    }
  });

  // Инициализация для режима редактирования
  if (orderData && orderData.order) {
    try {
      const order = orderData.order;
      
      // Клиент
      const clientOption = document.querySelector(`#clientSelect option[value='${order.client_id}']`);
      if (clientOption) clientOption.selected = true;

      // Статус
      const initialStatus = order.status;
      const statusEl = document.getElementById('statusSelect');
      if (['refund','cancel_no_answer','cancel_not_suitable_year','cancel_wrong_order','cancel_found_other','cancel_delivery_terms','cancel_no_quantity','cancel_incomplete'].includes(initialStatus)) {
        if (statusEl) statusEl.value = 'cancelled';
        if (cancelReasonWrapper) cancelReasonWrapper.classList.remove('d-none');
        if (cancelReasonSelect) cancelReasonSelect.value = (initialStatus === 'refund') ? 'refund' : initialStatus;
      } else {
        if (statusEl) statusEl.value = initialStatus;
      }
      
      document.getElementById('sourceSelect').value = order.source;
      document.getElementById('paymentSelect').value = order.payment_method;
      document.getElementById('deliverySelect').value = order.delivery_method;
      document.getElementById('promoSwitch').checked = order.is_promo;
      document.getElementById('notesInput').value = order.notes || '';

      // Товары
      if (order.items && Array.isArray(order.items)) {
        order.items.forEach(it => {
          items.push({
            product_id: it.product_id,
            name: it.name,
            code: it.code,
            price: parseFloat(it.price),
            quantity: it.quantity,
            city: it.city
          });
        });
        renderItems();
      }

      // Поля клиента
      if (orderData.client_initial) {
        const ci = orderData.client_initial;
        if (clientPhoneInput) clientPhoneInput.value = ci.phone || '';
        if (clientNameInput) clientNameInput.value = ci.name || '';
        if (clientCityInput) clientCityInput.value = ci.city || '';
        if (clientAddressComment) clientAddressComment.value = [ci.address, ci.address_comment].filter(Boolean).join(' | ');
      }
    } catch (e) {
      console.error('Error initializing order data', e);
    }
  }
})();

