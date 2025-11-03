from django import template
from decimal import Decimal

register = template.Library()


@register.filter(name='format_currency')
def format_currency(value):
    """
    Форматирует сумму с сокращениями:
    - до 1000: просто число
    - от 1000 до 999999: К (тысячи) - например 1.5К
    - от 1000000: М (миллионы) - например 2.3М
    """
    try:
        # Преобразуем в Decimal для точности
        amount = Decimal(str(value))
        
        # Если 0 или отрицательное, возвращаем 0
        if amount <= 0:
            return '0 ₸'
        
        # Миллионы
        if amount >= 1000000:
            millions = amount / 1000000
            # Округляем до 1 знака после запятой
            if millions >= 100:
                return f"{int(millions)}М ₸"
            else:
                return f"{millions:.1f}М ₸".replace('.', ',')
        
        # Тысячи
        elif amount >= 1000:
            thousands = amount / 1000
            # Округляем до 1 знака после запятой
            if thousands >= 100:
                return f"{int(thousands)}К ₸"
            else:
                return f"{thousands:.1f}К ₸".replace('.', ',')
        
        # До 1000 - просто число с пробелами
        else:
            return f"{int(amount):,} ₸".replace(',', ' ')
    
    except (ValueError, TypeError, AttributeError):
        return f"{value} ₸"

