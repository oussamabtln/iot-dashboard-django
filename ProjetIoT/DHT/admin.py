from django.contrib import admin
from .models import Dht11, Incident, OperateurProfile

# ✅ si tu veux récupérer TEMP_MIN/TEMP_MAX depuis api.py (recommandé)
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
    list_display = ("id", "is_open", "start_at", "end_at", "counter", "max_temp",
                    "temp_min_autorisee", "temp_max_autorisee")
    list_filter = ("is_open",)
    search_fields = ("id",)

    # --- Helpers: on essaye plusieurs noms de champs sans casser ---
    def _get_any(self, obj, names):
        for n in names:
            if hasattr(obj, n):
                return getattr(obj, n)
        return None

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
        return v if v is not None else TEMP_MIN

    @admin.display(description="temp_max_autorisee")
    def temp_max_autorisee(self, obj):
        v = self._get_any(obj, ["temp_max_autorisee", "temp_max", "max_allowed"])
        return v if v is not None else TEMP_MAX
