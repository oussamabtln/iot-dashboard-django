import os
import django
import json
import paho.mqtt.client as mqtt

# ---------------------------------------------------------
# 1. CONFIGURATION DE DJANGO (Indispensable !)
# ---------------------------------------------------------
# On dit au script où trouver les réglages du site
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'projet.settings')
django.setup()

# On importe le modèle (la table de la base de données)
# Si ton App s'appelle différemment de 'DHT', change-le ici.
from DHT.models import Dht11

# ---------------------------------------------------------
# 2. CONFIGURATION MQTT
# ---------------------------------------------------------
BROKER = "127.0.0.1"  # Adresse de Mosquitto (Ton PC)
PORT = 1883  # Le port standard
TOPIC = "sensors/esp8266-001/dht11"  # Le sujet qu'on écoute


# ---------------------------------------------------------
# 3. FONCTIONS (Ce que le script doit faire)
# ---------------------------------------------------------

def on_connect(client, userdata, flags, rc):
    """S'active quand on réussit à se connecter à Mosquitto"""
    if rc == 0:
        print("✅ CONNECTÉ À MOSQUITTO !")
        # On s'abonne au sujet
        client.subscribe(TOPIC)
        print(f"👂 En écoute sur : {TOPIC}")
    else:
        print(f"❌ Échec connexion. Code erreur : {rc}")


def on_message(client, userdata, msg):
    """S'active à chaque fois qu'un message arrive"""
    try:
        # 1. On décode le message reçu
        payload = msg.payload.decode()
        print(f"📩 Reçu : {payload}")

        # 2. On transforme le texte JSON en dictionnaire Python
        data = json.loads(payload)
        temp = data['temperature']
        hum = data['humidity']

        # 3. SAUVEGARDE DANS LA BASE DE DONNÉES DJANGO
        # On crée une nouvelle ligne dans la table Dht11
        nouvelle_mesure = Dht11(temp=temp, hum=hum)
        nouvelle_mesure.save()

        print(f"💾 Sauvegardé en BDD : {temp}°C / {hum}%")

    except Exception as e:
        print(f"⚠️ Erreur lors du traitement : {e}")


# ---------------------------------------------------------
# 4. DÉMARRAGE DU PROGRAMME
# ---------------------------------------------------------
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print("🚀 Démarrage du Subscriber...")
try:
    client.connect(BROKER, PORT, 60)
    client.loop_forever()  # Boucle infinie (ne s'arrête jamais)
except Exception as e:
    print(f"❌ Impossible de se connecter à Mosquitto : {e}")