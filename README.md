# Utilități România – Home Assistant Integration

Integrarea **Utilități România** aduce într-un singur loc datele de consum, facturare și interacțiune cu furnizorii de utilități din România, direct în Home Assistant.

Am construit integrarea asta dintr-o nevoie reală: să nu mai intru în mai multe aplicații pentru fiecare furnizor și să pot face lucruri simple, cum ar fi trimiterea indexului, direct din Home Assistant.

---

## 📸 Preview

### Overview
![Overview](images/overview.png)

### Administrare integrare
![Admin](images/admin.png)

### Exemplu furnizor
![Device](images/device.png)

### eBloc (exemplu avansat)
![eBloc](images/ebloc.png)

---

## 🔥 Ce oferă integrarea

- Integrare unificată pentru mai mulți furnizori
- Suport pentru mai multe locații / contracte
- Senzori pentru:
  - consum
  - facturi
  - plăți
  - scadențe
  - solduri
- Trimitere index direct din Home Assistant
- Gestionare număr persoane (unde este permis)
- Panou central de administrare
- Reload global pentru toate sub-integrările
- Diagnostics integrat pentru debugging

---

## 🏢 Furnizori suportați

- Hidroelectrica  
- E.ON România  
- myElectrica  
- Apă Canal Sibiu  
- eBloc  
- Digi România  
- Nova Power & Gas  

---

## 📦 Instalare

### Varianta recomandată (HACS)

1. Deschide HACS  
2. Mergi la Integrations  
3. Meniu (⋮) → Custom repositories  
4. Adaugă:  
https://github.com/mariusonitiu/utilitati_romania  
5. Tip: Integration  
6. Instalează  
7. Restart Home Assistant  

---

## ⚙️ Configurare

1. Settings → Devices & Services  
2. Add Integration  
3. Caută „Utilități România”  
4. Alege furnizorul  
5. Introdu datele de login + cheia de licență  

---

## 🔐 Licență

- 🆓 90 zile trial (complet funcțional)
- 💎 licență lifetime

După expirare:
- integrarea rămâne activă
- dar nu mai actualizează datele și nu mai execută acțiuni

---

## 🧩 Administrare

Se creează un device separat: **Administrare integrare**

Acolo ai:
- Reload all sub-integrations
- Status licență
- Valabilitate
- Plan
- Cont licență

---

## 🔁 Reload global

Din UI sau:

service: utilitati_romania.reload_all

---

## ❤️ Suport

Dacă îți este utilă integrarea:

⭐ lasă un star pe GitHub  
☕ susține proiectul: https://buymeacoffee.com/mariusonitiu  

---

## 👨‍💻 Autor

Marius Onițiu  
https://github.com/mariusonitiu  

---

## ⚖️ Disclaimer

Integrarea nu este afiliată oficial cu furnizorii și folosește API-uri publice sau reverse engineered.
