# Utilități România – Home Assistant Integration

Integrarea **Utilități România** aduce într-un singur loc toate informațiile importante despre utilitățile tale: consum, facturi, plăți și interacțiuni directe cu furnizorii – direct în Home Assistant.

Scopul integrării este simplu: să elimine nevoia de a intra în mai multe aplicații și să permită controlul complet dintr-un singur loc.

---

## 📸 Preview

### Overview

### Administrare integrare

### Exemplu furnizor

### eBloc (exemplu avansat)

---

## 🔥 Funcționalități principale

- Integrare unificată pentru mai mulți furnizori
- Suport pentru mai multe locații și contracte
- Senzori detaliați pentru:
  - consum
  - facturi
  - plăți
  - scadențe
  - solduri
- Trimitere index direct din Home Assistant
- Gestionare număr persoane (unde este permis)
- Sistem de licențiere integrat
- Notificări automate
- Card custom pentru dashboard
- Diagnostics complet pentru debugging

---

## 🧠 Modul Administrare

Integrarea include un modul central de administrare, disponibil automat după instalare.

Acesta oferă:

- status complet al licenței
- informații despre contul asociat
- perioadă de valabilitate
- acțiuni globale (ex: reload integrare)
- informații utile pentru suport și diagnostic

---

## 💳 Card custom (Lovelace)

Integrarea include un **card custom dedicat**, care afișează centralizat toate informațiile importante.

### Include:

- facturi (cu evidențiere pentru cele neplătite)
- notificări pentru:
  - factură nouă emisă
  - deschidere perioadă citire contor
- status general al furnizorilor
- secțiune dedicată licenței:
  - plan activ
  - dată expirare
  - utilizator asociat
  - actualizare cheie licență direct din UI

---

## 🔔 Notificări

Integrarea generează automat notificări pentru:

- emiterea unei facturi noi
- deschiderea perioadei de transmitere index

Notificările sunt gândite să fie utile în viața reală, nu doar informative.

---

## 🏢 Furnizori suportați

- Hidroelectrica
- E.ON România
- myElectrica
- Apă Canal Sibiu
- eBloc
- Digi România
- Nova Power & Gas

> ⚠️ Funcționalitățile pot varia în funcție de furnizor.

---

## 📦 Instalare

### HACS (recomandat)

1. Deschide HACS
2. Mergi la Integrations
3. Meniu (⋮) → Custom repositories
4. Adaugă:
   https://github.com/mariusonitiu/utilitati_romania
5. Tip: Integration
6. Instalează
7. Restart Home Assistant

---

### Instalare manuală

Copiază folderul:

`custom_components/utilitati_romania`

și restart Home Assistant.

---

## ⚙️ Configurare

1. Settings → Devices & Services
2. Add Integration
3. Caută „Utilități România”
4. Selectează furnizorul
5. Introdu datele de autentificare
6. Introdu cheia de licență

---

## 🔐 Licență

Integrarea include sistem de licențiere:

- perioadă trial (complet funcțională)
- licență lifetime

După expirare:

- integrarea rămâne vizibilă
- dar nu mai actualizează datele și nu mai execută acțiuni

Licența poate fi gestionată direct din cardul din dashboard.

---

## 🔁 Reload global

Poți reîncărca toate sub-integrările:

Din UI sau prin serviciu:

`utilitati_romania.reload_all`

---

## 🛠 Troubleshooting

**Nu apar entități**

- restart complet Home Assistant
- verifică logs

**Entități unavailable**

- verifică autentificarea
- verifică licența

---

## 🧾 Diagnostics

Integrarea oferă export complet pentru debugging (fără date sensibile).

---

## 👨‍💻 Autor

Marius Onițiu
https://github.com/mariusonitiu

---

## ❤️ Suport

Dacă integrarea îți este utilă:

⭐ lasă un star pe GitHub
☕ Buy me a coffee

---

## ⚖️ Disclaimer

Integrarea nu este afiliată oficial cu furnizorii și utilizează API-uri publice sau reverse engineered.
