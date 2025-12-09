from django.urls import path
from . import views
from . import api

urlpatterns = [
    # Tes URLs existantes pour l'API
    path("api/", api.Dlist, name='json'),
    path("api/post", api.Dhtviews.as_view(), name='json'),
    path('download_csv/', views.download_csv, name='download_csv'),
    path('index/', views.table, name='table'),
    path('myChart/', views.graphique, name='myChart'),
    path("latest/", views.latest_json, name="latest_json"),

    # --- AJOUTE CES DEUX LIGNES ICI ---
    path('graph-temp/', views.graph_temp, name='graph_temp'),  # (NOUVEAU) Pour la page Température
    path('graph-hum/', views.graph_hum, name='graph_hum'),    # (NOUVEAU) Pour la page Humidité

    # La page d'accueil (Dashboard)
    path('', views.dashboard, name='dashboard'),
]