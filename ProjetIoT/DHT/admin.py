
from django.utils import timezone
from django.contrib import admin
from .models import Dht11, OperateurProfile, Incident, IoTSettings




# ✅ NEW: Settings model (page admin pour TEMP_MIN/TEMP_MAX)
try:
    from .models import IoTSettings
except Exception:
    IoTSettings = None

# ✅ si tu veux récupérer TEMP_MIN/TEMP_MAX depuis api.py (fallback)
try:
    from .api import TEMP_MIN, TEMP_MAX
except Exception:
    TEMP_MIN, TEMP_MAX = 2, 8


@admin.register(Dht11)
class Dht11Admin(admin.ModelAdmin):
    list_display = ("dt", "temp", "hum")
    list_filter = ("dt",)
    search_fields = ("dt",)


@admin.register(OperateurProfile)
class OperateurProfileAdmin(admin.ModelAdmin):
    list_display = ("niveau", "prenom", "nom", "telephone", "user")
    search_fields = ("nom", "prenom", "telephone", "user__username")
    list_filter = ("niveau",)


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    # ✅ on garde EXACTEMENT tes noms dans list_display
    list_display = (
        "id", "is_open", "start_at", "end_at", "counter", "max_temp",
        "temp_min_autorisee", "temp_max_autorisee"
    )
    list_filter = ("is_open",)
    search_fields = ("id",)

    # ✅ Actions demandées
    actions = ("action_close_incidents", "action_reset_counter", "action_mark_ack")

    # --- Helpers: on essaye plusieurs noms de champs sans casser ---
    def _get_any(self, obj, names):
        for n in names:
            if hasattr(obj, n):
                return getattr(obj, n)
        return None

    def _set_any(self, obj, names, value):
        """
        Essaie de setter le 1er champ existant dans `names`.
        Retourne True si un champ a été set, sinon False.
        """
        for n in names:
            if hasattr(obj, n):
                try:
                    setattr(obj, n, value)
                    return True
                except Exception:
                    pass
        return False

    def _now(self):
        return timezone.now()

    # ✅ "start_at" affiché même si ton modèle a created_at / start_dt etc.
    @admin.display(description="start_at")
    def start_at(self, obj):
        v = self._get_any(obj, ["start_at", "created_at", "start_dt", "start_time", "dt_start"])
        return v if v is not None else "-"

    # ✅ "end_at" affiché même si ton modèle a ended_at / closed_at etc.
    @admin.display(description="end_at")
    def end_at(self, obj):
        v = self._get_any(obj, ["end_at", "ended_at", "closed_at", "end_dt", "end_time", "dt_end"])
        return v if v is not None else "-"

    # ✅ champs “autorisés” : soit existent dans le modèle, soit constantes
    @admin.display(description="temp_min_autorisee")
    def temp_min_autorisee(self, obj):
        v = self._get_any(obj, ["temp_min_autorisee", "temp_min", "min_allowed"])
        if v is not None:
            return v

        # ✅ si Settings existe, on affiche depuis Settings
        if IoTSettings is not None:
            try:
                return IoTSettings.get_solo().temp_min
            except Exception:
                pass

        return TEMP_MIN

    @admin.display(description="temp_max_autorisee")
    def temp_max_autorisee(self, obj):
        v = self._get_any(obj, ["temp_max_autorisee", "temp_max", "max_allowed"])
        if v is not None:
            return v

        # ✅ si Settings existe, on affiche depuis Settings
        if IoTSettings is not None:
            try:
                return IoTSettings.get_solo().temp_max
            except Exception:
                pass

        return TEMP_MAX

    # -------------------------------------------------------------------------
    # ✅ ACTION 1 : Fermer incident
    # -------------------------------------------------------------------------
    @admin.action(description="✅ Fermer incident(s) sélectionné(s)")
    def action_close_incidents(self, request, queryset):
        updated = 0
        now = self._now()

        for obj in queryset:
            # ferme le flag principal
            self._set_any(obj, ["is_open", "open", "active"], False)

            # met une date de fin si le champ existe
            self._set_any(obj, ["end_at", "ended_at", "closed_at", "end_dt", "end_time", "dt_end"], now)

            # optionnel: si ton modèle a un champ "is_acknowledged" etc, on peut le marquer aussi
            self._set_any(obj, ["is_acknowledged", "acknowledged", "is_acquitted", "acquitted"], True)

            obj.save()
            updated += 1

        self.message_user(request, f"{updated} incident(s) fermé(s) avec succès.")

    # -------------------------------------------------------------------------
    # ✅ ACTION 2 : Reset compteur
    # -------------------------------------------------------------------------
    @admin.action(description="🔄 Reset compteur (counter=0)")
    def action_reset_counter(self, request, queryset):
        updated = 0
        for obj in queryset:
            if self._set_any(obj, ["counter", "count", "attempts"], 0):
                obj.save()
                updated += 1

        self.message_user(request, f"{updated} incident(s) : compteur remis à 0.")

    # -------------------------------------------------------------------------
    # ✅ ACTION 3 : Marquer incident comme acquitté
    # -------------------------------------------------------------------------
    @admin.action(description="✅ Marquer comme acquitté (ack)")
    def action_mark_ack(self, request, queryset):
        updated = 0
        now = self._now()

        for obj in queryset:
            # ✅ met un flag acquitté si ton modèle l'a
            self._set_any(obj, ["is_acknowledged", "acknowledged", "is_acquitted", "acquitted", "mute"], True)

            # ✅ met un champ ack_by si existe (ton front utilise incident.ack_by)
            if self._set_any(obj, ["ack_by", "acknowledged_by", "acquitted_by"], request.user.get_username()):
                pass

            # ✅ met une date d'acquittement si existe
            self._set_any(obj, ["ack_at", "acknowledged_at", "acquitted_at"], now)

            obj.save()
            updated += 1

        self.message_user(request, f"{updated} incident(s) marqué(s) acquitté(s).")


# -----------------------------------------------------------------------------
# ✅ Admin Settings (TEMP_MIN / TEMP_MAX)
# -----------------------------------------------------------------------------
if IoTSettings is not None:

    @admin.register(IoTSettings)
    class IoTSettingsAdmin(admin.ModelAdmin):
        list_display = ("temp_min", "temp_max", "updated_at")
        readonly_fields = ("updated_at",)

        def has_add_permission(self, request):
            # ✅ Singleton : un seul objet
            return not IoTSettings.objects.exists()

        def has_delete_permission(self, request, obj=None):
            # ✅ éviter suppression accidentelle
            return False
