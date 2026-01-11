# DHT/views.py
import csv
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction, models
from django.contrib import messages
from .models import IncidentComment

from .models import Dht11, Incident, OperateurProfile
from .services import process_temperature_event


def healthz(request):
    return JsonResponse({"status": "ok"})


# ==============================
# AUTH : LOGIN / LOGOUT
# ==============================
class OperateurLoginView(LoginView):
    template_name = "login.html"
    redirect_authenticated_user = True


class OperateurLogoutView(LogoutView):
    next_page = reverse_lazy("login")


MIN_OK = 2.0
MAX_OK = 8.0

ROLE_CHOICES = (
    ("OP1", "Opérateur 1"),
    ("CHEF", "Chef équipe"),
    ("DIRECTEUR", "Directeur"),
)


# ==============================
# Helpers rôles / profils
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
    return str(prof.niveau).upper() in {"DIRECTEUR", "3"}


def directeur_exists():
    return OperateurProfile.objects.filter(models.Q(niveau=3) | models.Q(niveau="DIRECTEUR")).exists()


def normalize_role_for_profile(role_code: str):
    role_code = (role_code or "").upper().strip()
    mapping_int = {"OP1": 1, "CHEF": 2, "DIRECTEUR": 3}
    return mapping_int.get(role_code, 1)


# ==========================================
# DASHBOARD
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
# TOGGLE ALARME
# ==========================================
@login_required
@require_POST
def toggle_alarm(request):
    current = bool(request.session.get("manual_mute", False))
    request.session["manual_mute"] = not current
    return JsonResponse({"ok": True, "manual_mute": request.session["manual_mute"]})


# ==========================================
# ACK
# ==========================================
@login_required
def valider_incident(request):
    if request.method == "POST":
        note_user = (request.POST.get("note") or "").strip() or "Alarme acquittée"
        operateur_actuel = (request.POST.get("operator") or "Opérateur 1").strip()

        try:
            compteur_actuel = int(request.POST.get("compteur_val") or 0)
        except Exception:
            compteur_actuel = 0

        inc = Incident.objects.filter(is_open=True).order_by("-created_at").first()
        if inc:
            if compteur_actuel > (inc.counter or 0):
                inc.counter = min(9, compteur_actuel)

            op = operateur_actuel.lower().strip()

            if ("opérateur 1" in op) or ("operateur 1" in op) or ("op1" in op):
                inc.op1_ack = True
                inc.op1_comment = note_user
                IncidentComment.objects.create(
                    incident=inc,
                    role="OP1",
                    text=note_user,
                    user=request.user
                )

            elif ("chef" in op) or ("opérateur 2" in op) or ("operateur 2" in op) or ("op2" in op):
                inc.op2_ack = True
                inc.op2_comment = note_user
                IncidentComment.objects.create(
                    incident=inc,
                    role="OP2",
                    text=note_user,
                    user=request.user
                )

            elif ("directeur" in op) or ("opérateur 3" in op) or ("operateur 3" in op) or ("op3" in op):
                inc.op3_ack = True
                inc.op3_comment = note_user
                IncidentComment.objects.create(
                    incident=inc,
                    role="OP3",
                    text=note_user,
                    user=request.user
                )

            else:
                inc.op1_ack = True
                inc.op1_comment = note_user

            inc.save()

        request.session["alarme_coupee"] = True

    return redirect("dashboard")


# ==========================================
# API LATEST (dashboard fetch)
# ==========================================
def latest_json(request):
    data = Dht11.objects.last()
    last_dt_str = ""
    if data and data.dt:
        last_dt_str = timezone.localtime(data.dt).strftime("%d/%m/%Y %H:%M:%S")

    if not data or data.temp is None or data.hum is None:
        return JsonResponse({
            "temperature": 0,
            "humidity": 0,
            "last_dt": last_dt_str,

            "alarme_coupee": False,
            "message": "Pas d’incident",
            "incident": {"active": False}
        })

    t = float(data.temp)
    h = float(data.hum)
    now = timezone.now()

    inc = Incident.objects.filter(is_open=True).order_by("-created_at").first()
    in_range = (MIN_OK <= t <= MAX_OK)
    manual_mute = bool(request.session.get("manual_mute", False))

    if in_range:
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
            "message": "Pas d’incident",
            "incident": {"active": False}
        })

    kind = "HOT" if t > MAX_OK else "COLD"

    if not inc:
        inc = Incident.objects.create(
            kind=kind,
            max_temp=t,
            counter=1,
            last_counter_at=now,
            last_dht_id=data.id,
            is_open=True,
            temp_min_autorisee=MIN_OK,
            temp_max_autorisee=MAX_OK,
        )
    else:
        inc.kind = kind
        if inc.max_temp is None:
            inc.max_temp = t
        else:
            if inc.kind == "HOT" and t > float(inc.max_temp):
                inc.max_temp = t
            if inc.kind == "COLD" and t < float(inc.max_temp):
                inc.max_temp = t

        if inc.last_dht_id != data.id:
            inc.counter = min(9, (inc.counter or 0) + 1)
            inc.last_dht_id = data.id

        inc.save()

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
    last_dt_str = ""
    if data.dt:
        last_dt_str = data.dt.astimezone(timezone.get_current_timezone()).strftime("%d/%m/%Y %H:%M:%S")

    return JsonResponse({
        "temperature": t,
        "humidity": h,
        "last_dt": last_dt_str,
        "alarme_coupee": mute_global,
        "message": "Incident en cours",
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
            "op1_comment": getattr(inc, "op1_comment", "") or "",
            "op2_comment": getattr(inc, "op2_comment", "") or "",
            "op3_comment": getattr(inc, "op3_comment", "") or "",
        }
    })


# ==========================================
# Simulation (IMPORTANT: déclenche alertes)
# ==========================================
@login_required
def simulation_data(request):
    if request.method == "POST":
        temp = float(request.POST.get("temp"))
        hum = float(request.POST.get("hum"))

        Dht11.objects.create(temp=temp, hum=hum)

        # ✅ même système que l'API POST
        process_temperature_event(temp, recipients=["oussama.boutalount.23@ump.ac.ma"])

        messages.success(request, "Simulation injectée ✅ (alerte envoyée si hors plage)")
        return redirect("dashboard")

    return redirect("dashboard")


# ==========================================
# Graph / Table
# ==========================================
@login_required
def graph_temp(request):
    qs = list(reversed(Dht11.objects.order_by("-dt")[:200]))
    labels = [(d.dt.strftime("%d/%m %H:%M:%S") if d.dt else "") for d in qs]
    values = [d.temp for d in qs]
    return render(request, "graph_temp.html", {"labels": labels, "values": values})


@login_required
def graph_hum(request):
    qs = list(reversed(Dht11.objects.order_by("-dt")[:200]))
    labels = [(d.dt.strftime("%d/%m %H:%M:%S") if d.dt else "") for d in qs]
    values = [d.hum for d in qs]
    return render(request, "graph_hum.html", {"labels": labels, "values": values})


@login_required
def table(request):
    datas = Dht11.objects.order_by("-dt")[:300]
    return render(request, "table.html", {"datas": datas})


# ==========================================
# CSV
# ==========================================
@login_required
def download_dht_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="historique_dht.csv"'
    writer = csv.writer(response)
    writer.writerow(["Date", "Heure", "Température (°C)", "Humidité (%)"])

    for d in Dht11.objects.all().order_by("-dt"):
        writer.writerow([
            d.dt.date() if d.dt else "",
            d.dt.time().strftime("%H:%M:%S") if d.dt else "",
            d.temp,
            d.hum
        ])
    return response


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


# ==========================================
# Pages incidents
# ==========================================
@login_required
def incident_archive(request):
    incidents = Incident.objects.filter(is_open=False).order_by("-ended_at", "-created_at")
    return render(request, "incident_archive.html", {"incidents": incidents})


@login_required
def incident_detail(request, pk):
    incident = get_object_or_404(Incident, pk=pk)

    # جيب جميع التعاليق مرتبة بالوقت
    comments = incident.comments.select_related("user").order_by("created_at")

    return render(request, "incident_detail.html", {
        "incident": incident,
        "comments": comments,
    })

# ==========================================
# DIRECTEUR: créer compte
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
        email = (request.POST.get("email") or "").strip()
        telegram = (request.POST.get("telegram") or "").strip()
        role = (request.POST.get("role") or "OP1").strip()

        if role.upper() == "DIRECTEUR" and directeur_exists():
            messages.error(request, "❌ Il existe déjà un Directeur.")
            return redirect("create_operateur")

        if not username or not password:
            messages.error(request, "Username et mot de passe sont obligatoires.")
            return redirect("create_operateur")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Ce username existe déjà.")
            return redirect("create_operateur")

        with transaction.atomic():
            user = User.objects.create_user(username=username, password=password, email=email)
            user.is_active = True
            user.save()

            OperateurProfile.objects.create(
                user=user,
                prenom=prenom,
                nom=nom,
                telephone=telephone,
                email=email,
                telegram=telegram,
                niveau=normalize_role_for_profile(role),
            )

        messages.success(request, "✅ Compte créé. Connecte-toi maintenant.")
        return redirect("login")

    return render(request, "create_operateur.html", {"roles": ROLE_CHOICES})


# ==========================================
# DIRECTEUR: purge data
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


# ==========================================
# Signup request (en attente)
# ==========================================
def signup_request(request):
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = (request.POST.get("password") or "").strip()
        prenom = (request.POST.get("prenom") or "").strip()
        nom = (request.POST.get("nom") or "").strip()
        telephone = (request.POST.get("telephone") or "").strip()
        email = (request.POST.get("email") or "").strip()
        telegram = (request.POST.get("telegram") or "").strip()

        if not username or not password:
            messages.error(request, "Username et mot de passe sont obligatoires.")
            return redirect("signup_request")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Ce username existe déjà.")
            return redirect("signup_request")

        with transaction.atomic():
            user = User.objects.create_user(username=username, password=password, email=email)
            user.is_active = False
            user.save()

            OperateurProfile.objects.create(
                user=user,
                prenom=prenom,
                nom=nom,
                telephone=telephone,
                email=email,
                telegram=telegram,
                niveau=1,
            )

        messages.success(request, "✅ Compte créé. Attends l'autorisation du Directeur.")
        return redirect("login")

    return render(request, "signup.html")


# ==========================================
# Pending users
# ==========================================
@login_required
def pending_users(request):
    if not is_directeur(request.user):
        messages.error(request, "Accès refusé : réservé au Directeur.")
        return redirect("dashboard")

    users = User.objects.filter(is_active=False).order_by("-date_joined")
    return render(request, "pending_users.html", {"users": users})


@login_required
def approve_user(request, user_id):
    if not is_directeur(request.user):
        messages.error(request, "Accès refusé : réservé au Directeur.")
        return redirect("dashboard")

    user = get_object_or_404(User, id=user_id)
    if user.is_superuser:
        messages.error(request, "Action interdite.")
        return redirect("pending_users")

    user.is_active = True
    user.save()
    messages.success(request, f"✅ {user.username} autorisé.")
    return redirect("pending_users")


@login_required
def reject_user(request, user_id):
    if not is_directeur(request.user):
        messages.error(request, "Accès refusé : réservé au Directeur.")
        return redirect("dashboard")

    user = get_object_or_404(User, id=user_id)
    if user.is_superuser:
        messages.error(request, "Action interdite.")
        return redirect("pending_users")

    user.delete()
    messages.success(request, "❌ Compte supprimé.")
    return redirect("pending_users")


@login_required
def my_data(request):
    profile = OperateurProfile.objects.filter(user=request.user).first()
    return render(request, "my_data.html", {"profile": profile})


@login_required
@require_POST
def delete_my_account(request):
    pwd = (request.POST.get("password") or "").strip()

    if request.user.is_superuser:
        messages.error(request, "Action interdite pour ce compte.")
        return redirect("dashboard")

    if not request.user.check_password(pwd):
        messages.error(request, "❌ Mot de passe incorrect. Suppression annulée.")
        return redirect("dashboard")

    request.session.flush()
    request.user.delete()
    return redirect("login")
