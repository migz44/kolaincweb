import re
import secrets
import string
import uuid
from asyncio import Event

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from PIL import Image
import os

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

# ----------------- Payment Model -----------------
class Payment(models.Model):
    merchantId = models.CharField(unique=True, max_length=191)
    checkoutId = models.CharField(unique=True, max_length=191)
    phone = models.CharField(max_length=20)
    isSuccessful = models.BooleanField(default=False)
    ResultDesc = models.CharField(max_length=191, null=True)
    MpesaReceiptNumber = models.CharField(unique=True, max_length=191, null=True)
    amount = models.IntegerField(default=0)
    TransactionDate = models.DateTimeField(auto_now_add=True, null=True)

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
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, related_name='tickets', null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['unique_code']),
            models.Index(fields=['is_used']),
            models.Index(fields=['status']),
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
        return self.status == 'active' and not self.is_used

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

# ----------------- Contact Submission Model -----------------
class ContactSubmission(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name} ({self.email}) on {self.created_at.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-created_at']

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


class GalleryImage(models.Model):
    # Required fields
    image = models.ImageField(upload_to='gallery/')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)

    # Optional fields for better organization
    upload_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    # You can add more fields like category, tags, etc.

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-upload_date']  # Newest images first



def validate_event_poster_dimensions(image):
    """Validate that event poster has exact dimensions 3328x4160 pixels"""
    # Open the image to check dimensions
    img = Image.open(image)
    width, height = img.size

    # Check if dimensions match exactly
    if width != 3328 or height != 4160:
        raise ValidationError(
            f'Event poster must be exactly 3328×4160 pixels. Your image is {width}×{height} pixels. '
            f'Please resize your image to the required dimensions before uploading.'
        )


def validate_event_poster_dimensions(image):
    """Validate that event poster has exact dimensions 3328x4160 pixels"""
    # Open the image to check dimensions
    img = Image.open(image)
    width, height = img.size

    # Check if dimensions match exactly
    if width != 3328 or height != 4160:
        raise ValidationError(
            f'Event poster must be exactly 3328×4160 pixels. Your image is {width}×{height} pixels. '
            f'Please resize your image to the required dimensions before uploading.'
        )


class EventSchedule(models.Model):
    EVENT_NUMBER_CHOICES = [
        ('Event 1', 'Event 1'),
        ('Event 2', 'Event 2'),
        ('Event 3', 'Event 3'),
        ('Event 4', 'Event 4'),
        ('Event 5', 'Event 5'),
    ]

    MONTH_CHOICES = [
        ('January', 'January'),
        ('February', 'February'),
        ('March', 'March'),
        ('April', 'April'),
        ('May', 'May'),
        ('June', 'June'),
        ('July', 'July'),
        ('August', 'August'),
        ('September', 'September'),
        ('October', 'October'),
        ('November', 'November'),
        ('December', 'December'),
    ]

    # Required fields
    event_name = models.CharField(max_length=200)
    event_number = models.CharField(max_length=10, choices=EVENT_NUMBER_CHOICES)
    event_month = models.CharField(max_length=20, choices=MONTH_CHOICES)
    event_poster = models.ImageField(
        upload_to='events/posters/',
        validators=[validate_event_poster_dimensions]
    )
    event_location = models.CharField(max_length=200)
    event_host = models.CharField(max_length=100, default='By Kola')

    # Date field for proper sorting
    event_date = models.DateField(help_text="Actual date of the event")

    # Catalogue fields - ADD THESE
    show_in_catalogue = models.BooleanField(
        default=False,
        help_text="Show this event in the catalogue carousel"
    )
    catalogue_order = models.IntegerField(
        default=0,
        help_text="Higher numbers appear first in catalogue"
    )
    catalogue_link = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional: Custom URL for this event in catalogue"
    )

    # Management fields
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(
        default=0,
        help_text="Higher number appears first (optional)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.event_number} - {self.event_name} ({self.event_month})"

    def clean(self):
        """Additional validation"""
        super().clean()
        if self.event_poster:
            # Ensure the image is re-validated on save
            validate_event_poster_dimensions(self.event_poster)

    class Meta:
        ordering = ['-display_order', '-event_date']
        verbose_name = 'Event Schedule'
        verbose_name_plural = 'Event Schedules'