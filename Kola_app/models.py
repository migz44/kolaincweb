from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.urls import reverse
from django.utils.text import slugify
import uuid
import secrets
import string
import re

# ----------------- Validators -----------------
def validate_kenyan_phone_number(value):
    pattern = r'^(\+?254|0)?[17]\d{8}$'
    if not re.match(pattern, value):
        raise ValidationError('Enter a valid Kenyan phone number (e.g., 0712345678 or +254712345678)')

def validate_email_domain(value):
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
        raise ValidationError('Enter a valid email address')

def make_unique_code(length: int = 8):
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# ----------------- Event Model -----------------
class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=191, unique=True)
    slug = models.SlugField(max_length=200, unique=True)  # SEO-friendly URL
    description = models.TextField(blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    location = models.CharField(max_length=191, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start_date']

    def __str__(self):
        return self.name

    # Auto-generate slug from name
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    # Sitemap compatibility
    def get_absolute_url(self):
        return reverse('event-detail', kwargs={'slug': self.slug})

# ----------------- Ticket Model -----------------
class Ticket(models.Model):
    TICKET_CHOICES = [
        ('earlyBird', 'Early Bird'),
        ('standard', 'Standard'),
        ('gate', 'Gate'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('card', 'Credit Card'),
        ('cash', 'Cash'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=191, validators=[validate_email_domain], db_index=True)
    phone = models.CharField(max_length=20, validators=[validate_kenyan_phone_number])
    ticket_type = models.CharField(max_length=50, choices=TICKET_CHOICES)
    ticket_price = models.IntegerField()
    number_of_tickets = models.IntegerField(default=1)
    total_price = models.IntegerField()
    message = models.TextField(blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='mpesa')
    mpesa_number = models.CharField(max_length=20, blank=True, validators=[validate_kenyan_phone_number])
    created_at = models.DateTimeField(auto_now_add=True)
    qr_code = models.ImageField(upload_to='qrcodes/', blank=True)
    unique_code = models.CharField(max_length=12, unique=True, blank=True)
    is_used = models.BooleanField(default=False)

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='tickets')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['unique_code']),
            models.Index(fields=['is_used']),
        ]

    def clean(self):
        super().clean()
        if self.payment_method == 'mpesa' and not self.mpesa_number:
            raise ValidationError({'mpesa_number': 'MPesa number is required for MPesa payments'})
        if self.ticket_price and self.number_of_tickets:
            calculated_total = self.ticket_price * self.number_of_tickets
            if self.total_price != calculated_total:
                self.total_price = calculated_total

    def save(self, *args, **kwargs):
        if not self.unique_code:
            candidate = make_unique_code(8)
            while Ticket.objects.filter(unique_code=candidate).exists():
                candidate = make_unique_code(8)
            self.unique_code = candidate
        if not self.total_price and self.ticket_price and self.number_of_tickets:
            self.total_price = self.ticket_price * self.number_of_tickets
        self.full_clean()
        super().save(*args, **kwargs)

    def mark_as_used(self):
        try:
            self.is_used = True
            self.save(update_fields=['is_used'])
            return True
        except Exception as e:
            print(f"Error marking ticket as used: {e}")
            return False

    def is_valid_for_scan(self):
        return not self.is_used

    def __str__(self):
        return f"{self.full_name} - {self.ticket_type} ({self.unique_code})"

# ----------------- TicketScan Model -----------------
class TicketScan(models.Model):
    SCAN_STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('duplicate', 'Duplicate Scan'),
    ]
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='scans')
    status = models.CharField(max_length=20, choices=SCAN_STATUS_CHOICES)
    scanned_at = models.DateTimeField(auto_now_add=True)
    scanned_by = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-scanned_at']
        indexes = [
            models.Index(fields=['scanned_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.ticket.unique_code} - {self.status} at {self.scanned_at}"

    def save(self, *args, **kwargs):
        if not self.scanned_by and hasattr(self, 'request_user'):
            self.scanned_by = self.request_user.username
        super().save(*args, **kwargs)

# ----------------- Payment Model -----------------
class Payment(models.Model):
    merchardId = models.CharField(unique=True, max_length=191)
    checkoutId = models.CharField(unique=True, max_length=191)
    phone = models.CharField(max_length=20)
    isSuccessful = models.BooleanField(default=False)
    ResultDesc = models.CharField(max_length=191, null=True)
    MpesaReceiptNumber = models.CharField(unique=True, max_length=191, null=True)
    amount = models.IntegerField(default=0)
    TransactionDate = models.DateTimeField(auto_now_add=True, null=True)

# ----------------- TicketScanLog Model -----------------
class TicketScanLog(models.Model):
    ticket_id = models.CharField(max_length=100)
    scanned_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=[
        ('valid', 'Valid'),
        ('invalid', 'Invalid'),
        ('duplicate', 'Duplicate'),
    ])
    scanned_by = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.ticket_id} - {self.status}"
