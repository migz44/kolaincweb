import json
from io import BytesIO

import qrcode
from django.conf import settings
from django.core.files import File
from django.core.mail import EmailMultiAlternatives
from django.http import Http404, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django_daraja.mpesa.core import MpesaClient
from requests import Response
from rest_framework.decorators import api_view

from .models import Ticket, TicketScan, Payment


def index(request):
    return render(request, 'index.html')


def TicketStop(request):
    return render(request, 'TicketStop.html')


def OurGallery(request):
    return render(request, 'OurGallery.html')


def ShopMen(request):
    return render(request, 'ShopMen.html')


def ShopWomen(request):
    return render(request, 'ShopWomen.html')


def AllTickets(request):
    return render(request, 'AllTickets.html')


def Kolacopia(request):
    return render(request, 'Kolacopia.html')


def Kolacopia2(request):
    return render(request, 'Kolacopia2.html')


def ProjectKola(request):
    return render(request, 'ProjectKola.html')


def ContactUs(request):
    return render(request, 'ContactUs.html')


def test(request):
    return render(request, 'test.html')




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
        ticket_type = request.POST.get('TicketForm')
        number_of_tickets = int(request.POST.get('ticket-form-number') or 1)
        message = request.POST.get('ticket-form-message', '')
        payment_method = request.POST.get('paymentMethod')
        mpesa_number = request.POST.get('mpesaNumber')
        ticket_price = int(ticket_type)  # assuming value passed is price
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
            verify_url = request.build_absolute_uri(reverse('verify-ticket', kwargs={'ticket_id': t.id}))
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
            qr_img = qrcode.make(request.build_absolute_uri(reverse('verify-ticket', kwargs={'ticket_id': t.id})))
            qr_img.save(qr_buffer, format='PNG')
            qr_buffer.seek(0)
            attachment_name = f"Ticket_{t.unique_code}.png"
            msg.attach(attachment_name, qr_buffer.getvalue(), 'image/png')

        msg.send(fail_silently=False)

        # Redirect to ticket_success
        last_ticket = created_tickets[-1]
        success_url = reverse('ticket-success', kwargs={'ticket_id': last_ticket.id})
        return redirect(f"{success_url}?count={number_of_tickets}")

    return render(request, 'TicketForm.html')


def triggerSTK(phone, amount):
    cl = MpesaClient()
    phone_number = phone
    amount = 1
    account_reference = 'reference'
    transaction_desc = 'Payment of the amazing show'
    # ngrok http --url=frog-knowing-mole.ngrok-free.app 7000
    callback_url = 'https://frog-knowing-mole.ngrok-free.app/call-back/ggdudud/ggfsg'
    response = cl.stk_push(phone_number, amount, account_reference, transaction_desc, callback_url)
    mrid =response.merchant_request_id
    crid = response.checkout_request_id
    Payment.objects.create(merchardId=mrid, checkoutId=crid, phone=phone_number)
    print(mrid, crid)
    # saving
    return response

# --- QR Code Scanner view (keeps original name) ---
def Scanner(request):
    return render(request, 'Scanner.html')


# --- Verify Ticket by UUID (used by QRs) ---
def verify_ticket(request, ticket_id):
    try:
        ticket = Ticket.objects.get(id=ticket_id)
        if ticket.is_used:
            TicketScan.objects.create(ticket=ticket, status="failed")
            return JsonResponse({"status": "error", "message": "❌ Ticket already used!"})
        ticket.is_used = True
        ticket.save()
        TicketScan.objects.create(ticket=ticket, status="success")
        return JsonResponse({"status": "success", "message": f"✅ Ticket valid for {ticket.full_name} ({ticket.ticket_type})"})
    except Ticket.DoesNotExist:
        return JsonResponse({"status": "error", "message": "❌ Invalid Ticket!"})


# --- Verify by unique code (fallback) ---
def verify_ticket_code(request, code):
    try:
        ticket = Ticket.objects.get(unique_code=code)
        if ticket.is_used:
            return JsonResponse({"status": "error", "message": "❌ Ticket already used!"})
        ticket.is_used = True
        ticket.save()
        TicketScan.objects.create(ticket=ticket, status="success")
        return JsonResponse({"status": "success", "message": f"✅ Ticket valid for {ticket.full_name} ({ticket.ticket_type})"})
    except Ticket.DoesNotExist:
        return JsonResponse({"status": "error", "message": "❌ Invalid Ticket Code!"})


def ticket_success(request, ticket_id):
    try:
        ticket = Ticket.objects.get(id=ticket_id)
    except Ticket.DoesNotExist:
        raise Http404("Ticket not found")

    # read optional count from query param
    count = request.GET.get('count')
    try:
        count = int(count) if count else ticket.number_of_tickets
    except Exception:
        count = ticket.number_of_tickets

    return render(request, 'ticket_success.html', {'ticket': ticket, 'purchased_count': count})





@api_view(['POST'])
def handleMpesaResponse(request):
    json_data = request.data
    print(json_data)
    result_code = json_data['Body']['stkCallback']['ResultCode']
    merchardId = json_data['Body']['stkCallback']['MerchantRequestID']
    checkoutId = json_data['Body']['stkCallback']['CheckoutRequestID']
    payment = Payment.objects.get(merchardId=merchardId, checkoutId=checkoutId)

    if result_code == 0:
        print("Success")
        # check if in db
    #     retrieve the data
        array_data=  json_data['Body']['stkCallback']['CallbackMetadata']['Item']
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
        payment.MpesaReceiptNumber=receipt_number
        payment.MpesaAmount=amount
        payment.MpesaPhoneNumber=phone_number
        payment.isSuccessful=True
        payment.save()
    else:
        print("Failure")
    return JsonResponse({'success':'Received'})