/* VerbrauchsMonitor dashboard card – v0.0.2 R111 */
class VerbrauchsMonitorCard extends HTMLElement {
  setConfig(config) {
    this.config = config || {};
  }

  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  getCardSize() {
    return 4;
  }

  render() {
    if (!this._hass) return;
    const states = Object.values(this._hass.states).filter((state) =>
      state.entity_id.startsWith("sensor.") &&
      state.attributes?.vm_role
    );
    const brightness = states.find((state) => state.attributes.vm_role === "outdoor_illuminance");
    const meterStates = states.filter((state) => state.attributes.vm_role !== "outdoor_illuminance");
    const groups = new Map();
    for (const state of meterStates) {
      const key = state.attributes.card_meter_id || state.attributes.meter_id || state.attributes.meter_number || state.entity_id;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(state);
    }
    const meters = [...groups.values()];
    const hasFeedIn = states.some((s) =>
      ["feed_in_counter", "feed_in_power"].includes(s.attributes.vm_role)
    );
    const lang = (this._hass.locale?.language || "de").toLowerCase().startsWith("de") ? "de" : "en";
    const text = (de, en) => lang === "de" ? de : en;

    const tile = (title, value, icon, detail = "") => `
      <div class="tile">
        <ha-icon icon="${icon}"></ha-icon>
        <div class="copy">
          <div class="title">${this.escape(title)}</div>
          <div class="value">${this.escape(value)}</div>
          ${detail ? `<div class="detail">${this.escape(detail)}</div>` : ""}
        </div>
      </div>`;

    const hasValue = (state) =>
      Boolean(state) &&
      !["unknown", "unavailable", "none", ""].includes(String(state.state).toLowerCase()) &&
      Number.isFinite(Number(state.state));

    const format = (state) => {
      if (!hasValue(state)) return "";
      const unit = state.attributes.unit_of_measurement || "";
      const number = Number(state.state);
      const shown = Number.isFinite(number)
        ? new Intl.NumberFormat(this._hass.locale?.language || "de-DE", {
            minimumFractionDigits: unit === "€" ? 2 : 0,
            maximumFractionDigits: 2
          }).format(number)
        : state.state;
      return `${shown}${unit ? ` ${unit}` : ""}`;
    };

    const find = (meter, role) => meter.find((s) => s.attributes.vm_role === role);
    let cards = "";
    for (const [meterIndex, meter] of meters.entries()) {
      const name = meter.find((s) => s.attributes.card_meter_name)?.attributes.card_meter_name || meter.find((s) => s.attributes.meter_name)?.attributes.meter_name || "Stromzähler";
      const consumptionPower = find(meter, "consumption_power");
      const consumptionCounter = find(meter, "consumption_counter");
      const feedPower = find(meter, "feed_in_power");
      const feedCounter = find(meter, "feed_in_counter");
      const consumptionBalance = find(meter, "consumption_balance");
      const feedInBalance = find(meter, "feed_in_balance");
      const consumptionForecast = find(meter, "consumption_forecast_annual_balance");
      const consumptionAdvanceForecast = find(meter, "consumption_forecast_monthly_advance");
      const feedInForecast = find(meter, "feed_in_forecast_annual_balance");
      const feedInAdvanceForecast = find(meter, "feed_in_forecast_monthly_advance");

      const consumptionTiles = [];
      const centerTiles = [];
      const feedInTiles = [];

      // Feste Spaltenzuordnung wie in der bisherigen Dashboard-Karte:
      // Verbrauch links, ergänzende Messwerte mittig, Einspeisung rechts.
      if (hasValue(consumptionPower)) consumptionTiles.push(tile(text("Verbrauch – Aktuell", "Consumption – Current"), format(consumptionPower), "mdi:flash"));
      if (hasValue(consumptionCounter)) consumptionTiles.push(tile(text("Verbrauch – Zählerstand", "Consumption – Meter reading"), format(consumptionCounter), "mdi:counter"));
      if (hasValue(consumptionBalance)) consumptionTiles.push(tile(text("Verbrauch – Kontostand", "Consumption balance"), format(consumptionBalance), "mdi:cash"));
      if (hasValue(consumptionForecast)) consumptionTiles.push(tile(text("Verbrauch – Jahresprognose", "Consumption – Annual forecast"), format(consumptionForecast), "mdi:chart-timeline-variant"));
      if (hasValue(consumptionAdvanceForecast)) consumptionTiles.push(tile(text("Verbrauch – Abschlag empfohlen", "Consumption – Recommended advance"), format(consumptionAdvanceForecast), "mdi:cash-clock"));

      if (meterIndex === 0 && brightness && hasValue(brightness)) centerTiles.push(tile(text("Außenhelligkeit", "Outdoor illuminance"), format(brightness), "mdi:brightness-5"));

      if (hasFeedIn && hasValue(feedPower)) feedInTiles.push(tile(text("Einspeisung – Aktuell", "Feed-in – Current"), format(feedPower), "mdi:transmission-tower-export"));
      if (hasFeedIn && hasValue(feedCounter)) feedInTiles.push(tile(text("Einspeisung – Zählerstand", "Feed-in – Meter reading"), format(feedCounter), "mdi:counter"));
      if (hasFeedIn && hasValue(feedInBalance)) feedInTiles.push(tile(text("Einspeisung – Kontostand", "Feed-in balance"), format(feedInBalance), "mdi:cash-plus"));
      if (hasFeedIn && hasValue(feedInForecast)) feedInTiles.push(tile(text("Einspeisung – Jahresprognose", "Feed-in – Annual forecast"), format(feedInForecast), "mdi:chart-timeline-variant"));
      if (hasFeedIn && hasValue(feedInAdvanceForecast)) feedInTiles.push(tile(text("Einspeisung – Abschlag empfohlen", "Feed-in – Recommended advance"), format(feedInAdvanceForecast), "mdi:cash-clock"));

      cards += `<section class="meter"><h2>${this.escape(name)}</h2><div class="columns">
        <div class="column consumption">${consumptionTiles.join("")}</div>
        <div class="column center">${centerTiles.join("")}</div>
        <div class="column feed-in">${feedInTiles.join("")}</div>
      </div></section>`;
    }

    if (!meters.length) {
      cards = `<div class="empty">${text("Noch kein Stromzähler konfiguriert. Bitte zuerst die Zähler unter VerbrauchsMonitor konfigurieren.", "No electricity meter configured yet. Configure a meter under VerbrauchsMonitor settings first.")}</div>`;
    }

    this.innerHTML = `
      <ha-card header="${this.escape(this.config.title || "VerbrauchsMonitor")}">
        <div class="content">${cards}
        </div>
      </ha-card>
      <style>
        :host { display:block; }
        ha-card { overflow:hidden; }
        .content { padding:16px; }
        .meter + .meter { border-top:1px solid var(--divider-color); margin-top:18px; padding-top:12px; }
        h2 { font-size:1rem; font-weight:600; margin:0 0 12px; color:var(--primary-text-color); }
         .columns { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; align-items:start; }
        .column { min-width:0; display:flex; flex-direction:column; gap:12px; }
        .column:empty { display:none; }
        .tile { min-width:0; min-height:76px; box-sizing:border-box; display:flex; align-items:center; gap:14px; padding:12px 16px; border:1px solid var(--divider-color); border-radius:16px; background:var(--card-background-color); }
        ha-icon { color:var(--state-icon-color, var(--primary-color)); --mdc-icon-size:28px; flex:0 0 auto; }
        .copy { min-width:0; }
        .title { font-size:14px; font-weight:600; color:var(--primary-text-color); }
        .value { margin-top:4px; font-size:16px; color:var(--primary-text-color); overflow-wrap:anywhere; }
        .detail { font-size:12px; color:var(--secondary-text-color); }
        .empty { padding:16px; color:var(--secondary-text-color); }
        @media (max-width: 700px) { .columns { grid-template-columns:repeat(2,minmax(0,1fr)); } }
        @media (max-width: 440px) { .columns { grid-template-columns:1fr; } }
      </style>`;
  }

  escape(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    })[char]);
  }

  static getConfigElement() { return document.createElement("verbrauchsmonitor-card-editor"); }
  static getStubConfig() { return { type: "custom:verbrauchsmonitor-card", title: "VerbrauchsMonitor" }; }
}

class VerbrauchsMonitorCardEditor extends HTMLElement {
  setConfig(config) { this.config = config; this.render(); }
  set hass(hass) { this._hass = hass; }
  render() {
    if (!this.config) return;
    this.innerHTML = `<div class="editor"><label>Titel <input id="title" type="text" value="${String(this.config.title || "VerbrauchsMonitor").replace(/"/g, "&quot;")}"></label></div>
      <style>.editor{padding:12px}label{display:flex;gap:12px;align-items:center}input{flex:1;min-width:0;padding:8px;background:var(--card-background-color);color:var(--primary-text-color);border:1px solid var(--divider-color);border-radius:6px}</style>`;
    this.querySelector("#title").addEventListener("change", (event) => {
      this.config = { ...this.config, title: event.target.value };
      this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this.config }, bubbles: true, composed: true }));
    });
  }
}
customElements.define("verbrauchsmonitor-card", VerbrauchsMonitorCard);
customElements.define("verbrauchsmonitor-card-editor", VerbrauchsMonitorCardEditor);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "verbrauchsmonitor-card",
  name: "VerbrauchsMonitor",
  description: "Übersicht der konfigurierten Stromzähler."
});

/* Billing card: one independently movable Lovelace card per logical meter.
 * All billing directions belonging to that meter are shown side by side.
 * Each direction keeps a fixed minimum width; the card grows with its column count.
 */
class VerbrauchsMonitorBillingCard extends HTMLElement {
  setConfig(config) { this.config = config || {}; }
  set hass(hass) {
    this._hass = hass;
    if (this._editing && this.querySelector("form.contract-edit")) return;
    this.render();
  }
  getCardSize() { return 8; }
  static getConfigElement() { return document.createElement("verbrauchsmonitor-billing-card-editor"); }
  static getStubConfig() { return { type: "custom:verbrauchsmonitor-billing-card", title: "Aktuelle Abrechnung" }; }

  render() {
    if (!this._hass) return;
    const locale = this._hass.locale?.language || "de-DE";
    const de = locale.toLowerCase().startsWith("de");
    const t = (a, b) => de ? a : b;
    const states = Object.values(this._hass.states).filter(s => s.entity_id.startsWith("sensor.") && s.attributes?.vm_role && s.attributes.vm_role !== "outdoor_illuminance");
    const groups = new Map();
    for (const state of states) {
      const id = state.attributes.meter_id || state.attributes.meter_number || state.entity_id;
      if (!groups.has(id)) groups.set(id, []);
      groups.get(id).push(state);
    }
    const esc = v => String(v ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
    const valid = s => s && !["unknown", "unavailable", "none", ""].includes(String(s.state).toLowerCase()) && Number.isFinite(Number(s.state));
    const num = (v, digits=2) => Number.isFinite(Number(v)) ? new Intl.NumberFormat(locale,{minimumFractionDigits:digits,maximumFractionDigits:digits}).format(Number(v)) : "–";
    const money = v => `${num(v,2)} €`;
    // Show the real tariff precision (including VAT-derived fractions);
    // two decimals could hide enough precision to change a large kWh total.
    const tariff = v => Number.isFinite(Number(v)) ? new Intl.NumberFormat(locale,{minimumFractionDigits:2,maximumFractionDigits:6,useGrouping:false}).format(Number(v)) : "–";
    const inputNumber = (value, digits=2, trim=false) => {
      const number = Number(value);
      if (!Number.isFinite(number)) return "0";
      // Normalize binary floating point noise before formatting editable values.
      const normalized = Number(number.toFixed(Math.min(6, digits)));
      return new Intl.NumberFormat("de-DE",{minimumFractionDigits:trim?0:digits,maximumFractionDigits:digits,useGrouping:false}).format(normalized);
    };
    const withColon = label => /:$/.test(String(label).trim()) ? String(label) : `${label}:`;
    const field = (label, value, unit="", emphasis=false) => `<div class="row${emphasis?" emphasis":""}"><span>${esc(withColon(label))}</span><strong>${esc(value)}${unit?` ${esc(unit)}`:""}</strong></div>`;

    const selectedId = this.config.meter_id || (groups.size === 1 ? [...groups.keys()][0] : "");
    const selectedDirection = this.config.direction === "feed_in" ? "feed_in" : "consumption";
    const group = selectedId ? groups.get(selectedId) : null;
    if (!group) {
      const message = groups.size
        ? t("Bitte einen logischen Zähler und einen Abrechnungsbereich auswählen.","Select a logical meter and a billing direction.")
        : t("Noch keine Zählerdaten verfügbar.","No meter data available yet.");
      this.innerHTML = `<ha-card><div class="content"><h1>${esc(this.config.title || t("Aktuelle Abrechnung","Current billing"))}</h1><p>${esc(message)}</p></div></ha-card>`;
      return;
    }

    const get = role => group.find(s => s.attributes.vm_role === role);
    const counter = get("consumption_counter"), feed = get("feed_in_counter");
    const balance = get("consumption_balance"), feedBalance = get("feed_in_balance");
    const meterMeta = counter || feed || balance || feedBalance || group[0];
    const a = meterMeta.attributes || {};
    const meterName = a.meter_name || "Stromzähler";
    const vat = Number(a.vat_rate_percent || 0);
    const baselineC = Number(a.previous_consumption_reading ?? balance?.attributes?.baseline_reading ?? 0);
    const baselineF = Number(a.previous_feed_in_reading ?? feedBalance?.attributes?.baseline_reading ?? 0);
    const baselineMeta = (direction) => {
      const prefix = direction === "feed_in" ? "feed_in" : "consumption";
      const source = a[`${prefix}_baseline_source`] || "manual";
      const date = a[`${prefix}_baseline_updated_at`] || "";
      const label = source === "routine" ? t("Abrechnungsroutine", "Billing routine") : source === "corrected" ? t("Korrigiert", "Corrected") : t("Manuell eingetragen", "Entered manually");
      const dateText = /^\d{4}-\d{2}-\d{2}$/.test(String(date).slice(0,10)) ? new Intl.DateTimeFormat(locale).format(new Date(`${String(date).slice(0,10)}T00:00:00`)) : "";
      return `<span class="baseline-meta"><span class="baseline-badge ${source === "routine" ? "routine" : "manual"}">${esc(label)}</span>${dateText ? `<span class="baseline-date">${esc(dateText)}</span>` : ""}</span>`;
    };
    const periodStart = String(a.billing_period_start || a.billing_start || a.contract_start || "").slice(0,10);
    const periodMonths = Math.max(1, Number(a.billing_period_months || 12));
    const periodStartDate = /^\d{4}-\d{2}-\d{2}$/.test(periodStart) ? new Date(`${periodStart}T00:00:00`) : null;
    const periodEndDate = periodStartDate ? new Date(periodStartDate.getFullYear(), periodStartDate.getMonth()+periodMonths, 0) : null;
    const periodEndText = periodEndDate ? `${periodEndDate.getFullYear()}-${String(periodEndDate.getMonth()+1).padStart(2,"0")}-${String(periodEndDate.getDate()).padStart(2,"0")}` : "";
    const allMeterChanges = Array.isArray(a.meter_changes) ? a.meter_changes : [];
    const meterChanges = allMeterChanges.filter(change => {
      const date = String(change.date || "").slice(0,10);
      return /^\d{4}-\d{2}-\d{2}$/.test(date) && periodStart && date >= periodStart && (!periodEndDate || date <= periodEndText);
    });
    const currentC = valid(counter) ? Number(counter.state) : null;
    const currentF = valid(feed) ? Number(feed.state) : null;
    const deltaC = currentC === null ? null : currentC-baselineC;
    const deltaF = currentF === null ? null : currentF-baselineF;
    const gross = n => Number(n || 0)*(1+vat/100);
    const priceC = gross(a.purchase_price_net_ct_kwh);
    const priceF = gross(a.feed_in_price_net_ct_kwh);
    const costC = deltaC !== null && deltaC >= 0 ? deltaC*priceC/100 : null;
    const costF = deltaF !== null && deltaF >= 0 ? deltaF*priceF/100 : null;
    const base = gross(a.base_price_net);
    let elapsedMonths = 0;
    if (periodStart && /^\d{4}-\d{2}-\d{2}$/.test(periodStart)) {
      const startDate = new Date(`${periodStart}T00:00:00`), now = new Date();
      if (startDate <= now) elapsedMonths = Math.max(0,(now.getFullYear()-startDate.getFullYear())*12+now.getMonth()-startDate.getMonth()+1);
    }
    if (a.billing_period_months) elapsedMonths = Math.min(elapsedMonths,Number(a.billing_period_months));
    const proratedBase = base*elapsedMonths/12;
    const financeFor = (sourceState, direction, balanceState) => {
      const sourceAttributes = { ...(balanceState?.attributes || {}), ...(sourceState?.attributes || {}) };
      const sourcePeriodStart = String(
        sourceAttributes.billing_period_start ||
        sourceAttributes.billing_start ||
        sourceAttributes.contract_start ||
        periodStart
      ).slice(0, 10);
      const sourcePeriodMonths = Math.max(1, Number(sourceAttributes.billing_period_months || periodMonths));
      const sourcePeriodEnd = sourceAttributes.billing_end || sourceAttributes.contract_end || "";
      const todayText = new Date().toLocaleDateString("en-CA");
      const bookings = Array.isArray(sourceAttributes.bookings) ? sourceAttributes.bookings : [];
      const validBookings = bookings.filter(b => {
        const d = String(b.date || "").slice(0, 10);
        const bookingDirection = b.direction || direction;
        return bookingDirection === direction &&
          (!sourcePeriodStart || !d || d >= sourcePeriodStart) &&
          (!d || d <= todayText) &&
          (!sourcePeriodEnd || !d || d <= String(sourcePeriodEnd).slice(0, 10));
      });
      const extraCharges = validBookings
        .filter(b => b.booking_type === "extra_charge")
        .reduce((sum, b) => sum + Number(b.amount || 0), 0);
      const credits = validBookings
        .filter(b => b.booking_type === "credit")
        .reduce((sum, b) => sum + Math.abs(Number(b.amount || 0)), 0);
      const corrections = validBookings
        .filter(b => b.booking_type === "correction")
        .reduce((sum, b) => sum + Number(b.amount || 0), 0);
      const additionalPaymentBookings = validBookings
        .filter(b => b.booking_type === "payment" && Number(b.amount || 0) !== 0);
      const additionalPayments = additionalPaymentBookings
        .reduce((sum, b) => sum + Number(b.amount || 0), 0);
      const correctionBookings = validBookings
        .filter(b => b.booking_type === "correction" && Number(b.amount || 0) !== 0);
      const recordedAdvances = validBookings.filter(b => b.booking_type === "advance");
      const recordedAdvanceTotal = recordedAdvances.reduce((sum, b) => sum + Number(b.amount || 0), 0);

      let automaticMonths = 0;
      // Both consumption and feed-in advances are paid automatically on
      // the first of each month; their amounts remain direction-specific.
      if (sourcePeriodStart && /^\d{4}-\d{2}-\d{2}$/.test(sourcePeriodStart)) {
        const start = new Date(`${sourcePeriodStart}T00:00:00`);
        const configuredEnd = sourcePeriodEnd
          ? new Date(`${String(sourcePeriodEnd).slice(0, 10)}T00:00:00`)
          : new Date(start.getFullYear(), start.getMonth() + sourcePeriodMonths, 0);
        const today = new Date();
        const end = today < configuredEnd ? today : configuredEnd;
        if (start <= end) {
          let due = new Date(start.getFullYear(), start.getMonth(), 1);
          if (due < start) due = new Date(due.getFullYear(), due.getMonth() + 1, 1);
          while (due <= end) {
            const monthKey = `${due.getFullYear()}-${String(due.getMonth() + 1).padStart(2, "0")}`;
            if (!recordedAdvances.some(b => String(b.date || "").slice(0, 7) === monthKey)) {
              automaticMonths += 1;
            }
            due = new Date(due.getFullYear(), due.getMonth() + 1, 1);
          }
        }
      }
      const monthlyGross = Number(sourceAttributes.monthly_advance_gross ?? 0);
      const calculatedAdvancePaid = recordedAdvanceTotal + automaticMonths * monthlyGross;
      // Project rule: each first day of a month in the billing period
      // automatically counts as a paid monthly advance. Explicit advance
      // bookings replace the automatic amount for their month.
      const advancePaid = Number.isFinite(Number(sourceAttributes.recorded_advances_paid))
        ? Number(sourceAttributes.recorded_advances_paid)
        : calculatedAdvancePaid;
      return {
        extraCharges,
        credits,
        corrections,
        additionalPayments,
        additionalPaymentCount: additionalPaymentBookings.length,
        correctionCount: correctionBookings.length,
        advancePaid,
      };
    };
    const financeC=financeFor(counter, "consumption", balance), financeF=financeFor(feed, "feed_in", feedBalance);
    const side = (isFeed) => {
      const current=isFeed?currentF:currentC, baseline=isFeed?baselineF:baselineC, delta=isFeed?deltaF:deltaC;
      const bal=isFeed?feedBalance:balance;
      const backendPrice = Number(bal?.attributes?.vm_gross_tariff_ct_kwh);
      const price = Number.isFinite(backendPrice) ? backendPrice : (isFeed?priceF:priceC);
      const amount = Number.isFinite(Number(bal?.attributes?.vm_energy_amount)) ? Number(bal.attributes.vm_energy_amount) : (isFeed?costF:costC);
      const sourceState=isFeed?feed:counter, finance=isFeed?financeF:financeC;
      const directionTitle=isFeed?t("Einspeisung","Feed-in"):t("Verbrauch","Consumption");
      const balanceAttributes = bal?.attributes || {};
      const backendEnergyAmount = Number(balanceAttributes.vm_energy_amount);
      const backendBaseAmount = Number(balanceAttributes.vm_base_amount);
      const backendTotalCosts = Number(balanceAttributes.vm_total_costs);
      const displayedAmount = Number.isFinite(backendEnergyAmount) ? backendEnergyAmount : amount;
      const displayedBase = Number.isFinite(backendBaseAmount) ? backendBaseAmount : proratedBase;
      const totalCosts = Number.isFinite(backendTotalCosts) ? backendTotalCosts :
        (displayedAmount===null?0:displayedAmount)+(isFeed?0:displayedBase)+finance.extraCharges;
      const monthlyAdvance = Number((sourceState?.attributes || {}).monthly_advance_gross ?? 0);
      const balanceValue = valid(bal) ? Number(bal.state) : null;
      const balanceClass = balanceValue === null || balanceValue === 0 ? "settled" : balanceValue < 0 ? "liability" : "credit";
      const balanceLabel = balanceValue === null ? (isFeed?t("Aktuelles Guthaben","Current credit"):t("Offener Betrag","Outstanding amount")) : balanceValue < 0 ? t("Offener Betrag","Outstanding amount") : balanceValue > 0 ? t("Aktuelles Guthaben","Current credit") : t("Ausgeglichen","Settled");
      const balanceText = balanceValue === null ? "–" : `${balanceValue > 0 ? "+" : balanceValue < 0 ? "−" : ""}${money(Math.abs(balanceValue))}`;
      // Forecast sensors are unique to this logical meter and billing direction.
      // Keep their values informational: they never modify the live account balance.
      const forecastBalance = get(`${isFeed ? "feed_in" : "consumption"}_forecast_annual_balance`);
      const forecastAdvance = get(`${isFeed ? "feed_in" : "consumption"}_forecast_monthly_advance`);
      const forecastAvailable = valid(forecastBalance) || valid(forecastAdvance);
      const forecastReliability = Number(forecastBalance?.attributes?.forecast_reliability_percent ?? forecastAdvance?.attributes?.forecast_reliability_percent);
      const seasonValue = forecastBalance?.attributes?.forecast_current_season ?? forecastAdvance?.attributes?.forecast_current_season;
      const seasonNames = {spring:t("Frühling","Spring"),summer:t("Sommer","Summer"),autumn:t("Herbst","Autumn"),winter:t("Winter","Winter")};
      const seasonLabel = seasonNames[String(seasonValue || "").toLowerCase()] || null;
      const hasForecastReliability = Number.isFinite(forecastReliability);
      const reliabilityIcon = forecastReliability >= 80 ? "🟢" : forecastReliability >= 50 ? "🟡" : "🔴";
      const forecastEndLabel = periodEndDate
        ? new Intl.DateTimeFormat(locale, { day: "2-digit", month: "2-digit", year: "numeric" }).format(periodEndDate)
        : "";
      const currentMonthlyAdvance = Number(sourceState?.attributes?.monthly_advance_gross ?? 0);
      const recommendedMonthlyAdvance = valid(forecastAdvance) ? Number(forecastAdvance.state) : null;
      let advanceTrend = "steady", advanceTrendIcon = "↔", advanceTrendText = t("Der Abschlag muss nicht geändert werden", "The advance does not need to be changed");
      if (recommendedMonthlyAdvance !== null && currentMonthlyAdvance > 0) {
        const difference = recommendedMonthlyAdvance - currentMonthlyAdvance;
        if (difference > 0.5) { advanceTrend = "increase"; advanceTrendIcon = "↑"; advanceTrendText = t("Der Abschlag sollte erhöht werden", "The advance should be increased"); }
        else if (difference < -0.5) { advanceTrend = "decrease"; advanceTrendIcon = "↓"; advanceTrendText = t("Der Abschlag könnte verringert werden", "The advance could be reduced"); }
      }
      const forecastEnabled = isFeed ? a.forecast_feed_in_enabled === true : a.forecast_consumption_enabled !== false;
      const forecastBox = `<section class="forecast-box" aria-label="${esc(t("Prognose", "Forecast"))}">
        <div class="forecast-heading">${esc(t("Prognose zum Abrechnungsende am", "Forecast at the end of the billing period on"))}${forecastEndLabel ? ` <span>${esc(forecastEndLabel)}</span>` : ""}</div>
        ${seasonLabel ? `<div class="forecast-season">${esc(t("Jahreszeit:","Season:"))} ${esc(seasonLabel)}</div>` : ""}
        ${hasForecastReliability ? `<div class="forecast-reliability">${esc(t("Zuverlässigkeit:", "Reliability:"))} ${forecastReliability.toFixed(1)}% ${reliabilityIcon}</div>` : ""}
        ${valid(forecastBalance) ? `<div class="forecast-balance"><span>${esc(t("Erwarteter Abrechnungssaldo:", "Expected billing balance:"))}</span><strong class="${Number(forecastBalance.state) < 0 ? "negative" : "positive"}">${esc(`${Number(forecastBalance.state) > 0 ? "+" : Number(forecastBalance.state) < 0 ? "−" : ""}${money(Math.abs(Number(forecastBalance.state)))}`)}</strong></div>` : ""}
        ${valid(forecastAdvance) ? `<div class="forecast-advance ${advanceTrend}"><div class="forecast-trend ${advanceTrend}"><span>${esc(advanceTrendText)}</span><b aria-hidden="true">${advanceTrendIcon}</b></div><span>${esc(t("Möglicher Monatsabschlag:", "Possible monthly advance:"))}</span><div class="forecast-advance-line"><strong>${esc(money(recommendedMonthlyAdvance))}</strong><span class="forecast-monthly-unit">${esc(t("pro Monat", "per month"))}</span><span class="forecast-start-month">→ ${esc(t("ab", "from"))} ${esc(new Intl.DateTimeFormat(locale, {month:"long"}).format(new Date(new Date().getFullYear(), new Date().getMonth()+1, 1)))}</span></div>${forecastAdvance.attributes?.advance_recommendation_limit_applied ? `<small class="forecast-limit-note">${esc(t("Die Empfehlung ist wegen der begrenzten Datenbasis vorsichtig angepasst.", "The recommendation is conservatively adjusted due to limited data."))}</small>` : ""}</div>` : `<div class="forecast-unavailable">${esc(forecastAvailable ? t("Abschlagsprognose derzeit nicht verfügbar", "Monthly advance forecast currently unavailable") : t("Prognosesensoren fehlen oder sind nicht verfügbar. Bitte Prognosekonfiguration und Integrationsprotokoll prüfen.", "Forecast sensors are missing or unavailable. Check forecast configuration and integration logs."))}</div>`}
      </section>`;
      const meterChangeRows = meterChanges.filter(change => isFeed ? change.feed_in_reading !== undefined : change.consumption_reading !== undefined).map(change => {
        const label = `${isFeed?t("Einspeisung bis zum Zählerwechsel","Feed-in until meter replacement"):t("Verbrauch bis zum Zählerwechsel","Consumption until meter replacement")} – ${new Intl.DateTimeFormat(locale).format(new Date(change.date + "T00:00:00"))}`;
        return field(label, num(isFeed ? change.feed_in_reading : change.consumption_reading, 3), "kWh");
      }).join("");
      return `<section class="side"><h3>${esc(directionTitle)}</h3>
        ${meterChangeRows}
        <div class="row baseline-row"><span class="baseline-label">${esc(withColon(t("Zählerstand Abrechnungsbeginn","Meter reading at billing start")))}<span class="baseline-meta-inline">${baselineMeta(isFeed ? "feed_in" : "consumption")}</span></span><strong>${esc(num(baseline,3))} kWh</strong></div>
        ${field(t("Aktueller Zählerstand","Current meter reading"),current===null?"–":num(current,3),"kWh")}
        <div class="row period-row"><span class="period-label">${esc(withColon(t(isFeed?"Einspeisung im Abrechnungszeitraum":"Verbrauch im Abrechnungszeitraum",isFeed?"Feed-in during billing period":"Consumption during billing period")))}${(() => {
          if (!periodStartDate || !periodEndDate) return "";
          const now = new Date();
          const start = new Date(periodStartDate.getFullYear(), periodStartDate.getMonth(), periodStartDate.getDate());
          const end = new Date(periodEndDate.getFullYear(), periodEndDate.getMonth(), periodEndDate.getDate());
          const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
          const elapsed = Math.max(0, Math.min(Math.floor((Math.min(today, end)-start)/86400000)+1, Math.floor((end-start)/86400000)+1));
          let months = (today.getFullYear()-start.getFullYear())*12 + today.getMonth()-start.getMonth();
          const anchor = new Date(start.getFullYear(), start.getMonth()+months, start.getDate());
          if (anchor > today) months--;
          months = Math.max(0, months);
          const monthAnchor = new Date(start.getFullYear(), start.getMonth()+months, start.getDate());
          const days = Math.max(0, Math.floor((today-monthAnchor)/86400000));
          const totalDays = Math.floor((end-start)/86400000)+1;
          const percent = totalDays > 0 ? Math.min(100, Math.round(elapsed/totalDays*100)) : 0;
          const duration = `${months} ${months===1?t("Monat","month"):t("Monate","months")} und ${days} ${days===1?t("Tag","day"):t("Tage","days")}`;
          return `<span class="baseline-meta period-progress">${percent} % · ${esc(duration)}</span>`;
        })()}</span><strong>${esc(delta===null||delta<0?"–":`${num(delta,3)} kWh`)}</strong></div>
        ${field(isFeed?t("Einspeisevergütung","Feed-in tariff"):t("Arbeitspreis","Energy price"),tariff(price),"ct/kWh")}
        <div class="finance-group"><h4>${withColon(isFeed?t("Vergütung","Remuneration"):t("Kosten","Costs"))}</h4>
          ${isFeed ? `<div class="row"><span>${esc(withColon(t("Einspeisevergütung","Feed-in remuneration")))}</span><strong>${amount===null?"–":money(displayedAmount)}</strong></div>` : field(t("Energiekosten","Energy costs"),amount===null?"–":money(displayedAmount))}
          ${!isFeed?`<div class="row"><span>${esc(withColon(t("Anteiliger angefallener Grundpreis","Prorated base price")))} <span class="informational">(${money(base)})</span></span><strong>${money(displayedBase)}</strong></div>`:""}
          ${finance.extraCharges?field(isFeed?t("Zusätzliche Vergütung","Additional remuneration"):t("Zusatzkosten","Extra charges"),money(finance.extraCharges)):""}
          ${!isFeed?(() => {
            // The monthly average is based on the billing-period start, not on
            // when the historical baseline reading was entered or edited.
            // Use the same period-start value that is displayed in the card
            // header. Count elapsed local calendar days, including the start
            // date; the baseline's manual-entry timestamp is intentionally ignored.
            const billingStartTimestamp = periodStart;
            const today = new Date();
            const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(billingStartTimestamp);
            const elapsedDays = match ? Math.max(0, Math.floor((
              Date.UTC(today.getFullYear(), today.getMonth(), today.getDate()) -
              Date.UTC(Number(match[1]), Number(match[2])-1, Number(match[3]))
            ) / 86400000) + 1) : 0;
            // Average all accrued period costs over the elapsed time since
            // billing-period start. The historical baseline entry timestamp
            // is deliberately not part of this calculation.
            const monthlyAverage = elapsedDays > 0 && amount !== null
              ? totalCosts / elapsedDays * 30.436875
              : null;
            return `<div class="row cost-average"><span>${esc(withColon(t("Ø Aktuell im Monat","Average current month")))}</span><strong>${monthlyAverage === null ? esc(t("noch nicht berechenbar","not yet calculable")) : `ca. ${esc(money(monthlyAverage))}`}</strong></div>${field(t("Aktueller Abrechnungszeitraum","Current billing period"),money(totalCosts),"",true)}`;
          })():""}
          ${isFeed?`<div class="row"><span>${esc(withColon(t("Erhaltene Abschläge","Advances received")))} <span class="informational">(${t("mtl.","monthly")} ${money(monthlyAdvance)})</span></span><strong>${money(finance.advancePaid)}</strong></div>
          ${finance.additionalPayments !== 0 ? field(
            finance.additionalPaymentCount === 1
              ? t("Sonderzahlung","Additional payment")
              : t("Sonderzahlungen","Additional payments"),
            money(finance.additionalPayments)
          ) : ""}
          ${finance.corrections !== 0 ? field(
            finance.correctionCount === 1 ? t("Korrektur","Correction") : t("Korrekturen","Corrections"),
            money(finance.corrections)
          ) : ""}
          ${field(t("Gesamt geleistete Zahlungen","Total payments received"),money(finance.advancePaid+finance.additionalPayments+finance.corrections),"",true)}`:`<h4>${t("Bereits gezahlt:","Payments received:")}</h4>
          <div class="row"><span>${esc(withColon(t("Abschläge","Advances")))} <span class="informational">(${t("mtl.","monthly")} ${money(monthlyAdvance)})</span></span><strong>${money(finance.advancePaid)}</strong></div>
          ${finance.additionalPayments !== 0 ? field(
            finance.additionalPaymentCount === 1
              ? t("Summe der Sonderzahlung","Total additional payment")
              : t("Summe der Sonderzahlungen","Total additional payments"),
            money(finance.additionalPayments),
            "",
            true
          ) : ""}
          ${finance.corrections !== 0 ? field(
            finance.correctionCount === 1 ? t("Korrektur","Correction") : t("Korrekturen","Corrections"),
            money(finance.corrections)
          ) : ""}
          ${field(t("Gesamt geleistete Zahlungen","Total payments received"),money(finance.advancePaid+finance.additionalPayments+finance.corrections),"",true)}` }
          ${finance.credits?field(t("Gutschriften","Credits"),money(finance.credits)):""}
          <div class="grand-balance ${balanceClass}">${field(balanceLabel,balanceText,"",true)}</div>
          ${forecastEnabled ? forecastBox : ""}
        </div></section>`;
    };
    const selectedCounter = selectedDirection === "feed_in" ? feed : counter;
    const selectedBalance = selectedDirection === "feed_in" ? feedBalance : balance;
    const directions=[];
    if (selectedCounter || selectedBalance) directions.push({kind:selectedDirection,html:side(selectedDirection === "feed_in")});
    const periodStartForMeter=String(a.billing_period_start||a.billing_start||a.contract_start||"").slice(0,10);
    let periodText="";
    if (/^\d{4}-\d{2}-\d{2}$/.test(periodStartForMeter)) {
      const start=new Date(`${periodStartForMeter}T00:00:00`), months=Math.max(1,Number(a.billing_period_months||12));
      const end=new Date(start.getFullYear(),start.getMonth()+months,0);
      const fmt=new Intl.DateTimeFormat(locale,{day:"2-digit",month:"2-digit",year:"numeric"});
      periodText=`${t("Aktueller Abrechnungsstand:","Current billing status:")}<br><span class="billing-period-line">${t("Abrechnungszeitraum:","Billing period:")} ${fmt.format(start)} – ${fmt.format(end)}</span>`;
    }
    const changeRows = meterChanges.map((change,index)=>`<div class="meter-change-row" data-id="${esc(change.id||"")}">
      <label>${t("Datum des Zählerwechsels","Meter replacement date")}<input type="date" class="change-date" value="${esc(change.date)}"></label>
      <label>${t("Verbrauch bis zum Zählerwechsel (kWh)","Consumption until meter replacement (kWh)")}<input class="change-consumption" inputmode="decimal" value="${esc(inputNumber(change.consumption_reading,3,true))}"></label>
      ${feed?`<label>${t("Einspeisung bis zum Zählerwechsel (kWh)","Feed-in until meter replacement (kWh)")}<input class="change-feed-in" inputmode="decimal" value="${esc(inputNumber(change.feed_in_reading,3,true))}"></label>`:""}
      <button type="button" class="remove-meter-change">${t("Entfernen","Remove")}</button></div>`).join("");
    const editForm=this._editing?`<form class="contract-edit" data-entry="${esc(a.hub_entry_id)}" data-contract="${esc(a.contract_id)}" data-meter="${esc(selectedId)}">
      <h4>${t("Vertrags- und Abrechnungswerte bearbeiten","Edit contract and billing values")}</h4>
      <section class="meter-changes-editor"><h4>${t("Zählerwechsel im aktuellen Abrechnungszeitraum","Meter replacements in current billing period")}</h4><div class="meter-change-list">${changeRows}</div><button type="button" class="add-meter-change">${t("Zählerwechsel hinzufügen","Add meter replacement")}</button></section>
      <label>${t("Mehrwertsteuer (%)","VAT (%)")}<input name="vat_rate_percent" inputmode="decimal" value="${esc(inputNumber(vat,2,true))}"></label>
      ${selectedDirection === "feed_in" ? `<label>${t("Einspeisetarif brutto (ct/kWh)","Gross feed-in tariff (ct/kWh)")}<input name="feed_in_price_gross_ct_kwh" inputmode="decimal" value="${esc(inputNumber(priceF,6,true))}"></label>` : `<label>${t("Arbeitspreis brutto (ct/kWh)","Gross energy price (ct/kWh)")}<input name="purchase_price_gross_ct_kwh" inputmode="decimal" value="${esc(inputNumber(priceC,6,true))}"></label>`}
      <label>${t("Jährlicher Grundpreis brutto (€)","Annual gross base price (€)")}<input name="base_price_gross" inputmode="decimal" value="${esc(inputNumber(base,6,true))}"></label>
      <label>${t("Monatlicher Abschlag brutto (€)","Monthly gross advance (€)")}<input name="monthly_advance_gross" inputmode="decimal" value="${esc(inputNumber(gross(a.monthly_advance_net),6,true))}"></label>
      <label>${t("Zählerstand Abrechnungsbeginn Verbrauch (kWh)","Consumption meter reading at billing start (kWh)")}<input name="previous_consumption_reading" inputmode="decimal" value="${esc(inputNumber(baselineC,6,true))}" data-original="${esc(inputNumber(baselineC,6,true))}"></label>
      ${feed?`<label>${t("Zählerstand Abrechnungsbeginn Einspeisung (kWh)","Feed-in meter reading at billing start (kWh)")}<input name="previous_feed_in_reading" inputmode="decimal" value="${esc(inputNumber(baselineF,6,true))}" data-original="${esc(inputNumber(baselineF,6,true))}"></label>`:""}
      <div class="edit-actions"><button type="submit">${t("Speichern","Save")}</button><button type="button" class="cancel-edit">${t("Abbrechen","Cancel")}</button></div>
    </form>`:"";
    const cardHeading=`<div class="card-heading"><div class="heading-copy"><h1>${esc(meterName)}</h1>${periodText?`<div class="period-info">${periodText}</div>`:""}</div><button type="button" class="toggle-edit">${this._editing?t("Bearbeiten schließen","Close editing"):t("Bearbeiten","Edit")}</button></div>`;
    this.innerHTML=`<ha-card class="billing-card"><div class="content">${cardHeading}<div class="billing-direction">${directions.map(d=>d.html).join("")}</div>${editForm}</div></ha-card>
      <style>
        /* One native Lovelace card represents exactly one meter reading / billing direction. */
        :host{display:block;width:100%;min-width:0;max-width:100%;box-sizing:border-box}
        .billing-card{display:block;width:100%;min-width:0;max-width:100%;box-sizing:border-box}
        .content{box-sizing:border-box;width:100%;min-width:0;padding:20px}
        .card-heading{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin:0 0 18px;min-width:0}
        .heading-copy{min-width:0}.card-heading h1{font-size:1.5rem;font-weight:400;margin:0}.card-heading h2{font-size:1rem;font-weight:600;margin:5px 0 0}
        .period-info{margin-top:5px;color:var(--secondary-text-color);font-size:.9rem;line-height:1.45}.billing-period-line{display:inline-block;white-space:nowrap}@media(max-width:520px){.billing-period-line{font-size:.88em}}
        .card-heading button,.edit-actions button{padding:8px 14px;border:0;border-radius:6px;background:var(--primary-color);color:var(--text-primary-color,#fff);cursor:pointer;white-space:nowrap}
        .billing-direction{display:block;width:100%;min-width:0}
        .side{box-sizing:border-box;width:100%;min-width:0;padding:0}.side h3{font-size:1rem;margin:0 0 10px;color:var(--primary-color)}
        .row{display:flex;justify-content:space-between;gap:12px;padding:8px 0;border-bottom:1px solid var(--divider-color)}
        .period-row{align-items:center;padding:4px 0;border-bottom:1px solid var(--divider-color)}.period-label{display:inline-flex;flex-direction:column;align-items:flex-start;gap:0;line-height:18px}.period-progress{display:block;margin:0;font-size:9px;line-height:10px}
        /* The final meter-reading row has no thin bottom rule; the thicker section divider follows after spacing. */
        .side > .row:nth-child(5){border-bottom:0}
        .row span{min-width:0;color:var(--secondary-text-color);overflow-wrap:anywhere}.row strong{text-align:right;white-space:nowrap;flex:0 0 auto;font-weight:400}.row.emphasis strong{font-weight:700}.row.emphasis span{font-weight:400}
        .row .informational{color:var(--disabled-text-color,var(--secondary-text-color));font-weight:400;font-style:normal}
        .cost-average{margin-top:4px;padding-top:10px;border-top:1px solid var(--divider-color)}
        .baseline-row{align-items:center;padding:4px 0;border-bottom:1px solid var(--divider-color)}
        .baseline-row .baseline-label{display:inline-flex;flex-direction:column;align-items:flex-start;gap:0;line-height:18px}
        .baseline-meta-inline{display:block;height:10px;line-height:10px;margin-top:0}
        .baseline-meta{display:inline-flex;align-items:center;gap:6px;margin:0;font-size:9px;line-height:10px;vertical-align:top}
        .baseline-badge{display:inline-block;padding:0 3px;border-radius:7px;font-size:9px;line-height:10px;font-weight:500}
        .baseline-badge.routine{color:#137a3b;background:#d8f2e5}
        .baseline-badge.manual{color:#145a9e;background:#dcecfb}
        .baseline-date{color:var(--secondary-text-color);font-size:9px;line-height:10px}
        .finance-group{margin-top:10px;padding-top:8px;border-top:2px solid var(--divider-color)}.finance-group h4{font-size:.95rem;margin:8px 0 4px;color:var(--primary-text-color)}
        .grand-balance{margin-top:10px;padding:10px;border-radius:8px;font-size:1.08rem}.grand-balance .row{border:0}.grand-balance .row strong{font-size:1.15rem}.grand-balance.liability{background:color-mix(in srgb,var(--error-color,#db4437) 12%,var(--card-background-color,#fff));color:var(--error-color,#db4437)}.grand-balance.credit{background:color-mix(in srgb,var(--success-color,#0b8043) 12%,var(--card-background-color,#fff));color:var(--success-color,#0b8043)}.grand-balance.settled{background:var(--secondary-background-color);color:var(--secondary-text-color)}.grand-balance .row span,.grand-balance .row strong{color:inherit}
        .forecast-box{margin-top:10px;padding:13px 14px;border-radius:8px;background:#fff;color:#171717;border:1.5px solid #d5d5d5}
        .forecast-season{font-size:12px;opacity:.8;margin:3px 0 6px}.forecast-heading{font-weight:700;font-size:.96rem;margin-bottom:2px;color:#171717}.forecast-heading span{font-weight:400;color:#171717;white-space:nowrap}
        .forecast-reliability{font-size:.76rem;line-height:1.35;color:var(--secondary-text-color);margin:0 0 8px}
        .forecast-balance{display:flex;justify-content:space-between;gap:12px;padding:5px 0 10px;border-bottom:1px solid var(--divider-color);color:var(--primary-text-color)}.forecast-balance strong{white-space:nowrap;text-decoration-line:underline;text-decoration-style:double;text-decoration-color:#000;text-underline-offset:3px}.forecast-balance strong.positive{color:#000}.forecast-balance strong.negative{color:#d32f2f}
        .forecast-advance{margin-top:10px;padding:12px 14px;border-radius:8px;color:#202020;border:1px solid rgba(0,0,0,.08)}
        .forecast-advance.increase{background:#fbe8e7}.forecast-advance.decrease{background:#e5f3e9}.forecast-advance.steady{background:#e5eff8}
        .forecast-advance>span{display:block;font-size:.82rem;font-weight:800;letter-spacing:0;color:#202020}.forecast-start-month{font-size:.9rem;font-weight:700;color:#202020}
        .forecast-advance-line{display:flex;align-items:baseline;flex-wrap:wrap;column-gap:4px;row-gap:4px;margin-top:3px;color:#202020}.forecast-advance-line>strong{display:inline-block;font-size:1.9rem;line-height:1.2;font-weight:800;color:#171717;white-space:nowrap}.forecast-limit-note{display:block;margin-top:6px;font-size:.72rem;color:#555}.forecast-monthly-unit{font-size:.9rem;font-weight:700;color:#202020}
        .forecast-trend{display:inline-flex;align-items:baseline;gap:2px;font-size:.9rem;font-weight:700;white-space:normal;color:#202020}.forecast-trend b{font-size:1.2rem;line-height:1;font-weight:900;margin-left:1px}.forecast-unavailable{padding-top:8px;color:var(--secondary-text-color);font-size:.88rem}
        .contract-edit{display:grid;grid-template-columns:minmax(0,1fr);gap:10px;padding:14px;margin-top:14px;border:1px solid var(--divider-color);border-radius:10px}
        .contract-edit h4{margin:0}.meter-changes-editor{display:grid;gap:8px}.meter-change-row{display:grid;gap:8px;padding:10px;border:1px solid var(--divider-color);border-radius:8px}.meter-change-row button,.meter-changes-editor>button{justify-self:start;padding:6px 10px;border:1px solid var(--divider-color);border-radius:6px;background:var(--secondary-background-color);color:var(--primary-text-color);cursor:pointer}.contract-edit label{display:flex;flex-direction:column;gap:4px;color:var(--secondary-text-color);font-size:12px}
        .contract-edit input{box-sizing:border-box;width:100%;min-width:0;padding:8px;border:1px solid var(--divider-color);border-radius:6px;background:var(--card-background-color);color:var(--primary-text-color)}
        .edit-actions{display:flex;gap:8px;justify-content:flex-end}
      </style>`;
    this.querySelector(".toggle-edit")?.addEventListener("click",()=>{this._editing=!this._editing;this.render();});
    this.querySelector(".cancel-edit")?.addEventListener("click",()=>{this._editing=false;this.render();});
    const changeList=this.querySelector(".meter-change-list");
    this.querySelector(".add-meter-change")?.addEventListener("click",()=>{
      const row=document.createElement("div");row.className="meter-change-row";row.innerHTML=`<label>${t("Datum des Zählerwechsels","Meter replacement date")}<input type="date" class="change-date"></label><label>${t("Verbrauch bis zum Zählerwechsel (kWh)","Consumption until meter replacement (kWh)")}<input class="change-consumption" inputmode="decimal"></label>${feed?`<label>${t("Einspeisung bis zum Zählerwechsel (kWh)","Feed-in until meter replacement (kWh)")}<input class="change-feed-in" inputmode="decimal"></label>`:""}<button type="button" class="remove-meter-change">${t("Entfernen","Remove")}</button>`;changeList.append(row);row.querySelector(".remove-meter-change").addEventListener("click",()=>row.remove());
    });
    this.querySelectorAll(".remove-meter-change").forEach(button=>button.addEventListener("click",()=>button.closest(".meter-change-row").remove()));
    this.querySelector("form.contract-edit")?.addEventListener("submit",async ev=>{
      ev.preventDefault();const form=ev.currentTarget;
      const payload={entry_id:form.dataset.entry,contract_id:form.dataset.contract,meter_id:form.dataset.meter};
      const meterChanges=[];
      for(const row of form.querySelectorAll(".meter-change-row")){
        const date=row.querySelector(".change-date")?.value||"";
        const parseField=selector=>{const raw=String(row.querySelector(selector)?.value??"").trim().replace(/\s/g,"");if(!raw)return null;const normalized=raw.includes(",")?raw.replace(/\./g,"").replace(",","."):raw;const value=Number(normalized);if(!Number.isFinite(value)||value<0)throw new Error(t("Ungültiger Zählerwechselwert","Invalid meter replacement value"));return value;};
        if(!date){alert(t("Bitte für jeden Zählerwechsel ein Datum angeben.","Please enter a date for every meter replacement."));return;}
        try{const record={id:row.dataset.id||undefined,date,consumption_reading:parseField(".change-consumption")};if(record.consumption_reading===null)throw new Error(t("Verbrauchs-Endstand fehlt.","Consumption closing reading is required."));if(feed){record.feed_in_reading=parseField(".change-feed-in");if(record.feed_in_reading===null)throw new Error(t("Einspeisungs-Endstand fehlt.","Feed-in closing reading is required."));}meterChanges.push(record);}catch(error){alert(error.message);return;}
      }
      const outsidePeriod=allMeterChanges.filter(change=>{const date=String(change.date||"").slice(0,10);return !(periodStart&&date>=periodStart&&(!periodEndDate||date<=periodEndText));});
      payload.meter_changes=[...outsidePeriod,...meterChanges];
      for(const name of ["vat_rate_percent","purchase_price_gross_ct_kwh","feed_in_price_gross_ct_kwh","base_price_gross","monthly_advance_gross","previous_consumption_reading","previous_feed_in_reading"]){
        const input=form.elements.namedItem(name);if(!input)continue;
        if(name.startsWith("previous_") && input.value.trim() === input.dataset.original) continue;
        const raw=String(input.value).trim().replace(/\s/g,"");const normalized=raw.includes(",")?raw.replace(/\./g,"").replace(",","."):raw;
        if(!/^\d+(?:\.\d{1,6})?$/.test(normalized)){alert(t("Bitte gültige Werte mit höchstens sechs Nachkommastellen eingeben.","Enter valid values with no more than six decimal places."));return;}
        const value=Number(normalized);if(!Number.isFinite(value)||value<0){alert(t("Bitte gültige nichtnegative Werte eingeben.","Enter valid non-negative values."));return;}payload[name]=normalized;
      }
      try{await this._hass.callService("verbrauchsmonitor","update_contract",payload);this._editing=false;this.render();}
      catch(err){alert(t("Vertragswerte konnten nicht gespeichert werden.","Contract values could not be saved."));}
    });
  }
}
customElements.define("verbrauchsmonitor-billing-card",VerbrauchsMonitorBillingCard);

class VerbrauchsMonitorBillingCardEditor extends HTMLElement {
  setConfig(config){this.config={...config};this.render();}
  set hass(hass){this._hass=hass;this.render();}
  render(){
    if(!this._hass||!this.config)return;
    const de=(this._hass.locale?.language||"de").toLowerCase().startsWith("de");
    const t=(a,b)=>de?a:b;
    const meters=new Map();
    for(const state of Object.values(this._hass.states)){
      if(!state.entity_id.startsWith("sensor.")||!state.attributes?.vm_role||state.attributes.vm_role==="outdoor_illuminance")continue;
      const id=state.attributes.meter_id||state.attributes.meter_number||state.entity_id;
      const name=state.attributes.meter_name||t("Stromzähler","Electricity meter");
      const number=state.attributes.meter_number||"";
      if(!meters.has(id))meters.set(id,{id,name,number,consumption:false,feed_in:false});
      const m=meters.get(id);
      if(["consumption_counter","consumption_balance"].includes(state.attributes.vm_role))m.consumption=true;
      if(["feed_in_counter","feed_in_balance"].includes(state.attributes.vm_role))m.feed_in=true;
    }
    const esc=v=>String(v??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
    const options=[...meters.values()].map(m=>`<option value="${esc(m.id)}" ${this.config.meter_id===m.id?"selected":""}>${esc(m.name+(m.number?` (${m.number})`:""))}</option>`).join("");
    const selected=meters.get(this.config.meter_id)||[...meters.values()][0];
    const directionOptions=selected?[
      ...(selected.consumption?[{id:"consumption",label:t("Verbrauch","Consumption")}]:[]),
      ...(selected.feed_in?[{id:"feed_in",label:t("Einspeisung","Feed-in")}]:[])
    ]:[];
    const directionHtml=directionOptions.map(d=>`<option value="${d.id}" ${(this.config.direction||"consumption")===d.id?"selected":""}>${d.label}</option>`).join("");
    this.innerHTML=`<div class="editor"><label>${t("Zähler","Meter")}<select id="meter"><option value="">${t("Zähler auswählen …","Select a meter …")}</option>${options}</select></label><label>${t("Zählerstand / Abrechnungsbereich","Meter reading / billing direction")}<select id="direction"><option value="">${t("Bereich auswählen …","Select a direction …")}</option>${directionHtml}</select></label><p>${t("Eine Karte zeigt genau einen Zählerstand: entweder Verbrauch oder Einspeisung. Für jeden weiteren Zählerstand eine eigene Lovelace-Karte hinzufügen.","One card shows exactly one meter reading: either consumption or feed-in. Add a separate Lovelace card for every additional meter reading.")}</p></div><style>.editor{display:grid;gap:12px;padding:12px;color:var(--primary-text-color)}.editor label{display:grid;gap:5px}.editor input,.editor select{box-sizing:border-box;width:100%;padding:9px;background:var(--card-background-color);color:var(--primary-text-color);border:1px solid var(--divider-color);border-radius:6px}.editor p{color:var(--secondary-text-color);margin:0}</style>`;
    this.querySelector("#meter").addEventListener("change",e=>{
      const id=e.target.value;this.config={...this.config,meter_id:id,direction:"consumption"};this.render();this.dispatchEvent(new CustomEvent("config-changed",{detail:{config:this.config},bubbles:true,composed:true}));
    });
    this.querySelector("#direction").addEventListener("change",e=>this._change({direction:e.target.value}));
  }
  _change(update){this.config={...this.config,...update};this.dispatchEvent(new CustomEvent("config-changed",{detail:{config:this.config},bubbles:true,composed:true}));}
}
customElements.define("verbrauchsmonitor-billing-card-editor",VerbrauchsMonitorBillingCardEditor);
window.customCards.push({type:"verbrauchsmonitor-billing-card",name:"VerbrauchsMonitor – Aktuelle Abrechnung",description:"Eine eigenständig verschiebbare Karte je Zählerstand und Abrechnungsbereich."});
