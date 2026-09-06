# users/permissions.py
from rest_framework import permissions

class IsAdminVerified(permissions.BasePermission):
    """Autorise l'accès uniquement si l'utilisateur est vérifié par email ET par un admin"""
    
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.is_verified and 
            request.user.is_admin_verified
        )

class IsEmailVerified(permissions.BasePermission):
    """Autorise l'accès si l'utilisateur a vérifié son email"""
    
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.is_verified
        )