/* Litetox card — bundled with the litetox integration (ALTOX heater/tracker). */

const CARD_VERSION = "1.0.6";
const PLATFORM = "litetox";
// role -> [domain, translation_key] of this integration's entities
const ROLES = {
  online: ["binary_sensor", "online"],
  altox: ["binary_sensor", "altox"],
  heater: ["binary_sensor", "heater"],
  flame: ["binary_sensor", "flame"],
  webasto: ["binary_sensor", "webasto_error"],
  voltage: ["sensor", "voltage"],
  cabin: ["sensor", "cabin_temp"],
  heaterTemp: ["sensor", "heater_temp"],
  minutes: ["sensor", "heater_minutes"],
  balance: ["sensor", "balance"],
  gsm: ["sensor", "gsm"],
  cell: ["sensor", "gsm_cell"],
  lastSeen: ["sensor", "last_seen"],
  satellites: ["sensor", "satellites"],
  odometer: ["sensor", "odometer_km"],
  statusTs: ["sensor", "heater_ts"],
  heaterSwitch: ["switch", "heater_switch"],
  output: ["switch", "output"],
  btnStatus: ["button", "request_status"],
  btnBalance: ["button", "request_balance"],
  btnDiag: ["button", "request_diag"],
  btnCells: ["button", "request_cells"],
};
const DURATIONS = [10, 20, 30, 45, 60]; // START:N, the service accepts 10–120 min
const PENDING_MS = 90000; // the module answers in 5–40 s; give up after the server's timeout

// Entities come from the registry, so renamed entity_ids keep working.
// With several trackers the card takes `device_id` (or the first one found).
const discover = (hass, deviceId) => {
  const found = {};
  for (const e of Object.values(hass?.entities || {})) {
    if (e.platform !== PLATFORM || (deviceId && e.device_id !== deviceId)) continue;
    deviceId = deviceId || e.device_id;
    for (const [key, [domain, tk]] of Object.entries(ROLES)) {
      if (e.translation_key === tk && e.entity_id.startsWith(domain + ".")) found[key] = e.entity_id;
    }
  }
  return { device_id: deviceId, ...found };
};

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const ok = (st) => st && st.state !== "unknown" && st.state !== "unavailable";
const num = (st) => {
  const v = Number(st?.state);
  return ok(st) && Number.isFinite(v) ? v : null;
};
const fmt = (v, digits = 0) =>
  v === null ? "—" : v.toLocaleString("ru-RU", { minimumFractionDigits: digits, maximumFractionDigits: digits });

const ago = (iso) => {
  if (!iso) return "нет данных";
  const t = new Date(iso).getTime();
  if (!Number.isFinite(t)) return "нет данных";
  const m = Math.round((Date.now() - t) / 60000);
  if (m < 1) return "только что";
  if (m < 60) return `${m} мин назад`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h} ч назад`;
  return new Date(t).toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit" });
};

// Original top-down SUV silhouette, front to the left (used when no `image` is set).
const CAR_SVG = `
<svg viewBox="0 0 910 650" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <defs>
    <linearGradient id="lb" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#2b2f36"/><stop offset=".5" stop-color="#3a3f48"/><stop offset="1" stop-color="#2b2f36"/>
    </linearGradient>
    <linearGradient id="lg" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#7d8da3"/><stop offset="1" stop-color="#42505f"/>
    </linearGradient>
  </defs>
  <g fill="#15171b">
    <rect x="150" y="128" width="120" height="34" rx="12"/><rect x="640" y="128" width="120" height="34" rx="12"/>
    <rect x="150" y="488" width="120" height="34" rx="12"/><rect x="640" y="488" width="120" height="34" rx="12"/>
  </g>
  <path d="M70 230 Q70 150 150 146 L790 146 Q852 150 856 230 L856 420 Q852 500 790 504 L150 504 Q70 500 70 420 Z"
        fill="url(#lb)" stroke="#585f6b" stroke-width="4"/>
  <path d="M98 250 Q98 196 140 190 L250 190 L250 460 L140 460 Q98 454 98 400 Z" fill="#30353d" stroke="#4b525d" stroke-width="3"/>
  <path d="M120 300 L235 300 M120 350 L235 350" stroke="#444b55" stroke-width="4" stroke-linecap="round"/>
  <path d="M262 200 Q300 178 380 186 L380 464 Q300 472 262 450 Z" fill="url(#lg)" opacity=".85"/>
  <rect x="392" y="190" width="320" height="270" rx="26" fill="#262a31" stroke="#4b525d" stroke-width="3"/>
  <g stroke="#4f5763" stroke-width="5" stroke-linecap="round">
    <path d="M410 214 L694 214"/><path d="M410 436 L694 436"/>
  </g>
  <path d="M724 196 Q790 194 808 236 L808 414 Q790 456 724 454 Z" fill="url(#lg)" opacity=".75"/>
  <path d="M520 146 L520 504 M640 150 L640 500" stroke="#20242a" stroke-width="3"/>
  <g fill="#f4f1d0"><rect x="74" y="178" width="18" height="56" rx="8"/><rect x="74" y="416" width="18" height="56" rx="8"/></g>
  <g fill="#d43a3a"><rect x="842" y="180" width="12" height="54" rx="5"/><rect x="842" y="416" width="12" height="54" rx="5"/></g>
  <g fill="#2b2f36" stroke="#585f6b" stroke-width="3">
    <path d="M330 146 L344 116 L372 116 L366 146 Z"/><path d="M330 504 L344 534 L372 534 L366 504 Z"/>
  </g>
</svg>`;

const STYLE = `
  :host { display: block; }
  ha-card { display: block; overflow: hidden; padding: 14px; container-type: inline-size; }
  .ttl {
    display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap;
    position: relative; padding-left: 28px; margin-bottom: 12px;
    font-size: 19px; font-weight: 600;
  }
  .ttl > ha-icon { position: absolute; left: 0; top: 2px; --mdc-icon-size: 20px; color: #8bc34a; }
  .acc { font-size: 14px; font-weight: 400; color: var(--secondary-text-color); }
  .pill-bad {
    align-self: center; font-size: 13px; font-weight: 600; padding: 1px 8px; border-radius: 10px;
    background: rgba(244,67,54,.18); color: #f44336;
  }
  .cols { display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr); gap: 14px; align-items: start; }
  @container (max-width: 560px) { .cols { grid-template-columns: minmax(0, 1fr); } }

  /* ---- left: car with status pills ---- */
  .car { position: relative; aspect-ratio: 910 / 650; border-radius: 16px; }
  .car img, .car svg { position: absolute; inset: 6% 3%; width: 94%; height: 88%; object-fit: contain; }
  .glow {
    position: absolute; left: 0; top: 18%; width: 46%; height: 64%; border-radius: 50%;
    background: radial-gradient(closest-side, rgba(255,140,0,.75), rgba(255,90,0,.25) 60%, transparent);
    opacity: 0; transition: opacity .6s; pointer-events: none; mix-blend-mode: screen;
  }
  .car.heating .glow { opacity: 1; animation: breathe 2.4s ease-in-out infinite; }
  @keyframes breathe { 50% { opacity: .55; } }
  .pill {
    position: absolute; transform: translate(var(--tx, -50%), -50%);
    display: inline-flex; align-items: center; gap: 4.4px; white-space: nowrap;
    padding: 2px 10px 2px 7px; border-radius: 13px; background: rgba(0,0,0,.55);
    color: #fff; font-size: 14.3px; font-weight: 600; cursor: pointer;
    backdrop-filter: blur(2px);
  }
  .pill ha-icon { --mdc-icon-size: 17.6px; color: var(--c, #fff); }
  .center {
    position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%);
    display: flex; flex-direction: column; align-items: center; gap: 2px;
    padding: 6px 12px; border-radius: 14px; background: rgba(0,0,0,.6); color: #fff; cursor: pointer;
    text-align: center; min-width: 96px;
  }
  .center ha-icon { --mdc-icon-size: 28px; color: var(--c); filter: drop-shadow(0 0 6px var(--c)); }
  .center b { font-size: 15px; }
  .center small { font-size: 12px; opacity: .8; }
  .heating .center ha-icon { animation: flicker 1.2s ease-in-out infinite; }
  @keyframes flicker { 50% { transform: scale(1.12); } }

  /* ---- right: commands with their results ---- */
  .cmds { display: flex; flex-direction: column; gap: 8px; }
  .heat {
    display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 10px;
    padding: 10px 12px; border-radius: 16px; border: 1px solid color-mix(in srgb, var(--c) 40%, transparent);
    background: color-mix(in srgb, var(--c) 10%, transparent);
  }
  .heat > ha-icon { --mdc-icon-size: 30px; color: var(--c); filter: drop-shadow(0 0 6px color-mix(in srgb, var(--c) 55%, transparent)); }
  .heat .t b { display: block; font-size: 15px; }
  .heat .t small { color: var(--secondary-text-color); font-size: 12.5px; }
  .go {
    font: inherit; font-weight: 700; font-size: 13px; border: 0; cursor: pointer; white-space: nowrap;
    padding: 8px 14px; border-radius: 12px; color: #fff; background: var(--c);
    display: inline-flex; align-items: center; gap: 4px;
  }
  .go ha-icon { --mdc-icon-size: 18px; }
  .go.armed { animation: blink .5s steps(1) infinite; }
  .go[disabled] { opacity: .55; cursor: default; }
  .dur { grid-column: 1 / -1; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
  .dur > ha-icon { --mdc-icon-size: 20px; color: var(--c); }
  .dur button {
    flex: 1 1 0; min-width: 0; white-space: nowrap;
    font: inherit; font-size: 13px; font-weight: 600; cursor: pointer; padding: 5px 8px; border-radius: 10px;
    color: var(--primary-text-color); background: color-mix(in srgb, var(--c) 12%, transparent);
    border: 1px solid color-mix(in srgb, var(--c) 35%, transparent);
  }
  .dur button.sel { color: #fff; background: var(--c); border-color: var(--c); }
  @keyframes blink { 50% { filter: brightness(1.35); } }
  .grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .cmd {
    display: flex; flex-direction: column; gap: 2px; min-width: 0; position: relative;
    padding: 10px 10px 9px; border-radius: 16px; cursor: pointer;
    border: 1px solid color-mix(in srgb, var(--c) 40%, transparent);
    background: color-mix(in srgb, var(--c) 10%, transparent);
  }
  .cmd .h { display: flex; align-items: center; gap: 6px; font-size: 13px; opacity: .9; padding-right: 30px; }
  .cmd .h ha-icon { --mdc-icon-size: 20px; color: var(--c); }
  .cmd .v { font-size: 17px; font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .cmd .v small { font-size: 12px; font-weight: 500; }
  .cmd .w { font-size: 12px; color: var(--secondary-text-color); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .run {
    position: absolute; right: 6px; top: 6px; width: 30px; height: 30px; border-radius: 10px; border: 0;
    display: grid; place-items: center; cursor: pointer; color: var(--c);
    background: color-mix(in srgb, var(--c) 18%, transparent);
  }
  .run ha-icon { --mdc-icon-size: 18px; }
  .run[disabled] { cursor: default; }
  .busy .run ha-icon { animation: spin 1s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .foot {
    display: flex; flex-wrap: wrap; justify-content: center; gap: 6px 14px; margin-top: 12px; padding-top: 10px;
    border-top: 1px solid var(--divider-color); font-size: 13px; color: var(--secondary-text-color);
  }
  .foot span { display: inline-flex; align-items: center; gap: 4px; cursor: pointer; }
  .foot ha-icon { --mdc-icon-size: 16px; }
  .warn { padding: 8px; color: var(--error-color, #f44336); }
`;

const GREEN = "#66bb6a", RED = "#f44336", ORANGE = "#ff9800", YELLOW = "#fdd835", BLUE = "#42a5f5", GREY = "#9e9e9e", AMBER = "#ffb300";

const createCardClass = (Base) => class LitetoxCard extends Base {
  setConfig(config) {
    this._userConfig = config || {};
    this._config = null;
    this._pending = this._pending || {};
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
      this.shadowRoot.addEventListener("click", (ev) => this._onClick(ev));
    }
    this._render();
  }

  set hass(hass) {
    if (!this._config && hass.entities) {
      this._config = { ...discover(hass, this._userConfig.device_id), ...this._userConfig };
    }
    const keys = this._config ? Object.keys(ROLES).map((k) => this._config[k]).filter(Boolean) : [];
    const changed = !this._hass || keys.some((k) => hass.states[k] !== this._hass.states[k]);
    this._hass = hass;
    if (changed) this._render();
  }

  connectedCallback() {
    this._timer = setInterval(() => this._render(), 15000);
  }

  disconnectedCallback() {
    clearInterval(this._timer);
    clearTimeout(this._armTimer);
  }

  getCardSize() {
    return 7;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6 };
  }

  static getStubConfig() {
    return {};
  }

  _st(role) {
    return this._config?.[role] ? this._hass.states[this._config[role]] : undefined;
  }

  _more(entityId) {
    if (!entityId) return;
    this.dispatchEvent(new CustomEvent("hass-more-info",
      { detail: { entityId }, bubbles: true, composed: true }));
  }

  // When the module last answered each command: a press is pending until this moves past it.
  _resultTs(cmd) {
    const s = (r) => this._st(r);
    switch (cmd) {
      case "status": return s("statusTs")?.state;
      case "balance": return s("balance")?.attributes?.updated;
      case "diag": return s("webasto")?.attributes?.updated;
      case "cells": return s("cell")?.attributes?.updated;
      case "heater": return s("statusTs")?.state;
      default: return null;
    }
  }

  _isPending(cmd) {
    const at = this._pending[cmd];
    if (!at) return false;
    const ts = new Date(this._resultTs(cmd) || 0).getTime();
    if (ts > at || Date.now() - at > PENDING_MS) {
      delete this._pending[cmd];
      return false;
    }
    return true;
  }

  _press(cmd) {
    const c = this._config;
    const btn = { status: c.btnStatus, balance: c.btnBalance, diag: c.btnDiag, cells: c.btnCells }[cmd];
    if (btn) {
      this._pending[cmd] = Date.now();
      this._hass.callService("button", "press", { entity_id: btn })
        .catch(() => { delete this._pending[cmd]; this._render(); });
    } else if (cmd === "out") {
      const on = this._st("output")?.state === "on";
      this._hass.callService("switch", on ? "turn_off" : "turn_on", { entity_id: c.output });
    }
    this._render();
  }

  _onClick(ev) {
    const el = ev.target.closest("[data-act]");
    if (!el || el.disabled || !this._hass || !this._config) return;
    ev.stopPropagation();
    const { act, entity, cmd } = el.dataset;
    if (act === "more") return this._more(entity);
    if (act === "run") return this._press(cmd);
    if (act === "dur") {
      this._minutes = Number(el.dataset.min);
      try { localStorage.setItem(this._minKey(), String(this._minutes)); } catch (_) { /* private mode */ }
      return this._render();
    }
    if (act === "heat") {
      const on = this._st("heaterSwitch")?.state === "on";
      // starting a fuel heater deserves a second tap; stopping never does
      if (!on && !this._armed) {
        this._armed = true;
        clearTimeout(this._armTimer);
        this._armTimer = setTimeout(() => { this._armed = false; this._render(); }, 4000);
        return this._render();
      }
      this._armed = false;
      clearTimeout(this._armTimer);
      this._pending.heater = Date.now();
      const call = on
        ? this._hass.callService("switch", "turn_off", { entity_id: this._config.heaterSwitch })
        : this._hass.callService(PLATFORM, "start_heater",
          { device_id: this._config.device_id, minutes: this._getMinutes() });
      call.catch(() => { delete this._pending.heater; this._render(); });
      this._render();
    }
  }

  _minKey() {
    return `litetox-minutes:${this._config?.device_id || ""}`;
  }

  // chosen run time: last pick on this device/browser, else card option `minutes`, else 30
  _getMinutes() {
    if (!this._minutes) {
      let saved = null;
      try { saved = Number(localStorage.getItem(this._minKey())); } catch (_) { /* private mode */ }
      this._minutes = DURATIONS.includes(saved) ? saved : Number(this._config?.minutes) || 30;
    }
    return this._minutes;
  }

  _pill(x, y, role, icon, text, color) {
    const st = this._st(role);
    if (!st) return "";
    // anchored to the nearer edge so wider text grows inward, not off the card
    const pos = x < 50 ? `left:${x}%;--tx:0` : `left:${x}%;--tx:-100%`;
    return `<span class="pill" style="${pos};top:${y}%;--c:${color}" data-act="more" data-entity="${esc(st.entity_id)}">
      <ha-icon icon="${icon}"></ha-icon>${text}</span>`;
  }

  _cmd(cmd, role, entity, icon, title, value, when, color) {
    if (!entity) return "";
    const busy = this._isPending(cmd);
    return `<div class="cmd${busy ? " busy" : ""}" style="--c:${color}" data-act="more" data-entity="${esc(entity)}">
      <div class="h"><ha-icon icon="${icon}"></ha-icon>${title}</div>
      <div class="v">${value}</div>
      <div class="w">${busy ? "ждём ответ модуля…" : esc(when)}</div>
      ${role ? `<button class="run" data-act="run" data-cmd="${cmd}" title="Отправить команду" ${busy ? "disabled" : ""}>
        <ha-icon icon="${busy ? "mdi:loading" : "mdi:send"}"></ha-icon></button>` : ""}
    </div>`;
  }

  _render() {
    if (!this.shadowRoot) return;
    const c = this._config;
    if (!c || !this._hass) {
      this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card><div class="warn">Загрузка…</div></ha-card>`;
      return;
    }
    if (!c.heaterSwitch && !c.voltage) {
      this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card><div class="warn">
        Сущности интеграции «Litetox Proxy» не найдены</div></ha-card>`;
      return;
    }
    const s = (r) => this._st(r);
    const online = s("online")?.state === "on";
    const heaterOn = (s("heaterSwitch") || s("heater"))?.state === "on";
    const flame = s("flame")?.state === "on";
    const minutes = num(s("minutes"));
    const heatBusy = this._isPending("heater");
    const devName = c.name || this._hass.devices?.[c.device_id]?.name_by_user
      || this._hass.devices?.[c.device_id]?.name || "Автомобиль";

    // pills on the car
    const v = num(s("voltage"));
    // 12 V lead-acid at rest: ≥12.4 charged, 12.1–12.4 half, 11.8–12.1 low, <11.8 flat; >13.2 = charging
    const [vColor, vGrade] = v === null ? [GREY, ""] : v >= 13.2 ? [BLUE, "заряжается"]
      : v >= 12.4 ? [GREEN, "заряжен"] : v >= 12.1 ? [YELLOW, "заряд ~50%"]
      : v >= 11.8 ? [ORANGE, "разряжен"] : [RED, "сильно разряжен"];
    const bal = num(s("balance"));
    const balColor = bal === null ? GREY : bal < 100 ? YELLOW : GREEN;
    const gsm = num(s("gsm"));
    const gsmColor = gsm === null ? GREY : gsm < 10 ? RED : gsm < 18 ? ORANGE : GREEN;
    const gsmIcon = gsm === null ? "mdi:signal-off" : gsm < 10 ? "mdi:signal-cellular-1"
      : gsm < 18 ? "mdi:signal-cellular-2" : "mdi:signal-cellular-3";
    const cab = num(s("cabin"));
    const ht = num(s("heaterTemp"));
    const heatColor = heaterOn ? ORANGE : GREY;
    const altox = s("altox");

    const img = c.image ? `<img src="${esc(c.image)}" alt="">` : CAR_SVG;
    const centerText = heaterOn
      ? `<b>${flame ? "Греет" : "Запуск…"}</b><small>${minutes ? `осталось ${minutes} мин` : "работает"}</small>`
      : `<b>Отопитель</b><small>выключен</small>`;

    const car = `
      <div class="car${heaterOn ? " heating" : ""}">
        ${img}
        <div class="glow"></div>
        ${this._pill(3, 8, "online", online ? "mdi:cloud-check-outline" : "mdi:cloud-off-outline",
          online ? "онлайн" : "офлайн", online ? GREEN : RED)}
        ${this._pill(3, 19, "gsm", gsmIcon, gsm === null ? "—" : `${gsm}/31`, gsmColor)}
        ${this._pill(97, 8, "voltage", "mdi:car-battery", `${fmt(v, 1)} В`, vColor)}
        ${this._pill(97, 19, "balance", "mdi:sim", `${fmt(bal, 0)} ₽`, balColor)}
        ${this._pill(3, 92, "heaterTemp", "mdi:radiator", `${fmt(ht)} °C`, ht !== null && ht > 40 ? ORANGE : BLUE)}
        ${this._pill(97, 92, "cabin", "mdi:car-seat-heater", `${fmt(cab)} °C`, cab !== null && cab < 5 ? BLUE : AMBER)}
        <div class="center" style="--c:${heaterOn ? ORANGE : GREY}" data-act="more" data-entity="${esc(c.heater || c.heaterSwitch)}">
          <ha-icon icon="${heaterOn ? "mdi:fire" : "mdi:fire-off"}"></ha-icon>${centerText}
        </div>
      </div>`;

    // commands
    const armed = this._armed;
    const runMin = this._getMinutes();
    const heatLabel = heatBusy ? "Ждём…" : heaterOn ? "Стоп" : armed ? `Точно? ${runMin} мин` : "Запуск";
    const durs = heaterOn ? "" : `
        <div class="dur" title="Время работы отопителя"><ha-icon icon="mdi:timer-outline"></ha-icon>${(DURATIONS.includes(runMin) ? DURATIONS : [...DURATIONS, runMin].sort((a, b) => a - b))
          .map((m) => `<button class="${m === runMin ? "sel" : ""}" data-act="dur" data-min="${m}">${m}</button>`).join("")}</div>`;
    const heat = c.heaterSwitch ? `
      <div class="heat" style="--c:${heaterOn ? RED : ORANGE}">
        <ha-icon icon="mdi:radiator"></ha-icon>
        <div class="t" data-act="more" data-entity="${esc(c.heaterSwitch)}">
          <b>Отопитель ${heaterOn ? "работает" : "выключен"}</b>
          <small>${heaterOn ? (minutes ? `осталось ${minutes} мин` : "запущен") + (flame ? " · пламя есть" : "")
            : `${fmt(ht)} °C · статус ${ago(s("statusTs")?.state)}`}</small>
        </div>
        <button class="go${armed ? " armed" : ""}" data-act="heat" ${heatBusy || !online ? "disabled" : ""}>
          <ha-icon icon="${heaterOn ? "mdi:stop" : "mdi:play"}"></ha-icon>${heatLabel}</button>${durs}
      </div>` : "";

    const stTs = s("statusTs")?.state;
    const balSt = s("balance");
    const diag = s("webasto");
    const diagErr = diag?.state === "on";
    const diagKnown = ok(diag);
    const cell = s("cell");
    const out = s("output");
    const outOn = out?.state === "on";

    const sat = num(s("satellites"));
    const odo = num(s("odometer"));

    const cmds = [
      this._cmd("status", c.btnStatus, c.statusTs || c.btnStatus, "mdi:refresh", "Статус",
        `${fmt(v, 1)}<small> В${vGrade ? " · " + vGrade : ""}</small>`, `обновлён ${ago(stTs)}`, vColor),
      this._cmd("balance", c.btnBalance, c.balance || c.btnBalance, "mdi:cash-sync", "Баланс SIM",
        `${fmt(bal, 2)}<small> ₽</small>`, `запрошен ${ago(balSt?.attributes?.updated)}`, balColor),
      this._cmd("diag", c.btnDiag, c.webasto || c.btnDiag, "mdi:car-wrench", "Диагностика Webasto",
        !diagKnown ? "—" : diagErr ? `код ${esc(diag.attributes?.error_code ?? "?")}` : "нет ошибок",
        `проверено ${ago(diag?.attributes?.updated)}`, !diagKnown ? GREY : diagErr ? RED : GREEN),
      this._cmd("cells", c.btnCells, c.cell || c.btnCells, "mdi:radio-tower", "Соты GSM",
        ok(cell) ? esc(cell.state) : "—", `запрошены ${ago(cell?.attributes?.updated)}`, BLUE),
      this._cmd("sat", null, c.satellites, sat ? "mdi:satellite-variant" : "mdi:crosshairs-off", "Спутники GPS",
        sat === null ? "—" : `${sat}<small> ${sat >= 6 ? "· точно" : sat >= 3 ? "· слабо" : "· нет фикса"}</small>`,
        `обновлено ${ago(stTs)}`, sat === null ? GREY : sat >= 6 ? GREEN : sat >= 3 ? YELLOW : RED),
      this._cmd("odo", null, c.odometer, "mdi:counter", "Пробег",
        `${fmt(odo, 1)}<small> км</small>`, "по GPS-трекингу", BLUE),
      out ? this._cmd("out", c.output, c.output, "mdi:electric-switch", "Выход OUT",
        outOn ? "включён" : "выключен", "нажмите ▶ для переключения", outOn ? GREEN : GREY) : "",
    ].filter(Boolean).join("");

    const foot = [
      s("lastSeen") ? `<span data-act="more" data-entity="${esc(c.lastSeen)}"><ha-icon icon="mdi:clock-outline"></ha-icon>связь ${ago(s("lastSeen").state)}</span>` : "",
      altox ? `<span data-act="more" data-entity="${esc(c.altox)}" style="color:${altox.state === "on" ? "inherit" : RED}">
        <ha-icon icon="${altox.state === "on" ? "mdi:server-network" : "mdi:server-network-off"}"></ha-icon>ALTOX ${altox.state === "on" ? "на связи" : "нет связи"}</span>` : "",
    ].join("");

    this.shadowRoot.innerHTML = `
      <style>${STYLE}</style>
      <ha-card>
        <div class="ttl"><ha-icon icon="mdi:car-estate"></ha-icon><span>${esc(devName)}</span>
          <span class="acc">отопитель и трекер</span>${online ? "" : `<span class="pill-bad">нет связи</span>`}</div>
        <div class="cols">
          ${car}
          <div class="cmds">${heat}<div class="grid">${cmds}</div></div>
        </div>
        ${foot ? `<div class="foot">${foot}</div>` : ""}
      </ha-card>`;
  }
};

/*
 * browser_mod and hui-element load the @webcomponents/scoped-custom-element-registry
 * polyfill, which replaces window.customElements and window.HTMLElement. Build the class
 * from the live globals and retry after the polyfill had a chance to load.
 */
function defineLitetoxCard() {
  const reg = window.customElements;
  if (reg && !reg.get("litetox-card")) reg.define("litetox-card", createCardClass(window.HTMLElement));
}

defineLitetoxCard();
if (!window.__litetoxCardScheduled) {
  window.__litetoxCardScheduled = true;
  const retry = () => {
    try {
      defineLitetoxCard();
    } catch (_) {
      /* a concurrent registry swap is harmless; the next pass settles it */
    }
  };
  Promise.resolve().then(retry);
  requestAnimationFrame(retry);
  setTimeout(retry, 0);
  setTimeout(retry, 1000);
  setTimeout(retry, 5000);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "litetox-card")) window.customCards.push({
  type: "litetox-card",
  name: "Litetox",
  description: "Автомобиль, отопитель и команды модуля ALTOX (интеграция Litetox Proxy)",
  preview: true,
});

console.info(`%c LITETOX-CARD %c ${CARD_VERSION} `,
  "background:#ff9800;color:#000;font-weight:700", "background:#263238;color:#fff");
