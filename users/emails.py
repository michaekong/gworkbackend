# users/emails.py
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.conf import settings
from .tokens import email_verification_token, risky_action_token
import time

def send_verification_email(user):
    """Envoie l'email de vérification de compte"""
    token = email_verification_token.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    verification_url = f"{settings.FRONTEND_URL}/verify-email?uid={uid}&token={token}"
    
    context = {
        'username': user.first_name or user.username, # Utilise le prénom s'il existe
        'verification_url': verification_url,
        'app_name': 'GWork',
        'expiry_hours': settings.EMAIL_VERIFICATION_TOKEN_TIMEOUT // 3600,
    }
    
    subject = '🚀 Activez votre compte GWork'
    
    # Version texte brut (fallback)
    text_content = f"""
    Bonjour {user.username},
    
    Merci de vous être inscrit sur GWork !
    
    Pour activer votre compte, cliquez sur le lien suivant :
    {verification_url}
    
    Ce lien expirera dans {context['expiry_hours']} heures.
    
    Cordialement,
    L'équipe GWork
    """
    
    # Version HTML
    html_content = render_to_string('emails/verify_email.html', context)
    
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email]
    )
    email.attach_alternative(html_content, "text/html")
    email.send()


def send_password_reset_email(user):
    """Envoie l'email de réinitialisation de mot de passe"""
    from django.contrib.auth.tokens import default_token_generator
    
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    reset_url = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
    
    context = {
        'username': user.username,
        'reset_url': reset_url,
        'app_name': 'GWork',
        'expiry_minutes': settings.PASSWORD_RESET_TOKEN_TIMEOUT // 60,
    }
    
    subject = '🔐 Réinitialisation de votre mot de passe GWork'
    
    text_content = f"""
    Bonjour {user.username},
    
    Vous avez demandé à réinitialiser votre mot de passe.
    
    Cliquez sur le lien suivant pour créer un nouveau mot de passe :
    {reset_url}
    
    Ce lien expirera dans {context['expiry_minutes']} minutes.
    
    Si vous n'avez pas fait cette demande, ignorez cet email.
    
    Cordialement,
    L'équipe GWork
    """
    
    html_content = render_to_string('emails/reset_password.html', context)
    
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email]
    )
    email.attach_alternative(html_content, "text/html")
    email.send()


def send_risky_action_email(user, action_description):
    """Envoie l'email de vérification pour actions à risque"""
    token = risky_action_token.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    confirmation_url = f"{settings.BACKEND_URL}/api/users/confirm-action/?uid={uid}&token={token}"
    
    context = {
        'username': user.username,
        'action_description': action_description,
        'confirmation_url': confirmation_url,
        'app_name': 'GWork',
        'expiry_minutes': settings.RISKY_ACTION_TOKEN_TIMEOUT // 60,
    }
    
    subject = '⚠️ Action sensible détectée - Vérification requise'
    
    text_content = f"""
    Bonjour {user.username},
    
    Une action sensible a été détectée sur votre compte GWork :
    
    {action_description}
    
    Pour confirmer cette action, cliquez sur le lien suivant :
    {confirmation_url}
    
    Ce lien expirera dans {context['expiry_minutes']} minutes.
    
    Si vous n'êtes pas à l'origine de cette action, contactez-nous immédiatement.
    
    Cordialement,
    L'équipe GWork
    """
    
    html_content = render_to_string('emails/risky_action.html', context)
    
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email]
    )
    email.attach_alternative(html_content, "text/html")
    email.send()