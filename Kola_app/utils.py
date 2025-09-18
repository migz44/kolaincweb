# utils.py
import qrcode
from io import BytesIO
from django.core.files import File
from django.conf import settings

def generate_qr_code(url, ticket_instance):
    """
    Generates a QR code image from a given URL and saves it to the ticket_instance.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    # Create an in-memory stream for the image data
    img_buffer = BytesIO()
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)  # Go to the beginning of the stream

    # Generate a filename and save to the model
    file_name = f'ticket_qr_{ticket_instance.unique_code}.png'
    ticket_instance.qr_code.save(file_name, File(img_buffer), save=False)

    return ticket_instance