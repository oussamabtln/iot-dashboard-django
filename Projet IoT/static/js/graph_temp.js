{% load static %}
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Historique & Analyse Température</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>⚡</text></svg>">

    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <style>
        /* --- 1. DESIGN GÉNÉRAL --- */
        body {
            font-family: 'Poppins', sans-serif;
            background: linear-gradient(135deg, #FF9966 0%, #FF5E62 100%); /* Fond Chaud */
            min-height: 100vh;
            margin: 0;
            padding: 20px;
            color: #333;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        /* --- 2. LAYOUT EN 2 PARTIES --- */
        .main-wrapper {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            max-width: 1200px;
            width: 100%;
            margin-top: 20px;
        }

        /* --- 3. CARTE DU "TOON" (GAUCHE) --- */
        .toon-card {
            flex: 1;
            min-width: 300px;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 30px;
            padding: 40px;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0,0,0,0.2);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }

        #toon-icon {
            font-size: 8rem; /* Très grande icône */
            margin-bottom: 20px;
            transition: all 0.5s ease;
        }

        .toon-status {
            font-size: 1.5rem;
            font-weight: 800;
            text-transform: uppercase;
            color: #FF5E62;
        }

        .toon-desc {
            color: #777;
            font-size: 0.9rem;
            margin-top: 10px;
        }

        /* --- 4. CARTE DU GRAPHIQUE (DROITE) --- */
        .chart-card {
            flex: 2;
            min-width: 300px;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 30px;
            padding: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.2);
            height: 450px; /* Hauteur fixe pour le graphe */
            position: relative;
        }

        h1 { margin: 0 0 20px 0; color: #333; font-size: 1.5rem; }

        /* --- 5. BOUTONS --- */
        .btn-container {
            width: 100%;
            max-width: 1200px;
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }

        .btn {
            padding: 10px 20px;
            border-radius: 50px;
            text-decoration: none;
            color: white;
            font-weight: 600;
            background: rgba(0,0,0,0.3);
            transition: 0.3s;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        .btn:hover { background: rgba(0,0,0,0.5); transform: translateY(-3px); }
        .btn-download { background: #27ae60; }
        .btn-download:hover { background: #219150; }

        /* --- 6. ANIMATIONS CSS --- */

        /* Animation : Tremblement (Froid) */
        @keyframes shake {
            0% { transform: translate(1px, 1px) rotate(0deg); }
            10% { transform: translate(-1px, -2px) rotate(-1deg); }
            20% { transform: translate(-3px, 0px) rotate(1deg); }
            30% { transform: translate(3px, 2px) rotate(0deg); }
            40% { transform: translate(1px, -1px) rotate(1deg); }
            50% { transform: translate(-1px, 2px) rotate(-1deg); }
            60% { transform: translate(-3px, 1px) rotate(0deg); }
            70% { transform: translate(3px, 1px) rotate(-1deg); }
            80% { transform: translate(-1px, -1px) rotate(1deg); }
            90% { transform: translate(1px, 2px) rotate(0deg); }
            100% { transform: translate(1px, -2px) rotate(-1deg); }
        }
        .shaking { animation: shake 0.5s; animation-iteration-count: infinite; color: #3498db; }

        /* Animation : Pulsation (Chaud) */
        @keyframes pulse-red {
            0% { transform: scale(1); text-shadow: 0 0 0 rgba(255, 0, 0, 0.7); }
            50% { transform: scale(1.1); text-shadow: 0 0 20px rgba(255, 0, 0, 0); }
            100% { transform: scale(1); text-shadow: 0 0 0 rgba(255, 0, 0, 0); }
        }
        .sweating { animation: pulse-red 1.5s infinite; color: #e74c3c; }

        /* Animation : Rebond (Normal) */
        @keyframes bounce {
            0%, 20%, 50%, 80%, 100% {transform: translateY(0);}
            40% {transform: translateY(-20px);}
            60% {transform: translateY(-10px);}
        }
        .happy { animation: bounce 2s infinite; color: #f1c40f; }

    </style>
</head>
<body>

    <div class="btn-container">
        <a href="/" class="btn"><i class="fas fa-arrow-left"></i> Retour</a>

        <a href="/download_csv/" class="btn btn-download">
            <i class="fas fa-file-csv"></i> Exporter CSV
        </a>
    </div>

    <div class="main-wrapper">

        <div class="toon-card">
            <div id="toon-icon"><i class="fas fa-spinner fa-spin"></i></div>

            <div id="toon-text" class="toon-status">Chargement...</div>
            <div id="toon-desc" class="toon-desc">Analyse des données capteur</div>

            <hr style="width: 50%; margin: 20px auto; border: 1px solid #eee;">
           
        </div>

        <div class="chart-card">
            <h1><i class="fas fa-chart-line"></i> Évolution Température</h1>
            <canvas id="tempChart"></canvas>
        </div>

    </div>

    <script src="{% static 'js/graph_temp.js' %}"></script>

</body>
</html>