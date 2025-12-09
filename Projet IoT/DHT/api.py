from .models import Dht11
from .serializers import DHT11serialize
from rest_framework.decorators import api_view
from rest_framework import generics
from rest_framework.response import Response
from django.core.mail import send_mail
from django.conf import settings
from .utils import send_telegram
from django.utils.dateparse import parse_date  # 👈 IMPORTANT : Pour lire les dates


# --- API DE RÉCUPÉRATION (GET) AVEC FILTRE ---
@api_view(['GET'])
def Dlist(request):
    # 1. On récupère toutes les données triées par date (important pour le graphe)
    all_data = Dht11.objects.all().order_by('dt')

    # 2. On récupère les paramètres de l'URL (ex: ?start=2023-01-01&end=2023-01-02)
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')

    # 3. Si une date de début est fournie, on filtre
    if start_date:
        parsed_start = parse_date(start_date)
        if parsed_start:
            # __gte = Plus grand ou égal (Greater Than or Equal)
            all_data = all_data.filter(dt__date__gte=parsed_start)

    # 4. Si une date de fin est fournie, on filtre
    if end_date:
        parsed_end = parse_date(end_date)
        if parsed_end:
            # __lte = Plus petit ou égal (Less Than or Equal)
            all_data = all_data.filter(dt__date__lte=parsed_end)

    # 5. On sérialise les données
    data = DHT11serialize(all_data, many=True).data

    # 6. On renvoie le résultat dans la structure attendue par ton JS ({'data': ...})
    return Response({'data': data})


# --- API D'ENREGISTREMENT (POST) AVEC ALERTES ---
class Dhtviews(generics.CreateAPIView):
    queryset = Dht11.objects.all()
    serializer_class = DHT11serialize

    def perform_create(self, serializer):
        instance = serializer.save()
        temp = instance.temp

        # Vérification du seuil d'alerte
        if temp > 25:
            # 1) Email
            try:
                send_mail(
                    subject="⚠️ Alerte Température élevée",
                    message=f"Bonjour monsieur nous sommes BOUTALOUNT Oussama et Azaal Inass. La température a atteint {temp:.1f} °C à {instance.dt}.",
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=["oussama.boutalount.23@ump.ac.ma"],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Erreur envoi email: {e}")

            # 2) Telegram
            try:
                msg = f"⚠️ Alerte DHT11: {temp:.1f} °C (>25) à {instance.dt}"
                send_telegram(msg)
            except Exception as e:
                print(f"Erreur envoi Telegram: {e}")