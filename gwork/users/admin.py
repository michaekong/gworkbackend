# users/admin.py
from django.contrib import admin
from django.contrib.gis import admin as gis_admin
from django.utils.html import format_html
from .models import User, SeekerProfile, ProviderProfile

@admin.register(User)
class UserAdmin(gis_admin.GISModelAdmin):
    list_display = (
        'email', 'full_name', 'cni_number', 'age', 'sex', 
        'user_type', 'is_verified', 'is_admin_verified', 'cni_preview'
    )
    list_filter = ('user_type', 'is_verified', 'is_admin_verified', 'sex')
    search_fields = ('email', 'first_name', 'last_name', 'cni_number')
    readonly_fields = ('date_joined', 'last_login', 'cni_recto_display', 'cni_verso_display')
    
    fieldsets = (
        ('Informations de connexion', {'fields': ('email', 'password')}),
        ('Identité (À vérifier avec la CNI)', {'fields': ('first_name', 'last_name', 'age', 'sex', 'cni_number')}),
        ('Profil', {'fields': ('user_type', 'phone', 'bio', 'location')}),
        ('Vérifications', {'fields': ('is_verified', 'is_admin_verified')}),
        ('Preuves d\'identité', {'fields': ('cni_recto_display', 'cni_verso_display', 'cni_recto', 'cni_verso')}),
    )

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Nom complet'

    def cni_preview(self, obj):
        if obj.cni_recto and obj.cni_verso:
            return format_html(
                '<a href="{}" target="_blank">Voir CNI</a>', 
                obj.cni_recto.url
            )
        return "Manquant"
    cni_preview.short_description = 'Aperçu CNI'

    def cni_recto_display(self, obj):
        if obj.cni_recto:
            return format_html('<img src="{}" width="300" style="border: 2px solid #ccc; border-radius: 8px;" />', obj.cni_recto.url)
        return "Aucune image"
    cni_recto_display.short_description = 'CNI Recto'

    def cni_verso_display(self, obj):
        if obj.cni_verso:
            return format_html('<img src="{}" width="300" style="border: 2px solid #ccc; border-radius: 8px;" />', obj.cni_verso.url)
        return "Aucune image"
    cni_verso_display.short_description = 'CNI Verso'

@admin.register(SeekerProfile)
class SeekerProfileAdmin(gis_admin.GISModelAdmin):
    list_display = ('user', 'experience_years', 'max_commute_km')

@admin.register(ProviderProfile)
class ProviderProfileAdmin(gis_admin.GISModelAdmin):
    list_display = ('user', 'company_name', 'sector')