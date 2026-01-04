/* Fichier : static/js/app.js
   Description : Cerveau du Météo-Blob et gestion de la météo
*/

const API_URL_LATEST = "/latest/";

// --- SÉLECTION DES ÉLÉMENTS HTML ---
const tempElement = document.getElementById('temp');
const humElement  = document.getElementById('hum');
const trendTempEl = document.getElementById('trend-temp');
const trendHumEl  = document.getElementById('trend-hum');
const blob        = document.getElementById('blob-character');
const blobBubble  = document.getElementById('char-bubble-text');

// Éléments Météo (Pluie, Neige, Soleil)
const weatherScene = document.getElementById('weatherScene');
const weatherParticles = document.getElementById('weatherParticles');

// --- FONCTION : CRÉER PLUIE / NEIGE ---
function createParticles(type, count) {
    // Vide les anciennes particules
    weatherParticles.innerHTML = '';
    // Ajoute la classe (rain ou snow) pour le style CSS
    weatherParticles.className = 'weather-particles ' + type;

    for (let i = 0; i < count; i++) {
        let p = document.createElement('div');
        p.className = 'particle';
        // Position horizontale aléatoire
        p.style.left = Math.random() * 100 + '%';
        // Vitesse de chute aléatoire
        p.style.animationDuration = (Math.random() * 1 + 0.5) + 's';
        // Délai de départ aléatoire (pour que ça ne tombe pas tout en même temps)
        p.style.animationDelay = Math.random() * 2 + 's';
        weatherParticles.appendChild(p);
    }
}

// --- FONCTION PRINCIPALE (Boucle) ---
async function updateDashboard() {
  try {
    const response = await fetch(API_URL_LATEST);
    if (!response.ok) throw new Error("Erreur API");
    const data = await response.json();

    // Sécurisation des noms de variables (supporte 'temp' et 'temperature')
    const t = (data.temperature !== undefined) ? data.temperature : data.temp;
    const h = (data.humidity !== undefined)    ? data.humidity    : data.hum;
    const pt = data.prev_temp;
    const ph = data.prev_hum;

    // Mise à jour Affichage Chiffres
    if (tempElement) tempElement.textContent = t;
    if (humElement)  humElement.textContent = h;

    // Mise à jour Flèches et Animation
    updateTrend(trendTempEl, t, pt, "°C");
    updateTrend(trendHumEl, h, ph, "%");
    updateWeatherAndMood(t, h);

  } catch (error) {
    console.error("Erreur:", error);
    // En cas d'erreur, message + blob bleu
    if (blobBubble) blobBubble.innerText = "Pas de signal...";
    if (blob) blob.className = "blob cold";
    weatherParticles.className = 'weather-particles'; // Stop météo
    if (weatherScene) weatherScene.classList.remove('sunny');
  }
}

// --- CERVEAU DU MONSTRE & MÉTÉO ---
function updateWeatherAndMood(temp, hum) {
    if (!blob) return;

    // 1. RESET (On remet tout à zéro)
    blob.className = "blob";
    weatherParticles.className = 'weather-particles'; // Stop pluie/neige
    weatherParticles.innerHTML = ''; // Nettoyage particules
    if (weatherScene) weatherScene.classList.remove('sunny'); // Cache le soleil

    // Remet le ciel bleu par défaut
    document.body.style.background = 'linear-gradient(135deg, #89f7fe 0%, #66a6ff 100%)';

    let text = "Tout va bien !";

    // --- CONDITIONS MÉTÉO ---

    // 1. GLACE & NEIGE (Froid extrême < 5°C)
    if (temp <= 5) {
        blob.classList.add('cold'); // Cube de glace
        createParticles('snow', 50); // Lance la neige
        text = "Brrr... Il neige ! 🌨️";
        // Fond Gris Hiver
        document.body.style.background = 'linear-gradient(135deg, #e6dada 0%, #274046 100%)';
    }

    // 2. FEU (Chaud extrême > 35°C)
    else if (temp >= 35) {
        blob.classList.add('hot'); // Rouge + Feu
        text = "AU SECOURS ! JE BRÛLE ! 🔥";
        // Fond Rouge Canicule
        document.body.style.background = 'linear-gradient(135deg, #ff4e50 0%, #f9d423 100%)';
    }

    // 3. PLUIE (Humide > 75%)
    else if (hum >= 75) {
        blob.classList.add('wet'); // Parapluie
        createParticles('rain', 100); // Lance la pluie
        text = "Il pleut ! J'ai mon parapluie ! ☔";
        // Fond Bleu Foncé Orage
        document.body.style.background = 'linear-gradient(135deg, #4b6cb7 0%, #182848 100%)';
    }

    // 4. BRONZAGE (Chaud et Sec : 25-35°C et Hum < 50%)
    else if (temp >= 25 && hum < 50) {
        blob.classList.add('tanning'); // Serviette + Lunettes
        if (weatherScene) weatherScene.classList.add('sunny'); // Affiche le soleil
        text = "Ah... La belle vie ! 😎";
        // Fond Jaune Plage
        document.body.style.background = 'linear-gradient(135deg, #fceabb 0%, #f8b500 100%)';
    }

    // 5. NORMAL (Tout le reste)
    else {
        blob.classList.add('normal'); // Vert + Rebond
        text = "Salut ! La vie est belle.";
    }

    if (blobBubble) blobBubble.innerText = text;
}

// --- FONCTION FLÈCHES ---
function updateTrend(el, cur, prev, unit) {
    if (!el || prev == null) return;
    let icon = '=';
    if (cur > prev) icon = '⬆';
    else if (cur < prev) icon = '⬇';
    el.innerHTML = `${icon} Prev: ${prev}${unit}`;
}

// --- LANCEMENT ---
// Mise à jour toutes les 2 secondes
setInterval(updateDashboard, 2000);
// Premier lancement immédiat
updateDashboard();