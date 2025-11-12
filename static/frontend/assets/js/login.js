// Логика переключения видимости пароля на странице входа
document.addEventListener('DOMContentLoaded', function() {
  const passwordToggle = document.getElementById('password-toggle');
  const passwordInput = document.getElementById('password');
  const toggleIcon = document.getElementById('password-toggle-icon');
  
  if (!passwordToggle || !passwordInput || !toggleIcon) {
    console.error('Элементы не найдены');
    return;
  }
  
  passwordToggle.addEventListener('click', function(e) {
    e.preventDefault();
    e.stopPropagation();
    
    if (passwordInput.type === 'password') {
      passwordInput.type = 'text';
      // Убираем text-security если установлен
      passwordInput.style.webkitTextSecurity = 'none';
      passwordInput.style.textSecurity = 'none';
      // Удаляем placeholder при показе пароля
      passwordInput.removeAttribute('placeholder');
      toggleIcon.classList.remove('ri-eye-off-line');
      toggleIcon.classList.add('ri-eye-line');
    } else {
      passwordInput.type = 'password';
      // Восстанавливаем placeholder при скрытии, если поле пустое
      if (!passwordInput.value) {
        passwordInput.setAttribute('placeholder', '············');
      }
      toggleIcon.classList.remove('ri-eye-line');
      toggleIcon.classList.add('ri-eye-off-line');
    }
    // Принудительно обновляем отображение
    const currentValue = passwordInput.value;
    passwordInput.value = '';
    setTimeout(function() {
      passwordInput.value = currentValue;
    }, 0);
  });
});

