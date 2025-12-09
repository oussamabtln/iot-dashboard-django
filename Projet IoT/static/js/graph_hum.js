 /* Fichier : static/js/graph_hum.js (VERSION UNIVERSELLE) */

const API_URL_LIST = "/api/";

document.addEventListener("DOMContentLoaded", function() {
    initGraphiqueHum();
});

async function initGraphiqueHum() {
    const ctx = document.getElementById('humChart').getContext('2d');

    try {
        console.log("🔍 Récupération des données depuis :", API_URL_LIST);
        const response = await fetch(API_URL_LIST);
        const jsonResponse = await response.json();

        console.log("📦 Réponse brute reçue :", jsonResponse);

        // --- PARTIE INTELLIGENTE : Recherche automatique de la liste ---
        let rawData = [];

        if (Array.isArray(jsonResponse)) {
            // Cas 1 : C'est déjà une liste [ ... ]
            rawData = jsonResponse;
        }
        else if (jsonResponse.data && Array.isArray(jsonResponse.data)) {
            // Cas 2 : C'est dans { data: [ ... ] }
            rawData = jsonResponse.data;
        }
        else if (jsonResponse.results && Array.isArray(jsonResponse.results)) {
            // Cas 3 : C'est dans { results: [ ... ] } (Standard Django REST)
            rawData = jsonResponse.results;
        }
        else {
            // Cas 4 : On ne trouve pas de liste
            console.error("❌ Impossible de trouver une liste dans la réponse JSON !");
            throw new Error("Format JSON invalide (pas de liste trouvée)");
        }
        // -------------------------------------------------------------

        // On garde les 20 dernières mesures
        const data = rawData.slice(-20);

        const labels = data.map(entry => {
            const dateObj = new Date(entry.dt);
            return dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        });

        // Extraction humidité
        // On vérifie si c'est 'hum' ou 'humidity'
        const values = data.map(entry => entry.hum !== undefined ? entry.hum : entry.humidity);

        // Mise à jour Toon
        if (values.length > 0) {
            updateToonHum(values[values.length - 1]);
        }

        // Dégradé Bleu
        let gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, 'rgba(33, 147, 176, 0.5)');
        gradient.addColorStop(1, 'rgba(33, 147, 176, 0)');

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Humidité (%)',
                    data: values,
                    borderColor: '#2193b0',
                    backgroundColor: gradient,
                    borderWidth: 3,
                    pointBackgroundColor: '#fff',
                    pointBorderColor: '#2193b0',
                    pointRadius: 5,
                    pointHoverRadius: 8,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, max: 100 },
                    x: { grid: { display: false } }
                }
            }
        });

    } catch (error) {
        console.error("🚨 ERREUR CRITIQUE :", error);
        const statusEl = document.getElementById('toon-status');
        if (statusEl) statusEl.innerText = "Erreur Données";
    }
}

// Fonction Toon inchangée
function updateToonHum(hum) {
    const iconEl = document.getElementById('toon-icon');
    const statusEl = document.getElementById('toon-status');
    const descEl = document.getElementById('toon-desc');
    if (!iconEl) return;

    iconEl.className = "";
    if (hum >= 70) {
        iconEl.innerHTML = '<i class="fas fa-umbrella"></i>';
        iconEl.classList.add('floating');
        statusEl.innerText = "ÇA MOUILLE !";
        statusEl.style.color = "#3498db";
        descEl.innerText = "Humidité élevée.";
    } else if (hum <= 30) {
        iconEl.innerHTML = '<i class="fas fa-sun"></i>';
        iconEl.classList.add('drying');
        statusEl.innerText = "C'EST SEC...";
        statusEl.style.color = "#e67e22";
        descEl.innerText = "Air sec.";
    } else {
        iconEl.innerHTML = '<i class="fas fa-cloud-sun"></i>';
        iconEl.classList.add('floating');
        statusEl.innerText = "CONFORTABLE";
        statusEl.style.color = "#2ecc71";
        descEl.innerText = "Air agréable.";
    }
}