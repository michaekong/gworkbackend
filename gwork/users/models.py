from django.db import models
# users/models.py
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.gis.db import models as gis_models
from django.utils.translation import gettext_lazy as _

class CustomUserManager(BaseUserManager):
    """Gestionnaire personnalisé pour créer des utilisateurs avec l'email comme identifiant"""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('L\'adresse email doit être renseignée'))
        email = self.normalize_email(email)
        # On génère un username interne automatique pour satisfaire Django
        username = extra_fields.pop('username', email.split('@')[0])
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_verified', True)
        extra_fields.setdefault('is_admin_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Un superutilisateur doit avoir is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Un superutilisateur doit avoir is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    # On lie le gestionnaire personnalisé au modèle
    objects = CustomUserManager()

    # 1. On définit l'email comme identifiant unique de connexion
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'age', 'sex', 'cni_number', 'user_type']

    # 2. Rendre le champ email unique
    email = models.EmailField(_('email address'), unique=True)

    # 3. Le champ username devient optionnel et interne
    username = models.CharField(max_length=150, unique=False, blank=True, null=True)

    USER_TYPE_CHOICES = (
        ('SEEKER', 'Demandeur d\'emploi'),
        ('PROVIDER', 'Offreur d\'emploi / Entreprise'),
    )
    
    SEX_CHOICES = (
        ('M', 'Homme'),
        ('F', 'Femme'),
        ('O', 'Autre / Préfère ne pas répondre'),
    )

    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
    
    # Champs d'identité
    first_name = models.CharField(max_length=150, help_text="Prénom tel qu'inscrit sur la CNI")
    last_name = models.CharField(max_length=150, help_text="Nom de famille tel qu'inscrit sur la CNI")
    age = models.IntegerField(null=True, blank=True, help_text="Âge du candidat")
    sex = models.CharField(max_length=1, choices=SEX_CHOICES)
    cni_number = models.CharField(max_length=50, unique=True, help_text="Numéro de la CNI")

    phone = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(
        upload_to='profiles/', 
        null=True, 
        blank=True, 
        help_text="Photo de profil de l'utilisateur"
    )
    # Localisation GPS
    location = gis_models.PointField(null=True, blank=True, srid=4326, help_text="Position GPS")
    
    # États de vérification
    is_verified = models.BooleanField(default=False, help_text="Vérifié par email")
    is_admin_verified = models.BooleanField(default=False, help_text="Vérifié par un admin")

    # Documents d'identité
    cni_recto = models.ImageField(upload_to='cni/recto/', null=True, blank=True, help_text="Photo recto CNI")
    cni_verso = models.ImageField(upload_to='cni/verso/', null=True, blank=True, help_text="Photo verso CNI")

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"


class SeekerProfile(gis_models.Model):
    user = models.OneToOneField(User, on_delete=gis_models.CASCADE, related_name='seeker_profile')
    skills = gis_models.JSONField(default=list)
    expected_salary = gis_models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    experience_years = gis_models.IntegerField(default=0)
    preferred_work_zone = gis_models.PolygonField(null=True, blank=True, srid=4326)
    max_commute_km = gis_models.IntegerField(default=20)

    def __str__(self):
        return f"Profil Seeker: {self.user.first_name} {self.user.last_name}"


class ProviderProfile(gis_models.Model):
    user = models.OneToOneField(User, on_delete=gis_models.CASCADE, related_name='provider_profile')
    company_name = gis_models.CharField(max_length=255)
    sector = gis_models.CharField(max_length=100)
    website = gis_models.URLField(blank=True)
    intervention_zone = gis_models.PolygonField(null=True, blank=True, srid=4326)
    intervention_radius_km = gis_models.IntegerField(default=50)

    def __str__(self):
        return f"Profil Provider: {self.company_name}"