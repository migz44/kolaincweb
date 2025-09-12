from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from Kola_app import views

urlpatterns = [
    path('', views.index, name='Home-page'),

    path('TicketStop', views.TicketStop, name='TicketStop-page'),
    path('OurGallery', views.OurGallery, name='OurGallery-page'),
    path('ShopMen', views.ShopMen, name='ShopMen-page'),
    path('TicketForm', views.TicketForm, name='TicketForm-page'),
    path('ShopWomen', views.ShopWomen, name='ShopWomen-page'),
    path('AllTickets', views.AllTickets, name='AllTickets-page'),
    path('Kolacopia', views.Kolacopia, name='Kolacopia-page'),
    path('Kolacopia2', views.Kolacopia2, name='Kolacopia2.0-page'),
    path('ProjectKola', views.ProjectKola, name='ProjectKola-page'),
    path('ContactUs', views.ContactUs, name='ContactUs-page'),
    path('test', views.test, name='test-page'),

    # Ticket success (UUID)
    path('ticket/success/<uuid:ticket_id>/', views.ticket_success, name='ticket-success'),

    # Scanner & verify endpoints
    path('Scanner', views.Scanner, name='Scanner-page'),
    path('verify-ticket/<uuid:ticket_id>/', views.verify_ticket, name='verify-ticket'),
    path('verify-code/<str:code>/', views.verify_ticket_code, name='verify-ticket-code'),
    path('call-back/ggdudud/ggfsg', views.handleMpesaResponse, name='mpesa-call-back-endpoint'),

    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
