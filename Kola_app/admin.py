from django.contrib import admin
from .models import GalleryImage
from .models import EventSchedule


class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ['title', 'upload_date', 'is_active']
    list_filter = ['upload_date', 'is_active']
    search_fields = ['title', 'description']


admin.site.register(GalleryImage, GalleryImageAdmin)


class EventScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'event_number',
        'event_name',
        'event_month',
        'event_location',
        'show_in_catalogue',
        'catalogue_order',  # ADD THIS
        'is_active',
        'display_order'
    ]
    list_filter = [
        'event_month',
        'is_active',
        'event_host',
        'show_in_catalogue'
    ]
    list_editable = [
        'is_active',
        'display_order',
        'show_in_catalogue',
        'catalogue_order'
    ]

    fieldsets = (
        ('Event Information', {
            'fields': ('event_name', 'event_number', 'event_month', 'event_date')
        }),
        ('Event Details', {
            'fields': ('event_location', 'event_host')
        }),
        ('Event Poster', {
            'fields': ('event_poster',),
            'description': 'Poster must be exactly 3328×4160 pixels'
        }),
        ('Catalogue Settings', {
            'fields': ('show_in_catalogue', 'catalogue_order', 'catalogue_link'),
            'classes': ('collapse',),
            'description': 'Settings for events catalogue display'
        }),
        ('Management', {
            'fields': ('is_active', 'display_order'),
            'classes': ('collapse',)
        }),
    )
admin.site.register(EventSchedule, EventScheduleAdmin)