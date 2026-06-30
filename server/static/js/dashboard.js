/* ── Config ── */
const MAX_POINTS = 60;
const WS_URL = `ws://${location.host}/ws`;
const API_BASE = "/api/sensors";

/* ── Chart setup ── */
const chartDefaults = {
  type: "line",
  options: {
    animation: false,
    responsive: true,
    maintainAspectRatio: true,
    aspectRatio: 2.5,
    plugins: { legend: { display: false } },
    scales: {
      x: {
        ticks: { color: "#8892a4", maxTicksLimit: 6, maxRotation: 0 },
        grid: { color: "#2e3248" },
      },
      y: {
        ticks: { color: "#8892a4" },
        grid: { color: "#2e3248" },
      },
    },
    elements: { point: { radius: 0 }, line: { tension: 0.3, borderWidth: 2 } },
  },
};

function makeChart(id, color) {
  const ctx = document.getElementById(id).getContext("2d");
  return new Chart(ctx, {
    ...chartDefaults,
    data: {
      labels: [],
      datasets: [{ data: [], borderColor: color, backgroundColor: color + "22", fill: true }],
    },
    options: { ...chartDefaults.options },
  });
}

const tempChart = makeChart("chart-temp", "#f97316");
const humiChart = makeChart("chart-humi", "#38bdf8");

/* ── DOM helpers ── */
const $ = (id) => document.getElementById(id);

function fmt(v, dec = 1) {
  return v != null ? Number(v).toFixed(dec) : "--";
}

function timeLabel(ts) {
  const d = new Date(ts);
  return d.toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function selectedDevice() {
  return $("device-select").value;
}

/* ── Update UI with a reading ── */
function applyReading(r) {
  $("temp-value").textContent = fmt(r.temperature);
  $("humi-value").textContent = fmt(r.humidity);
  $("last-updated").textContent = timeLabel(r.timestamp);
}

/* ── Push a point onto a chart ── */
function pushPoint(chart, label, value) {
  const { labels, datasets } = chart.data;
  labels.push(label);
  datasets[0].data.push(value);
  if (labels.length > MAX_POINTS) {
    labels.shift();
    datasets[0].data.shift();
  }
  chart.update("none");
}

function clearCharts() {
  for (const chart of [tempChart, humiChart]) {
    chart.data.labels = [];
    chart.data.datasets[0].data = [];
    chart.update("none");
  }
}

/* ── Load device list ── */
async function loadDevices() {
  try {
    const res = await fetch(`${API_BASE}/devices`);
    const devices = await res.json();
    const select = $("device-select");
    const current = select.value;

    select.innerHTML = '<option value="">デバイスを選択...</option>';
    for (const d of devices) {
      const opt = document.createElement("option");
      opt.value = d.device_id;
      opt.textContent = d.device_id;
      select.appendChild(opt);
    }

    // Restore selection or pick first device
    if (current && devices.find((d) => d.device_id === current)) {
      select.value = current;
    } else if (devices.length > 0) {
      select.value = devices[0].device_id;
    }
    return select.value;
  } catch (e) {
    console.error("loadDevices failed:", e);
    return "";
  }
}

/* ── Load history from API ── */
async function loadHistory(minutes) {
  const device = selectedDevice();
  if (!device) return;
  try {
    const res = await fetch(`${API_BASE}/history?device_id=${encodeURIComponent(device)}&minutes=${minutes}`);
    const rows = await res.json();

    clearCharts();
    const slice = rows.slice(-MAX_POINTS);
    for (const r of slice) {
      const lbl = timeLabel(r.timestamp);
      tempChart.data.labels.push(lbl);
      tempChart.data.datasets[0].data.push(r.temperature);
      humiChart.data.labels.push(lbl);
      humiChart.data.datasets[0].data.push(r.humidity);
    }
    tempChart.update("none");
    humiChart.update("none");

    if (slice.length > 0) applyReading(slice[slice.length - 1]);
  } catch (e) {
    console.error("loadHistory failed:", e);
  }
}

/* ── Load stats from API ── */
async function loadStats(minutes) {
  const device = selectedDevice();
  if (!device) return;
  try {
    const res = await fetch(`${API_BASE}/stats?device_id=${encodeURIComponent(device)}&minutes=${minutes}`);
    const s = await res.json();
    $("stat-temp-min").textContent = fmt(s.temperature.min) + " °C";
    $("stat-temp-avg").textContent = fmt(s.temperature.avg) + " °C";
    $("stat-temp-max").textContent = fmt(s.temperature.max) + " °C";
    $("stat-humi-min").textContent = fmt(s.humidity.min) + " %";
    $("stat-humi-avg").textContent = fmt(s.humidity.avg) + " %";
    $("stat-humi-max").textContent = fmt(s.humidity.max) + " %";
  } catch (e) {
    console.error("loadStats failed:", e);
  }
}

/* ── WebSocket ── */
let ws = null;
let wsRetryDelay = 2000;

function connectWS() {
  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    const el = $("ws-status");
    el.textContent = "● 接続中";
    el.className = "badge badge-connected";
    wsRetryDelay = 2000;
  };

  ws.onmessage = (ev) => {
    const r = JSON.parse(ev.data);
    // Update device list if a new device appears
    const select = $("device-select");
    const exists = [...select.options].some((o) => o.value === r.device_id);
    if (!exists) {
      const opt = document.createElement("option");
      opt.value = r.device_id;
      opt.textContent = r.device_id;
      select.appendChild(opt);
      // Auto-select if no device is selected
      if (!select.value) select.value = r.device_id;
    }

    // Only update charts for the currently selected device
    if (r.device_id !== selectedDevice()) return;

    const lbl = timeLabel(r.timestamp);
    applyReading(r);
    pushPoint(tempChart, lbl, r.temperature);
    pushPoint(humiChart, lbl, r.humidity);
    loadStats(Number($("period-select").value));
  };

  ws.onclose = ws.onerror = () => {
    const el = $("ws-status");
    el.textContent = "● 切断中";
    el.className = "badge badge-disconnected";
    setTimeout(connectWS, wsRetryDelay);
    wsRetryDelay = Math.min(wsRetryDelay * 2, 30000);
  };
}

/* ── Event listeners ── */
$("device-select").addEventListener("change", () => {
  clearCharts();
  const m = Number($("period-select").value);
  loadHistory(m);
  loadStats(m);
});

$("period-select").addEventListener("change", (e) => {
  const m = Number(e.target.value);
  loadHistory(m);
  loadStats(m);
});

// Refresh device list every 30 s (picks up newly connected ESP32s)
setInterval(loadDevices, 30_000);

/* ── Init ── */
(async () => {
  await loadDevices();
  const minutes = Number($("period-select").value);
  await loadHistory(minutes);
  await loadStats(minutes);
  connectWS();
})();
