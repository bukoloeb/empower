import random
from django.core.mail import send_mail
from django.conf import settings

def generate_and_send_pin(user):
    pin = str(random.randint(100000, 999999))
    user.verification_pin = pin
    user.save()

    subject = 'Your Empower Edge Verification Code'
    message = f'Hello {user.email}, your verification code is: {pin}'
    email_from = settings.DEFAULT_FROM_EMAIL
    recipient_list = [user.email]
    
    send_mail(subject, message, email_from, recipient_list)