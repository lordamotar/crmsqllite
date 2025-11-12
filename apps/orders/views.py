from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
import logging
from django.core.cache import cache
import json
from decimal import Decimal
from datetime import timedelta

from .models import Order, OrderItem
from apps.products.models import Product
from apps.clients.models import Client, ClientPhone


def _get_price_by_level(product, price_level):
    """Возвращает цену в зависимости от уровня цен заказа"""
    if price_level == 'wholesale' and product.wholesale_price:
        return product.wholesale_price
    elif price_level == 'promotional' and product.promotional_price:
        return product.promotional_price
    elif price_level == 'retail' and product.retail_price:
        return product.retail_price
    else:
        # Fallback на основную цену
        return product.price


@login_required
def orders_list(request):
    """Список заказов"""
    
    # Получаем параметры пагинации
    per_page = request.GET.get('per_page', '10')  # По умолчанию 10 записей
    try:
        per_page = int(per_page)
        if per_page not in [10, 25, 50, 100]:
            per_page = 10
    except (ValueError, TypeError):
        per_page = 10
    
    # Получаем параметры сортировки
    sort_by = request.GET.get('sort', 'created_at')
    order = request.GET.get('order', 'desc')
    
    # Маппинг полей для сортировки
    sort_mapping = {
        'order_number': 'order_number',
        'created_at': 'created_at',
        'responsible': 'responsible__last_name',
        'client': 'client__individual_data__last_name',
        'client__phones__phone': 'client__phones__phone',
        'client__individual_data__last_name': (
            'client__individual_data__last_name'
        ),
        'client__addresses__city': 'client__addresses__city',
        'items__branch_city': 'items__branch_city',
        'product_code': 'items__product_code',
        'segment': 'items__segment',
        'price': 'items__price',
        'quantity': 'items__quantity',
        'amount': 'items__amount',
        'status': 'status',
        'source': 'source',
        'payment_method': 'payment_method',
        'delivery_method': 'delivery_method',
    }
    
    # Определяем поле для сортировки
    sort_field = sort_mapping.get(sort_by, 'created_at')
    
    # Определяем направление сортировки
    if order == 'asc':
        sort_field = sort_field
    else:
        if not sort_field.startswith('-'):
            sort_field = f'-{sort_field}'
    
    # Получаем заказы с сортировкой - оптимизированные запросы
    orders_qs = Order.objects.select_related(
        'client', 'responsible', 'created_by'
    ).prefetch_related(
        'items__product',  # Добавляем связь с товаром для избежания N+1
        'client__phones',
        'client__addresses'
    ).order_by(sort_field)
    
    # Применяем фильтры
    if request.GET.get('order_number'):
        orders_qs = orders_qs.filter(order_number=request.GET.get('order_number'))
    
    if request.GET.get('date_today'):
        today = timezone.now().date()
        orders_qs = orders_qs.filter(created_at__date=today)
    elif request.GET.get('date_week'):
        week_ago = timezone.now().date() - timedelta(days=7)
        orders_qs = orders_qs.filter(created_at__date__gte=week_ago)
    elif request.GET.get('date_month'):
        month_ago = timezone.now().date() - timedelta(days=30)
        orders_qs = orders_qs.filter(created_at__date__gte=month_ago)
    
    if request.GET.get('responsible'):
        orders_qs = orders_qs.filter(responsible_id=request.GET.get('responsible'))
    
    if request.GET.get('phone'):
        orders_qs = orders_qs.filter(client__phones__phone=request.GET.get('phone'))
    
    if request.GET.get('client_name'):
        orders_qs = orders_qs.filter(client__name__icontains=request.GET.get('client_name'))
    
    if request.GET.get('client_city'):
        orders_qs = orders_qs.filter(client__addresses__city=request.GET.get('client_city'))
    
    if request.GET.get('product_code'):
        orders_qs = orders_qs.filter(items__product_code=request.GET.get('product_code'))
    
    if request.GET.get('segment'):
        orders_qs = orders_qs.filter(items__segment=request.GET.get('segment'))
    
    if request.GET.get('price_min'):
        orders_qs = orders_qs.filter(items__price__gte=request.GET.get('price_min'))
    if request.GET.get('price_max'):
        orders_qs = orders_qs.filter(items__price__lte=request.GET.get('price_max'))
    
    if request.GET.get('quantity_min'):
        orders_qs = orders_qs.filter(items__quantity__gte=request.GET.get('quantity_min'))
    if request.GET.get('quantity_max'):
        orders_qs = orders_qs.filter(items__quantity__lte=request.GET.get('quantity_max'))
    
    if request.GET.get('amount_min'):
        orders_qs = orders_qs.filter(items__amount__gte=request.GET.get('amount_min'))
    if request.GET.get('amount_max'):
        orders_qs = orders_qs.filter(items__amount__lte=request.GET.get('amount_max'))
    
    if request.GET.get('branch_city'):
        orders_qs = orders_qs.filter(items__branch_city=request.GET.get('branch_city'))
    
    if request.GET.get('status'):
        orders_qs = orders_qs.filter(status=request.GET.get('status'))
    
    if request.GET.get('source'):
        orders_qs = orders_qs.filter(source=request.GET.get('source'))
    
    if request.GET.get('payment_method'):
        orders_qs = orders_qs.filter(payment_method=request.GET.get('payment_method'))
    
    if request.GET.get('delivery_method'):
        orders_qs = orders_qs.filter(delivery_method=request.GET.get('delivery_method'))
    
    # Поиск по всем полям заказа
    search_query = request.GET.get('search')
    if search_query:
        orders_qs = orders_qs.filter(
            Q(order_number__icontains=search_query) |
            Q(client__individual_data__last_name__icontains=search_query) |
            Q(client__individual_data__first_name__icontains=search_query) |
            Q(client__individual_data__middle_name__icontains=search_query) |
            Q(client__legal_entity_data__company_name__icontains=search_query) |
            Q(client__phones__phone__icontains=search_query) |
            Q(client__addresses__city__icontains=search_query) |
            Q(items__product_code__icontains=search_query) |
            Q(items__product_name__icontains=search_query) |
            Q(items__segment__icontains=search_query) |
            Q(items__branch_city__icontains=search_query) |
            Q(responsible__first_name__icontains=search_query) |
            Q(responsible__last_name__icontains=search_query) |
            Q(status__icontains=search_query) |
            Q(source__icontains=search_query) |
            Q(payment_method__icontains=search_query) |
            Q(delivery_method__icontains=search_query) |
            Q(notes__icontains=search_query) |
            Q(sale_number__icontains=search_query)
        ).distinct()
    
    # Пагинация
    paginator = Paginator(orders_qs, per_page)
    page = request.GET.get('page')
    
    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        orders = paginator.page(1)
    except EmptyPage:
        orders = paginator.page(paginator.num_pages)
    
    # Получаем данные для фильтров - с кешированием
    from apps.accounts.models import User
    from apps.clients.models import ClientPhone, ClientAddress
    
    # Кешируем часто используемые данные
    cache_key_prefix = 'orders_filters_'
    cache_timeout = 300  # 5 минут
    
    responsible_users = cache.get(f'{cache_key_prefix}responsible_users')
    if responsible_users is None:
        responsible_users = list(
            User.objects.filter(responsible_orders__isnull=False)
            .distinct().only('id', 'first_name', 'last_name')
        )
        cache.set(f'{cache_key_prefix}responsible_users', 
                 responsible_users, cache_timeout)
    
    phone_numbers = cache.get(f'{cache_key_prefix}phone_numbers')
    if phone_numbers is None:
        phone_numbers = list(ClientPhone.objects.values_list('phone', flat=True).distinct()[:20])
        cache.set(f'{cache_key_prefix}phone_numbers', phone_numbers, cache_timeout)
    
    client_names = cache.get(f'{cache_key_prefix}client_names')
    if client_names is None:
        client_names = list(Order.objects.values_list('client__name', flat=True).distinct()[:20])
        cache.set(f'{cache_key_prefix}client_names', client_names, cache_timeout)
    
    client_cities = cache.get(f'{cache_key_prefix}client_cities')
    if client_cities is None:
        client_cities = list(ClientAddress.objects.values_list('city', flat=True).distinct()[:20])
        cache.set(f'{cache_key_prefix}client_cities', client_cities, cache_timeout)
    
    product_codes = cache.get(f'{cache_key_prefix}product_codes')
    if product_codes is None:
        product_codes = list(OrderItem.objects.values_list('product_code', flat=True).distinct()[:20])
        cache.set(f'{cache_key_prefix}product_codes', product_codes, cache_timeout)
    
    segments = cache.get(f'{cache_key_prefix}segments')
    if segments is None:
        segments = list(OrderItem.objects.values_list('segment', flat=True).distinct()[:20])
        cache.set(f'{cache_key_prefix}segments', segments, cache_timeout)
    
    branch_cities = cache.get(f'{cache_key_prefix}branch_cities')
    if branch_cities is None:
        branch_cities = list(OrderItem.objects.values_list('branch_city', flat=True).distinct()[:20])
        cache.set(f'{cache_key_prefix}branch_cities', branch_cities, cache_timeout)
    
    context = {
        'orders': orders,
        'responsible_users': responsible_users,
        'phone_numbers': phone_numbers,
        'client_names': client_names,
        'client_cities': client_cities,
        'product_codes': product_codes,
        'segments': segments,
        'branch_cities': branch_cities,
        'statuses': Order.STATUS_CHOICES,
        'sources': Order.SOURCE_CHOICES,
        'payment_methods': Order.PAYMENT_CHOICES,
        'delivery_methods': Order.DELIVERY_CHOICES,
    }
    return render(request, 'orders/orders_list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def add_order(request):
    """Страница создания заказа и обработчик POST (AJAX)."""
    if request.method == 'GET':
        # Загружаем только активные товары с ограничением для быстрой загрузки
        products = Product.objects.filter(is_active=True).only(
            'id', 'name', 'code', 'price', 'wholesale_price',
            'promotional_price', 'retail_price', 'assortment_group',
            'tire_type', 'branch_city__name'
        ).select_related('branch_city').order_by('name')[:1000]
        
        clients = Client.objects.all().only('id', 'name').order_by('-created_at')[:200]
        return render(
            request,
            'orders/order_form.html',
            {
                'is_edit': False,
                'products': products,
                'clients': clients,
            }
        )

    # POST JSON
    if request.headers.get('Content-Type', '').startswith('application/json'):
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except Exception:
            return HttpResponseBadRequest('Invalid JSON')

        client_id = payload.get('client_id')
        items = payload.get('items') or []
        if not client_id or not items:
            return JsonResponse(
                {'status': 'error', 'message': 'Клиент и товары обязательны'},
                status=400,
            )

        try:
            client = Client.objects.get(pk=client_id)
        except Client.DoesNotExist:
            return JsonResponse(
                {'status': 'error', 'message': 'Клиент не найден'},
                status=404,
            )

        with transaction.atomic():
            order = Order(
                client=client,
                responsible=request.user,
                status=payload.get('status') or Order.STATUS_NEW,
                source=payload.get('source') or 'website',
                payment_method=payload.get('payment_method') or 'cash',
                delivery_method=payload.get('delivery_method') or 'pickup',
                price_level=payload.get('price_level') or 'retail',
                is_promo=bool(payload.get('is_promo')),
                sale_number=payload.get('sale_number') or '',
                notes=payload.get('notes') or '',
                created_by=request.user,
                updated_by=request.user,
            )
            order.save()

            total = 0
            for it in items:
                product_id = it.get('product_id')
                quantity = int(it.get('quantity') or 1)
                city = it.get('city', '')  # Получаем город из формы
                if not product_id or quantity <= 0:
                    transaction.set_rollback(True)
                    return JsonResponse(
                        {
                            'status': 'error',
                            'message': 'Некорректные позиции заказа',
                        },
                        status=400,
                    )
                try:
                    product = Product.objects.get(pk=product_id)
                except Product.DoesNotExist:
                    transaction.set_rollback(True)
                    return JsonResponse(
                        {
                            'status': 'error',
                            'message': f'Товар {product_id} не найден',
                        },
                        status=404,
                    )

                # Определяем цену в зависимости от уровня цен заказа
                price = _get_price_by_level(product, order.price_level)

                order_item = OrderItem(
                    order=order,
                    product=product,
                    product_code=product.code or '',
                    product_name=product.name,
                    price=price,
                    segment=product.assortment_group or '',
                    tire_type=product.tire_type or '',
                    branch_city=city,  # Используем город из формы
                    quantity=quantity,
                    amount=price * quantity,
                )
                order_item.save()
                total += order_item.amount

            # Итоговая сумма и возможная акция -10%
            if order.is_promo:
                total = Decimal(total) * Decimal('0.9')
            order.total_amount = total
            order.updated_at = timezone.now()
            order.save(update_fields=['total_amount', 'updated_at'])

        return JsonResponse(
            {
                'status': 'success',
                'order_id': order.id,
                'order_number': order.order_number,
                'redirect_url': (
                    f"/orders/{order.id}/"
                ),
            }
        )

    return HttpResponseBadRequest('Unsupported Content-Type')


@login_required
def order_detail(request, pk):
    """Детали заказа"""
    order = get_object_or_404(
        Order.objects.prefetch_related('items'),
        pk=pk
    )
    context = {
        'order': order,
    }
    return render(request, 'orders/order_detail.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def edit_order(request, pk):
    """Страница редактирования заказа и обработчик POST (AJAX)."""
    order = get_object_or_404(Order.objects.prefetch_related('items'), pk=pk)

    if request.method == 'GET':
        # Оптимизированная загрузка товаров для редактирования
        products = Product.objects.filter(is_active=True).only(
            'id', 'name', 'code', 'price', 'wholesale_price',
            'promotional_price', 'retail_price', 'assortment_group',
            'tire_type', 'branch_city__name'
        ).select_related('branch_city').order_by('name')[:1000]
        
        clients = Client.objects.all().only('id', 'name').order_by('-created_at')[:200]
        
        # Предзаполним данные клиента для шага 2
        c = order.client
        primary_phone = c.phones.filter(is_primary=True).first() or c.phones.first()
        primary_addr = c.addresses.filter(is_primary=True).first() or c.addresses.first()
        client_initial = {
            'id': str(c.pk),
            'name': c.name,
            'phone': primary_phone.phone if primary_phone else '',
            'city': primary_addr.city if primary_addr else '',
            'address': primary_addr.address if primary_addr else '',
            'address_comment': primary_addr.comment if primary_addr else '',
        }
        return render(
            request,
            'orders/order_form.html',
            {
                'is_edit': True,
                'order': order,
                'products': products,
                'clients': clients,
                'client_initial': client_initial,
            }
        )

    # POST JSON
    if request.headers.get('Content-Type', '').startswith('application/json'):
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except Exception:
            return HttpResponseBadRequest('Invalid JSON')

        client_id = payload.get('client_id')
        items = payload.get('items') or []
        if not client_id or not items:
            return JsonResponse(
                {'status': 'error', 'message': 'Клиент и товары обязательны'},
                status=400,
            )

        try:
            client = Client.objects.get(pk=client_id)
        except Client.DoesNotExist:
            return JsonResponse(
                {'status': 'error', 'message': 'Клиент не найден'},
                status=404,
            )

        with transaction.atomic():
            order.client = client
            order.status = payload.get('status') or order.status
            order.source = payload.get('source') or order.source
            order.payment_method = (
                payload.get('payment_method') or order.payment_method
            )
            order.delivery_method = (
                payload.get('delivery_method') or order.delivery_method
            )
            order.is_promo = bool(payload.get('is_promo'))
            order.sale_number = payload.get('sale_number') or ''
            order.notes = payload.get('notes') or ''
            order.updated_by = request.user
            order.save()

            # Пересобираем позиции
            order.items.all().delete()
            total = 0
            for it in items:
                product_id = it.get('product_id')
                quantity = int(it.get('quantity') or 1)
                city = it.get('city', '')  # Получаем город из формы
                if not product_id or quantity <= 0:
                    transaction.set_rollback(True)
                    return JsonResponse(
                        {
                            'status': 'error',
                            'message': 'Некорректные позиции заказа',
                        },
                        status=400,
                    )
                try:
                    product = Product.objects.get(pk=product_id)
                except Product.DoesNotExist:
                    transaction.set_rollback(True)
                    return JsonResponse(
                        {
                            'status': 'error',
                            'message': f'Товар {product_id} не найден',
                        },
                        status=404,
                    )

                # Определяем цену в зависимости от уровня цен заказа
                price = _get_price_by_level(product, order.price_level)

                order_item = OrderItem(
                    order=order,
                    product=product,
                    product_code=product.code or '',
                    product_name=product.name,
                    price=price,
                    segment=product.assortment_group or '',
                    tire_type=product.tire_type or '',
                    branch_city=city,  # Используем город из формы
                    quantity=quantity,
                    amount=price * quantity,
                )
                order_item.save()
                total += order_item.amount

            if order.is_promo:
                total = Decimal(total) * Decimal('0.9')
            order.total_amount = total
            order.updated_at = timezone.now()
            order.save(update_fields=['total_amount', 'updated_at'])

        return JsonResponse(
            {
                'status': 'success',
                'order_id': order.id,
                'order_number': order.order_number,
                'redirect_url': (
                    f"/orders/{order.id}/"
                ),
            }
        )

    return HttpResponseBadRequest('Unsupported Content-Type')


@login_required
@require_http_methods(["GET"])
def product_search(request):
    """Поиск товаров. Поддержка выбора поля: name-only через search_field=name."""
    query = request.GET.get('q', '').strip()
    search_field = (request.GET.get('search_field') or '').strip().lower()
    logger = logging.getLogger('django')
    if not query:
        logger.info('product_search: empty query')
        return JsonResponse({'products': []})

    # Базовый queryset
    qs = Product.objects.filter(is_active=True)

    # Фильтр по полю
    if search_field == 'name':
        qs = qs.filter(name__icontains=query)
    else:
        qs = qs.filter(Q(code__icontains=query) | Q(name__icontains=query))

    products = qs.select_related('branch_city').only(
        'id', 'name', 'code', 'price', 'wholesale_price', 
        'promotional_price', 'retail_price', 'assortment_group', 
        'tire_type', 'branch_city__name'
    )[:50]  # Ограничиваем результаты
    
    results = []
    for product in products:
        results.append({
            'id': product.id,
            'name': product.name,
            'code': product.code or '',
            'price': float(product.price),
            'wholesale_price': float(product.wholesale_price) if product.wholesale_price else None,
            'promotional_price': float(product.promotional_price) if product.promotional_price else None,
            'retail_price': float(product.retail_price) if product.retail_price else None,
            'assortment_group': product.assortment_group or '',
            'tire_type': product.tire_type or '',
            'branch_city': product.branch_city.name if product.branch_city else '',
        })
    
    logger.info(
        'product_search: field=%s q="%s" results=%d',
        (search_field or 'code|name'), query, len(results)
    )
    return JsonResponse({'products': results})


@login_required
@require_http_methods(["GET"])
def client_lookup(request):
    """Поиск клиента по id или телефону для автоподстановки (AJAX)."""
    client_id = request.GET.get('id')
    phone = request.GET.get('phone')

    client = None
    if client_id:
        try:
            client = Client.objects.get(pk=client_id)
        except Client.DoesNotExist:
            return JsonResponse(
                {'status': 'error', 'message': 'Клиент не найден'},
                status=404,
            )
    elif phone:
        # Нормализация телефона: оставляем только цифры, допускаем +7 / 8
        digits = ''.join(ch for ch in phone if ch.isdigit())
        if digits.startswith('8'):
            digits = '7' + digits[1:]
        # Ищем совпадения по окончанию, т.к. могут храниться в формате
        # +7XXXXXXXXXX
        cp = ClientPhone.objects.filter(phone__regex=r"[0-9]+")
        cp = (
            cp.filter(phone__endswith=digits[-10:])
            if len(digits) >= 10
            else cp.filter(phone__contains=digits)
        )
        cp = cp.select_related('client').first()
        client = cp.client if cp else None

    if not client:
        return JsonResponse({'status': 'not_found'})

    # Основной телефон и адрес (если есть)
    primary_phone = (
        client.phones.filter(is_primary=True).first()
        or client.phones.first()
    )
    primary_addr = (
        client.addresses.filter(is_primary=True).first()
        or client.addresses.first()
    )

    return JsonResponse({
        'status': 'success',
        'id': str(client.pk),
        'name': client.name,
        'city': (primary_addr.city if primary_addr else ''),
        'address': (primary_addr.address if primary_addr else ''),
        'address_comment': (primary_addr.comment if primary_addr else ''),
        'phone': (primary_phone.phone if primary_phone else ''),
    })


@login_required
@require_http_methods(["POST"])
def update_order_status(request):
    """Обновить статус заказа (AJAX)."""
    # Поддержим JSON и form-encoded
    if request.headers.get('Content-Type', '').startswith('application/json'):
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except Exception:
            return HttpResponseBadRequest('Invalid JSON')
        order_id = payload.get('order_id')
        new_status = payload.get('status')
    else:
        order_id = request.POST.get('order_id')
        new_status = request.POST.get('status')

    if not order_id or not new_status:
        return JsonResponse({'status': 'error', 'message': 'order_id и status обязательны'}, status=400)

    order = get_object_or_404(Order, pk=order_id)

    valid_values = {key for key, _ in Order.STATUS_CHOICES}
    if new_status not in valid_values:
        return JsonResponse({'status': 'error', 'message': 'Недопустимый статус'}, status=400)

    order.status = new_status
    order.updated_by = request.user
    order.updated_at = timezone.now()
    order.save(update_fields=['status', 'updated_by', 'updated_at'])

    # Готовим данные для UI
    display_map = dict(Order.STATUS_CHOICES)
    from .templatetags.order_extras import status_text_class, status_css_class
    text_class = status_text_class(new_status)
    css_class = status_css_class(new_status)

    return JsonResponse({
        'status': 'success',
        'order_id': order.id,
        'new_status': new_status,
        'status_display': display_map.get(new_status, new_status),
        'text_class': text_class,
        'css_class': css_class,
    })
