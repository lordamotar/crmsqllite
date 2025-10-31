from django import template
import re

register = template.Library()


@register.filter(name='spaced_thousands')
def spaced_thousands(value):
    """Форматирует число как 1 234 567 с пробелами между тысячами.

    Поддерживает Decimal/float/int/str. Возвращает строку.
    """
    try:
        # Приводим к строке через int, если это целое число
        # Если есть дробная часть, отбрасываем для целей отображения суммы
        as_int = int(round(float(value)))
        s = f"{as_int:,}"  # даёт формат с запятыми
        return s.replace(',', ' ')
    except Exception:
        return str(value)


@register.filter(name='status_css_class')
def status_css_class(status):
    """Преобразует статус заказа в CSS класс для цветовой схемы"""
    status_mapping = {
        'new': 'status-new',
        'new_paid': 'status-new-paid',
        'reserve': 'status-reserve',
        'transfer': 'status-transfer',
        'delivery': 'status-delivery',
        'callback': 'status-callback',
        'completed': 'status-completed',
        'refund': 'status-refund',
        'cancelled': 'status-cancelled',
        'cancel_no_answer': 'status-cancelled-no-call',
        'cancel_not_suitable_year': 'status-cancelled-year',
        'cancel_wrong_order': 'status-cancelled-wrong',
        'cancel_found_other': 'status-cancelled-found-other',
        'cancel_delivery_terms': 'status-cancelled-delivery',
        'cancel_no_quantity': 'status-cancelled-no-quantity',
        'cancel_incomplete': 'status-cancelled-no-set',
    }
    return status_mapping.get(status, '')


@register.filter(name='status_text_class')
def status_text_class(status):
    """Преобразует статус заказа в CSS класс для текстовых цветов Materio"""
    status_mapping = {
        'new': 'text-success',  # Новый - зеленый
        'new_paid': 'text-success',  # Новый оплаченный - зеленый
        'reserve': 'text-warning',  # Резерв - желтый
        'transfer': 'text-info',  # Перемещение - синий
        'delivery': 'text-primary',  # Доставка - основной цвет
        'callback': 'text-warning',  # Перезвонить - желтый
        'completed': 'text-success',  # Выполнен - зеленый
        'refund': 'text-info',  # Возврат средств - синий
        'cancelled': 'text-secondary',  # Отменен - серый
        'cancel_no_answer': 'text-danger',  # Отменен - не дозвонился
        'cancel_not_suitable_year': 'text-danger',  # Отменен - не устроил год
        'cancel_wrong_order': 'text-danger',  # Отменен - ошибочный заказ
        'cancel_found_other': 'text-danger',  # Отменен - нашел другие
        'cancel_delivery_terms': 'text-danger',  # Отменен - условия доставки
        'cancel_no_quantity': 'text-danger',  # Отменен - нет нужного кол-ва
        'cancel_incomplete': 'text-danger',  # Отменен - не комплект
    }
    return status_mapping.get(status, 'text-secondary')


@register.filter(name='format_phone')
def format_phone(phone):
    """Форматирует телефон в формате +# ### ### ## ##"""
    if not phone:
        return ""

    # Убираем все символы кроме цифр
    digits = re.sub(r'\D', '', str(phone))

    # Если номер начинается с 7, заменяем на +7
    if digits.startswith('7') and len(digits) == 11:
        digits = '+7' + digits[1:]
    elif digits.startswith('8') and len(digits) == 11:
        digits = '+7' + digits[1:]
    elif not digits.startswith('+') and len(digits) == 10:
        digits = '+7' + digits
    elif not digits.startswith('+'):
        digits = '+' + digits

    # Форматируем: +# ### ### ## ##
    if len(digits) >= 12:  # +7XXXXXXXXXX
        formatted = (f"{digits[:2]} {digits[2:5]} {digits[5:8]} "
                     f"{digits[8:10]} {digits[10:12]}")
        return formatted

    return phone


@register.filter(name='payment_method_text_class')
def payment_method_text_class(payment_method):
    """Преобразует способ оплаты в CSS класс для текстовых цветов"""
    payment_mapping = {
        'airba': 'text-primary',       # Airba Pay - синий
        'cash': 'text-success',        # Наличные - зеленый
        'bcc': 'text-success',         # БЦК - зеленый
        'halyk': 'text-success',       # Halyk - зеленый
        'kaspi': 'text-danger',        # Kaspi - красный
        'woopay': 'text-primary',      # Wooppay - синий
        'cassa': 'text-warning',       # На кассе - желтый
        'account': 'text-info',        # По счету - голубой
        'installment': 'text-warning',  # Рассрочка - оранжевый
        'site': 'text-primary',        # Сайт - синий
        'card': 'text-info',           # Карта - голубой
        'transfer': 'text-info',       # Перевод - голубой
    }
    return payment_mapping.get(payment_method, 'text-secondary')


@register.filter(name='source_text_class')
def source_text_class(source):
    """Преобразует источник заказа в CSS класс для текстовых цветов"""
    source_mapping = {
        '2gis': 'text-success',      # 2GIS WhatsApp - зеленый
        'callcentr': 'text-warning',  # Call-центр 2710 - янтарный
        'email': 'text-info',        # E-mail - синий
        'instagram': 'text-danger',  # Instagram - розово-красный
        'kaspi': 'text-danger',      # Kaspi - красный
        'whatsapp': 'text-success',  # Whatsapp - зеленый
        'website': 'text-primary',   # Сайт - синий
    }
    return source_mapping.get(source, 'text-secondary')


@register.filter(name='source_display')
def source_display(source):
    """Возвращает читаемое название источника по коду.
    Надёжнее, чем get_source_display, если в БД попали некорректные значения.
    """
    mapping = {
        'callcentr': 'Call-центр 2710',
        '2gis': '2GIS WhatsApp',
        'email': 'E-mail',
        'instagram': 'Instagram',
        'kaspi': 'Kaspi',
        'whatsapp': 'WhatsApp',
        'website': 'Сайт',
    }
    return mapping.get(source, source or '')


@register.filter(name='payment_method_display')
def payment_method_display(payment):
    """Возвращает читаемое название способа оплаты по коду.
    Надёжнее, чем get_payment_method_display, если в БД попали некорректные значения.
    """
    mapping = {
        'airba': 'Airba Pay',
        'halyk': 'Halyk',
        'kaspi': 'Kaspi',
        'woopay': 'Wooppay',
        'bcc': 'БЦК',
        'cassa': 'На кассе',
        'account': 'По счету',
        'installment': 'Рассрочка (сайт)',
        'site': 'Сайт',
        'card': 'Карта',
        'transfer': 'Перевод',
        'cash': 'Наличные',
    }
    return mapping.get(payment, payment or '')
