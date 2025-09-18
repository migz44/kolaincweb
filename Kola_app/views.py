from io import BytesIO

import qrcode
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import Count, Sum, Q, Avg
from django.db.models.fields import json
from django.http import Http404, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django_daraja.mpesa.core import MpesaClient
from rest_framework.decorators import api_view
from django.http import JsonResponse
from .models import TicketScanLog
from .models import Ticket, TicketScan, Payment


def index(request):
    return render(request, 'index.html')


def TicketStop(request):
    return render(request, 'events/TicketStop.html')


def OurGallery(request):
    return render(request, 'OurGallery.html')


def ShopMen(request):
    return render(request, 'merchandise/ShopMen.html')


def ShopWomen(request):
    return render(request, 'merchandise/ShopWomen.html')


def AllTickets(request):
    return render(request, 'events/AllTickets.html')


def Kolacopia(request):
    return render(request, 'events/Kolacopia.html')


def Kolacopia2(request):
    return render(request, 'events/Kolacopia2.html')


def ProjectKola(request):
    return render(request, 'events/ProjectKola.html')


def ContactUs(request):
    return render(request, 'ContactUs.html')


def test(request):
    return render(request, 'test.html')


def TicketForm(request):
    """
    Generates QR codes that link to the validation endpoint using the short unique_code.
    """
    if request.method == "POST":
        full_name = request.POST.get('ticket-form-name')
        email = request.POST.get('ticket-form-email')
        phone = request.POST.get('ticket-form-phone')
        ticket_type_key = request.POST.get('TicketForm')
        number_of_tickets = int(request.POST.get('ticket-form-number') or 1)
        message = request.POST.get('ticket-form-message', '')
        payment_method = request.POST.get('paymentMethod')
        mpesa_number = request.POST.get('mpesaNumber')

        TICKET_PRICES = {
            'earlyBird': 1500,
            'standard': 2000,
            'gate': 2500,
        }
        ticket_price = TICKET_PRICES.get(ticket_type_key, 0)
        purchase_total = ticket_price * number_of_tickets

        # Initiate payment
        triggerSTK(mpesa_number, purchase_total)
        created_tickets = []

        for i in range(number_of_tickets):
            # Create the ticket. The save() method will generate the unique_code and QR code.
            t = Ticket.objects.create(
                full_name=full_name,
                email=email,
                phone=phone,
                ticket_type=ticket_type_key,
                ticket_price=ticket_price,
                number_of_tickets=1,
                total_price=ticket_price,
                message=message,
                payment_method=payment_method,
                mpesa_number=mpesa_number,
            )
            created_tickets.append(t)

        # Send email with attachments
        email_subject = "🎉 Your Tickets for WeWannaParty 🎉"
        email_body = f"""
            <div style="font-family: Arial, sans-serif; text-align: center; padding: 18px;">
                <h2 style="color:#28a745; margin-bottom:6px;">🎉 Congratulations {full_name}! 🎉</h2>
                <p style="margin-top:0; color:#333;">
                    You purchased <strong>{number_of_tickets}</strong> ticket(s). 
                    Please find the QR codes attached below — present either at the gate.
                </p>
                <p style="font-size:12px; color:#999; margin-top:12px;">Total paid: KES {purchase_total}</p>
            </div>
        """

        msg = EmailMultiAlternatives(
            subject=email_subject,
            body="Please open in an HTML-capable email client to view the ticket(s).",
            from_email=settings.EMAIL_HOST_USER,
            to=[email],
        )
        msg.attach_alternative(email_body, "text/html")

        # Attach each QR code. The QR code is now saved to the model automatically.
        for t in created_tickets:
            if t.qr_code: # Check if the QR code was generated and saved
                # Read the file from the storage and attach it
                with open(t.qr_code.path, 'rb') as f:
                    file_data = f.read()
                attachment_name = f"Ticket_{t.unique_code}.png"
                msg.attach(attachment_name, file_data, 'image/png')
            else:
                # Fallback: Generate a simple QR code if something went wrong
                print(f"Warning: QR code not found for ticket {t.unique_code}. Generating fallback.")
                verify_url = request.build_absolute_uri(reverse('verify_ticket_code', kwargs={'code': t.unique_code}))
                qr_img = qrcode.make(verify_url)
                buffer = BytesIO()
                qr_img.save(buffer, format='PNG')
                buffer.seek(0)
                attachment_name = f"Ticket_{t.unique_code}.png"
                msg.attach(attachment_name, buffer.getvalue(), 'image/png')

        msg.send(fail_silently=False)

        # Redirect to ticket_success
        last_ticket = created_tickets[-1]
        success_url = reverse('ticket-success', kwargs={'ticket_id': last_ticket.id})
        return redirect(f"{success_url}?count={number_of_tickets}")

    return render(request, 'ticket_forms/TicketForm.html')

def TicketForm2(request):
    """
    Generates QR codes that link to the validation endpoint using the short unique_code.
    """
    if request.method == "POST":
        full_name = request.POST.get('ticket-form-name')
        email = request.POST.get('ticket-form-email')
        phone = request.POST.get('ticket-form-phone')
        ticket_type_key = request.POST.get('TicketForm')
        number_of_tickets = int(request.POST.get('ticket-form-number') or 1)
        message = request.POST.get('ticket-form-message', '')
        payment_method = request.POST.get('paymentMethod')
        mpesa_number = request.POST.get('mpesaNumber')

        TICKET_PRICES = {
            'earlyBird': 1500,
            'standard': 2000,
            'gate': 2500,
        }
        ticket_price = TICKET_PRICES.get(ticket_type_key, 0)
        purchase_total = ticket_price * number_of_tickets

        # Initiate payment
        triggerSTK(mpesa_number, purchase_total)
        created_tickets = []

        for i in range(number_of_tickets):
            # Create the ticket. The save() method will generate the unique_code and QR code.
            t = Ticket.objects.create(
                full_name=full_name,
                email=email,
                phone=phone,
                ticket_type=ticket_type_key,
                ticket_price=ticket_price,
                number_of_tickets=1,
                total_price=ticket_price,
                message=message,
                payment_method=payment_method,
                mpesa_number=mpesa_number,
            )
            created_tickets.append(t)

        # Send email with attachments
        email_subject = "🎉 Your Tickets for WannaParty 🎉"
        email_body = f"""
            <div style="font-family: Arial, sans-serif; text-align: center; padding: 18px;">
                <h2 style="color:#28a745; margin-bottom:6px;">🎉 Congratulations {full_name}! 🎉</h2>
                <p style="margin-top:0; color:#333;">
                    You purchased <strong>{number_of_tickets}</strong> ticket(s). 
                    Please find the QR codes attached below — present either at the gate.
                </p>
                <p style="font-size:12px; color:#999; margin-top:12px;">Total paid: KES {purchase_total}</p>
            </div>
        """

        msg = EmailMultiAlternatives(
            subject=email_subject,
            body="Please open in an HTML-capable email client to view the ticket(s).",
            from_email=settings.EMAIL_HOST_USER,
            to=[email],
        )
        msg.attach_alternative(email_body, "text/html")

        # Attach each QR code. The QR code is now saved to the model automatically.
        for t in created_tickets:
            if t.qr_code: # Check if the QR code was generated and saved
                # Read the file from the storage and attach it
                with open(t.qr_code.path, 'rb') as f:
                    file_data = f.read()
                attachment_name = f"Ticket_{t.unique_code}.png"
                msg.attach(attachment_name, file_data, 'image/png')
            else:
                # Fallback: Generate a simple QR code if something went wrong
                print(f"Warning: QR code not found for ticket {t.unique_code}. Generating fallback.")
                verify_url = request.build_absolute_uri(reverse('verify_ticket_code', kwargs={'code': t.unique_code}))
                qr_img = qrcode.make(verify_url)
                buffer = BytesIO()
                qr_img.save(buffer, format='PNG')
                buffer.seek(0)
                attachment_name = f"Ticket_{t.unique_code}.png"
                msg.attach(attachment_name, buffer.getvalue(), 'image/png')

        msg.send(fail_silently=False)

        # Redirect to ticket_success
        last_ticket = created_tickets[-1]
        success_url = reverse('ticket-success', kwargs={'ticket_id': last_ticket.id})
        return redirect(f"{success_url}?count={number_of_tickets}")

    return render(request, 'ticket_forms/TicketForm2.html')

def TicketForm3(request):
    """
    Generates QR codes that link to the validation endpoint using the short unique_code.
    """
    if request.method == "POST":
        full_name = request.POST.get('ticket-form-name')
        email = request.POST.get('ticket-form-email')
        phone = request.POST.get('ticket-form-phone')
        ticket_type_key = request.POST.get('TicketForm')
        number_of_tickets = int(request.POST.get('ticket-form-number') or 1)
        message = request.POST.get('ticket-form-message', '')
        payment_method = request.POST.get('paymentMethod')
        mpesa_number = request.POST.get('mpesaNumber')

        TICKET_PRICES = {
            'earlyBird': 1500,
            'standard': 2000,
            'gate': 2500,
        }
        ticket_price = TICKET_PRICES.get(ticket_type_key, 0)
        purchase_total = ticket_price * number_of_tickets

        # Initiate payment
        triggerSTK(mpesa_number, purchase_total)
        created_tickets = []

        for i in range(number_of_tickets):
            # Create the ticket. The save() method will generate the unique_code and QR code.
            t = Ticket.objects.create(
                full_name=full_name,
                email=email,
                phone=phone,
                ticket_type=ticket_type_key,
                ticket_price=ticket_price,
                number_of_tickets=1,
                total_price=ticket_price,
                message=message,
                payment_method=payment_method,
                mpesa_number=mpesa_number,
            )
            created_tickets.append(t)

        # Send email with attachments
        email_subject = "🎉 Your Tickets for WannaParty 🎉"
        email_body = f"""
            <div style="font-family: Arial, sans-serif; text-align: center; padding: 18px;">
                <h2 style="color:#28a745; margin-bottom:6px;">🎉 Congratulations {full_name}! 🎉</h2>
                <p style="margin-top:0; color:#333;">
                    You purchased <strong>{number_of_tickets}</strong> ticket(s). 
                    Please find the QR codes attached below — present either at the gate.
                </p>
                <p style="font-size:12px; color:#999; margin-top:12px;">Total paid: KES {purchase_total}</p>
            </div>
        """

        msg = EmailMultiAlternatives(
            subject=email_subject,
            body="Please open in an HTML-capable email client to view the ticket(s).",
            from_email=settings.EMAIL_HOST_USER,
            to=[email],
        )
        msg.attach_alternative(email_body, "text/html")

        # Attach each QR code. The QR code is now saved to the model automatically.
        for t in created_tickets:
            if t.qr_code: # Check if the QR code was generated and saved
                # Read the file from the storage and attach it
                with open(t.qr_code.path, 'rb') as f:
                    file_data = f.read()
                attachment_name = f"Ticket_{t.unique_code}.png"
                msg.attach(attachment_name, file_data, 'image/png')
            else:
                # Fallback: Generate a simple QR code if something went wrong
                print(f"Warning: QR code not found for ticket {t.unique_code}. Generating fallback.")
                verify_url = request.build_absolute_uri(reverse('verify_ticket_code', kwargs={'code': t.unique_code}))
                qr_img = qrcode.make(verify_url)
                buffer = BytesIO()
                qr_img.save(buffer, format='PNG')
                buffer.seek(0)
                attachment_name = f"Ticket_{t.unique_code}.png"
                msg.attach(attachment_name, buffer.getvalue(), 'image/png')

        msg.send(fail_silently=False)

        # Redirect to ticket_success
        last_ticket = created_tickets[-1]
        success_url = reverse('ticket-success', kwargs={'ticket_id': last_ticket.id})
        return redirect(f"{success_url}?count={number_of_tickets}")

    return render(request, 'ticket_forms/TicketForm3.html')

def TicketForm4(request):
    """
    Generates QR codes that link to the validation endpoint using the short unique_code.
    """
    if request.method == "POST":
        full_name = request.POST.get('ticket-form-name')
        email = request.POST.get('ticket-form-email')
        phone = request.POST.get('ticket-form-phone')
        ticket_type_key = request.POST.get('TicketForm')
        number_of_tickets = int(request.POST.get('ticket-form-number') or 1)
        message = request.POST.get('ticket-form-message', '')
        payment_method = request.POST.get('paymentMethod')
        mpesa_number = request.POST.get('mpesaNumber')

        TICKET_PRICES = {
            'earlyBird': 1500,
            'standard': 2000,
            'gate': 2500,
        }
        ticket_price = TICKET_PRICES.get(ticket_type_key, 0)
        purchase_total = ticket_price * number_of_tickets

        # Initiate payment
        triggerSTK(mpesa_number, purchase_total)
        created_tickets = []

        for i in range(number_of_tickets):
            # Create the ticket. The save() method will generate the unique_code and QR code.
            t = Ticket.objects.create(
                full_name=full_name,
                email=email,
                phone=phone,
                ticket_type=ticket_type_key,
                ticket_price=ticket_price,
                number_of_tickets=1,
                total_price=ticket_price,
                message=message,
                payment_method=payment_method,
                mpesa_number=mpesa_number,
            )
            created_tickets.append(t)

        # Send email with attachments
        email_subject = "🎉 Your Tickets for WannaParty 🎉"
        email_body = f"""
            <div style="font-family: Arial, sans-serif; text-align: center; padding: 18px;">
                <h2 style="color:#28a745; margin-bottom:6px;">🎉 Congratulations {full_name}! 🎉</h2>
                <p style="margin-top:0; color:#333;">
                    You purchased <strong>{number_of_tickets}</strong> ticket(s). 
                    Please find the QR codes attached below — present either at the gate.
                </p>
                <p style="font-size:12px; color:#999; margin-top:12px;">Total paid: KES {purchase_total}</p>
            </div>
        """

        msg = EmailMultiAlternatives(
            subject=email_subject,
            body="Please open in an HTML-capable email client to view the ticket(s).",
            from_email=settings.EMAIL_HOST_USER,
            to=[email],
        )
        msg.attach_alternative(email_body, "text/html")

        # Attach each QR code. The QR code is now saved to the model automatically.
        for t in created_tickets:
            if t.qr_code: # Check if the QR code was generated and saved
                # Read the file from the storage and attach it
                with open(t.qr_code.path, 'rb') as f:
                    file_data = f.read()
                attachment_name = f"Ticket_{t.unique_code}.png"
                msg.attach(attachment_name, file_data, 'image/png')
            else:
                # Fallback: Generate a simple QR code if something went wrong
                print(f"Warning: QR code not found for ticket {t.unique_code}. Generating fallback.")
                verify_url = request.build_absolute_uri(reverse('verify_ticket_code', kwargs={'code': t.unique_code}))
                qr_img = qrcode.make(verify_url)
                buffer = BytesIO()
                qr_img.save(buffer, format='PNG')
                buffer.seek(0)
                attachment_name = f"Ticket_{t.unique_code}.png"
                msg.attach(attachment_name, buffer.getvalue(), 'image/png')

        msg.send(fail_silently=False)

        # Redirect to ticket_success
        last_ticket = created_tickets[-1]
        success_url = reverse('ticket-success', kwargs={'ticket_id': last_ticket.id})
        return redirect(f"{success_url}?count={number_of_tickets}")

    return render(request, 'ticket_forms/TicketForm4.html')

def TicketForm5(request):
    """
    Generates QR codes that link to the validation endpoint using the short unique_code.
    """
    if request.method == "POST":
        full_name = request.POST.get('ticket-form-name')
        email = request.POST.get('ticket-form-email')
        phone = request.POST.get('ticket-form-phone')
        ticket_type_key = request.POST.get('TicketForm')
        number_of_tickets = int(request.POST.get('ticket-form-number') or 1)
        message = request.POST.get('ticket-form-message', '')
        payment_method = request.POST.get('paymentMethod')
        mpesa_number = request.POST.get('mpesaNumber')

        TICKET_PRICES = {
            'earlyBird': 1500,
            'standard': 2000,
            'gate': 2500,
        }
        ticket_price = TICKET_PRICES.get(ticket_type_key, 0)
        purchase_total = ticket_price * number_of_tickets

        # Initiate payment
        triggerSTK(mpesa_number, purchase_total)
        created_tickets = []

        for i in range(number_of_tickets):
            # Create the ticket. The save() method will generate the unique_code and QR code.
            t = Ticket.objects.create(
                full_name=full_name,
                email=email,
                phone=phone,
                ticket_type=ticket_type_key,
                ticket_price=ticket_price,
                number_of_tickets=1,
                total_price=ticket_price,
                message=message,
                payment_method=payment_method,
                mpesa_number=mpesa_number,
            )
            created_tickets.append(t)

        # Send email with attachments
        email_subject = "🎉 Your Tickets for WannaParty 🎉"
        email_body = f"""
            <div style="font-family: Arial, sans-serif; text-align: center; padding: 18px;">
                <h2 style="color:#28a745; margin-bottom:6px;">🎉 Congratulations {full_name}! 🎉</h2>
                <p style="margin-top:0; color:#333;">
                    You purchased <strong>{number_of_tickets}</strong> ticket(s). 
                    Please find the QR codes attached below — present either at the gate.
                </p>
                <p style="font-size:12px; color:#999; margin-top:12px;">Total paid: KES {purchase_total}</p>
            </div>
        """

        msg = EmailMultiAlternatives(
            subject=email_subject,
            body="Please open in an HTML-capable email client to view the ticket(s).",
            from_email=settings.EMAIL_HOST_USER,
            to=[email],
        )
        msg.attach_alternative(email_body, "text/html")

        # Attach each QR code. The QR code is now saved to the model automatically.
        for t in created_tickets:
            if t.qr_code: # Check if the QR code was generated and saved
                # Read the file from the storage and attach it
                with open(t.qr_code.path, 'rb') as f:
                    file_data = f.read()
                attachment_name = f"Ticket_{t.unique_code}.png"
                msg.attach(attachment_name, file_data, 'image/png')
            else:
                # Fallback: Generate a simple QR code if something went wrong
                print(f"Warning: QR code not found for ticket {t.unique_code}. Generating fallback.")
                verify_url = request.build_absolute_uri(reverse('verify_ticket_code', kwargs={'code': t.unique_code}))
                qr_img = qrcode.make(verify_url)
                buffer = BytesIO()
                qr_img.save(buffer, format='PNG')
                buffer.seek(0)
                attachment_name = f"Ticket_{t.unique_code}.png"
                msg.attach(attachment_name, buffer.getvalue(), 'image/png')

        msg.send(fail_silently=False)

        # Redirect to ticket_success
        last_ticket = created_tickets[-1]
        success_url = reverse('ticket-success', kwargs={'ticket_id': last_ticket.id})
        return redirect(f"{success_url}?count={number_of_tickets}")

    return render(request, 'ticket_forms/TicketForm5.html')


def triggerSTK(phone, amount):
    cl = MpesaClient()
    phone_number = phone
    account_reference = 'reference'
    transaction_desc = 'Payment of the amazing show'
    callback_url = 'https://frog-knowing-mole.ngrok-free.app/call-back/ggdudud/ggfsg'
    response = cl.stk_push(phone_number, amount, account_reference, transaction_desc, callback_url)
    mrid = getattr(response, 'merchant_request_id')
    # mrid = response.merchant_request_id
    crid = response.checkout_request_id
    Payment.objects.create(merchardId=mrid, checkoutId=crid, phone=phone_number, amount=amount)
    print(mrid, crid)
    return response


def Scanner(request):
    return render(request, 'scanner/Scanner.html')


# --- User-facing: Check ticket status via UUID (GET - Safe) ---
@require_http_methods(["GET"])
def verify_ticket(request, ticket_id):
    """User endpoint: GET this URL to check if a ticket is valid (without marking it used)."""
    try:
        ticket = Ticket.objects.get(id=ticket_id)
        if ticket.is_used:
            return JsonResponse({"status": "checked", "message": "ℹ️ This ticket has already been used."})
        else:
            return JsonResponse({"status": "checked", "message": "✅ This ticket is valid and has not been used yet."})
    except Ticket.DoesNotExist:
        return JsonResponse({"status": "error", "message": "❌ Invalid Ticket!"})


# --- User-facing: Check ticket status via Code (GET - Safe) ---
@require_http_methods(["GET"])
def verify_ticket_code(request, code):
    """User endpoint: GET this URL to check a ticket by code (without marking it used)."""
    try:
        ticket = Ticket.objects.get(unique_code=code)
        if ticket.is_used:
            return JsonResponse({"status": "checked", "message": "ℹ️ This ticket has already been used."})
        else:
            return JsonResponse({"status": "checked", "message": "✅ This ticket is valid and has not been used yet."})
    except Ticket.DoesNotExist:
        return JsonResponse({"status": "error", "message": "❌ Invalid Ticket Code!"})


# --- Scanner: Mark ticket used via UUID (POST only) ---
@require_http_methods(["POST"])
def scan_ticket(request, ticket_id):
    """Scanner endpoint: POST to this URL to mark a ticket as used."""
    try:
        ticket = Ticket.objects.get(id=ticket_id)
    except Ticket.DoesNotExist:
        return JsonResponse({"status": "error", "message": "❌ Invalid Ticket!"})

    with transaction.atomic():
        updated_count = Ticket.objects.filter(
            id=ticket_id, is_used=False
        ).update(is_used=True)

        if updated_count == 0:
            TicketScan.objects.create(ticket=ticket, status="failed", scanned_by="Scanner")
            return JsonResponse({"status": "error", "message": "❌ Ticket already used!"})
        else:
            TicketScan.objects.create(ticket=ticket, status="success", scanned_by="Scanner")
            return JsonResponse(
                {"status": "success", "message": f"✅ Ticket valid for {ticket.full_name} ({ticket.ticket_type})"})


# --- Scanner: Mark ticket used via Code (POST only) ---
@require_http_methods(["POST"])
def scan_ticket_code(request, code):
    """Scanner endpoint: POST to this URL to mark a ticket as used by its code."""
    try:
        ticket = Ticket.objects.get(unique_code=code)
    except Ticket.DoesNotExist:
        return JsonResponse({"status": "error", "message": "❌ Invalid Ticket Code!"})

    with transaction.atomic():
        updated_count = Ticket.objects.filter(
            unique_code=code, is_used=False
        ).update(is_used=True)

        if updated_count == 0:
            TicketScan.objects.create(ticket=ticket, status="failed", scanned_by="Scanner")
            return JsonResponse({"status": "error", "message": "❌ Ticket already used!"})
        else:
            TicketScan.objects.create(ticket=ticket, status="success", scanned_by="Scanner")
            return JsonResponse(
                {"status": "success", "message": f"✅ Ticket valid for {ticket.full_name} ({ticket.ticket_type})"})


def ticket_success(request, ticket_id):
    try:
        ticket = Ticket.objects.get(id=ticket_id)
    except Ticket.DoesNotExist:
        raise Http404("Ticket not found")

    count = request.GET.get('count')
    try:
        count = int(count) if count else ticket.number_of_tickets
    except Exception:
        count = ticket.number_of_tickets

    return render(request, 'ticket_forms/ticket_success.html', {'ticket': ticket, 'purchased_count': count})


# --- Enhanced Admin Dashboard View ---
@staff_member_required(login_url='/admin/login/')
def admin_dashboard(request):
    """Admin dashboard view with comprehensive event analytics"""
    # Check if user is admin
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('admin:login')

    # Current time for time-based calculations
    now = timezone.now()
    today = now.date()

    # 1. OVERVIEW STATISTICS
    total_tickets = Ticket.objects.count() or 0
    used_tickets = Ticket.objects.filter(is_used=True).count() or 0
    unused_tickets = Ticket.objects.filter(is_used=False).count() or 0

    # 2. TICKET TYPE BREAKDOWN - Enhanced with calculated fields
    ticket_type_stats = []
    for stat in Ticket.objects.values('ticket_type').annotate(
            count=Count('id'),
            used=Count('id', filter=Q(is_used=True)),
            revenue=Sum('ticket_price', filter=Q(is_used=True)),
            avg_price=Avg('ticket_price')
    ):
        # Handle None values safely
        count = stat.get('count', 0) or 0
        used = stat.get('used', 0) or 0
        revenue = stat.get('revenue', 0) or 0
        avg_price = stat.get('avg_price', 0) or 0

        stat['pending'] = count - used
        stat['usage_rate'] = (used / count * 100) if count > 0 else 0
        ticket_type_stats.append(stat)

    # 3. SCAN STATISTICS
    recent_scans = TicketScan.objects.select_related('ticket').order_by('-scanned_at')[:50]
    total_scans = TicketScan.objects.count() or 0
    successful_scans = TicketScan.objects.filter(status='success').count() or 0
    failed_scans = TicketScan.objects.filter(status='failed').count() or 0

    # Calculate scan success rate safely
    scan_success_rate = (successful_scans / total_scans * 100) if total_scans > 0 else 0

    # Daily scan statistics
    from django.db.models.functions import TruncDate
    daily_stats = []
    for stat in TicketScan.objects.annotate(
            date=TruncDate('scanned_at')
    ).values('date').annotate(
        total=Count('id'),
        success=Count('id', filter=Q(status='success')),
        failed=Count('id', filter=Q(status='failed'))
    ).order_by('-date')[:7]:
        # Handle None values
        stat['total'] = stat.get('total', 0) or 0
        stat['success'] = stat.get('success', 0) or 0
        stat['failed'] = stat.get('failed', 0) or 0
        daily_stats.append(stat)

    # 4. REVENUE ANALYTICS - Enhanced with calculated fields
    total_revenue_result = Ticket.objects.aggregate(
        total=Sum('ticket_price'),
        projected=Sum('ticket_price', filter=Q(is_used=True))
    )
    total_revenue = total_revenue_result['total'] or 0
    projected_revenue = total_revenue_result['projected'] or 0

    revenue_by_type = []
    for revenue in Ticket.objects.values('ticket_type').annotate(
            total=Sum('ticket_price'),
            collected=Sum('ticket_price', filter=Q(is_used=True))
    ):
        # Handle None values safely
        total = revenue.get('total', 0) or 0
        collected = revenue.get('collected', 0) or 0

        revenue['pending'] = total - collected
        revenue['collection_rate'] = (collected / total * 100) if total > 0 else 0
        revenue_by_type.append(revenue)

    # 5. ATTENDEE ANALYTICS
    total_attendees = Ticket.objects.values('email').distinct().count() or 0
    attended_attendees = Ticket.objects.filter(is_used=True).values('email').distinct().count() or 0
    expected_attendees = total_attendees - attended_attendees  # Calculate here instead of template

    # Calculate attendance rate safely
    attendance_rate = (attended_attendees / total_attendees * 100) if total_attendees > 0 else 0

    avg_tickets_result = Ticket.objects.values('email').annotate(
        ticket_count=Count('id')
    ).aggregate(avg=Avg('ticket_count'))
    avg_tickets_per_attendee = avg_tickets_result['avg'] or 0

    # 6. TIME-BASED ANALYTICS
    tickets_today = Ticket.objects.filter(created_at__date=today).count() or 0
    scans_today = TicketScan.objects.filter(scanned_at__date=today).count() or 0

    revenue_today_result = Ticket.objects.filter(created_at__date=today).aggregate(
        total=Sum('ticket_price')
    )
    revenue_today = revenue_today_result['total'] or 0

    context = {
        # Overview
        'total_tickets': total_tickets,
        'used_tickets': used_tickets,
        'unused_tickets': unused_tickets,
        'usage_percentage': (used_tickets / total_tickets * 100) if total_tickets > 0 else 0,

        # Ticket Analytics
        'ticket_type_stats': ticket_type_stats,

        # Scan Analytics
        'recent_scans': recent_scans,
        'daily_stats': daily_stats,
        'total_scans': total_scans,
        'successful_scans': successful_scans,
        'failed_scans': failed_scans,
        'scan_success_rate': scan_success_rate,

        # Revenue Analytics
        'total_revenue': total_revenue,
        'projected_revenue': projected_revenue,
        'revenue_by_type': revenue_by_type,
        'revenue_today': revenue_today,

        # Attendee Analytics
        'total_attendees': total_attendees,
        'attended_attendees': attended_attendees,
        'expected_attendees': expected_attendees,  # Added this calculated field
        'attendance_rate': attendance_rate,
        'avg_tickets_per_attendee': avg_tickets_per_attendee,

        # Time-based
        'tickets_today': tickets_today,
        'scans_today': scans_today,

        # Current time for display
        'current_time': now,
    }

    return render(request, 'admin/admin-dashboard.html', context)


@api_view(['POST'])
def handleMpesaResponse(request):
    json_data = request.data
    print(json_data)
    result_code = json_data['Body']['stkCallback']['ResultCode']
    merchardId = json_data['Body']['stkCallback']['MerchardRequestID']
    checkoutId = json_data['Body']['stkCallback']['CheckoutRequestID']
    payment = Payment.objects.get(merchardId=merchardId, checkoutId=checkoutId)

    if result_code == 0:
        print("Success")
        array_data = json_data['Body']['stkCallback']['CallbackMetadata']['Item']
        for data in array_data:
            if data['Name'] == 'Amount':
                amount = data['Value']
            if data['Name'] == 'MpesaReceiptNumber':
                receipt_number = data['Value']
            if data['Name'] == 'Balance':
                balance = data['Value']
            if data['Name'] == 'TransactionDate':
                transaction_date = data['Value']
            if data['Name'] == 'PhoneNumber':
                phone_number = data['Value']
        payment.MpesaReceiptNumber = receipt_number
        payment.MpesaAmount = amount
        payment.MpesaPhoneNumber = phone_number
        payment.isSuccessful = True
        payment.save()
    else:
        print("Failure")
    return JsonResponse({'success': 'Received'})


# views.py (add this new view)

@csrf_exempt
@require_http_methods(["POST"])
def api_validate_ticket(request):
    """
    NEW: Modern API endpoint for the scanner.
    Expects a JSON payload: {'code': 'ABC123DEF'}
    """
    # Check if request contains JSON data
    if not request.body:
        return JsonResponse({'status': 'error', 'message': 'No data received.'}, status=400)

    try:
        data = json.loads(request.body)
        scanned_code = data.get('code', '').strip().upper() # Get code from JSON, clean it
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON.'}, status=400)

    if not scanned_code:
        return JsonResponse({'status': 'error', 'message': 'No ticket code provided.'}, status=400)

    # Now use the existing logic from scan_ticket_code, but enhanced
    try:
        ticket = Ticket.objects.get(unique_code=scanned_code)
    except Ticket.DoesNotExist:
        # Log the failed scan attempt
        TicketScan.objects.create(
            status='failed',
            notes=f"Ticket with code {scanned_code} not found in database."
        )
        return JsonResponse({"status": "error", "message": "❌ Invalid Ticket Code!"})

    with transaction.atomic():
        # Try to mark the ticket as used. This is atomic to prevent race conditions.
        updated_count = Ticket.objects.filter(
            unique_code=scanned_code, is_used=False
        ).update(is_used=True)

        if updated_count == 0:
            # Ticket was already used
            TicketScan.objects.create(ticket=ticket, status="duplicate", scanned_by="Scanner")
            return JsonResponse({
                "status": "error",
                "message": "❌ Ticket already used!",
                "ticket_details": { # Send back info for the scanner UI
                    "full_name": ticket.full_name,
                    "ticket_type": ticket.get_ticket_type_display(),
                }
            })
        else:
            # Ticket was successfully validated and marked used
            TicketScan.objects.create(ticket=ticket, status="success", scanned_by="Scanner")
            return JsonResponse({
                "status": "success",
                "message": f"✅ Entry granted for {ticket.full_name}!",
                "ticket_details": {
                    "full_name": ticket.full_name,
                    "email": ticket.email,
                    "ticket_type": ticket.get_ticket_type_display(),
                }
            })




def log_ticket_scan(request):
    if request.method == "POST":
        ticket_id = request.POST.get("ticket_id")
        status = request.POST.get("status", "valid")

        log = TicketScanLog.objects.create(
            ticket_id=ticket_id,
            status=status,
            scanned_by=request.user.username if request.user.is_authenticated else "anonymous"
        )

        total_scans = TicketScanLog.objects.count()

    return JsonResponse({
            "message": "Scan logged successfully",
            "scan_id": log.id,
            "total_scans": total_scans
        })

