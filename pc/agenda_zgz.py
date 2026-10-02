#!/usr/bin/env python3
"""Relais local Agenda Zaragoza (v2).
Télécharge depuis ce PC (en Espagne) l'agenda officiel de la mairie de Zaragoza
(données ouvertes), le trie et le publie dans le dépôt GitHub
ChrisSorbadere/agenda-zaragoza (data/agenda.json).
- Se met à jour tout seul depuis le dépôt.
- Ne publie qu'une fois par jour, même s'il est lancé plusieurs fois."""
import json, datetime as dt, urllib.request, urllib.parse, urllib.error
import base64, os, sys, re, html, time

REPO = "ChrisSorbadere/agenda-zaragoza"
CONF = os.path.expanduser("~/.config/agenda-zaragoza")
TOKEN_FILE = os.path.join(CONF, "token")
STAMP = os.path.join(CONF, "derniere-execution")
LOG = os.path.join(CONF, "journal.txt")
API = "https://www.zaragoza.es/sede/servicio/cultura/evento/list.json"
SELF_URL = f"https://raw.githubusercontent.com/{REPO}/main/pc/agenda_zgz.py"
JOURS = 16          # fenêtre couverte
LONG = 45           # au-delà : activité « permanente »
DOW = {"lunes":0,"martes":1,"miercoles":2,"miércoles":2,"jueves":3,"viernes":4,
       "sabado":5,"sábado":5,"domingo":6}
ABR = ["lun","mar","mié","jue","vie","sáb","dom"]

def log(msg):
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M} {msg}"
    print(line)
    with open(LOG, "a") as f: f.write(line + "\n")

def http(url, data=None, method="GET", headers=None, timeout=90, raw=False):
    h = {"User-Agent": "agenda-zaragoza-relais", "Accept": "application/json"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read() if raw else json.load(r)

def auto_maj():
    """Remplace ce script par la dernière version du dépôt si elle a changé."""
    if os.environ.get("AGENDA_ZGZ_MAJ"): return
    try:
        neuf = http(f"{SELF_URL}?t={int(time.time())}", raw=True, timeout=30)
        moi = os.path.abspath(__file__)
        if neuf and neuf != open(moi, "rb").read():
            compile(neuf, moi, "exec")
            open(moi, "wb").write(neuf)
            log("script mis à jour depuis GitHub")
            os.environ["AGENDA_ZGZ_MAJ"] = "1"
            os.execv(sys.executable, [sys.executable, moi] + sys.argv[1:])
    except Exception as e:
        log(f"mise à jour impossible ({e}), on continue avec la version actuelle")

def L(x):
    if x is None: return []
    return x if isinstance(x, list) else [x]

def d10(s):
    try: return dt.date.fromisoformat((s or "")[:10])
    except ValueError: return None

def texte(s, n=220):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n] + ("…" if len(s) > n else "")

def sans_accent(s):
    return (s or "").lower().replace("é","e").replace("á","a")

def telecharger(hoy, fin):
    eventos, start, rows = [], 0, 500
    fq = f"startDate:[* TO {fin}T23:59:59Z] AND endDate:[{hoy}T00:00:00Z TO *]"
    filtro = True
    while True:
        p = {"rows": rows, "start": start}
        if filtro: p["fq"] = fq
        try:
            data = http(API + "?" + urllib.parse.urlencode(p))
        except Exception as e:
            if filtro and start == 0:
                log(f"filtre de dates refusé ({e}), nouvel essai sans filtre")
                filtro = False; continue
            raise
        res = L(data.get("result"))
        eventos.extend(res)
        start += rows
        if not res or start >= (data.get("totalCount") or 0) or start >= 8000: break
    return eventos

def occurrences(ev, hoy, fin):
    """Dates (dans la fenêtre) où l'activité a lieu, et horaires lisibles."""
    fechas, horas = set(), []
    subs = L(ev.get("subEvent")) or [ev]
    for s in subs:
        a = d10(s.get("startDate")) or d10(ev.get("startDate"))
        b = d10(s.get("endDate")) or d10(ev.get("endDate")) or a
        if not a: continue
        jours = set()
        for oh in L(s.get("openingHours")):
            if not isinstance(oh, dict): continue
            j = DOW.get(sans_accent(oh.get("dayOfWeek")))
            t = "-".join(x for x in (oh.get("startTime"), oh.get("endTime")) if x)
            if j is not None:
                jours.add(j); horas.append(f"{ABR[j]} {t}".strip())
            elif t: horas.append(t)
        d = max(a, hoy)
        while d <= min(b, fin):
            if not jours or d.weekday() in jours: fechas.add(d)
            d += dt.timedelta(days=1)
    def cle(h):
        t = h.split(" ")[0]
        return (ABR.index(t) if t in ABR else 9, h)
    return sorted(fechas), sorted(dict.fromkeys(horas), key=cle)

def lieu(ev):
    for s in L(ev.get("subEvent")):
        t = (s.get("location") or {}).get("title") if isinstance(s.get("location"), dict) else None
        if t and "por determinar" not in t.lower(): return t
    return ev.get("location") if isinstance(ev.get("location"), str) and ev.get("location") else None

def prix(ev):
    out = []
    for p in L(ev.get("price")):
        if not isinstance(p, dict): continue
        g, v = p.get("fareGroup"), p.get("hasCurrencyValue")
        if v in (0, "0") or (g and "gratu" in g.lower()): out.append("Gratuit")
        elif v not in (None, ""): out.append(f"{g+' ' if g else ''}{v} €")
    return ", ".join(dict.fromkeys(out)) or None

def traiter(brut, hoy, fin):
    eventos, expos, ecartes = [], [], 0
    for ev in brut:
        fechas, horas = occurrences(ev, hoy, fin)
        if not fechas: continue
        a = d10(ev.get("startDate")); b = d10(ev.get("endDate")) or a
        duree = (b - a).days if a and b else 0
        cats = [c.get("title") for c in L(ev.get("category")) if isinstance(c, dict) and c.get("title")]
        base = {
            "titulo": ev.get("title"),
            "lugar": lieu(ev),
            "categorias": cats,
            "tipo": ev.get("type"),
            "publico": [p.get("title") for p in L(ev.get("population")) if isinstance(p, dict)] or None,
            "precio": prix(ev),
            "url": ev.get("alt") or f"https://www.zaragoza.es/sede/servicio/cultura/evento/{ev.get('id')}",
        }
        if duree > LONG:
            if any(c in ("Exposiciones", "Artes plásticas") for c in cats) or "xposici" in (ev.get("type") or ""):
                expos.append({**base, "hasta": b.isoformat() if b else None,
                              "horario": "; ".join(horas[:4]) or None})
            else:
                ecartes += 1   # ateliers permanents, itinéraires valables des années…
            continue
        eventos.append({**base, "fechas": [f.isoformat() for f in fechas],
                        "horario": "; ".join(horas[:6]) or None,
                        "descripcion": texte(ev.get("description"))})
    fus = {}
    for e in eventos:
        k = ((e["titulo"] or "").strip().lower(), (e["lugar"] or "").strip().lower())
        if k in fus:
            f = fus[k]
            f["fechas"] = sorted(set(f["fechas"]) | set(e["fechas"]))
            if e["horario"] and e["horario"] not in (f["horario"] or ""):
                f["horario"] = "; ".join(x for x in (f["horario"], e["horario"]) if x)
        else:
            fus[k] = e
    eventos = list(fus.values())
    vus = {}
    for x in expos:
        vus.setdefault(((x["titulo"] or "").lower(), (x["lugar"] or "").lower()), x)
    expos = list(vus.values())
    eventos.sort(key=lambda e: (e["fechas"][0], e["titulo"] or ""))
    expos.sort(key=lambda e: e["titulo"] or "")
    return eventos, expos, ecartes

def publier(token, chemin, contenu, message):
    url = f"https://api.github.com/repos/{REPO}/contents/{chemin}"
    hd = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    sha = None
    try: sha = http(url, headers=hd).get("sha")
    except urllib.error.HTTPError as e:
        if e.code != 404: raise
    body = {"message": message, "content": base64.b64encode(contenu.encode()).decode()}
    if sha: body["sha"] = sha
    http(url, data=json.dumps(body).encode(), method="PUT",
         headers={**hd, "Content-Type": "application/json"})

def main():
    os.makedirs(CONF, exist_ok=True)
    auto_maj()
    today = dt.date.today()
    force = "--force" in sys.argv
    if not force and os.path.exists(STAMP) and open(STAMP).read().strip() == today.isoformat():
        return
    token = open(TOKEN_FILE).read().strip()
    hoy, fin = today, today + dt.timedelta(days=JOURS)
    try:
        brut = telecharger(hoy.isoformat(), fin.isoformat())
    except Exception as e:
        log(f"ÉCHEC téléchargement mairie : {e}"); sys.exit(1)
    eventos, expos, ecartes = traiter(brut, hoy, fin)
    meta = {"generado": dt.datetime.now().isoformat(timespec="minutes"),
            "desde": hoy.isoformat(), "hasta": fin.isoformat(),
            "eventos": len(eventos), "exposiciones": len(expos),
            "permanentes_descartados": ecartes, "version": 2,
            "fuente": "Ayuntamiento de Zaragoza - Datos abiertos (Agenda de Zaragoza)"}
    try:
        publier(token, "data/agenda.json",
                json.dumps({"meta": meta, "eventos": eventos, "exposiciones": expos},
                           ensure_ascii=False, separators=(",", ":")),
                f"Agenda {hoy} ({len(eventos)} eventos, {len(expos)} expos)")
    except Exception as e:
        log(f"ÉCHEC envoi GitHub : {e}"); sys.exit(1)
    open(STAMP, "w").write(hoy.isoformat())
    log(f"OK : {len(eventos)} événements + {len(expos)} expositions publiés ({hoy} → {fin})")

if __name__ == "__main__":
    main()
