from django.db import models
import uuid
import secrets
import string


def make_unique_code(length: int = 8):
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class Ticket(models.Model):
    TICKET_CHOICES = [
        ('earlyBird', 'Early Bird'),
        ('standard', 'Standard'),
        ('gate', 'Gate'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    ticket_type = models.CharField(max_length=50, choices=TICKET_CHOICES)
    ticket_price = models.IntegerField()
    number_of_tickets = models.IntegerField(default=1)
    total_price = models.IntegerField()
    message = models.TextField(blank=True, null=True)
    payment_method = models.CharField(max_length=20, default='mpesa')
    mpesa_number = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    qr_code = models.ImageField(upload_to='qrcodes/', blank=True, null=True)

    # unique short code for fallback scanning
    unique_code = models.CharField(max_length=12, unique=True, blank=True)
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # ensure unique_code
        if not self.unique_code:
            # try generating until unique (very unlikely collision)
            candidate = make_unique_code(8)
            while Ticket.objects.filter(unique_code=candidate).exists():
                candidate = make_unique_code(8)
            self.unique_code = candidate

        # ensure total_price is set
        if not self.total_price:
            # if someone stored price and count, compute
            self.total_price = (self.ticket_price or 0) * (self.number_of_tickets or 1)

        super().save(*args, **kwargs)

    def mark_as_used(self):
        self.is_used = True
        self.save()

    def __str__(self):
        return f"{self.full_name} - {self.ticket_type} ({self.id})"


class TicketScan(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='scans')
    status = models.CharField(max_length=20, choices=(('success', 'success'), ('failed', 'failed')))
    scanned_at = models.DateTimeField(auto_now_add=True)
    scanned_by = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.ticket} - {self.status} at {self.scanned_at}"


class Payment(models.Model):
    merchardId = models.CharField(unique=True ,max_length=100)
    checkoutId = models.CharField( unique=True, max_length=100)
    phone = models.CharField(max_length=20)
    isSuccessful = models.BooleanField(max_length=20, default=False)
    ResultDesc = models.CharField(max_length=100, null=True)
    MpesaReceiptNumber = models.CharField(unique=True,max_length=100, null=True)
    amount = models.IntegerField(default=0)
    TransactionDate = models.DateTimeField(auto_now_add=True, null=True)
