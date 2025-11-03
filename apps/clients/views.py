import logging
import pandas as pd
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db import transaction
from .models import (
    Client,
    ClientPhone,
    ClientAddress,
    ClientCar,
    IndividualClientData,
    LegalEntityClientData,
)
from .forms import IndividualClientForm, LegalEntityClientForm
from apps.cities.models import City
from apps.accounts.models import User

# Настройка логгера
logger = logging.getLogger('client')

@login_required(login_url='accounts:login')
def clients_list(request):
    """Список всех клиентов"""
    # Получаем параметры сортировки
    sort_by = request.GET.get('sort', '-created_at')
    order = request.GET.get('order', 'desc')
    
    # Маппинг полей для сортировки
    sort_mapping = {
        'name': 'name',
        'phone': 'phones__phone',  # Сортировка по основному телефону
        'city': 'addresses__city',  # Сортировка по основному городу
        'email': 'email',
        'created_at': 'created_at',
    }
    
    # Определяем поле для сортировки
    sort_field = sort_mapping.get(sort_by, sort_by)
    
    # Определяем направление сортировки
    if order == 'asc':
        sort_field = sort_field
    else:
        sort_field = f'-{sort_field}' if not sort_field.startswith('-') else sort_field
    
    # Применяем сортировку с distinct для избежания дублирования
    clients_qs = (Client.objects.select_related()
                  .prefetch_related('phones', 'addresses')
                  .distinct().order_by(sort_field))
    
    # Поиск по имени и телефону
    search_query = (request.GET.get('search') or '').strip()
    if search_query:
        from django.db.models import Q
        clients_qs = clients_qs.filter(
            Q(name__icontains=search_query) |
            Q(phones__phone__icontains=search_query)
        ).distinct()

    # Пагинация
    try:
        per_page = int(request.GET.get('per_page', 25))
    except ValueError:
        per_page = 25
    if per_page not in (10, 25, 50, 100):
        per_page = 25

    paginator = Paginator(clients_qs, per_page)
    page = request.GET.get('page') or 1
    try:
        clients = paginator.page(page)
    except PageNotAnInteger:
        clients = paginator.page(1)
    except EmptyPage:
        clients = paginator.page(paginator.num_pages)

    return render(
        request,
        'clients/clients_list.html',
        {
            'clients': clients,
            'current_sort': sort_by,
            'current_order': order,
            'per_page': per_page,
        },
    )

@login_required(login_url='accounts:login')
def add_client(request):
    """Добавление нового клиента"""
    # Обработка AJAX запросов
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            
            client_type = data.get('client_type', 'individual')
            name = data.get('name', '').strip()
            phone = data.get('phone', '').strip()
            city = data.get('city', '').strip()
            address = data.get('address', '').strip()
            address_comment = data.get('address_comment', '').strip()
            
            if not name or not phone:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Имя и телефон обязательны для заполнения'
                })
            
            with transaction.atomic():
                # Создаем клиента
                client = Client.objects.create(
                    client_type=client_type,
                    name=name,
                    created_by=request.user,
                    modified_by=request.user,
                )
                
                # Создаем дополнительные данные в зависимости от типа клиента
                if client_type == 'individual':
                    # Разбираем ФИО для физического лица
                    name_parts = name.split()
                    first_name = name_parts[0] if len(name_parts) > 0 else ''
                    last_name = name_parts[1] if len(name_parts) > 1 else ''
                    middle_name = name_parts[2] if len(name_parts) > 2 else ''
                    
                    IndividualClientData.objects.create(
                        client=client,
                        first_name=first_name,
                        last_name=last_name,
                        middle_name=middle_name
                    )
                else:
                    LegalEntityClientData.objects.create(
                        client=client,
                        company_name=name
                    )
                
                # Добавляем телефон
                ClientPhone.objects.create(
                    client=client,
                    phone=phone,
                    is_primary=True
                )
                
                # Добавляем адрес если указан
                if city or address:
                    ClientAddress.objects.create(
                        client=client,
                        city=city,
                        address=address,
                        comment=address_comment,
                        is_primary=True
                    )
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Клиент успешно добавлен',
                    'client_id': str(client.id)
                })
                
        except Exception as e:
            logger.error(f'Ошибка при добавлении клиента через AJAX: {e}')
            return JsonResponse({
                'status': 'error',
                'message': 'Ошибка при добавлении клиента'
            })
    
    # Обычная обработка GET/POST запросов
    client_type = request.POST.get('client_type', 'individual')
    individual_form = IndividualClientForm()
    legal_form = LegalEntityClientForm()
    
    if request.method == 'POST':
        logger.debug(
            'Получен POST запрос на добавление клиента. Тип: %s',
            client_type,
        )
        
        if client_type == 'individual':
            form = IndividualClientForm(request.POST)
            individual_form = form
            logger.debug('Обработка формы физического лица')
        else:
            form = LegalEntityClientForm(request.POST)
            legal_form = form
            logger.debug('Обработка формы юридического лица')
            
        if form.is_valid():
            try:
                logger.debug('Форма валидна, сохраняем данные')
                
                # Создаем основную запись клиента
                name_value = (
                    form.cleaned_data.get('company_name', '')
                    if client_type == 'legal_entity'
                    else (
                        f"{form.cleaned_data.get('first_name', '')} "
                        f"{form.cleaned_data.get('last_name', '')}"
                    )
                )
                client = Client.objects.create(
                    client_type=client_type,
                    name=name_value,
                    first_name=(
                        form.cleaned_data.get('first_name')
                        if client_type == 'individual'
                        else None
                    ),
                    last_name=(
                        form.cleaned_data.get('last_name')
                        if client_type == 'individual'
                        else None
                    ),
                    middle_name=(
                        form.cleaned_data.get('middle_name')
                        if client_type == 'individual'
                        else None
                    ),
                    email=form.cleaned_data.get('email', ''),
                    created_by=request.user,
                    modified_by=request.user,
                )
                logger.info(
                    f'Создан новый клиент ID: {client.id}, тип: {client_type}'
                )

                # Создаем и сохраняем дополнительные данные клиента
                if client_type == 'individual':
                    individual_data = IndividualClientData.objects.create(
                        client=client,
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        middle_name=form.cleaned_data.get('middle_name', ''),
                        gender=form.cleaned_data.get('gender'),
                        birth_date=form.cleaned_data.get('birth_date')
                    )
                    # Обновляем имя клиента после создания individual_data
                    client.name = str(individual_data)
                    client.save()
                else:
                    LegalEntityClientData.objects.create(
                        client=client,
                        company_name=form.cleaned_data.get('company_name', ''),
                        bin=form.cleaned_data.get('bin'),
                        tax_number=form.cleaned_data.get('tax_number'),
                        registration_date=form.cleaned_data.get('registration_date'),
                        director_name=form.cleaned_data.get('director_name'),
                        bank_account=form.cleaned_data.get('bank_account'),
                        bank_name=form.cleaned_data.get('bank_name')
                    )
                logger.debug(
                    'Сохранены дополнительные данные клиента ID: %s',
                    client.id,
                )


                # Сохранение адреса
                city_id = request.POST.get('city', '').strip()
                address = request.POST.get('address', '').strip()
                address_comment = request.POST.get('address_comment', '').strip()
                if city_id or address:
                    city_name = ''
                    if city_id:
                        try:
                            city = City.objects.get(id=city_id)
                            city_name = city.name
                        except City.DoesNotExist:
                            pass
                    
                    ClientAddress.objects.create(
                        client=client,
                        city=city_name,
                        address=address,
                        comment=address_comment,
                        is_primary=True
                    )
                    logger.debug('Добавлен адрес для клиента ID: %s', client.id)

                # Сохранение телефонов
                phone = request.POST.get('phone', '').strip()
                phone2 = request.POST.get('phone2', '').strip()
                def normalize(p):
                    digits = ''.join(ch for ch in p if ch.isdigit())
                    return f"+7{digits[-10:]}" if len(digits) >= 10 else None
                norm1 = normalize(phone)
                norm2 = normalize(phone2)
                if norm1:
                    ClientPhone.objects.create(client=client, phone=norm1, is_primary=True)
                if norm2 and norm2 != norm1:
                    ClientPhone.objects.create(client=client, phone=norm2, is_primary=False)

                # Сохранение данных автомобиля для физических лиц
                if client_type == 'individual':
                    car_brand = request.POST.get('car_brand', '').strip()
                    car_model = request.POST.get('car_model', '').strip()
                    car_year = request.POST.get('car_year', '').strip()
                    license_plate = request.POST.get('license_plate', '').strip()
                    vin_number = request.POST.get('vin_number', '').strip()
                    if car_brand and car_model:
                        ClientCar.objects.create(
                            client=client,
                            brand=car_brand,
                            model=car_model,
                            year=int(car_year) if car_year.isdigit() else None,
                            license_plate=license_plate,
                            vin_number=vin_number,
                            is_primary=True
                        )
                        logger.debug(
                            'Добавлены данные автомобиля для клиента ID: %s',
                            client.id,
                        )

                success_type = (
                    'Физическое' if client_type == 'individual' else 'Юридическое'
                )
                messages.success(
                    request,
                    f'{success_type} лицо успешно добавлено в базу клиентов',
                )
                logger.info(
                    'Клиент ID: %s успешно создан со всеми данными',
                    client.id,
                )
                
                # Возвращаем JSON-ответ для AJAX
                return JsonResponse(
                    {
                    'status': 'success',
                        'message': (
                            'Физическое' if client_type == 'individual' else 'Юридическое'
                        )
                        + ' лицо успешно добавлено',
                        'redirect_url': reverse('clients:clients_list'),
                    }
                )
                
            except Exception as e:
                logger.error(
                    'Ошибка при сохранении клиента: %s', str(e), exc_info=True
                )
                return JsonResponse(
                    {
                    'status': 'error',
                        'message': f'Ошибка при сохранении: {str(e)}',
                    }
                )
        else:
            logger.warning(
                'Форма не прошла валидацию', extra={'errors': form.errors}
            )
            return JsonResponse({'status': 'error', 'errors': form.errors})
        
    return render(
        request,
        'clients/add_client.html',
        {
        'form': individual_form,
        'legal_form': legal_form,
        'client_type': client_type,
            'cities': City.objects.filter(is_active=True).order_by('name'),
        },
    )

@login_required(login_url='accounts:login')
def edit_client(request, client_id):
    """Редактирование клиента"""
    client = get_object_or_404(Client, id=client_id)
    
    if request.method == 'POST':
        logger.debug(f'POST данные: {dict(request.POST)}')
        logger.debug(f'Телефон из POST: "{request.POST.get("phone", "")}"')
        
        if client.client_type == 'individual':
            try:
                individual_data = client.individual_data
                form = IndividualClientForm(request.POST, instance=individual_data)
            except Client.individual_data.RelatedObjectDoesNotExist:
                # Создаем данные для физического лица если их нет
                from apps.clients.models import IndividualClientData
                individual_data = IndividualClientData.objects.create(client=client)
                form = IndividualClientForm(request.POST, instance=individual_data)
        else:
            try:
                legal_entity_data = client.legal_entity_data
                form = LegalEntityClientForm(request.POST, instance=legal_entity_data)
            except Client.legal_entity_data.RelatedObjectDoesNotExist:
                # Создаем данные для юридического лица если их нет
                from apps.clients.models import LegalEntityClientData
                legal_entity_data = LegalEntityClientData.objects.create(client=client)
                form = LegalEntityClientForm(request.POST, instance=legal_entity_data)
            
        logger.debug(f'Форма валидна: {form.is_valid()}')
        if not form.is_valid():
            logger.warning(f'Ошибки формы: {form.errors}')
            
        if form.is_valid():
            try:
                # Сохраняем основные данные клиента
                client_data = form.save(commit=False)
                
                # Обновляем имя клиента
                if client.client_type == 'individual':
                    client.name = f"{form.cleaned_data['first_name']} {form.cleaned_data['last_name']} {form.cleaned_data.get('middle_name', '')}"
                else:
                    client.name = form.cleaned_data['company_name']
                client.email = form.cleaned_data.get('email', '')
                client.modified_by = request.user
                client.save()
                client_data.save()


                # Обновляем адрес
                city_id = request.POST.get('city', '').strip()
                address = request.POST.get('address', '').strip()
                address_comment = request.POST.get('address_comment', '').strip()
                
                logger.debug(f'Данные адреса: city_id={city_id}, address={address}, comment={address_comment}')
                
                # Удаляем старые адреса
                client.addresses.all().delete()
                
                if city_id or address:
                    city_name = ''
                    if city_id:
                        try:
                            city = City.objects.get(id=city_id)
                            city_name = city.name
                            logger.debug(f'Найден город: {city_name}')
                        except City.DoesNotExist:
                            logger.warning(f'Город с ID {city_id} не найден')
                            pass
                    
                    ClientAddress.objects.create(
                        client=client,
                        city=city_name,
                        address=address,
                        comment=address_comment,
                        is_primary=True
                    )
                    logger.debug(f'Создан адрес: {city_name}, {address}')

                # Обновляем данные автомобиля для физических лиц
                if client.client_type == 'individual':
                    car_brand = request.POST.get('car_brand', '').strip()
                    car_model = request.POST.get('car_model', '').strip()
                    car_year = request.POST.get('car_year', '').strip()
                    license_plate = request.POST.get('license_plate', '').strip()
                    vin_number = request.POST.get('vin_number', '').strip()
                    
                    logger.debug(f'Данные автомобиля: brand={car_brand}, model={car_model}, year={car_year}')
                    
                    # Удаляем старые данные автомобиля
                    client.cars.all().delete()
                    
                    if car_brand and car_model:
                        ClientCar.objects.create(
                            client=client,
                            brand=car_brand,
                            model=car_model,
                            year=int(car_year) if car_year.isdigit() else None,
                            license_plate=license_plate,
                            vin_number=vin_number,
                            is_primary=True
                        )
                        logger.debug(f'Создан автомобиль: {car_brand} {car_model}')

                # Обновляем телефоны
                phone = request.POST.get('phone', '').strip()
                phone2 = request.POST.get('phone2', '').strip()
                def normalize(p):
                    digits = ''.join(ch for ch in p if ch.isdigit())
                    return f"+7{digits[-10:]}" if len(digits) >= 10 else None
                norm1 = normalize(phone)
                norm2 = normalize(phone2)
                client.phones.all().delete()
                if norm1:
                    ClientPhone.objects.create(client=client, phone=norm1, is_primary=True)
                if norm2 and norm2 != norm1:
                    ClientPhone.objects.create(client=client, phone=norm2, is_primary=False)

                return JsonResponse(
                    {
                    'status': 'success',
                    'message': 'Данные успешно сохранены',
                        'redirect_url': '/clients/',
                    }
                )
            except Exception as e:
                logger.error(f'Ошибка при сохранении клиента: {str(e)}', exc_info=True)
                return JsonResponse(
                    {
                    'status': 'error',
                        'message': f'Ошибка при сохранении: {str(e)}',
                    }
                )
        else:
            logger.warning('Форма не прошла валидацию')
            errors = {field: error[0] for field, error in form.errors.items()}
            return JsonResponse(
                {
                'status': 'error',
                'message': 'Пожалуйста, исправьте ошибки в форме',
                    'errors': errors,
                }
            )

    if client.client_type == 'individual':
        try:
            individual_data = client.individual_data
            form = IndividualClientForm(instance=individual_data)
        except Client.individual_data.RelatedObjectDoesNotExist:
            # Создаем данные для физического лица если их нет
            from apps.clients.models import IndividualClientData
            individual_data = IndividualClientData.objects.create(client=client)
            form = IndividualClientForm(instance=individual_data)
    else:
        try:
            legal_entity_data = client.legal_entity_data
            form = LegalEntityClientForm(instance=legal_entity_data)
        except Client.legal_entity_data.RelatedObjectDoesNotExist:
            # Создаем данные для юридического лица если их нет
            from apps.clients.models import LegalEntityClientData
            legal_entity_data = LegalEntityClientData.objects.create(client=client)
            form = LegalEntityClientForm(instance=legal_entity_data)

    context = {
        'client': client,
        'form': form,
        'cities': City.objects.filter(is_active=True).order_by('name'),
    }
    return render(request, 'clients/edit_client.html', context)

@login_required(login_url='accounts:login')
def delete_client(request, client_id):
    """Удаление клиента"""
    client = get_object_or_404(Client, id=client_id)
    client_type = 'физическое' if client.client_type == 'individual' else 'юридическое'
    client_name = client.name
    
    try:
        client.delete()
        return JsonResponse(
            {
            'status': 'success',
                'message': (
                    f'{client_type.capitalize()} лицо {client_name} успешно удалено'
                ),
            }
        )
    except Exception as e:
        logger.error(
            f'Ошибка при удалении клиента: {str(e)}', exc_info=True
        )
        return JsonResponse(
            {
            'status': 'error',
                'message': f'Ошибка при удалении клиента: {str(e)}',
            }
        )


@login_required(login_url='accounts:login')
def import_clients_excel(request):
    """Импорт клиентов из Excel файла"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Метод не поддерживается'})
    
    if 'excel_file' not in request.FILES:
        return JsonResponse({'status': 'error', 'message': 'Файл не выбран'})
    
    excel_file = request.FILES['excel_file']
    
    # Проверяем расширение файла
    if not excel_file.name.endswith(('.xlsx', '.xls')):
        return JsonResponse({'status': 'error', 'message': 'Поддерживаются только файлы Excel (.xlsx, .xls)'})
    
    try:
        # Сохраняем файл временно
        file_path = default_storage.save(f'temp/{excel_file.name}', ContentFile(excel_file.read()))
        full_path = default_storage.path(file_path)
        
        # Читаем Excel файл
        df = pd.read_excel(full_path)
        
        # Проверяем наличие необходимых колонок
        required_columns = ['Телефон', 'Тип клиента', 'ФИО/Компания']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            # Удаляем временный файл
            default_storage.delete(file_path)
            return JsonResponse({
                'status': 'error', 
                'message': f'Отсутствуют обязательные колонки: {", ".join(missing_columns)}'
            })
        
        # Получаем системного пользователя
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = request.user
        
        imported_count = 0
        skipped_count = 0
        errors = []
        duplicate_names = 0
        duplicate_phones = 0
        empty_rows = 0
        invalid_type = 0
        
        with transaction.atomic():
            for index, row in df.iterrows():
                try:
                    # Получаем данные из строки
                    phone = str(row.get('Телефон', '')).strip() if pd.notna(row.get('Телефон')) else ''
                    phone2 = str(row.get('Телефон 2', '')).strip() if pd.notna(row.get('Телефон 2')) else ''
                    email = str(row.get('Email', '')).strip() if pd.notna(row.get('Email')) else ''
                    client_type_raw = str(row.get('Тип клиента', '')).strip() if pd.notna(row.get('Тип клиента')) else ''
                    full_name = str(row.get('ФИО/Компания', '')).strip() if pd.notna(row.get('ФИО/Компания')) else ''
                    last_name = str(row.get('Фамилия', '')).strip() if pd.notna(row.get('Фамилия')) else ''
                    first_name = str(row.get('Имя', '')).strip() if pd.notna(row.get('Имя')) else ''
                    middle_name = str(row.get('Отчество', '')).strip() if pd.notna(row.get('Отчество')) else ''
                    city = str(row.get('Город', '')).strip() if pd.notna(row.get('Город')) else ''
                    
                    # Проверяем что строка не пустая
                    if not phone and not full_name:
                        empty_rows += 1
                        skipped_count += 1
                        continue
                    
                    # Определяем тип клиента
                    if client_type_raw in ['Физическое лицо', 'Физ. лицо', 'Физическое', 'individual']:
                        client_type = 'individual'
                    elif client_type_raw in ['Юридическое лицо', 'Юр. лицо', 'Юридическое', 'legal_entity']:
                        client_type = 'legal_entity'
                    else:
                        invalid_type += 1
                        skipped_count += 1
                        continue

                    # Нормализуем телефон
                    def normalize_phone(phone_str):
                        if not phone_str:
                            return None
                        digits = ''.join(filter(str.isdigit, phone_str))
                        if len(digits) == 10:
                            return f"+7{digits}"
                        elif len(digits) == 11 and digits.startswith('7'):
                            return f"+{digits}"
                        elif len(digits) == 11 and digits.startswith('8'):
                            return f"+7{digits[1:]}"
                        return None

                    normalized_phone = normalize_phone(phone)
                    normalized_phone2 = normalize_phone(phone2) if phone2 else None

                    # Проверяем существующих клиентов по телефону
                    existing_client = None
                    if normalized_phone:
                        existing_client = Client.objects.filter(phones__phone=normalized_phone).first()
                    
                    # Если клиент не найден по телефону, проверяем по имени
                    if not existing_client and full_name:
                        existing_client = Client.objects.filter(name=full_name).first()
                    
                    # Если клиент существует, обновляем его данные
                    if existing_client:
                        # Обновляем основные данные клиента
                        existing_client.name = full_name
                        existing_client.first_name = first_name
                        existing_client.last_name = last_name
                        existing_client.middle_name = middle_name
                        existing_client.email = email if email else existing_client.email
                        existing_client.modified_by = admin_user
                        existing_client.save()
                        
                        # Обновляем дополнительные данные в зависимости от типа
                        if client_type == 'individual':
                            try:
                                individual_data = existing_client.individual_data
                                individual_data.first_name = first_name
                                individual_data.last_name = last_name
                                individual_data.middle_name = middle_name if middle_name else None
                                individual_data.save()
                            except:
                                IndividualClientData.objects.create(
                                    client=existing_client,
                                    first_name=first_name,
                                    last_name=last_name,
                                    middle_name=middle_name if middle_name else None
                                )
                        else:  # legal_entity
                            try:
                                legal_data = existing_client.legal_entity_data
                                legal_data.company_name = full_name
                                legal_data.save()
                            except:
                                LegalEntityClientData.objects.create(
                                    client=existing_client,
                                    company_name=full_name
                                )
                        
                        # Обновляем или добавляем дополнительные телефоны
                        if normalized_phone2:
                            phone2_obj, created = ClientPhone.objects.get_or_create(
                                client=existing_client,
                                phone=normalized_phone2,
                                defaults={
                                    'is_primary': False,
                                    'description': "Дополнительный номер",
                                    'created_by': admin_user,
                                    'modified_by': admin_user
                                }
                            )
                        
                        # Обновляем или добавляем адрес/город
                        if city:
                            address_obj, created = ClientAddress.objects.get_or_create(
                                client=existing_client,
                                is_primary=True,
                                defaults={
                                    'city': city,
                                    'address': None,
                                    'comment': None
                                }
                            )
                            if not created:
                                address_obj.city = city
                                address_obj.save()
                        
                        imported_count += 1
                        continue

                    # Создаем клиента
                    client = Client.objects.create(
                        client_type=client_type,
                        name=full_name,
                        first_name=first_name,
                        last_name=last_name,
                        middle_name=middle_name,
                        email=email if email else None,
                        created_by=admin_user,
                        modified_by=admin_user
                    )

                    # Создаем дополнительные данные в зависимости от типа
                    if client_type == 'individual':
                        IndividualClientData.objects.create(
                            client=client,
                            first_name=first_name,
                            last_name=last_name,
                            middle_name=middle_name if middle_name else None
                        )
                    else:  # legal_entity
                        LegalEntityClientData.objects.create(
                            client=client,
                            company_name=full_name
                        )

                    # Добавляем телефоны
                    if normalized_phone:
                        ClientPhone.objects.create(
                            client=client,
                            phone=normalized_phone,
                            is_primary=True,
                            created_by=admin_user,
                            modified_by=admin_user
                        )

                    if normalized_phone2:
                        ClientPhone.objects.create(
                            client=client,
                            phone=normalized_phone2,
                            is_primary=False,
                            description="Дополнительный номер",
                            created_by=admin_user,
                            modified_by=admin_user
                        )

                    # Добавляем адрес/город как primary адрес, если указан
                    if city:
                        ClientAddress.objects.create(
                            client=client,
                            city=city,
                            address=None,
                            comment=None,
                            is_primary=True
                        )

                    imported_count += 1

                except Exception as e:
                    errors.append(f'Строка {index + 2}: {str(e)}')
                    skipped_count += 1
        
        # Удаляем временный файл
        default_storage.delete(file_path)
        
        # Формируем результат
        result = {
            'status': 'success',
            'message': 'Импорт завершен',
            'imported': imported_count,
            'skipped': skipped_count,
            'duplicate_names': duplicate_names,
            'duplicate_phones': duplicate_phones,
            'empty_rows': empty_rows,
            'invalid_type': invalid_type,
            'errors': errors[:10] if errors else []  # Показываем только первые 10 ошибок
        }
        
        return JsonResponse(result)
        
    except Exception as e:
        # Удаляем временный файл в случае ошибки
        if 'file_path' in locals():
            default_storage.delete(file_path)
        
        logger.error(f'Ошибка импорта Excel: {str(e)}', exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка импорта: {str(e)}'
        })
