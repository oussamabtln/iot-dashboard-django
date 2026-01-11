from django.contrib.auth.models import User
from django.db import models


# --- MODELE 1 : CAPTEUR (T° / H%) ---
class Dht11(models.Model):
    temp = models.FloatField(null=True, blank=True)
    hum = models.FloatField(null=True, blank=True)
    dt = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"{self.temp}°C / {self.hum}%"


# --- MODELE 2 : PROFIL OPERATEUR ---
class OperateurProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="operateur_profile"
    )

    nom = models.CharField(max_length=60)
    prenom = models.CharField(max_length=60)
    telephone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    telegram = models.CharField(max_length=80, blank=True)

    # 1=op1, 2=chef, 3=directeur (كتخدم حتى مع str فـ views)
    niveau = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return f"Op{self.niveau} - {self.prenom} {self.nom} ({self.user.username})"


# --- MODELE 3 : INCIDENTS ---
class Incident(models.Model):
    KIND_CHOICES = [
        ("HOT", "HOT"),
        ("COLD", "COLD"),
    ]

    notified_lvl1 = models.BooleanField(default=False)
    notified_lvl2 = models.BooleanField(default=False)
    notified_lvl3 = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    is_open = models.BooleanField(default=True)

    kind = models.CharField(max_length=4, choices=KIND_CHOICES, default="HOT")
    max_temp = models.FloatField(null=True, blank=True)

    counter = models.IntegerField(default=0)
    last_counter_at = models.DateTimeField(null=True, blank=True)
    last_dht_id = models.IntegerField(null=True, blank=True)

    temp_min_autorisee = models.FloatField(default=2.0)
    temp_max_autorisee = models.FloatField(default=8.0)

    op1_ack = models.BooleanField(default=False)
    op1_comment = models.CharField(max_length=200, null=True, blank=True)

    op2_ack = models.BooleanField(default=False)
    op2_comment = models.CharField(max_length=200, null=True, blank=True)

    op3_ack = models.BooleanField(default=False)
    op3_comment = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return f"Incident #{self.id} ({'OPEN' if self.is_open else 'CLOSED'})"


# --- MODELE COMMENTS (مرة وحدة فقط) ---
class IncidentComment(models.Model):
    ROLE_CHOICES = [
        ("OP1", "Opérateur 1"),
        ("OP2", "Chef équipe"),
        ("OP3", "Directeur"),
    ]

    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name="comments")
    role = models.CharField(max_length=3, choices=ROLE_CHOICES)
    text = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Comment {self.role} on incident {self.incident_id}"


# --- MODELE 4 : REGLAGES IOT ---
class IoTSettings(models.Model):
    temp_min = models.FloatField(default=2.0)
    temp_max = models.FloatField(default=8.0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Réglages IoT"
        verbose_name_plural = "Réglages IoT"

    def __str__(self):
        return f"Réglages IoT (min={self.temp_min}, max={self.temp_max})"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
