from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
import os
import tempfile
from .models import Product
from apps.cities.models import City


@login_required(login_url='login')
def products_list(request):
    """Список всех товаров"""
    sort_by = request.GET.get('sort', '-created_at')
    order = request.GET.get('order', 'desc')
    per_page = int(request.GET.get('per_page', 25))

    sort_mapping = {
        'code': 'code',
        'name': 'name',
        'price': 'price',
        'assortment_group': 'assortment_group',
        'branch_city': 'branch_city__name',
        'created_at': 'created_at',
    }

    sort_field = sort_mapping.get(sort_by, sort_by)

    if order == 'asc':
        sort_field = sort_field
    else:
        if not sort_field.startswith('-'):
            sort_field = f'-{sort_field}'

    products_queryset = (
        Product.objects.select_related('branch_city')
        .filter(is_active=True)
        .order_by(sort_field)
    )

    # Пагинация
    paginator = Paginator(products_queryset, per_page)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)

    return render(
        request,
        'products/products_list.html',
        {
            'products': products,
            'current_sort': sort_by,
            'current_order': order,
            'per_page': per_page,
        },
    )


@login_required(login_url='login')
def add_product(request):
    """Добавление нового товара"""
    if request.method == 'POST':
        try:
            Product.objects.create(
                code=request.POST.get('code'),
                name=request.POST.get('name'),
                description=request.POST.get('description', ''),
                price=request.POST.get('price'),
                segment=request.POST.get('segment'),
                branch_city_id=request.POST.get('branch_city'),
                is_active=True
            )

            return JsonResponse({
                'status': 'success',
                'message': 'Товар успешно добавлен',
                'redirect_url': reverse('products:products_list'),
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Ошибка при сохранении: {str(e)}',
            })

    cities = City.objects.filter(is_active=True).order_by('name')
    return render(request, 'products/add_product.html', {
        'cities': cities,
    })


@login_required(login_url='login')
def edit_product(request, product_id):
    """Редактирование товара"""
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        try:
            product.code = request.POST.get('code')
            product.name = request.POST.get('name')
            product.description = request.POST.get('description', '')
            product.price = request.POST.get('price')
            product.segment = request.POST.get('segment')
            product.branch_city_id = request.POST.get('branch_city')
            product.save()

            return JsonResponse({
                'status': 'success',
                'message': 'Товар успешно обновлён',
                'redirect_url': reverse('products:products_list'),
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Ошибка при сохранении: {str(e)}',
            })

    cities = City.objects.filter(is_active=True).order_by('name')
    return render(request, 'products/edit_product.html', {
        'product': product,
        'cities': cities,
    })


@login_required(login_url='login')
def delete_product(request, product_id):
    """Удаление товара"""
    product = get_object_or_404(Product, id=product_id)

    try:
        product_name = product.name
        product.delete()
        return JsonResponse({
            'status': 'success',
            'message': f'Товар {product_name} успешно удалён',
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка при удалении: {str(e)}',
        })


@login_required(login_url='login')
@require_http_methods(["POST"])
def import_products(request):
    """Импорт товаров из Excel файла"""
    try:
        # Получаем файл из запроса
        if 'file' not in request.FILES:
            return JsonResponse({
                'status': 'error',
                'message': 'Файл не выбран'
            })
        
        uploaded_file = request.FILES['file']
        
        # Проверяем расширение файла
        if not uploaded_file.name.lower().endswith(('.xlsx', '.xls')):
            return JsonResponse({
                'status': 'error',
                'message': 'Поддерживаются только файлы Excel (.xlsx, .xls)'
            })
        
        # Получаем параметры
        clear_existing = request.POST.get('clear_existing') == 'true'
        limit = request.POST.get('limit')
        limit = int(limit) if limit else None
        
        # Сохраняем файл во временную папку
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, uploaded_file.name)
        
        with open(temp_file_path, 'wb') as temp_file:
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
        
        # Запускаем команду импорта
        from django.core.management import call_command
        from io import StringIO
        import sys
        
        # Перенаправляем вывод команды
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            # Подготавливаем аргументы команды
            args = [temp_file_path]
            kwargs = {}
            
            if clear_existing:
                kwargs['clear_products'] = True
            
            if limit:
                kwargs['limit'] = limit
            
            # Всегда удаляем товары, которых нет в файле при обновлении через сайт
            kwargs['remove_missing'] = True
            
            # Выполняем команду
            call_command('universal_import', *args, **kwargs)
            
            # Получаем вывод команды
            output = sys.stdout.getvalue()
            
            # Парсим результат из вывода
            created = 0
            updated = 0
            deleted = 0
            
            for line in output.split('\n'):
                if 'Создано товаров:' in line:
                    try:
                        created = int(line.split('Создано товаров:')[1].strip())
                    except:
                        pass
                elif 'Обновлено товаров:' in line:
                    try:
                        updated = int(line.split('Обновлено товаров:')[1].strip())
                    except:
                        pass
                elif 'Удалено товаров:' in line and 'УДАЛЕНИЕ ОТСУТСТВУЮЩИХ ТОВАРОВ' in output:
                    try:
                        deleted = int(line.split('Удалено товаров:')[1].strip())
                    except:
                        pass
            
            return JsonResponse({
                'status': 'success',
                'message': 'Импорт завершен успешно',
                'created': created,
                'updated': updated,
                'deleted': deleted,
                'output': output
            })
            
        finally:
            # Восстанавливаем stdout
            sys.stdout = old_stdout
            
            # Удаляем временный файл
            try:
                os.unlink(temp_file_path)
                os.rmdir(temp_dir)
            except:
                pass
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка при импорте: {str(e)}'
        })
