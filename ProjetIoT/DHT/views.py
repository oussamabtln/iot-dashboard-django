from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from datetime import timedelta
import csv

from django.views.decorators.http import require_POST

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.models import User
from django.db import transaction
from django.db import models

from .models import Dht11, Incident, OperateurProfile


MIN_OK = 2.0
MAX_OK = 8.0
COUNTER_STEP_SECONDS = 30  # ✅ compteur auto chaque 30s

ROLE_CHOICES = (
    ("OP1", "Opérateur 1"),
    ("CHEF", "Chef équipe"),
    ("DIRECTEUR", "Directeur"),
)


# ==============================
# Helpers: rôles / profils
# ==============================
def role_label(niveau):
    v = str(niveau).upper()
    if v in {"OP1", "1"}:
        return "Opérateur 1"
    if v in {"CHEF", "2"}:
        return "Chef équipe"
    if v in {"DIRECTEUR", "3"}:
        return "Directeur"
    return str(niveau)


def is_directeur(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    prof = OperateurProfile.objects.filter(user=user).first()
    if not prof:
        return False
    v = str(prof.niveau).upper()
    return v in {"DIRECTEUR", "3"}


def normalize_role_for_profile(role_code: str):
    """
    Stocke OP1/CHEF/DIRECTEUR si niveau est CharField
    ou 1/2/3 si niveau est IntegerField (selon ton model)
    """
    role_code = (role_code or "").upper().strip()

    mapping_int = {"OP1": 1, "CHEF": 2, "DIRECTEUR": 3}
    mapping_str = {"OP1": "OP1", "CHEF": "CHEF", "DIRECTEUR": "DIRECTEUR"}

    field = OperateurProfile._meta.get_field("niveau")
    if isinstance(field, (models.IntegerField, models.SmallIntegerField, models.PositiveSmallIntegerField)):
        return mapping_int.get(role_code, 1)
    return mapping_str.get(role_code, "OP1")


# ==============================
# AUTH : LOGIN / LOGOUT
# ==============================
class OperateurLoginView(LoginView):
    template_name = "login.html"
    redirect_authenticated_user = True


class OperateurLogoutView(LogoutView):
    pass


# ==========================================
# 1) DASHBOARD
# ==========================================
@login_required
def dashboard(request):
    nb_incidents = Incident.objects.filter(is_open=False).count()
    incidents = Incident.objects.filter(is_open=False).order_by("-ended_at", "-created_at")[:30]

    profile = OperateurProfile.objects.filter(user=request.user).first()

    return render(request, "dashboard.html", {
        "nb_incidents": nb_incidents,
        "incidents": incidents,
        "profile": profile,
        "is_directeur": is_directeur(request.user),
        "role_label": role_label(profile.niveau) if profile else "",
    })


# ==========================================
# ✅ 1bis) TOGGLE ALARME (AJOUTÉ)
# ==========================================
@login_required
@require_POST
def toggle_alarm(request):
    """
    Active/Désactive l'alarme manuellement via session.
    Important: ne supprime pas les ACK, c'est juste un mute manuel.
    """
    current = bool(request.session.get("manual_mute", False))
    request.session["manual_mute"] = not current
    return JsonResponse({
        "ok": True,
        "manual_mute": request.session["manual_mute"],
    })


# ==========================================
# 2) ACK (ACQUITTEMENT)
# ==========================================
@login_required
def valider_incident(request):
    if request.method == "POST":
        note_user = (request.POST.get("note") or "").strip() or "Alarme acquittée"
        operateur_actuel = (request.POST.get("operator") or "Opérateur 1").strip()

        try:
            compteur_actuel = int(request.POST.get("compteur_val") or 0)
        except:
            compteur_actuel = 0

        inc = Incident.objects.filter(is_open=True).order_by("-created_at").first()
        if inc:
            if compteur_actuel > (inc.counter or 0):
                inc.counter = min(9, compteur_actuel)

            op = operateur_actuel.lower().strip()

            if ("opérateur 1" in op) or ("operateur 1" in op) or ("op1" in op) or ("operateur1" in op) or ("opérateur1" in op):
                inc.op1_ack = True
                inc.op1_comment = note_user

            elif ("chef" in op) or ("opérateur 2" in op) or ("operateur 2" in op) or ("op2" in op) or ("operateur2" in op) or ("opérateur2" in op):
                inc.op2_ack = True
                inc.op2_comment = note_user

            elif ("directeur" in op) or ("opérateur 3" in op) or ("operateur 3" in op) or ("op3" in op) or ("operateur3" in op) or ("opérateur3" in op):
                inc.op3_ack = True
                inc.op3_comment = note_user

            else:
                inc.op1_ack = True
                inc.op1_comment = note_user

            inc.save()

        # tes sessions existantes
        request.session["alarme_coupee"] = True

    return redirect("dashboard")


# ==========================================
# 3) API LATEST (JSON)
# ==========================================
def latest_json(request):
    data = Dht11.objects.last()
    if not data or data.temp is None or data.hum is None:
        return JsonResponse({
            "temperature": 0,
            "humidity": 0,
            "alarme_coupee": False,
            "incident": {"active": False}
        })

    t = float(data.temp)
    h = float(data.hum)
    now = timezone.now()

    inc = Incident.objects.filter(is_open=True).order_by("-created_at").first()
    in_range = (MIN_OK <= t <= MAX_OK)

    # ✅ mute manuel via session (bouton TOGGLE)
    manual_mute = bool(request.session.get("manual_mute", False))

    if in_range:
        # si la température redevient normale => on réactive tout
        request.session["alarme_coupee"] = False
        request.session["manual_mute"] = False

        if inc:
            inc.is_open = False
            inc.ended_at = now
            inc.save(update_fields=["is_open", "ended_at"])

        return JsonResponse({
            "temperature": t,
            "humidity": h,
            "alarme_coupee": False,
            "incident": {"active": False}
        })

    if not inc:
        inc = Incident.objects.create(
            kind="HOT" if t > MAX_OK else "COLD",
            max_temp=t,
            counter=1,
            last_counter_at=now,
            is_open=True,
            temp_min_autorisee=MIN_OK,
            temp_max_autorisee=MAX_OK,
        )
    else:
        if inc.max_temp is None:
            inc.max_temp = t
        else:
            if inc.kind == "HOT":
                if t > float(inc.max_temp):
                    inc.max_temp = t
            else:
                if t < float(inc.max_temp):
                    inc.max_temp = t

        if (inc.counter or 0) < 9:
            if inc.last_counter_at is None:
                inc.last_counter_at = now
            else:
                delta_seconds = (now - inc.last_counter_at).total_seconds()
                if delta_seconds >= COUNTER_STEP_SECONDS:
                    steps = int(delta_seconds // COUNTER_STEP_SECONDS)
                    inc.counter = min(9, (inc.counter or 0) + steps)
                    inc.last_counter_at = inc.last_counter_at + timedelta(seconds=steps * COUNTER_STEP_SECONDS)

        inc.save()

    # ✅ l'alarme est coupée si un ACK existe OU si mute manuel activé
    mute_global = bool(inc.op1_ack or inc.op2_ack or inc.op3_ack or manual_mute)

    ack_by = ""
    if inc.op3_ack:
        ack_by = "Directeur"
    elif inc.op2_ack:
        ack_by = "Chef Équipe"
    elif inc.op1_ack:
        ack_by = "Opérateur 1"
    elif manual_mute:
        ack_by = "Mode manuel"

    return JsonResponse({
        "temperature": t,
        "humidity": h,
        "alarme_coupee": mute_global,
        "incident": {
            "active": True,
            "id": inc.id,
            "counter": inc.counter,
            "kind": inc.kind,
            "max_temp": inc.max_temp,
            "op1_ack": inc.op1_ack,
            "op2_ack": inc.op2_ack,
            "op3_ack": inc.op3_ack,
            "ack_by": ack_by,
            "op1_comment": getattr(inc, "op1_comment", ""),
            "op2_comment": getattr(inc, "op2_comment", ""),
            "op3_comment": getattr(inc, "op3_comment", ""),
        }
    })


# ==========================================
# 4) SIMULATION
# ==========================================
@login_required
def simulation_data(request):
    if request.method == "POST":
        t = request.POST.get("temp")
        h = request.POST.get("hum")
        if t and h:
            try:
                Dht11.objects.create(temp=float(t), hum=float(h))
            except:
                pass
    return redirect("dashboard")


# ==========================================
# 5) GRAPHS
# ==========================================
@login_required
def graph_temp(request):
    qs = Dht11.objects.order_by("-dt")[:200]
    qs = list(reversed(qs))
    labels = [(d.dt.strftime("%d/%m %H:%M:%S") if d.dt else "") for d in qs]
    values = [d.temp for d in qs]
    return render(request, "graph_temp.html", {"labels": labels, "values": values})


@login_required
def graph_hum(request):
    qs = Dht11.objects.order_by("-dt")[:200]
    qs = list(reversed(qs))
    labels = [(d.dt.strftime("%d/%m %H:%M:%S") if d.dt else "") for d in qs]
    values = [d.hum for d in qs]
    return render(request, "graph_hum.html", {"labels": labels, "values": values})


@login_required
def graphique(request):
    datas = Dht11.objects.order_by("-dt")[:200]
    return render(request, "chart.html", {"data": datas})


# ==========================================
# 6) TABLE
# ==========================================
@login_required
def table(request):
    datas = Dht11.objects.order_by("-dt")[:300]
    return render(request, "table.html", {"datas": datas})


# ==========================================
# 7) CSV
# ==========================================
@login_required
def download_dht_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="historique_dht.csv"'
    writer = csv.writer(response)
    writer.writerow(["Date", "Heure", "Température (°C)", "Humidité (%)"])

    datas = Dht11.objects.all().order_by("-dt")
    for d in datas:
        writer.writerow([
            d.dt.date() if d.dt else "",
            d.dt.time().strftime("%H:%M:%S") if d.dt else "",
            d.temp,
            d.hum
        ])
    return response


@login_required
def download_csv(request):
    return download_dht_csv(request)


@login_required
def incident_archive_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="rapport_incidents.csv"'
    writer = csv.writer(response)

    writer.writerow(["ID", "Début", "Fin", "Type", "Temp extrême", "Compteur", "O1", "O2", "O3"])

    incidents = Incident.objects.filter(is_open=False).order_by("-ended_at", "-created_at")
    for i in incidents:
        writer.writerow([
            i.id,
            i.created_at.strftime("%d/%m/%Y %H:%M:%S") if i.created_at else "",
            i.ended_at.strftime("%d/%m/%Y %H:%M:%S") if i.ended_at else "",
            i.kind,
            i.max_temp,
            i.counter,
            "OK" if i.op1_ack else "NO",
            "OK" if i.op2_ack else "NO",
            "OK" if i.op3_ack else "NO",
        ])
    return response


@login_required
def csv_incidents(request):
    return incident_archive_csv(request)


# ==========================================
# 8) ARCHIVES + DETAILS
# ==========================================
@login_required
def incident_archive(request):
    incidents = Incident.objects.filter(is_open=False).order_by("-ended_at", "-created_at")
    return render(request, "incident_archive.html", {"incidents": incidents})


@login_required
def incident_detail(request, pk):
    incident = get_object_or_404(Incident, pk=pk)
    return render(request, "incident_detail.html", {"incident": incident})


# ==========================================
# ✅ DIRECTEUR: créer compte opérateur
# ==========================================
@login_required
def create_operateur(request):
    if not is_directeur(request.user):
        messages.error(request, "Accès refusé : réservé au Directeur.")
        return redirect("dashboard")

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = (request.POST.get("password") or "").strip()
        prenom = (request.POST.get("prenom") or "").strip()
        nom = (request.POST.get("nom") or "").strip()
        telephone = (request.POST.get("telephone") or "").strip()
        role = (request.POST.get("role") or "OP1").strip()

        if not username or not password:
            messages.error(request, "Username et mot de passe sont obligatoires.")
            return redirect("create_operateur")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Ce username existe déjà.")
            return redirect("create_operateur")

        with transaction.atomic():
            user = User.objects.create_user(username=username, password=password)
            OperateurProfile.objects.create(
                user=user,
                prenom=prenom,
                nom=nom,
                telephone=telephone,
                niveau=normalize_role_for_profile(role),
            )

        messages.success(request, "✅ Compte créé avec succès.")
        return redirect("dashboard")

    return render(request, "create_operateur.html", {"roles": ROLE_CHOICES})


# ==========================================
# ✅ DIRECTEUR: purge données + mot de passe
# ==========================================
@login_required
def purge_data(request):
    if not is_directeur(request.user):
        messages.error(request, "Accès refusé : réservé au Directeur.")
        return redirect("dashboard")

    if request.method != "POST":
        return redirect("dashboard")

    pwd = request.POST.get("password", "")
    if not request.user.check_password(pwd):
        messages.error(request, "❌ Mot de passe incorrect. Purge annulée.")
        return redirect("dashboard")

    Dht11.objects.all().delete()
    Incident.objects.all().delete()

    messages.success(request, "🧹 Données vidées (DHT + Incidents).")
    return redirect("dashboard")
