#include <ESP8266WiFi.h>
#include <ESPAsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <DHT.h>

// ===== WiFi =====
const char* ssid     = "Iphonei";
const char* password = "Imane.123";

// ===== DHT =====
#define DHTPIN D5
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);
float t = NAN, h = NAN;

// ===== Web =====
AsyncWebServer server(80);

// Polished, auto-updating UI (no template placeholders needed)
const char index_html[] PROGMEM = R"HTML(
<!DOCTYPE html><html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ESP8266 • DHT Monitor</title>
<style>
  :root { --bg:#0f172a; --card:#111827; --text:#e5e7eb; --muted:#9ca3af; --accent:#22c55e; --bad:#ef4444; }
  *{box-sizing:border-box} body{margin:0;background:linear-gradient(135deg,#0b1223,#111827);color:var(--text);font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,"Helvetica Neue",Arial}
  .wrap{max-width:720px;margin:40px auto;padding:24px}
  .card{background:rgba(17,24,39,.7);backdrop-filter:blur(8px);border:1px solid #1f2937;border-radius:20px;padding:20px;box-shadow:0 10px 30px rgba(0,0,0,.25)}
  header{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px}
  .title{font-weight:700;font-size:20px;letter-spacing:.3px}
  .pill{font-size:12px;padding:6px 10px;border-radius:999px;background:#1f2937;border:1px solid #374151;color:var(--muted)}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
  .metric{background:#0b1223;border:1px solid #1f2937;border-radius:16px;padding:18px}
  .label{color:var(--muted);font-size:12px;letter-spacing:.4px;text-transform:uppercase}
  .value{font-size:42px;font-weight:700;margin-top:6px}
  .unit{font-size:16px;color:var(--muted);margin-left:6px}
  .ok{color:var(--accent)} .bad{color:var(--bad)}
  .footer{margin-top:14px;color:var(--muted);font-size:13px;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}
  .btn{background:#1f2937;border:1px solid #374151;color:#e5e7eb;border-radius:10px;padding:8px 12px;font-size:13px;cursor:pointer}
  .btn:active{transform:translateY(1px)}
</style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <header>
        <div class="title">ESP8266 • DHT Monitor</div>
        <div class="pill" id="status">Starting…</div>
      </header>

      <div class="grid">
        <div class="metric">
          <div class="label">Temperature</div>
          <div class="value"><span id="temp">—</span><span class="unit">°C</span></div>
        </div>
        <div class="metric">
          <div class="label">Humidity</div>
          <div class="value"><span id="hum">—</span><span class="unit">%</span></div>
        </div>
      </div>

      <div class="footer">
        <div>Last updated: <span id="updated">—</span></div>
        <div>
          <button class="btn" id="refresh">Refresh now</button>
        </div>
      </div>
    </div>
  </div>

<script>
const elT = document.getElementById('temp');
const elH = document.getElementById('hum');
const elU = document.getElementById('updated');
const elS = document.getElementById('status');
const btn = document.getElementById('refresh');

function setStatus(text, good=true){
  elS.textContent = text;
  elS.classList.remove('ok','bad');
  elS.classList.add(good ? 'ok' : 'bad');
}

async function fetchData(){
  try{
    const r = await fetch('/api/sensor', {cache:'no-store'});
    if(!r.ok) throw new Error(r.statusText);
    const j = await r.json();
    if (isFinite(j.temperature)) elT.textContent = j.temperature.toFixed(1);
    else elT.textContent = '—';
    if (isFinite(j.humidity)) elH.textContent = j.humidity.toFixed(1);
    else elH.textContent = '—';
    const d = new Date();
    elU.textContent = d.toLocaleTimeString();
    setStatus('Online', true);
  }catch(e){
    setStatus('Offline', false);
  }
}

btn.addEventListener('click', fetchData);
fetchData();
setInterval(fetchData, 3000);
</script>
</body>
</html>
)HTML";

void setup() {
  Serial.begin(115200);
  delay(1200);
  Serial.println("\n[BOOT] DHT Monitor starting…");
  dht.begin();

  // Wi-Fi
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  Serial.printf("[WiFi] Connecting to \"%s\"", ssid);
  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && millis()-start < 15000) {
    delay(500); Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("[WiFi] Connected. IP: "); Serial.println(WiFi.localIP());
  } else {
    Serial.println("[WiFi] Failed. Starting AP.");
    WiFi.mode(WIFI_AP);
    WiFi.softAP("ESP8266-DHT", "12345678");
    Serial.print("[AP] IP: "); Serial.println(WiFi.softAPIP());
  }

  // ---- Web routes ----
  server.on("/", HTTP_GET, [](AsyncWebServerRequest *request){
    request->send_P(200, "text/html; charset=utf-8", index_html);
  });

  // JSON API for the page (and any other client/app you want)
  server.on("/api/sensor", HTTP_GET, [](AsyncWebServerRequest *request){
    String json = "{";
    json += "\"temperature\":" + (isnan(t) ? String("null") : String(t,1)) + ",";
    json += "\"humidity\":"    + (isnan(h) ? String("null") : String(h,1)) + "}";
    request->send(200, "application/json", json);
  });

  // Simple text endpoints (optional, kept for debugging)
  server.on("/temperature", HTTP_GET, [](AsyncWebServerRequest *request){
    request->send(200, "text/plain", isnan(t) ? "NaN" : String(t,1));
  });
  server.on("/humidity", HTTP_GET, [](AsyncWebServerRequest *request){
    request->send(200, "text/plain", isnan(h) ? "NaN" : String(h,1));
  });

  server.begin();
  Serial.println("[HTTP] Server started");
}

void loop() {
  static uint32_t lastRead = 0;
  if (millis() - lastRead >= 3000) {                 // update every 3s
    lastRead = millis();
    float newT = dht.readTemperature();              // °C
    float newH = dht.readHumidity();

    if (!isnan(newT)) { t = newT; Serial.printf("[DHT] T=%.1f°C\n", t); }
    else              { Serial.println("[DHT] Temp read failed"); }

    if (!isnan(newH)) { h = newH; Serial.printf("[DHT] H=%.1f%%\n", h); }
    else              { Serial.println("[DHT] Hum read failed"); }
  }
}