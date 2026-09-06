# users/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point, Polygon
from .models import SeekerProfile, ProviderProfile
import math

User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    
    # On utilise SerializerMethodField pour lire les coordonnées depuis le PointField 'location'
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    
    # Champs d'entrée pour la création (write_only pour qu'ils ne soient pas attendus en lecture)
    input_latitude = serializers.FloatField(write_only=True, required=False, allow_null=True)
    input_longitude = serializers.FloatField(write_only=True, required=False, allow_null=True)
    
    # Champs spécifiques aux profils
    skills = serializers.ListField(child=serializers.CharField(), required=False, write_only=True)
    company_name = serializers.CharField(required=False, write_only=True)
    sector = serializers.CharField(required=False, write_only=True)
    max_commute_km = serializers.IntegerField(required=False, write_only=True, default=20)
    intervention_radius_km = serializers.IntegerField(required=False, write_only=True, default=50)
    
    # Images CNI
    cni_recto = serializers.ImageField(required=True, write_only=True)
    cni_verso = serializers.ImageField(required=True, write_only=True)

    class Meta:
        model = User
        fields = [
            'email', 'password', 'first_name', 'last_name', 'age', 'sex', 'cni_number',
            'user_type', 'phone', 'latitude', 'longitude', 'input_latitude', 'input_longitude',
            'skills', 'company_name', 'sector', 
            'max_commute_km', 'intervention_radius_km',
            'cni_recto', 'cni_verso'
        ]
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'age': {'required': True},
            'sex': {'required': True},
            'cni_number': {'required': True},
        }

    # --- Méthodes pour la LECTURE (Réponse API) ---
    def get_latitude(self, obj):
        if obj.location:
            return float(obj.location.y)
        return None

    def get_longitude(self, obj):
        if obj.location:
            return float(obj.location.x)
        return None

    # --- Méthode pour la CRÉATION ---
    def _create_circle_polygon(self, center_point, radius_km):
        if not center_point or radius_km <= 0:
            return None
        radius_deg = radius_km / 111.0
        num_points = 64
        coords = []
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            lat_offset = radius_deg * math.cos(angle)
            lng_offset = radius_deg * math.sin(angle) / math.cos(math.radians(center_point.y))
            point_lat = center_point.y + lat_offset
            point_lng = center_point.x + lng_offset
            coords.append((point_lng, point_lat))
        coords.append(coords[0])
        return Polygon(coords, srid=4326)

    def create(self, validated_data):
        user_type = validated_data.pop('user_type')
        password = validated_data.pop('password')
        
        # On récupère les coordonnées d'entrée (et on les retire de validated_data)
        latitude = validated_data.pop('input_latitude', None)
        longitude = validated_data.pop('input_longitude', None)
        
        max_commute_km = validated_data.pop('max_commute_km', 20)
        intervention_radius_km = validated_data.pop('intervention_radius_km', 50)
        
        cni_recto = validated_data.pop('cni_recto')
        cni_verso = validated_data.pop('cni_verso')
        skills = validated_data.pop('skills', [])
        company_name = validated_data.pop('company_name', '')
        sector = validated_data.pop('sector', '')

        # Création du Point GIS
        location_point = None
        if latitude is not None and longitude is not None:
            # Attention : Point prend (longitude, latitude) dans cet ordre !
            location_point = Point(float(longitude), float(latitude), srid=4326)

        # Génération d'un username interne unique
        temp_username = validated_data['email'].split('@')[0] + "_" + str(User.objects.count() + 1)

        # 1. Création de l'utilisateur
        user = User.objects.create_user(
            username=temp_username,
            email=validated_data['email'],
            password=password,
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            age=validated_data['age'],
            sex=validated_data['sex'],
            cni_number=validated_data['cni_number'],
            user_type=user_type,
            phone=validated_data.get('phone', ''),
            location=location_point, # <-- C'est ici que le Point est sauvegardé
            cni_recto=cni_recto,
            cni_verso=cni_verso,
            is_active=True,
            is_verified=False,
            is_admin_verified=False
        )

        # 2. Création du profil associé avec la zone géographique
        if user_type == 'SEEKER':
            preferred_zone = self._create_circle_polygon(location_point, max_commute_km) if location_point and max_commute_km > 0 else None
            SeekerProfile.objects.create(
                user=user, skills=skills, max_commute_km=max_commute_km, preferred_work_zone=preferred_zone
            )
        elif user_type == 'PROVIDER':
            intervention_zone = self._create_circle_polygon(location_point, intervention_radius_km) if location_point and intervention_radius_km > 0 else None
            ProviderProfile.objects.create(
                user=user, company_name=company_name, sector=sector, intervention_radius_km=intervention_radius_km, intervention_zone=intervention_zone
            )

        return user
# users/serializers.py (à ajouter à la suite de tes autres sérialiseurs)

class SeekerProfileDetailSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les détails du profil Demandeur d'emploi"""
    class Meta:
        model = SeekerProfile
        fields = [
            'skills', 'expected_salary', 'experience_years', 
            'max_commute_km', 'preferred_work_zone'
        ]
        # Note: preferred_work_zone sera automatiquement renvoyé en format GeoJSON 
        # grâce à djangorestframework-gis, ce qui est parfait pour le frontend.


class ProviderProfileDetailSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les détails du profil Offreur d'emploi"""
    class Meta:
        model = ProviderProfile
        fields = [
            'company_name', 'sector', 'website', 
            'intervention_radius_km', 'intervention_zone'
        ]


class UserProfileSerializer(serializers.ModelSerializer):
    """Sérialiseur principal pour les informations de l'utilisateur connecté"""
    
    # Champs calculés pour la localisation (pour éviter d'envoyer du GeoJSON brut pour un point)
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    
    # Champ dynamique pour inclure le bon profil (Seeker ou Provider)
    profile_details = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'age', 'sex', 
            'cni_number', 'user_type', 'phone', 'bio', 
            'is_verified', 'is_admin_verified',
            'latitude', 'longitude', 'profile_details', 'profile_picture',  # ✅ DOIT ÊTRE ICI
            'cni_recto',        # ✅ DOIT ÊTRE ICI
            'cni_verso'
        ]
        read_only_fields = fields # En lecture seule, on ne modifie pas tout ici d'un coup

    def get_latitude(self, obj):
        return float(obj.location.y) if obj.location else None

    def get_longitude(self, obj):
        return float(obj.location.x) if obj.location else None

    def get_profile_details(self, obj):
        # ✅ CORRECTION : Vérifier que user_type est bien défini avant d'accéder aux profils
        if not obj.user_type:
            return None
            
        if obj.user_type == 'SEEKER' and hasattr(obj, 'seeker_profile'):
            from .serializers import SeekerProfileDetailSerializer
            return SeekerProfileDetailSerializer(obj.seeker_profile).data
        elif obj.user_type == 'PROVIDER' and hasattr(obj, 'provider_profile'):
            from .serializers import ProviderProfileDetailSerializer
            return ProviderProfileDetailSerializer(obj.provider_profile).data
        
        return None    
class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la mise à jour du profil utilisateur.
    Détecte les changements de champs sensibles et remet is_admin_verified à False.
    """
    
    # Champs de localisation (optionnels pour la mise à jour)
    input_latitude = serializers.FloatField(write_only=True, required=False, allow_null=True)
    input_longitude = serializers.FloatField(write_only=True, required=False, allow_null=True)
    
    # Champs calculés pour la réponse
    latitude = serializers.SerializerMethodField(read_only=True)
    longitude = serializers.SerializerMethodField(read_only=True)
    
    # Champs sensibles qui nécessitent une reverification admin
    SENSITIVE_FIELDS = ['first_name', 'last_name', 'age', 'sex', 'cni_number']

    class Meta:
        model = User
        fields = [
        'first_name', 'last_name', 'age', 'sex', 'cni_number',
        'phone', 'bio', 'profile_picture', 'cni_recto', 'cni_verso',
        'input_latitude', 'input_longitude', 'latitude', 'longitude', 'is_admin_verified'
    ]
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
            'age': {'required': False},
            'sex': {'required': False},
            'cni_number': {'required': False},
            'phone': {'required': False},
            'bio': {'required': False},
            'profile_picture': {'required': False},
        }

    def get_latitude(self, obj):
        return float(obj.location.y) if obj.location else None

    def get_longitude(self, obj):
        return float(obj.location.x) if obj.location else None

    def update(self, instance, validated_data):
        # 1. Extraire les coordonnées si présentes
        latitude = validated_data.pop('input_latitude', None)
        longitude = validated_data.pop('input_longitude', None)
        
        # 2. Mettre à jour la localisation si les coordonnées sont fournies
        if latitude is not None and longitude is not None:
            instance.location = Point(float(longitude), float(latitude), srid=4326)
            
            # Mettre à jour les zones géographiques des profils associés
            self._update_profile_zones(instance)
        
        # 3. Détecter si des champs sensibles ont été modifiés
        sensitive_fields_changed = False
        for field in self.SENSITIVE_FIELDS:
            if field in validated_data:
                new_value = validated_data[field]
                old_value = getattr(instance, field)
                
                # Comparer les valeurs (gérer les cas où l'un est None)
                if str(new_value) != str(old_value):
                    sensitive_fields_changed = True
                    break
        
        # 4. Si des champs sensibles ont changé, remettre is_admin_verified à False
        if sensitive_fields_changed and instance.is_admin_verified:
            instance.is_admin_verified = False
        
        # 5. Mettre à jour les autres champs
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance

    def _update_profile_zones(self, user):
        """Met à jour les zones géographiques quand la localisation change"""
        if user.user_type == 'SEEKER' and hasattr(user, 'seeker_profile'):
            profile = user.seeker_profile
            if user.location and profile.max_commute_km > 0:
                profile.preferred_work_zone = self._create_circle_polygon(
                    user.location, profile.max_commute_km
                )
                profile.save()
        
        elif user.user_type == 'PROVIDER' and hasattr(user, 'provider_profile'):
            profile = user.provider_profile
            if user.location and profile.intervention_radius_km > 0:
                profile.intervention_zone = self._create_circle_polygon(
                    user.location, profile.intervention_radius_km
                )
                profile.save()

    def _create_circle_polygon(self, center_point, radius_km):
        """Crée un polygone circulaire autour d'un point"""
        import math
        if not center_point or radius_km <= 0:
            return None
        radius_deg = radius_km / 111.0
        num_points = 64
        coords = []
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            lat_offset = radius_deg * math.cos(angle)
            lng_offset = radius_deg * math.sin(angle) / math.cos(math.radians(center_point.y))
            point_lat = center_point.y + lat_offset
            point_lng = center_point.x + lng_offset
            coords.append((point_lng, point_lat))
        coords.append(coords[0])
        return Polygon(coords, srid=4326)
# users/serializers.py

class AdminUserListSerializer(serializers.ModelSerializer):
    """Sérialiseur léger pour la liste des comptes en attente"""
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'user_type', 'date_joined', 'cni_number']

class AdminUserDetailSerializer(serializers.ModelSerializer):
    """Sérialiseur complet pour la révision par l'admin"""
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    profile_details = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'age', 'sex', 
            'cni_number', 'user_type', 'phone', 'bio', 
            'is_verified', 'is_admin_verified',
            'latitude', 'longitude', 
            'profile_picture', 'cni_recto', 'cni_verso',
            'profile_details', 'date_joined'
        ]

    def get_latitude(self, obj):
        return float(obj.location.y) if obj.location else None

    def get_longitude(self, obj):
        return float(obj.location.x) if obj.location else None

    def get_profile_details(self, obj):
        if obj.user_type == 'SEEKER' and hasattr(obj, 'seeker_profile'):
            from .serializers import SeekerProfileDetailSerializer
            return SeekerProfileDetailSerializer(obj.seeker_profile).data
        elif obj.user_type == 'PROVIDER' and hasattr(obj, 'provider_profile'):
            from .serializers import ProviderProfileDetailSerializer
            return ProviderProfileDetailSerializer(obj.provider_profile).data
        return None    