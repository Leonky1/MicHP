(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const SEGS = 32;
  const COLOR_A = [47, 107, 242];
  const COLOR_B = [122, 172, 255];

  // ---------- meter ----------
  const meter = $("meter");
  const segs = [];
  for (let i = 0; i < SEGS; i++) {
    const d = document.createElement("div");
    d.className = "seg";
    meter.appendChild(d);
    segs.push(d);
  }
  const litColor = (i) => {
    const t = i / (SEGS - 1);
    return "rgb(" + COLOR_A.map((v, k) => Math.round(v + (COLOR_B[k] - v) * t)).join(",") + ")";
  };
  let shown = 0;
  function paintMeter(level, active) {
    const target = active ? level : 0;
    // rises fast, falls slowly (nicer to look at)
    shown = target > shown ? target : shown + (target - shown) * 0.25;
    if (shown < 0.01) shown = 0;
    const lit = Math.round(shown * SEGS);
    for (let i = 0; i < SEGS; i++) {
      segs[i].style.background = i < lit ? litColor(i) : "";
    }
  }

  // ---------- API ----------
  async function api(path, body) {
    const opts = body === undefined ? {} : {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-MicHP": "1" },
      body: JSON.stringify(body),
    };
    const r = await fetch(path, opts);
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  }

  async function act(path, body) {
    try {
      const r = await api(path, body);
      if (r && r.state) render(r.state);
      return r;
    } catch (e) {
      setOffline(true);
    }
  }

  // ---------- render ----------
  let hintMsg = "";
  let hintUntil = 0;
  let dragging = false;
  let dragTimer = null;
  let gainTimer = null;
  let lastDevicesKey = "";
  let lastOthersKey = "";

  const OFFLINE_MSG = "MicHP has stopped. Start it again.";

  function setOffline(off) {
    const w = $("warn");
    if (off) {
      w.hidden = false;
      w.textContent = OFFLINE_MSG;
    } else if (w.textContent === OFFLINE_MSG) {
      w.hidden = true;
      w.textContent = "";
    }
  }

  function renderOutputs(audio) {
    const key = JSON.stringify([audio.devices, audio.virtual_index]);
    if (key === lastDevicesKey) return;
    lastDevicesKey = key;
    const sel = $("output");
    sel.textContent = "";
    const none = document.createElement("option");
    none.value = "";
    none.textContent = audio.available ? "None" : "Audio unavailable";
    sel.appendChild(none);
    audio.devices.forEach((d) => {
      const o = document.createElement("option");
      o.value = String(d.index);
      o.textContent = d.name;
      sel.appendChild(o);
    });
    sel.value = audio.virtual_index === null ? "" : String(audio.virtual_index);
  }

  function renderOthers(devices) {
    const key = JSON.stringify(devices.slice(1));
    if (key === lastOthersKey) return;
    lastOthersKey = key;
    const box = $("others");
    box.textContent = "";
    devices.slice(1).forEach((d) => {
      const row = document.createElement("div");
      row.className = "other";
      const name = document.createElement("span");
      name.textContent = d.name; // textContent: names coming from the network must never become HTML
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = "Connect";
      btn.dataset.id = d.id;
      row.appendChild(name);
      row.appendChild(btn);
      box.appendChild(row);
    });
  }

  function fmtDuration(sec) {
    sec = Math.max(0, Math.floor(Number(sec) || 0));
    const p = (n) => String(n).padStart(2, "0");
    return p(Math.floor(sec / 3600)) + ":" + p(Math.floor(sec / 60) % 60) + ":" + p(sec % 60);
  }

  const LAST_LABELS = {
    lost: "Connection lost after",
    phone: "Phone stopped after",
  };

  // Frozen timer: the connected time of the last connection that ended on its own.
  // The rows always take up space (only hidden) so the layout does not shift.
  function renderLast(s) {
    const frozen = s.state !== "connected" && s.last_session_seconds !== null &&
      s.last_session_seconds !== undefined;
    ["lastWaiting", "lastFound"].forEach((id) => {
      const row = $(id);
      row.classList.toggle("on", frozen);
      if (!frozen) return;
      row.querySelector(".lastLabel").textContent =
        LAST_LABELS[s.last_session_reason] || LAST_LABELS.lost;
      row.querySelector(".lastValue").textContent = fmtDuration(s.last_session_seconds);
    });
  }

  function render(s) {
    const connected = s.state === "connected";
    document.body.dataset.state = s.state;
    $("app").dataset.state = s.state;

    if (s.state === "found" && s.devices.length) {
      $("foundName").textContent = s.devices[0].name;
      $("btnConnect").dataset.id = s.devices[0].id;
      renderOthers(s.devices);
    }
    if (connected && s.active) {
      $("connName").textContent = s.active.name;
    }
    $("uptime").textContent = fmtDuration(connected ? s.connected_seconds : 0);
    renderLast(s);

    // sound test
    const live = $("livePill");
    live.className = connected ? "pill live" : "pill off";
    live.textContent = connected ? "LIVE" : "Inactive";
    paintMeter(s.level, connected);

    const monitor = $("monitor");
    monitor.setAttribute("aria-checked", s.audio.monitor ? "true" : "false");

    const gain = $("gain");
    if (!dragging) {
      gain.value = String(s.gain_percent);
      $("gainVal").textContent = s.gain_percent + "%";
    }

    const monTarget = s.audio.monitor && s.audio.monitor_target
      ? "Hearing yourself through: " + s.audio.monitor_target + ". " : "";
    $("hintText").textContent = Date.now() < hintUntil ? hintMsg : monTarget + (connected
      ? "In Discord / games, pick the microphone \"CABLE Output\". Use a headset when testing Hear yourself."
      : "You will only hear sound once the phone is connected. You can already change the settings now.");

    renderOutputs(s.audio);
    const warn = $("warn");
    let msg = "";
    if (s.audio.error) msg = s.audio.error;
    else if (s.audio.virtual_is_cable === false)
      msg = "Output is not CABLE Input: your voice plays straight out of \"" + s.audio.virtual_name +
        "\" and does not reach your Discord mic. Pick CABLE Input in Output.";
    else if (s.audio.available && s.audio.virtual_index === null)
      msg = "Virtual mic (VB-Cable) not found. Run the MicHP installer again (it installs VB-Cable too), or install it from vb-audio.com/Cable and restart the PC.";
    if (msg) {
      warn.hidden = false;
      warn.textContent = msg;
    } else if (warn.textContent !== OFFLINE_MSG) {
      warn.hidden = true;
      warn.textContent = "";
    }
  }

  // ---------- event ----------
  document.addEventListener("contextmenu", (e) => e.preventDefault());
  $("btnConnect").addEventListener("click", (e) => {
    const id = e.currentTarget.dataset.id;
    if (id) act("/api/connect", { id });
  });
  $("btnDisconnect").addEventListener("click", () => act("/api/disconnect", {}));
  $("others").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-id]");
    if (b) act("/api/connect", { id: b.dataset.id });
  });
  $("monitor").addEventListener("click", async () => {
    const on = $("monitor").getAttribute("aria-checked") !== "true";
    // switch the look right away so it feels responsive; the next render corrects it if it failed
    $("monitor").setAttribute("aria-checked", on ? "true" : "false");
    const r = await act("/api/monitor", { on });
    if (on && r && r.ok === false) {
      hintMsg = "Could not open the Windows default speakers/headphones.";
      hintUntil = Date.now() + 5000;
    }
  });
  $("output").addEventListener("change", (e) => {
    const v = e.target.value;
    act("/api/output", { index: v === "" ? null : Number(v) });
  });
  $("gain").addEventListener("input", (e) => {
    dragging = true;
    clearTimeout(dragTimer);
    const pct = Number(e.target.value);
    $("gainVal").textContent = pct + "%";
    clearTimeout(gainTimer);
    gainTimer = setTimeout(() => act("/api/gain", { percent: pct }), 60);
  });
  $("gain").addEventListener("change", () => {
    dragTimer = setTimeout(() => { dragging = false; }, 400);
  });

  // ---------- polling ----------
  let busy = false;
  async function tick() {
    if (busy) return;
    busy = true;
    try {
      const s = await api("/api/state");
      setOffline(false);
      render(s);
    } catch (e) {
      setOffline(true);
    } finally {
      busy = false;
    }
  }
  setInterval(tick, 80);
  tick();
})();
