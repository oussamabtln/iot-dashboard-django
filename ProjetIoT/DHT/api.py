from django.utils import timezone
from django.utils.dateparse import parse_date
from django.core.mail import send_mail
from django.conf import settings

from rest_framework.decorators import api_view
from rest_framework import generics
from rest_framework.response import Response

from .models import Dht11, Incident
from .serializers import DHT11serialize

# --- RÉGLAGE DU DOMAINE (FRIGO / MÉDICAMENTS) ---
TEMP_MIN = 2  # Alerte si en dessous de 2°C
TEMP_MAX = 8  # Alerte si au dessus de 8°C


# --- API DE RÉCUPÉRATION (GET) ---
@api_view(['GET'])
def Dlist(request):
    qs = Dht11.objects.all().order_by('dt')

    start_date = request.GET.get('start')
    end_date = request.GET.get('end')

    if start_date:
        parsed_start = parse_date(start_date)
        if parsed_start:
            qs = qs.filter(dt__date__gte=parsed_start)

    if end_date:
        parsed_end = parse_date(end_date)
        if parsed_end:
            qs = qs.filter(dt__date__lte=parsed_end)

    data = DHT11serialize(qs, many=True).data
    return Response({'data': data})


# --- API D'ENREGISTREMENT (POST) ---
class Dhtviews(generics.CreateAPIView):
    queryset = Dht11.objects.all()
    serializer_class = DHT11serialize

    def perform_create(self, serializer):
        instance = serializer.save()
        temp = instance.temp

        # sécurité
        if temp is None:
            return

        now = timezone.now()

        # incident ouvert actuel (s'il existe)
        inc = Incident.objects.filter(is_open=True).order_by("-created_at").first()

        # ---------- Gestion incident (création/fermeture) ----------
        in_range = (TEMP_MIN <= temp <= TEMP_MAX)

        if in_range:
            # si OK => fermer incident ouvert
            if inc:
                inc.is_open = False
                inc.ended_at = now
                inc.save(update_fields=["is_open", "ended_at"])
            return

        # hors plage => déterminer type
        kind = "HOT" if temp > TEMP_MAX else "COLD"

        # si aucun incident ouvert => créer un nouveau
        if not inc:
            Incident.objects.create(
                kind=kind,
                max_temp=temp,           # HOT => max ; COLD => min (stocké dans max_temp)
                counter=0,
                last_counter_at=now,     # important pour compteur auto 30s
                is_open=True,
            )
        else:
            # si incident existant mais type change (ex: HOT -> COLD), on clôture et on crée un nouveau
            if inc.kind != kind:
                inc.is_open = False
                inc.ended_at = now
                inc.save(update_fields=["is_open", "ended_at"])

                Incident.objects.create(
                    kind=kind,
                    max_temp=temp,
                    counter=0,
                    last_counter_at=now,
                    is_open=True,
                )
            else:
                # même incident => mise à jour température extrême
                if inc.max_temp is None:
                    inc.max_temp = temp
                else:
                    if inc.kind == "HOT":
                        if temp > float(inc.max_temp):
                            inc.max_temp = temp
                    else:  # COLD => on garde le MIN dans max_temp
                        if temp < float(inc.max_temp):
                            inc.max_temp = temp

                # si last_counter_at vide, on l'initialise
                if inc.last_counter_at is None:
                    inc.last_counter_at = now

                inc.save(update_fields=["max_temp", "last_counter_at"])

        # ---------- EMAIL (ton code, gardé) ----------
        if temp < TEMP_MIN or temp > TEMP_MAX:
            if temp < TEMP_MIN:
                sujet = "❄️ ALERTE CRITIQUE : GEL DÉTECTÉ"
                message = (
                    f"URGENT : La température est descendue à {temp:.1f}°C.\n"
                    f"C'est en dessous du minimum vital de {TEMP_MIN}°C."
                )
            else:
                sujet = "🔥 ALERTE CRITIQUE : SURCHAUFFE"
                message = (
                    f"URGENT : La température est montée à {temp:.1f}°C.\n"
                    f"La limite maximale de {TEMP_MAX}°C est dépassée."
                )

            try:
                send_mail(
                    subject=sujet,
                    message=message,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=["oussama.boutalount.23@ump.ac.ma"],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Erreur envoi email: {e}")
