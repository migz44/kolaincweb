# from django.contrib import admin
#
# # Register your models here.
# from django.contrib import admin
# from admin_charts.admin import AdminChartMixin
# from .models import TicketScan
#
# @admin.register(TicketScan)
# class TicketScanAdmin(AdminChartMixin, admin.ModelAdmin):
#     list_display = ("ticket", "status", "scanned_at")
#
#     # Define charts
#     chart_settings = [
#         {
#             "label": "Scans per Day",
#             "chart_type": "bar",
#             "date_field": "scanned_at",
#             "aggregate": "count",
#         },
#         {
#             "label": "Scans by Status",
#             "chart_type": "pie",
#             "fields": ["status"],
#         },
#     ]
