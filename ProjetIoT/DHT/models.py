from django.db import models
from django.contrib.auth.models import User

# --- MODELE 1 : CAPTEUR (T° / H%) ---
class Dht11(models.Model):
    temp = models.FloatField(null=True, blank=True)
    hum = models.FloatField(null=True, blank=True)
    dt = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"{self.temp}°C / {self.hum}%"


# --- MODELE 2 : OPERATEUR (TP) ---
class OperateurProfile(models.Model):
    """
    Profil opérateur (infos métier).
    Auth (login/mot de passe) gérée par le User Django.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="operateur_profile"
    )

    nom = models.CharField(max_length=60)
    prenom = models.CharField(max_length=60)
    telephone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)  # optionnel (User a déjà email)

    # Optionnel si tu veux "niveaux" OP1/OP2/OP3
    niveau = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return f"Op{self.niveau} - {self.prenom} {self.nom} ({self.user.username})"


# --- MODELE 3 : INCIDENTS (ALERTE + ARCHIVES) ---
class Incident(models.Model):
    KIND_CHOICES = [
        ("HOT", "HOT"),
        ("COLD", "COLD"),
    ]

    created_at = models.DateTimeField(auto_now_add=True)          # début incident
    ended_at = models.DateTimeField(null=True, blank=True)        # fin incident
    is_open = models.BooleanField(default=True)                   # état ouvert/fermé

    kind = models.CharField(max_length=4, choices=KIND_CHOICES, default="HOT")

    # HOT: max atteint | COLD: min atteint (nom conservé)
    max_temp = models.FloatField(null=True, blank=True)

    counter = models.IntegerField(default=0)                      # compteur alertes 0..9
    last_counter_at = models.DateTimeField(null=True, blank=True) # incrément auto

    # ✅ Champs demandés par le TP (plage autorisée)
    temp_min_autorisee = models.FloatField(default=2.0)
    temp_max_autorisee = models.FloatField(default=8.0)

    # ACK + commentaires (tu peux garder)
    op1_ack = models.BooleanField(default=False)
    op1_comment = models.CharField(max_length=200, null=True, blank=True)

    op2_ack = models.BooleanField(default=False)
    op2_comment = models.CharField(max_length=200, null=True, blank=True)

    op3_ack = models.BooleanField(default=False)
    op3_comment = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return f"Incident #{self.id} ({'OPEN' if self.is_open else 'CLOSED'})"
