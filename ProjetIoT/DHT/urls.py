from django.urls import path
from . import views
from . import api

urlpatterns = [
    # Auth
    path("login/", views.OperateurLoginView.as_view(), name="login"),
    path("logout/", views.OperateurLogoutView.as_view(), name="logout"),

    # Dashboard
    path("", views.dashboard, name="dashboard"),

    # ✅ Directeur: créer compte + purge
    path("accounts/create/", views.create_operateur, name="create_operateur"),
    path("purge/", views.purge_data, name="purge_data"),

    # API
    path("api/", api.Dlist, name="json"),
    path("api/post", api.Dhtviews.as_view(), name="json_post"),

    # latest JSON (dashboard fetch)
    path("latest/", views.latest_json, name="latest_json"),

    # ✅ IMPORTANT: toggle alarme (AJOUTÉ)
    path("toggle-alarm/", views.toggle_alarm, name="toggle_alarm"),

    # Simulation + ack
    path("simulation/", views.simulation_data, name="simulation_data"),
    path("valider_incident/", views.valider_incident, name="valider_incident"),

    # Graphes
    path("myChart/", views.graphique, name="myChart"),
    path("graph-temp/", views.graph_temp, name="graph_temp"),
    path("graph-hum/", views.graph_hum, name="graph_hum"),

    # Table
    path("index/", views.table, name="table"),

    # CSV
    path("download_csv/", views.download_csv, name="download_csv"),
    path("csv/dht/", views.download_dht_csv, name="csv_dht"),
    path("csv/incidents/", views.csv_incidents, name="csv_incidents"),

    # Incidents
    path("incident/archive/", views.incident_archive, name="incident_archive"),
    path("incident/<int:pk>/", views.incident_detail, name="incident_detail"),
]
