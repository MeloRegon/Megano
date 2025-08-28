from django.contrib import admin
from .models import Avatar, Profile

@admin.register(Avatar)
class AvatarAdmin(admin.ModelAdmin):
    list_display = ('src', 'alt')

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'email', 'phone', 'balance', 'avatar')
    search_fields = ('full_name', 'email', 'phone')
