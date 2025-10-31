from django import template

register = template.Library()

@register.filter
def format_phone(phone):
    """Форматирует номер телефона в формат 7 777 777 77 77"""
    if not phone:
        return '—'
    
    # Убираем все символы кроме цифр
    digits = ''.join(filter(str.isdigit, str(phone)))
    
    # Если номер не начинается с 7, добавляем 7
    if not digits.startswith('7'):
        digits = '7' + digits
    
    # Ограничиваем до 11 цифр
    if len(digits) > 11:
        digits = digits[:11]
    
    # Форматируем: 7 777 777 77 77
    if len(digits) == 11:
        return f"{digits[0]} {digits[1:4]} {digits[4:7]} {digits[7:9]} {digits[9:11]}"
    elif len(digits) == 10:
        return f"7 {digits[0:3]} {digits[3:6]} {digits[6:8]} {digits[8:10]}"
    else:
        return phone  # Возвращаем как есть, если формат не подходит
