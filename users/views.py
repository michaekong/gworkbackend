
from rest_framework import permissions
import threading
from .serializers import UserProfileSerializer
from rest_framework.generics import RetrieveAPIView
# users/views.py
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.conf import settings
from .serializers import UserRegistrationSerializer
from .emails import send_verification_email, send_password_reset_email, send_risky_action_email
from .tokens import email_verification_token, risky_action_token
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from rest_framework.generics import UpdateAPIView
from .serializers import UserProfileUpdateSerializer
from .emails import send_verification_email

User = get_user_model()

@extend_schema(
    tags=['Authentification'],
    summary="Inscription d'un nouvel utilisateur",
    description=(
        "Crée un nouveau compte utilisateur avec upload des photos de CNI "
        "et localisation GPS. Un email de vérification est envoyé automatiquement."
    ),
    request={
        'multipart/form-data': UserRegistrationSerializer,
    },
    responses={
        201: OpenApiResponse(description="Compte créé avec succès. Email de vérification envoyé."),
        400: OpenApiResponse(description="Données invalides."),
    },
)
class RegisterView(generics.CreateAPIView):
    """Inscription d'un nouvel utilisateur"""
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        threading.Thread(
            target=send_verification_email, 
            args=(user,)
        ).start()

@extend_schema(
    tags=['Authentification'],
    summary="Vérification de l'email",
    description="Active le compte utilisateur via le lien reçu par email.",
    parameters=[
        OpenApiParameter(name='uid', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=True, description="ID utilisateur encodé"),
        OpenApiParameter(name='token', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=True, description="Token de vérification"),
    ],
    responses={
        200: OpenApiResponse(description="Compte activé avec succès."),
        400: OpenApiResponse(description="Lien invalide ou expiré."),
    },
)
class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        uid = request.query_params.get('uid')
        token = request.query_params.get('token')

        if not uid or not token:
            return Response({"error": "UID et Token sont requis"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_id = urlsafe_base64_decode(uid).decode()
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"error": "Lien de vérification invalide"}, status=status.HTTP_400_BAD_REQUEST)

        if email_verification_token.check_token(user, token):
            if user.is_verified:
                # ✅ NOUVEAU : Message spécifique si déjà vérifié
                return Response({
                    "message": "Ce compte est déjà vérifié.",
                    "already_verified": True
                }, status=status.HTTP_200_OK)
            
            user.is_verified = True
            user.save()
            return Response({"message": "Compte activé avec succès !"}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Le lien de vérification a expiré ou est invalide."}, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    tags=['Authentification'],
    summary="Renvoyer l'email de vérification",
    description="Renvoie le lien de vérification si l'email n'a pas été reçu.",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'email': {'type': 'string', 'format': 'email'},
            },
            'required': ['email'],
        }
    },
    responses={
        200: OpenApiResponse(description="Email renvoyé (si le compte existe)."),
    },
)
class ResendVerificationEmailView(APIView):
    """Renvoie l'email de vérification"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        
        if not email:
            return Response({"error": "Email requis"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
            
            if user.is_verified:
                return Response({"message": "Ce compte est déjà vérifié."}, status=status.HTTP_200_OK)
            
            threading.Thread(
                target=send_verification_email, 
                args=(user,)
            ).start()
            return Response({"message": "Email de vérification renvoyé avec succès."}, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            # Pour des raisons de sécurité, on ne révèle pas si l'email existe ou non
            return Response({"message": "Si cet email existe dans notre système, vous recevrez un lien de vérification."}, status=status.HTTP_200_OK)

@extend_schema(
    tags=['Authentification'],
    summary="Connexion (Login)",
    description=(
        "Authentifie l'utilisateur et retourne les tokens JWT (access + refresh). "
        "Le compte doit être vérifié par email ET par un admin."
    ),
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'email': {'type': 'string', 'format': 'email'},
                'password': {'type': 'string'},
            },
            'required': ['email', 'password'],
        }
    },
    responses={
        200: OpenApiResponse(description="Connexion réussie avec tokens JWT."),
        401: OpenApiResponse(description="Identifiants invalides."),
        403: OpenApiResponse(description="Compte non vérifié ou non validé par admin."),
    },
    examples=[
        OpenApiExample(
            'Exemple de requête',
            value={"email": "cedric@example.com", "password": "MonMotDePasse123!"},
            request_only=True,
        ),
        OpenApiExample(
            'Exemple de réponse',
            value={
                "message": "Connexion réussie",
                "refresh": "eyJ0eXAiOiJKV1QiLCJhbGci...",
                "access": "eyJ0eXAiOiJKV1QiLCJhbGci...",
                "user": {
                    "id": 1,
                    "username": "cedric",
                    "email": "cedric@example.com",
                    "user_type": "SEEKER",
                    "is_verified": True,
                    "is_admin_verified": True
                }
            },
            response_only=True,
        ),
    ],
)
# Dans users/views.py, modifie la classe LoginView comme suit :

# Dans gwork/users/views.py, classe LoginView

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({"error": "Email et mot de passe requis"}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, username=email, password=password)

        if user is None:
            return Response({"error": "Email ou mot de passe incorrect"}, status=status.HTTP_401_UNAUTHORIZED)

        # ✅ MODIFICATION : On bloque seulement si l'email n'est PAS vérifié.
        # On laisse passer si c'est juste la CNI qui est en attente.
        if not user.is_verified:
            return Response({
                "error": "Votre compte n'est pas encore vérifié par email. Veuillez consulter votre boîte de réception."
            }, status=status.HTTP_403_FORBIDDEN)

        refresh = RefreshToken.for_user(user)

        return Response({
            "message": "Connexion réussie",
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "user_type": user.user_type,
                "is_verified": user.is_verified,
                "is_admin_verified": user.is_admin_verified, # Le frontend utilisera ceci
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser
            }
        }, status=status.HTTP_200_OK)

@extend_schema(
    tags=['Authentification'],
    summary="Demander la réinitialisation du mot de passe",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'email': {'type': 'string', 'format': 'email'},
            },
            'required': ['email'],
        }
    },
    responses={200: OpenApiResponse(description="Email de réinitialisation envoyé.")},
)
class RequestPasswordResetView(APIView):
    """Demande de réinitialisation de mot de passe"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        
        if not email:
            return Response({"error": "Email requis"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
            threading.Thread(
                target=send_password_reset_email, 
                args=(user,)
            ).start()
        except User.DoesNotExist:
            pass  # Pour des raisons de sécurité

        # Toujours renvoyer le même message pour ne pas révéler si l'email existe
        return Response({
            "message": "Si cet email existe dans notre système, vous recevrez un lien de réinitialisation."
        }, status=status.HTTP_200_OK)

@extend_schema(
    tags=['Authentification'],
    summary="Réinitialiser le mot de passe",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'uid': {'type': 'string'},
                'token': {'type': 'string'},
                'new_password': {'type': 'string', 'minLength': 8},
            },
            'required': ['uid', 'token', 'new_password'],
        }
    },
    responses={
        200: OpenApiResponse(description="Mot de passe réinitialisé."),
        400: OpenApiResponse(description="Lien invalide ou expiré."),
    },
)
class ResetPasswordView(APIView):
    """Réinitialisation effective du mot de passe"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')
        new_password = request.data.get('new_password')

        if not uid or not token or not new_password:
            return Response({"error": "UID, token et nouveau mot de passe requis"}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 8:
            return Response({"error": "Le mot de passe doit contenir au moins 8 caractères"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_id = urlsafe_base64_decode(uid).decode()
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"error": "Lien de réinitialisation invalide"}, status=status.HTTP_400_BAD_REQUEST)

        if default_token_generator.check_token(user, token):
            user.set_password(new_password)
            user.save()
            return Response({"message": "Mot de passe réinitialisé avec succès."}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Le lien de réinitialisation a expiré ou est invalide."}, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    tags=['Authentification'],
    summary="Demander confirmation pour action à risque",
    description="Envoie un email de confirmation pour une action sensible (suppression de compte, changement d'email, etc.).",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'action_description': {'type': 'string'},
            },
        }
    },
    responses={200: OpenApiResponse(description="Email de confirmation envoyé.")},
)
class RequestRiskyActionConfirmationView(APIView):
    """Demande de confirmation pour une action à risque"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        action_description = request.data.get('action_description', 'Action non spécifiée')
        
        send_risky_action_email(request.user, action_description)
        
        return Response({
            "message": "Email de confirmation envoyé. Veuillez vérifier votre boîte de réception."
        }, status=status.HTTP_200_OK)

@extend_schema(
    tags=['Authentification'],
    summary="Confirmer une action à risque",
    parameters=[
        OpenApiParameter(name='uid', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=True),
        OpenApiParameter(name='token', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=True),
        OpenApiParameter(name='action_type', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False),
    ],
    responses={
        200: OpenApiResponse(description="Action confirmée."),
        400: OpenApiResponse(description="Lien invalide ou expiré."),
    },
)
class ConfirmRiskyActionView(APIView):
    """Confirmation d'une action à risque"""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        uid = request.query_params.get('uid')
        token = request.query_params.get('token')
        action_type = request.query_params.get('action_type')

        if not uid or not token:
            return Response({"error": "UID et Token requis"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_id = urlsafe_base64_decode(uid).decode()
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"error": "Lien de confirmation invalide"}, status=status.HTTP_400_BAD_REQUEST)

        if risky_action_token.check_token(user, token):
            # Ici tu peux implémenter la logique spécifique selon action_type
            # Par exemple : suppression de compte, changement d'email, etc.
            
            return Response({
                "message": "Action confirmée avec succès.",
                "user_id": user.id,
                "action_type": action_type
            }, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Le lien de confirmation a expiré ou est invalide."}, status=status.HTTP_400_BAD_REQUEST)
        
class UserProfileView(RetrieveAPIView):
    """
    Récupère les informations de l'utilisateur actuellement authentifié.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # Au lieu de chercher par ID dans l'URL, on retourne directement l'utilisateur de la requête
        return self.request.user        


class UserProfileUpdateView(UpdateAPIView):
    """
    Permet à l'utilisateur connecté de modifier son profil.
    Si des informations sensibles changent (nom, prénom, âge, CNI, sexe),
    le compte est automatiquement marqué comme non vérifié par l'admin.
    """
    serializer_class = UserProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # Retourne l'utilisateur connecté
        return self.request.user

    def perform_update(self, serializer):
        # Sauvegarde les modifications
        user = serializer.save()
        
        # Si l'admin doit reverifier, on pourrait envoyer une notification ici
        if not user.is_admin_verified:
            # Optionnel : Envoyer un email à l'admin ou à l'utilisateur
            pass    
# users/views.py
from rest_framework.permissions import IsAdminUser
from rest_framework import generics, status
from rest_framework.response import Response
from .serializers import AdminUserListSerializer, AdminUserDetailSerializer

class PendingUsersListView(generics.ListAPIView):
    """Liste uniquement les utilisateurs vérifiés par email mais pas encore par un admin"""
    serializer_class = AdminUserListSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return User.objects.filter(is_verified=True, is_admin_verified=False).order_by('-date_joined')


class AdminUserVerificationView(generics.RetrieveUpdateAPIView):
    """Permet à l'admin de voir les détails complets et de changer le statut de vérification"""
    serializer_class = AdminUserDetailSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'pk'

    def get_queryset(self):
        return User.objects.all()

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        # On met à jour uniquement le champ is_admin_verified
        is_approved = request.data.get('is_admin_verified')
        if is_approved is not None:
            instance.is_admin_verified = bool(is_approved)
            instance.save()
            return Response({
                "message": "Statut de vérification mis à jour avec succès",
                "is_admin_verified": instance.is_admin_verified
            }, status=status.HTTP_200_OK)
        
        return Response({"error": "Données invalides"}, status=status.HTTP_400_BAD_REQUEST)        