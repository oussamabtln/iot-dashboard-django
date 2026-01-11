# DHT/services.py
from django.conf import settings
from django.core.mail import send_mail


def send_email_alert(subject: str, message: str, recipients: list[str]) -> None:
    """Envoi email via Gmail SMTP (logs visibles dans console)."""
    try:
        print("[EMAIL] tentative ->", recipients)
        if not settings.EMAIL_HOST_PASSWORD:
            print("[EMAIL] ❌ EMAIL_HOST_PASSWORD vide (settings).")
            return

        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", settings.EMAIL_HOST_USER),
            recipient_list=recipients,
            fail_silently=False,
        )
        print("[EMAIL] envoyé ✅")
    except Exception as e:
        print("[EMAIL] ERREUR ❌ :", repr(e))


def send_whatsapp_twilio(message: str) -> None:
    """Envoi WhatsApp via Twilio Sandbox."""
    try:
        from twilio.rest import Client

        sid = getattr(settings, "TWILIO_ACCOUNT_SID", "")
        token = getattr(settings, "TWILIO_AUTH_TOKEN", "")
        wa_from = getattr(settings, "TWILIO_WHATSAPP_FROM", "")
        wa_to = getattr(settings, "TWILIO_WHATSAPP_TO", "")

        print("[WA] config:", bool(sid), bool(token), wa_from, wa_to)

        if not all([sid, token, wa_from, wa_to]):
            print("[WA] ❌ Configuration manquante (SID/TOKEN/FROM/TO).")
            return

        client = Client(sid, token)
        client.messages.create(from_=wa_from, to=wa_to, body=message)
        print("[WA] envoyé ✅")

    except Exception as e:
        print("[WA] ERREUR ❌ :", repr(e))


def call_twilio_voice(message: str) -> None:
    """
    Lance un appel téléphonique Twilio Voice.
    - En trial: le numéro 'TO' doit être vérifié dans Twilio.
    - Le message lu dépend du TWILIO_TWIML_URL (TwiML Bin).
    """
    try:
        from twilio.rest import Client

        sid = getattr(settings, "TWILIO_ACCOUNT_SID", "")
        token = getattr(settings, "TWILIO_AUTH_TOKEN", "")
        call_from = getattr(settings, "TWILIO_VOICE_FROM", "")
        call_to = getattr(settings, "TWILIO_CALL_TO", "")
        twiml_url = getattr(settings, "TWILIO_TWIML_URL", "")

        print("[CALL] config:", bool(sid), bool(token), call_from, call_to, twiml_url)

        if not all([sid, token, call_from, call_to, twiml_url]):
            print("[CALL] ❌ Configuration manquante (SID/TOKEN/FROM/TO/TWIML_URL).")
            return

        client = Client(sid, token)
        client.calls.create(from_=call_from, to=call_to, url=twiml_url)
        print("[CALL] appel lancé ✅")

    except Exception as e:
        print("[CALL] ERREUR ❌ :", repr(e))


def process_alert(temp: float, recipients=None, force: bool = False) -> None:
    """
    Fonction centrale:
    - Envoie Email + WhatsApp + Appel si temp hors limites.
    - force=True pour tester même si temp OK.
    """
    MIN_OK = 2.0
    MAX_OK = 8.0
    recipients = recipients or [settings.EMAIL_HOST_USER]

    print("[ALERT] temp =", temp, "force =", force)

    if not force and (MIN_OK <= float(temp) <= MAX_OK):
        print("[ALERT] temp OK -> pas d'envoi")
        return

    if float(temp) < MIN_OK:
        subject = "❄️ ALERTE CRITIQUE : GEL DÉTECTÉ"
        msg = f"URGENT: Température trop basse: {float(temp):.1f}°C (min={MIN_OK}°C)"
    elif float(temp) > MAX_OK:
        subject = "🔥 ALERTE CRITIQUE : SURCHAUFFE"
        msg = f"URGENT: Température trop haute: {float(temp):.1f}°C (max={MAX_OK}°C)"
    else:
        subject = "✅ TEST ALERTE"
        msg = f"Test alerte (temp={float(temp):.1f}°C)"

    # Email
    send_email_alert(subject, msg, recipients)

    # WhatsApp
    send_whatsapp_twilio(msg)

    # Appel
    call_twilio_voice(msg)


# Alias (compatibilité avec tes imports existants)
def process_temperature_event(temp: float, recipients=None, force: bool = False) -> None:
    return process_alert(temp, recipients=recipients, force=force)
