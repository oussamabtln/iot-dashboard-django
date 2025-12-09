from django.http import HttpResponse
from django.http import JsonResponse
from django.utils import timezone
from .models import Dht11
import csv
from .serializers import DHT11serialize
from django.shortcuts import render
from .models import Dht11

def graphique(request):
    data = Dht11.objects.all()
    return render(request, 'chart.html', {'data': data})

def test(request):
    return HttpResponse('IoT Project')

def table(request):
    derniere_ligne = Dht11.objects.last()
    derniere_date = Dht11.objects.last().dt
    delta_temps = timezone.now()
    difference_minutes = delta_temps.seconds // 60
    temps_ecoule = ' il y a ' + str(difference_minutes) + ' min'
    if difference_minutes> 60:
        temps_ecoule = ('il y ' + str(difference_minutes // 60) + 'h' +
                        str(difference_minutes % 60) + 'min')
        valeurs = {'date': temps_ecoule, 'id': derniere_ligne.id, 'temp':
            derniere_ligne.temp, 'hum': derniere_ligne.hum}
        return render(request, 'value.html', {'valeurs': valeurs})

def download_csv(request):
    # Create the HTTP response with CSV content type
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="dht.csv"'

    # Create a CSV writer
    writer = csv.writer(response)

    # Write header row
    writer.writerow(['id', 'temp', 'hum', 'dt'])

    # Query all Dht11 objects and extract desired fields
    model_values = Dht11.objects.values_list('id', 'temp', 'hum', 'dt')

    # Write data rows
    for row in model_values:
        writer.writerow(row)

    return response
def dashboard(request):
    # Rend juste la page; les données sont chargées via JS
    return render(request, "dashboard.html")


# Dans DHT/views.py

def latest_json(request):
    # 1. On récupère les 2 dernières mesures (la plus récente et celle d'avant)
    data = Dht11.objects.order_by('-dt').values('temp', 'hum', 'dt')[:2]
    data_list = list(data)

    # Sécurité si la base de données est vide
    if not data_list:
        return JsonResponse({"detail": "Pas de données"}, status=404)

    # La mesure actuelle (Indice 0)
    current = data_list[0]

    # La mesure précédente (Indice 1) - on vérifie qu'elle existe
    previous = data_list[1] if len(data_list) > 1 else None

    # 2. On renvoie tout en JSON
    return JsonResponse({
        "temperature": current["temp"],
        "humidity": current["hum"],
        "timestamp": current["dt"].isoformat(),
        # C'est ici qu'on envoie les anciennes valeurs pour les flèches !
        "prev_temp": previous["temp"] if previous else None,
        "prev_hum": previous["hum"] if previous else None
    })
def graph_temp(request):
    # On change 'graph_temp.html' par 'graph_temp.html'
    return render(request, 'graph_temp.html')

def graph_hum(request):
    # Étape 2 : Affiche la page graphique Humidité (C'est celle qu'il manquait !)
    return render(request, 'graph_hum.html')
# Create your views here.
