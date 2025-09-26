from io import BytesIO
import json
import logging
from django.core.files import File


import qrcode
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import Count, Sum, Q, Avg
from django.http import Http404, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django_daraja.mpesa.core import MpesaClient
from rest_framework.decorators import api_view

from .models import Ticket, TicketScan, Payment, Event

logger = logging.getLogger(__name__)


def index(request):
    return render(request, 'index.html')

def TicketShop(request):
    return render(request, 'events/TicketShop.html')

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

def Kolacopia3(request):
    return render(request, 'events/Kolacopia3.html')

def ContactUs(request):
    return render(request, 'ContactUs.html')

def test(request):
    return render(request, 'test.html')


def payment_pending(request):
    # Get data from session
    pending_data = request.session.get('pending_payment', {})
    ticket_ids = request.session.get('pending_ticket_ids', [])

    context = {
        'full_name': pending_data.get('full_name', 'Customer'),
        'email': pending_data.get('email', ''),
        'amount': pending_data.get('amount', 0),
        'phone': pending_data.get('phone', ''),
        'ticket_count': pending_data.get('ticket_count', 1),
        'stk_success': pending_data.get('stk_success', False),
        'ticket_ids': ticket_ids
    }

    return render(request, 'ticket_forms/payment_pending.html', context)
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


def TicketForm(request):
    """
    Creates one Ticket object per seat purchased.
    Saves each ticket's QR into MEDIA and sends them as email attachments
    with the unique code shown directly below the QR code in each attachment.
    """
    if request.method == "POST":
        full_name = request.POST.get('ticket-form-name')
        email = request.POST.get('ticket-form-email')
        phone = request.POST.get('ticket-form-phone')
        ticket_type = request.POST.get('TicketForm')  # e.g. "earlyBird"
        number_of_tickets = int(request.POST.get('ticket-form-number') or 1)
        message = request.POST.get('ticket-form-message', '')
        payment_method = request.POST.get('paymentMethod')
        mpesa_number = request.POST.get('mpesaNumber')

        # ✅ Map ticket types to their prices
        ticket_prices = {
            "earlyBird": 500,
            "regular": 1000,
            "vip": 2000,
        }

        ticket_price = ticket_prices.get(ticket_type, 0)  # default 0 if invalid
        purchase_total = ticket_price * number_of_tickets


        triggerSTK(mpesa_number, 1)

        created_tickets = []

        for i in range(number_of_tickets):
            t = Ticket.objects.create(
                full_name=full_name,
                email=email,
                phone=phone,
                ticket_type=ticket_type,
                ticket_price=ticket_price,
                number_of_tickets=1,
                total_price=ticket_price,
                message=message,
                payment_method=payment_method,
                mpesa_number=mpesa_number,
            )

            # Generate QR code
            verify_url = request.build_absolute_uri(
                reverse('verify-ticket', kwargs={'ticket_id': t.id})
            )
            qr_img = qrcode.make(verify_url)
            buffer = BytesIO()
            qr_img.save(buffer, format='PNG')
            buffer.seek(0)

            # Save QR code to media
            t.qr_code.save(f"ticket_{t.id}.png", File(buffer), save=True)
            buffer.seek(0)
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

        # Attach each QR code with unique code below it
        for t in created_tickets:
            qr_buffer = BytesIO()
            qr_img = qrcode.make(
                request.build_absolute_uri(reverse('verify-ticket', kwargs={'ticket_id': t.id}))
            )
            qr_img.save(qr_buffer, format='PNG')
            qr_buffer.seek(0)
            attachment_name = f"Ticket_{t.unique_code}.png"
            msg.attach(attachment_name, qr_buffer.getvalue(), 'image/png')

        msg.send(fail_silently=False)

        # Redirect to ticket_success
        last_ticket = created_tickets[-1]
        success_url = reverse('ticket-success', kwargs={'ticket_id': last_ticket.id})
        return redirect(f"{success_url}?count={number_of_tickets}")

    return render(request, 'ticket_forms/TicketForm.html')

def triggerSTK(phone, amount):
    cl = MpesaClient()
    phone_number = phone
    amount = 1
    account_reference = 'reference'
    transaction_desc = 'Payment of the amazing show'
    # ngrok http --url=frog-knowing-mole.ngrok-free.app 7000
    callback_url = 'https://f5831ea1fe8e.ngrok-free.app /call-back/ggdudud/ggfsg'
    response = cl.stk_push(phone_number, amount, account_reference, transaction_desc, callback_url)
    mrid =response.merchant_request_id
    crid = response.checkout_request_id
    Payment.objects.create(merchantId=mrid, checkoutId=crid, phone=phone_number)
    print(mrid, crid)
    # saving
    return response

@api_view(['POST'])
def handleMpesaResponse(request):
    json_data = request.data
    logger.info(f"M-Pesa Callback received: {json_data}")
    
    try:
        result_code = json_data['Body']['stkCallback']['ResultCode']
        merchant_request_id = json_data['Body']['stkCallback']['MerchantRequestID']
        checkout_request_id = json_data['Body']['stkCallback']['CheckoutRequestID']
    except KeyError as e:
        logger.error(f"M-Pesa callback missing key: {e}")
        return JsonResponse({'error': f'Invalid callback data, missing {e}'}, status=400)

    try:
        payment = Payment.objects.get(merchantId=merchant_request_id, checkoutId=checkout_request_id)
    except Payment.DoesNotExist:
        logger.error(f"Payment not found for MerchantRequestID: {merchant_request_id}")
        return JsonResponse({'error': 'Payment record not found.'}, status=404)

    if result_code == 0:
        payment.isSuccessful = True
        payment.save()

        tickets = payment.tickets.all()
        if not tickets:
            logger.warning(f"No tickets found for successful payment: {payment.id}")
            return JsonResponse({'error': 'No tickets found for this payment.'})

        with transaction.atomic():
            for ticket in tickets:
                ticket.status = 'active'
                verify_url = request.build_absolute_uri(reverse('verify_ticket_code', kwargs={'code': ticket.unique_code}))
                qr_img = qrcode.make(verify_url)
                buffer = BytesIO()
                qr_img.save(buffer, format='PNG')
                file_name = f'qr_{ticket.unique_code}.png'
                ticket.qr_code.save(file_name, ContentFile(buffer.getvalue()), save=True)

        first_ticket = tickets.first()
        if first_ticket.event:
            email_subject = f"🎉 Your Tickets for {first_ticket.event.name}! 🎉"
        else:
            email_subject = "🎉 Your Tickets are Here! 🎉"
            
        email_body = f'''
            <div style="font-family: Arial, sans-serif; text-align: center; padding: 18px;">
                <h2 style="color:#28a745; margin-bottom:6px;">🎉 Congratulations {first_ticket.full_name}! 🎉</h2>
                <p style="margin-top:0; color:#333;">
                    You purchased <strong>{tickets.count()}</strong> ticket(s). 
                    Please find the QR codes attached below — present either at the gate.
                </p>
                <p style="font-size:12px; color:#999; margin-top:12px;">Total paid: KES {payment.amount}</p>
            </div>
        '''
        msg = EmailMultiAlternatives(
            subject=email_subject,
            body="Please open in an HTML-capable email client to view your ticket(s).",
            from_email=settings.EMAIL_HOST_USER,
            to=[first_ticket.email],
        )
        msg.attach_alternative(email_body, "text/html")

        for ticket in tickets:
            if ticket.qr_code:
                with open(ticket.qr_code.path, 'rb') as f:
                    file_data = f.read()
                attachment_name = f"Ticket_{ticket.unique_code}.png"
                msg.attach(attachment_name, file_data, 'image/png')
        
        try:
            msg.send(fail_silently=False)
        except Exception as e:
            logger.exception(f"Failed to send ticket email for payment {payment.id}: {e}")

    else:
        try:
            payment.ResultDesc = json_data['Body']['stkCallback']['ResultDesc']
        except KeyError:
            payment.ResultDesc = "Failed with no description."
        payment.save()
        payment.tickets.update(status='cancelled')

    return JsonResponse({'success': 'Callback received.'})


# ... (The rest of the views like Scanner, admin_dashboard, etc. remain the same) ...

def Scanner(request):
    """
    Handles the scanner page, which shows scan statistics, allows for scanning
    tickets, and displays a filterable log of recent scans.
    """
    now = timezone.now()
    today = now.date()
    week_start = today - timezone.timedelta(days=today.weekday())

    stats = {
        'total_scans': TicketScan.objects.count(),
        'today_scans': TicketScan.objects.filter(scanned_at__date=today).count(),
        'week_scans': TicketScan.objects.filter(scanned_at__date__gte=week_start).count(),
    }

    logs = TicketScan.objects.select_related('ticket').order_by('-scanned_at')

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    scanned_by = request.GET.get('scanned_by', '').strip()

    if start_date:
        logs = logs.filter(scanned_at__date__gte=start_date)
    if end_date:
        logs = logs.filter(scanned_at__date__lte=end_date)
    if scanned_by:
        logs = logs.filter(scanned_by__icontains=scanned_by)

    context = {
        'stats': stats,
        'logs': logs,
        'request': request,
    }
    return render(request, 'scanner/Scanner.html', context)


@require_http_methods(["GET"])
def verify_ticket(request, ticket_id):
    """User endpoint: GET this URL to check if a ticket is valid (without marking it used)."""
    try:
        ticket = Ticket.objects.get(id=ticket_id)
        if ticket.is_used:
            return JsonResponse({"status": "checked", "message": "ℹ️ This ticket has already been used."})
        elif ticket.status != 'active':
            return JsonResponse({"status": "checked", "message": f"️ Ticket is not active (status: {ticket.status})."})
        else:
            return JsonResponse({"status": "checked", "message": "✅ This ticket is valid and has not been used yet."})
    except Ticket.DoesNotExist:
        return JsonResponse({"status": "error", "message": "❌ Invalid Ticket!"})


@require_http_methods(["GET"])
def verify_ticket_code(request, code):
    """User endpoint: GET this URL to check a ticket by code (without marking it used)."""
    try:
        ticket = Ticket.objects.get(unique_code=code)
        if ticket.is_used:
            return JsonResponse({"status": "checked", "message": "ℹ️ This ticket has already been used."})
        elif ticket.status != 'active':
            return JsonResponse({"status": "checked", "message": f"️ Ticket is not active (status: {ticket.status})."})
        else:
            return JsonResponse({"status": "checked", "message": "✅ This ticket is valid and has not been used yet."})
    except Ticket.DoesNotExist:
        return JsonResponse({"status": "error", "message": "❌ Invalid Ticket Code!"})


@require_http_methods(["POST"])
def scan_ticket(request, ticket_id):
    """Scanner endpoint: POST to this URL to mark a ticket as used."""
    try:
        ticket = Ticket.objects.get(id=ticket_id)
    except Ticket.DoesNotExist:
        return JsonResponse({"status": "error", "message": "❌ Invalid Ticket!"})

    with transaction.atomic():
        if not ticket.is_valid_for_scan():
            TicketScan.objects.create(ticket=ticket, status="duplicate", scanned_by="Scanner")
            return JsonResponse({
                "status": "error",
                "message": f"❌ Ticket not valid! Status: {ticket.get_status_display()}, Used: {ticket.is_used}",
            })

        ticket.is_used = True
        ticket.save()
        TicketScan.objects.create(ticket=ticket, status="success", scanned_by="Scanner")
        return JsonResponse(
            {"status": "success", "message": f"✅ Ticket valid for {ticket.full_name} ({ticket.ticket_type})"})


@require_http_methods(["POST"])
def scan_ticket_code(request, code):
    """Scanner endpoint: POST to this URL to mark a ticket as used by its code."""
    try:
        ticket = Ticket.objects.get(unique_code=code)
    except Ticket.DoesNotExist:
        return JsonResponse({"status": "error", "message": "❌ Invalid Ticket Code!"})

    with transaction.atomic():
        if not ticket.is_valid_for_scan():
            TicketScan.objects.create(ticket=ticket, status="duplicate", scanned_by="Scanner")
            return JsonResponse({
                "status": "error",
                "message": f"❌ Ticket not valid! Status: {ticket.get_status_display()}, Used: {ticket.is_used}",
            })

        ticket.is_used = True
        ticket.save()
        TicketScan.objects.create(ticket=ticket, status="success", scanned_by="Scanner")
        return JsonResponse(
            {"status": "success", "message": f"✅ Ticket valid for {ticket.full_name} ({ticket.ticket_type})"})


@staff_member_required(login_url='/admin/login/')
def admin_dashboard(request):
    """Admin dashboard view with comprehensive event analytics"""
    now = timezone.now()
    today = now.date()

    total_tickets = Ticket.objects.count() or 0
    used_tickets = Ticket.objects.filter(is_used=True).count() or 0
    unused_tickets = Ticket.objects.filter(is_used=False).count() or 0

    ticket_type_stats = []
    for stat in Ticket.objects.values('ticket_type').annotate(
            count=Count('id'),
            used=Count('id', filter=Q(is_used=True)),
            revenue=Sum('ticket_price', filter=Q(is_used=True)),
            avg_price=Avg('ticket_price')
    ):
        count = stat.get('count', 0) or 0
        used = stat.get('used', 0) or 0
        revenue = stat.get('revenue', 0) or 0
        avg_price = stat.get('avg_price', 0) or 0

        stat['pending'] = count - used
        stat['usage_rate'] = (used / count * 100) if count > 0 else 0
        ticket_type_stats.append(stat)

    recent_scans = TicketScan.objects.select_related('ticket').order_by('-scanned_at')[:50]
    total_scans = TicketScan.objects.count() or 0
    successful_scans = TicketScan.objects.filter(status='success').count() or 0
    failed_scans = TicketScan.objects.filter(status='failed').count() or 0

    scan_success_rate = (successful_scans / total_scans * 100) if total_scans > 0 else 0

    from django.db.models.functions import TruncDate
    daily_stats = []
    for stat in TicketScan.objects.annotate(
            date=TruncDate('scanned_at')
    ).values('date').annotate(
        total=Count('id'),
        success=Count('id', filter=Q(status='success')),
        failed=Count('id', filter=Q(status='failed'))
    ).order_by('-date')[:7]:
        stat['total'] = stat.get('total', 0) or 0
        stat['success'] = stat.get('success', 0) or 0
        stat['failed'] = stat.get('failed', 0) or 0
        daily_stats.append(stat)

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
        total = revenue.get('total', 0) or 0
        collected = revenue.get('collected', 0) or 0

        revenue['pending'] = total - collected
        revenue['collection_rate'] = (collected / total * 100) if total > 0 else 0
        revenue_by_type.append(revenue)

    total_attendees = Ticket.objects.values('email').distinct().count() or 0
    attended_attendees = Ticket.objects.filter(is_used=True).values('email').distinct().count() or 0
    expected_attendees = total_attendees - attended_attendees

    attendance_rate = (attended_attendees / total_attendees * 100) if total_attendees > 0 else 0

    avg_tickets_result = Ticket.objects.values('email').annotate(
        ticket_count=Count('id')
    ).aggregate(avg=Avg('ticket_count'))
    avg_tickets_per_attendee = avg_tickets_result['avg'] or 0

    tickets_today = Ticket.objects.filter(created_at__date=today).count() or 0
    scans_today = TicketScan.objects.filter(scanned_at__date=today).count() or 0

    revenue_today_result = Ticket.objects.filter(created_at__date=today).aggregate(
        total=Sum('ticket_price')
    )
    revenue_today = revenue_today_result['total'] or 0

    context = {
        'total_tickets': total_tickets,
        'used_tickets': used_tickets,
        'unused_tickets': unused_tickets,
        'usage_percentage': (used_tickets / total_tickets * 100) if total_tickets > 0 else 0,
        'ticket_type_stats': ticket_type_stats,
        'recent_scans': recent_scans,
        'daily_stats': daily_stats,
        'total_scans': total_scans,
        'successful_scans': successful_scans,
        'failed_scans': failed_scans,
        'scan_success_rate': scan_success_rate,
        'total_revenue': total_revenue,
        'projected_revenue': projected_revenue,
        'revenue_by_type': revenue_by_type,
        'revenue_today': revenue_today,
        'total_attendees': total_attendees,
        'attended_attendees': attended_attendees,
        'expected_attendees': expected_attendees,
        'attendance_rate': attendance_rate,
        'avg_tickets_per_attendee': avg_tickets_per_attendee,
        'tickets_today': tickets_today,
        'scans_today': scans_today,
        'current_time': now,
    }

    return render(request, 'admin/admin-dashboard.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def api_validate_ticket(request):
    if not request.body:
        return JsonResponse({'status': 'error', 'message': 'No data received.'}, status=400)

    try:
        data = json.loads(request.body)
        scanned_code = data.get('code', '').strip().upper()
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON.'}, status=400)

    if not scanned_code:
        return JsonResponse({'status': 'error', 'message': 'No ticket code provided.'}, status=400)

    try:
        ticket = Ticket.objects.get(unique_code=scanned_code)
    except Ticket.DoesNotExist:
        return JsonResponse({"status": "error", "message": "❌ Invalid Ticket Code!"})

    with transaction.atomic():
        if not ticket.is_valid_for_scan():
            TicketScan.objects.create(ticket=ticket, status="duplicate", scanned_by="Scanner")
            return JsonResponse({
                "status": "error",
                "message": f"❌ Ticket not valid! Status: {ticket.get_status_display()}, Used: {ticket.is_used}",
            })
        else:
            ticket.is_used = True
            ticket.save()
            
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
