# DHT/api.py
from django.utils import timezone
from django.utils.dateparse import parse_date

from rest_framework.decorators import api_view
from rest_framework import generics
from rest_framework.response import Response

from .models import Dht11, Incident

try:
    from .models import IoTSettings
except Exception:
    IoTSettings = None

from .serializers import DHT11serialize
from .services import process_temperature_event, send_email_alert, send_whatsapp_twilio

TEMP_MIN_DEFAULT = 2.0
TEMP_MAX_DEFAULT = 8.0


def get_limits():
    """Retourne (temp_min, temp_max) depuis DB si IoTSettings existe."""
    if IoTSettings is None:
        return TEMP_MIN_DEFAULT, TEMP_MAX_DEFAULT
    try:
        s = IoTSettings.get_solo()
        return float(s.temp_min), float(s.temp_max)
    except Exception:
        return TEMP_MIN_DEFAULT, TEMP_MAX_DEFAULT


@api_view(["GET"])
def Dlist(request):
    qs = Dht11.objects.all().order_by("dt")

    start_date = request.GET.get("start")
    end_date = request.GET.get("end")

    if start_date:
        parsed_start = parse_date(start_date)
        if parsed_start:
            qs = qs.filter(dt__date__gte=parsed_start)

    if end_date:
        parsed_end = parse_date(end_date)
        if parsed_end:
            qs = qs.filter(dt__date__lte=parsed_end)

    data = DHT11serialize(qs, many=True).data
    return Response({"data": data})


class Dhtviews(generics.CreateAPIView):
    queryset = Dht11.objects.all()
    serializer_class = DHT11serialize

    def perform_create(self, serializer):
        instance = serializer.save()

        if instance.temp is None:
            return

        temp = float(instance.temp)
        now = timezone.now()
        temp_min, temp_max = get_limits()

        # ✅ 0) Toujours déclencher l'alerte (Email/WA/Call) via services.py
        # (le service décide si hors plage)
        process_temperature_event(temp, recipients=["oussama.boutalount.23@ump.ac.ma"])

        inc = Incident.objects.filter(is_open=True).order_by("-created_at").first()

        # 1) Gestion incident (fermer si OK)
        in_range = (temp_min <= temp <= temp_max)
        if in_range:
            if inc:
                inc.is_open = False
                inc.ended_at = now
                inc.save(update_fields=["is_open", "ended_at"])
            return

        # 2) Création / mise à jour incident
        kind = "HOT" if temp > temp_max else "COLD"

        if not inc:
            inc = Incident.objects.create(
                kind=kind,
                max_temp=temp,
                counter=0,
                last_counter_at=now,
                last_dht_id=instance.id,
                is_open=True,
                notified_lvl1=False,
                notified_lvl2=False,
                notified_lvl3=False,
                temp_min_autorisee=temp_min,
                temp_max_autorisee=temp_max,
            )
        else:
            # si type change
            if inc.kind != kind:
                inc.is_open = False
                inc.ended_at = now
                inc.save(update_fields=["is_open", "ended_at"])

                inc = Incident.objects.create(
                    kind=kind,
                    max_temp=temp,
                    counter=0,
                    last_counter_at=now,
                    last_dht_id=instance.id,
                    is_open=True,
                    notified_lvl1=False,
                    notified_lvl2=False,
                    notified_lvl3=False,
                    temp_min_autorisee=temp_min,
                    temp_max_autorisee=temp_max,
                )
            else:
                # mise à jour extrême
                if inc.max_temp is None:
                    inc.max_temp = temp
                else:
                    if inc.kind == "HOT" and temp > float(inc.max_temp):
                        inc.max_temp = temp
                    if inc.kind == "COLD" and temp < float(inc.max_temp):
                        inc.max_temp = temp

                # compteur à chaque nouvelle mesure
                if inc.last_dht_id != instance.id:
                    inc.counter = min(9, (inc.counter or 0) + 1)
                    inc.last_dht_id = instance.id

                inc.last_counter_at = now
                inc.save(update_fields=["kind", "max_temp", "counter", "last_dht_id", "last_counter_at"])

        # 3) Message clair
        if temp < temp_min:
            subject = "❄️ ALERTE CRITIQUE : GEL DÉTECTÉ"
            msg = (
                f"URGENT : Température trop basse.\n"
                f"T = {temp:.1f}°C < {temp_min:.1f}°C\n"
                f"Incident: {inc.kind} | ID: {inc.id}"
            )
        else:
            subject = "🔥 ALERTE CRITIQUE : SURCHAUFFE"
            msg = (
                f"URGENT : Température trop haute.\n"
                f"T = {temp:.1f}°C > {temp_max:.1f}°C\n"
                f"Incident: {inc.kind} | ID: {inc.id}"
            )

        recipients = ["oussama.boutalount.23@ump.ac.ma"]
        counter = int(getattr(inc, "counter", 0) or 0)

        # Niveau 1
        if not inc.notified_lvl1:
            send_email_alert(subject, msg, recipients)
            send_whatsapp_twilio("Niveau 1 - " + msg)
            inc.notified_lvl1 = True
            inc.save(update_fields=["notified_lvl1"])

        # Niveau 2
        if counter >= 4 and not inc.notified_lvl2:
            send_email_alert("⚠️ Niveau 2 - " + subject, msg, recipients)
            send_whatsapp_twilio("Niveau 2 - " + msg)
            inc.notified_lvl2 = True
            inc.save(update_fields=["notified_lvl2"])

        # Niveau 3
        if counter >= 7 and not inc.notified_lvl3:
            send_email_alert("🚨 Niveau 3 - " + subject, msg, recipients)
            send_whatsapp_twilio("Niveau 3 - " + msg)
            inc.notified_lvl3 = True
            inc.save(update_fields=["notified_lvl3"])
