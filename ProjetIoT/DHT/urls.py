from django.urls import path
from . import views
from . import api

urlpatterns = [
    path("login/", views.OperateurLoginView.as_view(), name="login"),
    path("logout/", views.OperateurLogoutView.as_view(next_page="login"), name="logout"),

    path("signup/", views.signup_request, name="signup_request"),

    path("", views.dashboard, name="dashboard"),

    path("my-data/", views.my_data, name="my_data"),
    path("me/", views.my_data, name="me"),  # ✅ même page, autre URL

    path("accounts/create/", views.create_operateur, name="create_operateur"),
    path("purge/", views.purge_data, name="purge_data"),

    path("accounts/pending/", views.pending_users, name="pending_users"),
    path("accounts/approve/<int:user_id>/", views.approve_user, name="approve_user"),
    path("accounts/reject/<int:user_id>/", views.reject_user, name="reject_user"),

    path("accounts/delete-me/", views.delete_my_account, name="delete_my_account"),

    path("api/", api.Dlist, name="json"),
    path("api/post", api.Dhtviews.as_view(), name="json_post"),
    path("api/post/", api.Dhtviews.as_view(), name="json_post_slash"),  # ✅ optionnel

    path("latest/", views.latest_json, name="latest_json"),
    path("toggle-alarm/", views.toggle_alarm, name="toggle_alarm"),

    path("simulation/", views.simulation_data, name="simulation_data"),
    path("valider_incident/", views.valider_incident, name="valider_incident"),

    path("graph-temp/", views.graph_temp, name="graph_temp"),
    path("graph-hum/", views.graph_hum, name="graph_hum"),
    path("index/", views.table, name="table"),

    path("csv/dht/", views.download_dht_csv, name="csv_dht"),
    path("csv/incidents/", views.incident_archive_csv, name="csv_incidents"),

    path("incident/archive/", views.incident_archive, name="incident_archive"),
    path("incident/<int:pk>/", views.incident_detail, name="incident_detail"),

    path("healthz/", views.healthz, name="healthz"),
]
