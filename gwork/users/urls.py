# users/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from .views import (
    RegisterView,
    VerifyEmailView,
    ResendVerificationEmailView,
    LoginView,
    RequestPasswordResetView,
    ResetPasswordView,
    RequestRiskyActionConfirmationView,
    ConfirmRiskyActionView,
    UserProfileView,
     UserProfileUpdateView,
     PendingUsersListView,
    AdminUserVerificationView,
)

urlpatterns = [
    # Inscription et vérification
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('resend-verification/', ResendVerificationEmailView.as_view(), name='resend-verification'),
    
    # Authentification
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('profile/update/', UserProfileUpdateView.as_view(), name='user-profile-update'),

    # Réinitialisation de mot de passe
    path('password/reset/', RequestPasswordResetView.as_view(), name='password-reset'),
    path('password/reset/confirm/', ResetPasswordView.as_view(), name='password-reset-confirm'),
       path('admin/pending-users/', PendingUsersListView.as_view(), name='admin-pending-users'),
    path('admin/users/<int:pk>/verify/', AdminUserVerificationView.as_view(), name='admin-user-verify'),

    # Actions à risque
    path('risky-action/request/', RequestRiskyActionConfirmationView.as_view(), name='risky-action-request'),
    path('risky-action/confirm/', ConfirmRiskyActionView.as_view(), name='risky-action-confirm'),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += staticfiles_urlpatterns()  # Ajoutez cette ligne pour servir les fichiers statiques