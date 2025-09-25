#from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from django.contrib.sitemaps.views import sitemap

from Kola_app import views
from Kola_app.sitemaps import EventSitemap

sitemaps = {
    'events': EventSitemap,
}
urlpatterns = [

    path("robots.txt", TemplateView.as_view(
        template_name="robots.txt", content_type="text/plain"
    )),
    path('', views.index, name='Home-page'),

    path('TicketStop', views.TicketStop, name='TicketStop-page'),
    path('OurGallery', views.OurGallery, name='OurGallery-page'),
    path('ShopMen', views.ShopMen, name='ShopMen-page'),
    path('TicketForm', views.TicketForm, name='TicketForm-page'),
    path('TicketForm2', views.TicketForm2, name='TicketForm2-page'),
    path('TicketForm3', views.TicketForm3, name='TicketForm3-page'),
    path('TicketForm4', views.TicketForm4, name='TicketForm4-page'),
    path('TicketForm5', views.TicketForm5, name='TicketForm5-page'),
    path('ShopWomen', views.ShopWomen, name='ShopWomen-page'),
    path('AllTickets', views.AllTickets, name='AllTickets-page'),
    path('Kolacopia', views.Kolacopia, name='Kolacopia-page'),
    path('Kolacopia2', views.Kolacopia2, name='Kolacopia2.0-page'),
    path('ProjectKola', views.ProjectKola, name='ProjectKola-page'),
    path('Kolacopia3', views.Kolacopia3, name='Kolacopia3.0-page'),
    path('ContactUs', views.ContactUs, name='ContactUs-page'),
    path('test', views.test, name='test-page'),

    # Ticket success (UUID)
    path('ticket/success/<uuid:ticket_id>/', views.ticket_success, name='ticket-success'),

    # User-facing verification (GET - Safe, doesn't change state)
    path('verify-ticket/<uuid:ticket_id>/', views.verify_ticket, name='verify-ticket'),
    path('verify-ticket/fallback/<str:code>/', views.verify_ticket_code, name='verify-ticket-code'),

    # Scanner-facing endpoint (POST - Changes state, marks ticket used)
    path('scan-ticket/<uuid:ticket_id>/', views.scan_ticket, name='scan-ticket'),
    path('scan-ticket/fallback/<str:code>/', views.scan_ticket_code, name='scan-ticket-code'),

    # Scanner page
    path('Scanner', views.Scanner, name='Scanner-page'),
    path('api/validate_ticket/', views.api_validate_ticket, name='api_validate_ticket'),

    # Mpesa callback
    path('result-data/ggdudud/ggfsg', views.handleMpesaResponse, name='mpesa-call-back-endpoint'),

    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django-sitemap'),

    path("sitemap.xml", TemplateView.as_view(template_name="sitemap.xml", content_type="application/xml")),

    path('admin/', admin.site.urls),


    path('admin-dashboard/', views.admin_dashboard, name='admin-dashboard'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
