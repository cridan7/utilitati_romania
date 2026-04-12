class UtilitatiRomaniaFacturiCard extends HTMLElement {
  setConfig(config) {
    this._config = {
      title: "Facturi utilități",
      entity: null,
      show_header: true,
      show_summary: true,
      only_unpaid: false,
      show_paid: true,
      ...config,
    };

    if (!this._expanded) {
      this._expanded = {};
    }
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 8;
  }

  _findEntityId() {
    if (this._config.entity && this._hass.states[this._config.entity]) {
      return this._config.entity;
    }

    const candidates = Object.keys(this._hass.states).filter((entityId) => {
      if (!entityId.startsWith("sensor.")) {
        return false;
      }
      const stateObj = this._hass.states[entityId];
      if (!stateObj) {
        return false;
      }
      const attrs = stateObj.attributes || {};
      return Array.isArray(attrs.locatii);
    });

    return candidates[0] || null;
  }

  _normalizeStatus(value) {
    const text = String(value ?? "").trim().toLowerCase();

    if (!text) return "unknown";
    if (["paid", "platita", "plătită", "platit", "achitata", "achitată"].includes(text)) return "paid";
    if (["unpaid", "neplatita", "neplătită", "neplatit", "restanta", "restanță", "de_plata", "de plată"].includes(text)) return "unpaid";
    if (["credit", "prosumator"].includes(text)) return "credit";

    return text;
  }

  _statusLabel(status) {
    if (status === "paid") return "Plătită";
    if (status === "unpaid") return "Neplătită";
    if (status === "credit") return "Credit";
    return "Necunoscut";
  }

  _formatDate(value) {
    if (!value) return "—";

    const text = String(value).trim();
    if (!text) return "—";

    if (/^\d{2}\.\d{2}\.\d{4}$/.test(text)) {
      return text;
    }

    const parsed = new Date(text);
    if (!Number.isNaN(parsed.getTime())) {
      try {
        return new Intl.DateTimeFormat("ro-RO").format(parsed);
      } catch (_err) {
        return text;
      }
    }

    return text;
  }

  _toNumber(value) {
    if (typeof value === "number") {
      return Number.isFinite(value) ? value : 0;
    }

    if (typeof value === "string") {
      const normalized = value.replace(/\s/g, "").replace(",", ".");
      const parsed = Number(normalized);
      return Number.isFinite(parsed) ? parsed : 0;
    }

    return 0;
  }

  _formatMoney(value, currency = "RON") {
    if (value === null || value === undefined || value === "") {
      return "—";
    }

    const amount = this._toNumber(value);

    try {
      return new Intl.NumberFormat("ro-RO", {
        style: "currency",
        currency,
        maximumFractionDigits: 2,
      }).format(amount);
    } catch (_err) {
      return `${amount.toFixed(2)} ${currency}`;
    }
  }

  _escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  _escapeAttr(value) {
    return this._escapeHtml(value);
  }

  _filterLocations(locations) {
    const onlyUnpaid = !!this._config.only_unpaid;
    const showPaid = this._config.show_paid !== false;

    return locations
      .map((location) => {
        const providers = Array.isArray(location.furnizori) ? location.furnizori : [];

        const filteredProviders = providers.filter((provider) => {
          const status = this._normalizeStatus(provider.status || provider.payment_status || provider.status_raw);

          if (onlyUnpaid) {
            return status === "unpaid";
          }

          if (!showPaid && status === "paid") {
            return false;
          }

          return true;
        });

        if (!filteredProviders.length) {
          return null;
        }

        return {
          ...location,
          furnizori: filteredProviders,
        };
      })
      .filter(Boolean);
  }

  _locationSummary(location) {
    const providers = Array.isArray(location.furnizori) ? location.furnizori : [];
    const paid = providers.filter((item) => this._normalizeStatus(item.status || item.payment_status || item.status_raw) === "paid").length;
    const unpaid = providers.filter((item) => this._normalizeStatus(item.status || item.payment_status || item.status_raw) === "unpaid").length;
    const credit = providers.filter((item) => this._normalizeStatus(item.status || item.payment_status || item.status_raw) === "credit").length;

    const parts = [];
    parts.push(`${providers.length} ${providers.length === 1 ? "factură" : "facturi"}`);
    if (paid > 0) parts.push(`${paid} plătite`);
    if (unpaid > 0) parts.push(`${unpaid} neplătite`);
    if (credit > 0) parts.push(`${credit} credit`);

    return parts.join(" • ");
  }

  _buildSummary(attrs) {
    const total = this._toNumber(attrs.numar_facturi);
    const paid = this._toNumber(attrs.numar_platite);
    const unpaid = this._toNumber(attrs.numar_neplatite);
    const unknown = this._toNumber(attrs.numar_necunoscute ?? attrs.numar_status_necunoscut);
    const totalUnpaid = attrs.total_neplatit_formatat || this._formatMoney(attrs.total_neplatit, attrs.moneda || "RON");

    return `
      <div class="summary">
        <div><span class="summary-label">Facturi:</span> <span class="summary-value">${total}</span></div>
        <div><span class="summary-label">Plătite:</span> <span class="summary-value">${paid}</span></div>
        <div><span class="summary-label">Neplătite:</span> <span class="summary-value">${unpaid}</span></div>
        <div><span class="summary-label">Necunoscute:</span> <span class="summary-value">${unknown}</span></div>
        <div><span class="summary-label">Total neplătit:</span> <span class="summary-value">${this._escapeHtml(totalUnpaid)}</span></div>
      </div>
    `;
  }

  _rowKey(location, provider, index) {
    const loc = location.locatie_cheie || location.eticheta_locatie || "loc";
    const furn = provider.furnizor || provider.furnizor_label || "furnizor";
    const inv = provider.invoice_id || provider.invoice_title || index;
    return `${loc}__${furn}__${inv}__${index}`;
  }

  _isExpanded(key) {
    return !!this._expanded[key];
  }

  _providerCompactTitle(provider) {
    return provider.invoice_title || provider.invoice_id || "Ultima factură";
  }

  _buildProviderRow(location, provider, index) {
    const supplier = provider.furnizor_label || provider.furnizor || "Furnizor";
    const title = this._providerCompactTitle(provider);
    const amountFormatted = this._formatMoney(provider.amount, provider.currency || "RON");
    const status = this._normalizeStatus(provider.status || provider.payment_status || provider.status_raw);
    const statusLabel = this._statusLabel(status);
    const issueDate = this._formatDate(provider.issue_date || provider.data_emitere);
    const dueDate = this._formatDate(provider.due_date || provider.data_scadenta);
    const tipServiciu = provider.tip_serviciu || "—";
    const numeCont = provider.nume_cont || "—";

    const key = this._rowKey(location, provider, index);
    const expanded = this._isExpanded(key);

    let statusClass = "status-unknown";
    if (status === "paid") statusClass = "status-paid";
    else if (status === "unpaid") statusClass = "status-unpaid";
    else if (status === "credit") statusClass = "status-credit";

    return `
      <div class="invoice-row-wrap">
        <div class="invoice-row">
          <div class="row-main">
            <div class="row-supplier">${this._escapeHtml(supplier)}</div>
            <div class="row-title">${this._escapeHtml(title)}</div>
          </div>

          <div class="row-amount">${this._escapeHtml(amountFormatted)}</div>

          <button class="details-btn" data-key="${this._escapeAttr(key)}">
            ${expanded ? "Ascunde" : "Detalii"}
          </button>
        </div>

        ${
          expanded
            ? `
              <div class="invoice-details">
                <div><span class="detail-label">Status:</span> <span class="detail-value ${statusClass}">${this._escapeHtml(statusLabel)}</span></div>
                <div><span class="detail-label">Data emiterii:</span> <span class="detail-value">${this._escapeHtml(issueDate)}</span></div>
                <div><span class="detail-label">Data scadenței:</span> <span class="detail-value">${this._escapeHtml(dueDate)}</span></div>
                <div><span class="detail-label">Serviciu:</span> <span class="detail-value">${this._escapeHtml(tipServiciu)}</span></div>
                <div><span class="detail-label">Cont:</span> <span class="detail-value">${this._escapeHtml(numeCont)}</span></div>
                ${
                  provider.pdf_url
                    ? `<div class="detail-actions"><button class="pdf-btn" data-url="${this._escapeAttr(provider.pdf_url)}">Deschide PDF</button></div>`
                    : ""
                }
              </div>
            `
            : ""
        }
      </div>
    `;
  }

  _attachEvents(root) {
    root.querySelectorAll(".details-btn[data-key]").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.stopPropagation();
        const key = button.getAttribute("data-key");
        if (!key) return;
        this._expanded[key] = !this._expanded[key];
        this._render();
      });
    });

    root.querySelectorAll(".pdf-btn[data-url]").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.stopPropagation();
        const url = button.getAttribute("data-url");
        if (url) {
          window.open(url, "_blank", "noopener");
        }
      });
    });
  }

  _render() {
    if (!this._hass) {
      return;
    }

    if (!this.content) {
      const card = document.createElement("ha-card");
      this.content = document.createElement("div");
      this.content.className = "card-content";
      card.appendChild(this.content);
      this.appendChild(card);
    }

    const entityId = this._findEntityId();
    const entity = entityId ? this._hass.states[entityId] : null;

    if (!entity) {
      this.content.innerHTML = `
        <style>${this._styles()}</style>
        <div class="wrapper">
          <div class="title">${this._escapeHtml(this._config.title)}</div>
          <div class="error">Nu am găsit senzorul agregat pentru facturi.</div>
        </div>
      `;
      return;
    }

    const attrs = entity.attributes || {};
    const locations = this._filterLocations(Array.isArray(attrs.locatii) ? attrs.locatii : []);

    this.content.innerHTML = `
      <style>${this._styles()}</style>
      <div class="wrapper">
        ${
          this._config.show_header
            ? `
              <div class="header">
                <div class="title">${this._escapeHtml(this._config.title || entity.attributes.friendly_name || "Facturi utilități")}</div>
                <div class="count">${locations.length} ${locations.length === 1 ? "adresă" : "adrese"}</div>
              </div>
            `
            : ""
        }

        ${this._config.show_summary ? this._buildSummary(attrs) : ""}

        <div class="locations">
          ${
            locations.length
              ? locations
                  .map(
                    (location) => `
                <div class="location">
                  <div class="location-title">${this._escapeHtml(location.eticheta_locatie || location.locatie_cheie || "Locație")}</div>
                  <div class="location-meta">${this._escapeHtml(this._locationSummary(location))}</div>
                  <div class="invoice-list">
                    ${(location.furnizori || [])
                      .map((provider, index) => this._buildProviderRow(location, provider, index))
                      .join("")}
                  </div>
                </div>
              `
                  )
                  .join("")
              : `<div class="empty">Nu există facturi de afișat pentru filtrele selectate.</div>`
          }
        </div>

        <div class="footer">Sursă date: ${this._escapeHtml(entity.entity_id)}</div>
      </div>
    `;

    this._attachEvents(this.content);
  }

  _styles() {
    return `
      .wrapper {
        padding: 16px;
      }

      .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
        margin-bottom: 14px;
      }

      .title {
        font-size: 1.1rem;
        font-weight: 600;
      }

      .count {
        font-size: 0.85rem;
        color: var(--secondary-text-color);
      }

      .summary {
        display: flex;
        flex-direction: column;
        gap: 6px;
        margin-bottom: 18px;
        padding-bottom: 14px;
        border-bottom: 1px solid var(--divider-color);
      }

      .summary-label {
        color: var(--secondary-text-color);
      }

      .summary-value {
        font-weight: 600;
      }

      .locations {
        display: flex;
        flex-direction: column;
        gap: 18px;
      }

      .location {
        padding-bottom: 14px;
        border-bottom: 1px solid var(--divider-color);
      }

      .location:last-child {
        border-bottom: none;
        padding-bottom: 0;
      }

      .location-title {
        font-size: 1rem;
        font-weight: 700;
        margin-bottom: 4px;
      }

      .location-meta {
        font-size: 0.85rem;
        color: var(--secondary-text-color);
        margin-bottom: 12px;
      }

      .invoice-list {
        display: flex;
        flex-direction: column;
        gap: 10px;
      }

      .invoice-row-wrap {
        border-radius: 10px;
        background: var(--secondary-background-color);
        overflow: hidden;
      }

      .invoice-row {
        display: grid;
        grid-template-columns: minmax(0, 1.8fr) auto auto;
        gap: 10px;
        align-items: center;
        padding: 10px 12px;
      }

      .row-main {
        min-width: 0;
      }

      .row-supplier {
        font-weight: 700;
        margin-bottom: 2px;
      }

      .row-title {
        font-size: 0.84rem;
        color: var(--secondary-text-color);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .row-amount {
        font-weight: 600;
        white-space: nowrap;
      }

      .details-btn {
        padding: 6px 10px;
        border-radius: 8px;
        border: 1px solid var(--divider-color);
        background: transparent;
        color: var(--primary-text-color);
        cursor: pointer;
        font: inherit;
        white-space: nowrap;
      }

      .details-btn:hover {
        background: rgba(255, 255, 255, 0.04);
      }

      .invoice-details {
        padding: 0 12px 12px 12px;
        display: flex;
        flex-direction: column;
        gap: 6px;
        font-size: 0.9rem;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
      }

      .detail-label {
        color: var(--secondary-text-color);
      }

      .detail-value {
        font-weight: 500;
      }

      .detail-actions {
        margin-top: 4px;
      }

      .pdf-btn {
        padding: 8px 10px;
        border-radius: 10px;
        border: 1px solid var(--divider-color);
        background: transparent;
        color: var(--primary-text-color);
        cursor: pointer;
        font: inherit;
      }

      .pdf-btn:hover {
        background: rgba(255, 255, 255, 0.04);
      }

      .status-paid {
        color: var(--success-color, #2e7d32);
      }

      .status-unpaid {
        color: var(--error-color);
      }

      .status-credit {
        color: var(--info-color, #1976d2);
      }

      .status-unknown {
        color: var(--secondary-text-color);
      }

      .empty,
      .error {
        color: var(--secondary-text-color);
      }

      .footer {
        margin-top: 16px;
        font-size: 0.78rem;
        color: var(--secondary-text-color);
      }

      @media (max-width: 640px) {
        .invoice-row {
          grid-template-columns: minmax(0, 1fr) auto;
        }

        .details-btn {
          grid-column: 2;
          grid-row: 1 / span 2;
          align-self: center;
        }

        .row-amount {
          font-size: 0.9rem;
        }
      }
    `;
  }

  static getStubConfig() {
    return {
      type: "custom:utilitati-romania-facturi-card",
      title: "Facturi utilități",
      show_header: true,
      show_summary: true,
      only_unpaid: false,
      show_paid: true,
    };
  }
}

customElements.define("utilitati-romania-facturi-card", UtilitatiRomaniaFacturiCard);

if (window.customCards) {
  window.customCards.push({
    type: "utilitati-romania-facturi-card",
    name: "Utilități România Facturi Card",
    description: "Card compact cu detalii expandabile pentru facturi agregate.",
  });
}