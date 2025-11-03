from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager


class Role(models.Model):
    """Роли пользователей (уровни доступа)"""
    name = models.CharField(max_length=50, unique=True, verbose_name='Название')
    description = models.TextField(null=True, blank=True, verbose_name='Описание')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'roles'
        verbose_name = 'Роль'
        verbose_name_plural = 'Роли'

    def __str__(self):
        return self.name


class Position(models.Model):
    """Должности в компании"""
    name = models.CharField(max_length=100, unique=True, verbose_name='Название')
    description = models.TextField(null=True, blank=True, verbose_name='Описание')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'positions'
        verbose_name = 'Должность'
        verbose_name_plural = 'Должности'

    def __str__(self):
        return self.name


class Branch(models.Model):
    """Филиалы компании"""
    name = models.CharField(max_length=255, verbose_name='Название филиала')
    city = models.CharField(max_length=100, verbose_name='Город')
    address = models.CharField(max_length=255, verbose_name='Адрес')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Телефон')
    email = models.EmailField(blank=True, null=True, verbose_name='Email')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'branches'
        verbose_name = 'Филиал'
        verbose_name_plural = 'Филиалы'

    def __str__(self):
        return f"{self.name} ({self.city})"


class UserManager(BaseUserManager):
    """Кастомный менеджер пользователей"""
    
    def create_user(self, email, username, password=None, **extra_fields):
        """Создание обычного пользователя"""
        if not email:
            raise ValueError('Email обязателен')
        
        # Получаем роль по умолчанию
        from apps.accounts.models import Role
        default_role, _ = Role.objects.get_or_create(
            name='operator',
            defaults={'description': 'Оператор'}
        )
        
        extra_fields.setdefault('role', default_role)
        
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, username, password=None, **extra_fields):
        """Создание суперпользователя"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        # Получаем роль admin
        from apps.accounts.models import Role
        admin_role, _ = Role.objects.get_or_create(
            name='admin',
            defaults={'description': 'Администратор системы'}
        )
        extra_fields.setdefault('role', admin_role)
        
        return self.create_user(email, username, password, **extra_fields)


class User(AbstractUser):
    """Расширенная модель пользователя с оргструктурой"""
    first_name = models.CharField(max_length=100, verbose_name='Имя', default='Имя')
    last_name = models.CharField(max_length=100, verbose_name='Фамилия', default='Фамилия')
    middle_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='Отчество')
    email = models.EmailField(unique=True, verbose_name='Email')
    phone = models.CharField(max_length=20, verbose_name='Телефон', default='+7-000-000-0000')
    
    # Связи с оргструктурой
    role = models.ForeignKey(
        Role, 
        on_delete=models.PROTECT, 
        related_name='users',
        verbose_name='Роль'
    )
    position = models.ForeignKey(
        Position, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='users',
        verbose_name='Должность'
    )
    branch = models.ForeignKey(
        Branch, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='users',
        verbose_name='Филиал'
    )
    
    # Иерархия сотрудников
    manager = models.ForeignKey(
        "self", 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="subordinates",
        verbose_name='Начальник'
    )
    
    # Дополнительные поля
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='Аватар')
    bio = models.TextField(max_length=500, blank=True, verbose_name='О себе')
    active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    objects = UserManager()

    class Meta:
        db_table = 'users'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role.name})"

    @property
    def full_name(self):
        """Полное имя с отчеством"""
        if self.middle_name:
            return f"{self.last_name} {self.first_name} {self.middle_name}"
        return f"{self.last_name} {self.first_name}"

    @property
    def short_name(self):
        """Краткое имя"""
        return f"{self.first_name} {self.last_name}"

    def get_subordinates(self):
        """Получить всех подчиненных"""
        return self.subordinates.filter(is_active=True)

    def get_manager_chain(self):
        """Получить цепочку начальников до самого верха"""
        chain = []
        current_manager = self.manager
        while current_manager:
            chain.append(current_manager)
            current_manager = current_manager.manager
        return chain

    def is_manager_of(self, user):
        """Проверить, является ли данный пользователь начальником"""
        return user in self.get_subordinates()

    def can_manage_user(self, user):
        """Проверить, может ли управлять пользователем (прямо или косвенно)"""
        return user in self.get_subordinates() or user == self