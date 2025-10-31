from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from .models import City


@login_required(login_url='login')
def cities_list(request):
    """Список городов"""
    search_query = request.GET.get('search', '')
    
    # Получаем параметры сортировки
    sort_by = request.GET.get('sort', 'name')
    order = request.GET.get('order', 'asc')
    
    # Определяем направление сортировки
    if order == 'asc':
        sort_field = sort_by
    else:
        sort_field = f'-{sort_by}' if not sort_by.startswith('-') else sort_by
    
    cities = City.objects.all().order_by(sort_field)
    
    if search_query:
        cities = cities.filter(
            Q(name__icontains=search_query) | 
            Q(region__icontains=search_query)
        )
    
    # Простая пагинация без использования Django Paginator
    page = int(request.GET.get('page', 1))
    per_page = 25
    start = (page - 1) * per_page
    end = start + per_page
    
    total_count = cities.count()
    cities_list = list(cities[start:end])
    
    # Создаем простой объект для пагинации
    class SimplePage:
        def __init__(self, objects, page, per_page, total):
            self.object_list = objects
            self.number = page
            self.per_page = per_page
            self.total_count = total
            self.paginator = SimplePaginator(total, per_page)
            
        def __iter__(self):
            return iter(self.object_list)
            
        def __len__(self):
            return len(self.object_list)
            
        @property
        def has_other_pages(self):
            return self.paginator.num_pages > 1
            
        @property
        def has_previous(self):
            return self.number > 1
            
        @property
        def has_next(self):
            return self.number < self.paginator.num_pages
            
        @property
        def previous_page_number(self):
            return self.number - 1 if self.has_previous else None
            
        @property
        def next_page_number(self):
            return self.number + 1 if self.has_next else None
            
        @property
        def start_index(self):
            return (self.number - 1) * self.per_page + 1
            
        @property
        def end_index(self):
            return min(self.number * self.per_page, self.total_count)
    
    class SimplePaginator:
        def __init__(self, total, per_page):
            self.count = total
            self.per_page = per_page
            self.num_pages = (total + per_page - 1) // per_page
    
    cities = SimplePage(cities_list, page, per_page, total_count)
    
    return render(request, 'cities/cities_list.html', {
        'cities': cities,
        'current_sort': sort_by,
        'current_order': order,
    })


@login_required(login_url='login')
def add_city(request):
    """Добавление города"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        region = request.POST.get('region', '').strip()
        country = request.POST.get('country', 'Казахстан').strip()
        
        if not name:
            return JsonResponse({
                'status': 'error',
                'message': 'Название города обязательно'
            })
        
        # Проверяем, не существует ли уже такой город
        if City.objects.filter(name=name).exists():
            return JsonResponse({
                'status': 'error',
                'message': 'Город с таким названием уже существует'
            })
        
        try:
            city = City.objects.create(
                name=name,
                region=region,
                country=country,
                created_by=request.user,
                modified_by=request.user
            )
            return JsonResponse({
                'status': 'success',
                'message': 'Город успешно добавлен',
                'redirect_url': '/cities/'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Ошибка при добавлении: {str(e)}'
            })
    
    return render(request, 'cities/add_city.html')


@login_required(login_url='login')
def edit_city(request, city_id):
    """Редактирование города"""
    city = get_object_or_404(City, id=city_id)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        region = request.POST.get('region', '').strip()
        country = request.POST.get('country', 'Казахстан').strip()
        is_active = request.POST.get('is_active') == 'on'
        
        if not name:
            return JsonResponse({
                'status': 'error',
                'message': 'Название города обязательно'
            })
        
        # Проверяем, не существует ли уже такой город (кроме текущего)
        if City.objects.filter(name=name).exclude(id=city_id).exists():
            return JsonResponse({
                'status': 'error',
                'message': 'Город с таким названием уже существует'
            })
        
        try:
            city.name = name
            city.region = region
            city.country = country
            city.is_active = is_active
            city.modified_by = request.user
            city.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Город успешно обновлен',
                'redirect_url': '/cities/'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Ошибка при обновлении: {str(e)}'
            })
    
    return render(request, 'cities/edit_city.html', {'city': city})


@login_required(login_url='login')
def delete_city(request, city_id):
    """Удаление города"""
    if request.method == 'POST':
        city = get_object_or_404(City, id=city_id)
        city_name = city.name
        
        try:
            city.delete()
            return JsonResponse({
                'status': 'success',
                'message': f'Город "{city_name}" успешно удален'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Ошибка при удалении: {str(e)}'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Метод не разрешен'})