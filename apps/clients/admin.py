from django.contrib import admin
from .models import (
    Client, IndividualClientData, LegalEntityClientData,
    ClientPhone, ClientAddress, ClientCar
)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'client_type', 'email', 'created_at', 'created_by')
    list_filter = ('client_type', 'created_at')
    search_fields = ('name', 'email', 'first_name', 'last_name')
    readonly_fields = ('created_at', 'modified_at', 'created_by', 'modified_by')
    
    def save_model(self, request, obj, form, change):
        if not change:  # Если создаем новый объект
            obj.created_by = request.user
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(IndividualClientData)
class IndividualClientDataAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'middle_name', 'gender', 'birth_date')
    search_fields = ('first_name', 'last_name', 'iin', 'passport_number')


@admin.register(LegalEntityClientData)
class LegalEntityClientDataAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'bin', 'director_name', 'registration_date')
    search_fields = ('company_name', 'bin', 'tax_number')


@admin.register(ClientPhone)
class ClientPhoneAdmin(admin.ModelAdmin):
    list_display = ('client', 'phone', 'is_primary', 'description')
    list_filter = ('is_primary',)


@admin.register(ClientAddress)
class ClientAddressAdmin(admin.ModelAdmin):
    list_display = ('client', 'city', 'address', 'is_primary')
    list_filter = ('city', 'is_primary')


@admin.register(ClientCar)
class ClientCarAdmin(admin.ModelAdmin):
    list_display = ('client', 'brand', 'model', 'year', 'license_plate', 'is_primary')
    list_filter = ('brand', 'year', 'is_primary')
