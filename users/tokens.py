# users/tokens.py
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.conf import settings
import time

class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """Générateur de token pour la vérification d'email"""
    
    def _make_hash_value(self, user, timestamp):
        return (
            str(user.pk) + str(timestamp) + str(user.is_verified) + user.email
        )

class RiskyActionTokenGenerator(PasswordResetTokenGenerator):
    """Générateur de token pour les actions à risque"""
    
    def _make_hash_value(self, user, timestamp):
        return (
            str(user.pk) + str(timestamp) + str(user.is_admin_verified) + 
            str(user.is_verified) + user.email
        )

email_verification_token = EmailVerificationTokenGenerator()
risky_action_token = RiskyActionTokenGenerator()