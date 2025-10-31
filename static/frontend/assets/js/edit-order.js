document.addEventListener('DOMContentLoaded', function() {
  console.log('DOM загружен, инициализация JavaScript...');
  
  // Добавление новой позиции
  const addItemBtn = document.getElementById('addItemBtn');
  if (!addItemBtn) {
    console.error('Кнопка addItemBtn не найдена!');
    return;
  }
  
  addItemBtn.addEventListener('click', function() {
    const container = document.getElementById('orderItems');
    const totalForms = document.querySelector('input[name="items-TOTAL_FORMS"]');
    if (!totalForms) {
      console.error('Поле TOTAL_FORMS не найдено!');
      return;
    }
    const formCount = parseInt(totalForms.value);
    
    // Создаем новую строку таблицы
    const newRow = document.createElement('tr');
    newRow.className = 'order-item-row';
           newRow.innerHTML = `
             <td>
               <div class="d-flex align-items-center">
                 <div class="avatar me-3">
                   <div class="avatar-initial bg-label-primary rounded-circle">
                     <i class="bx bx-package"></i>
                   </div>
                 </div>
                 <div class="flex-grow-1">
                   <input type="text" name="items-${formCount}-product_name" class="form-control" placeholder="Название товара">
                 </div>
               </div>
             </td>
             <td>
               <input type="number" name="items-${formCount}-price" class="form-control item-price" step="0.01" min="0" placeholder="0.00">
             </td>
             <td>
               <input type="number" name="items-${formCount}-quantity" class="form-control item-quantity" min="1" placeholder="1">
             </td>
             <td>
               <input type="text" class="form-control item-total" readonly>
             </td>
             <td>
               <button type="button" class="btn btn-outline-danger btn-sm remove-item">
                 <i class="ri-delete-bin-6-line"></i>
               </button>
             </td>
             <input type="hidden" name="items-${formCount}-id" value="">
             <input type="hidden" name="items-${formCount}-order" value="${document.querySelector('input[name="items-0-order"]')?.value || ''}">
             <input type="hidden" name="items-${formCount}-DELETE" value="">
           `;
    
    container.appendChild(newRow);
    totalForms.value = formCount + 1;
    
    // Добавляем обработчики событий
    addItemEventListeners(newRow);
  });
  
  // Удаление позиции
  document.addEventListener('click', function(e) {
    if (e.target.closest('.remove-item')) {
      const row = e.target.closest('.order-item-row');
      const deleteInput = row.querySelector('input[name$="-DELETE"]');
      if (deleteInput) {
        deleteInput.value = 'on';
        row.style.display = 'none';
      } else {
        row.remove();
      }
      updateOrderTotal();
    }
  });
  
  // Обработчики для существующих строк
  document.querySelectorAll('.order-item-row').forEach(addItemEventListeners);
  
  function addItemEventListeners(row) {
    const priceInput = row.querySelector('.item-price');
    const quantityInput = row.querySelector('.item-quantity');
    const totalInput = row.querySelector('.item-total');
    
    if (priceInput && quantityInput && totalInput) {
      priceInput.addEventListener('input', calculateItemTotal);
      quantityInput.addEventListener('input', calculateItemTotal);
      
      function calculateItemTotal() {
        const price = parseFloat(priceInput.value) || 0;
        const quantity = parseInt(quantityInput.value) || 0;
        const total = price * quantity;
        totalInput.value = total.toFixed(2);
        updateOrderTotal();
      }
    }
  }
  
  function updateOrderTotal() {
    let total = 0;
    document.querySelectorAll('.item-total').forEach(function(input) {
      const row = input.closest('.order-item-row');
      if (row.style.display !== 'none') {
        total += parseFloat(input.value) || 0;
      }
    });
    const totalElement = document.getElementById('orderTotal');
    if (totalElement) {
      totalElement.textContent = total.toFixed(0) + ' ₸';
    }
  }
  
  // Добавляем обработчик для отправки формы
  const form = document.querySelector('form');
  if (form) {
    form.addEventListener('submit', function(e) {
      console.log('Форма отправляется...');
      const formData = new FormData(this);
      console.log('Данные формы:');
      for (let [key, value] of formData.entries()) {
        console.log(key + ': ' + value);
      }
    });
  }
  
  // Инициализация итогов
  updateOrderTotal();
});
