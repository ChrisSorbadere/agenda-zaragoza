#!/usr/bin/env python3
"""Relais local : télécharge l'agenda officiel de la mairie de Zaragoza
(données ouvertes) depuis ce PC (en Espagne) et le publie dans le dépôt
GitHub ChrisSorbadere/agenda-zaragoza (data/agenda.json).
Ne s'exécute qu'une fois par jour, même s'il est lancé plusieurs fois."""
import json, datetime, urllib.request, urllib.parse, base64, os, sys

REPO = "ChrisSorbadere/agenda-zaragoza"
CONF = os.path.expanduser("~/.config/agenda-zaragoza")
TOKEN_FILE = os.path.join(CONF, "token")
STAMP = os.path.join(CONF, "derniere-execution")
LOG = os.path.join(CONF, "journal.txt")
API = "https://www.zaragoza.es/sede/servicio/cultura/evento/list.json"

def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M} {msg}"
    print(line)
    with open(LOG, "a") as f: f.write(line + "\n")

def http(url, data=None, method="GET", headers=None, timeout=90):
    h = {"User-Agent": "agenda-zaragoza-relais", "Accept": "application/json"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)

def pick(d, *keys):
    if not isinstance(d, dict): return None
    for k in keys:
        v = d.get(k)
        if v not in (None, "", []): return v
    return None

def as_list(x):
    if x is None: return []
    return x if isinstance(x, list) else [x]

def lugar(ev):
    for s in as_list(ev.get("subEvent")):
        loc = s.get("location") if isinstance(s, dict) else None
        n = pick(loc, "title", "name")
        if n: return n
    return pick(ev.get("location"), "title", "name")

def horario(ev):
    for s in as_list(ev.get("subEvent")):
        h = pick(s, "horario", "openingHours")
        if h: return h
    return pick(ev, "horario", "openingHours")

def telecharger(hoy, fin):
    eventos, primera, start, rows = [], None, 0, 500
    fq = f"startDate:[* TO {fin}T23:59:59Z] AND endDate:[{hoy}T00:00:00Z TO *]"
    filtro = True
    while True:
        params = {"rows": rows, "start": start}
        if filtro: params["fq"] = fq
        try:
            data = http(API + "?" + urllib.parse.urlencode(params))
        except Exception as e:
            if filtro and start == 0:
                log(f"filtre de dates refusé ({e}), nouvel essai sans filtre")
                filtro = False
                continue
            raise
        if primera is None: primera = data
        res = as_list(data.get("result") or data.get("results"))
        eventos.extend(res)
        total = data.get("totalCount") or 0
        start += rows
        if not res or start >= total or start >= 6000: break
    return eventos, primera, filtro

def simplifier(eventos, hoy, fin):
    out = []
    for ev in eventos:
        ini = (pick(ev, "startDate") or "")[:10]
        fn = (pick(ev, "endDate") or ini)[:10]
        if ini and not (ini <= fin and fn >= hoy): continue
        cats = [pick(c, "title", "name") for c in as_list(ev.get("category")) if isinstance(c, dict)]
        out.append({
            "titulo": pick(ev, "title"),
            "inicio": ini, "fin": fn,
            "horario": horario(ev), "lugar": lugar(ev),
            "categorias": [c for c in cats if c],
            "precio": pick(ev, "price", "precio"),
            "descripcion": (pick(ev, "description") or "")[:300],
            "url": (f"https://www.zaragoza.es/sede/servicio/cultura/evento/{ev['id']}"
                    if ev.get("id") else pick(ev, "web", "url")),
        })
    out.sort(key=lambda e: (e["inicio"] or "", e["titulo"] or ""))
    return out

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
    today = datetime.date.today()
    force = "--force" in sys.argv
    if not force and os.path.exists(STAMP) and open(STAMP).read().strip() == today.isoformat():
        return  # déjà fait aujourd'hui
    token = open(TOKEN_FILE).read().strip()
    hoy, fin = today.isoformat(), (today + datetime.timedelta(days=16)).isoformat()
    try:
        eventos, primera, filtro = telecharger(hoy, fin)
    except Exception as e:
        log(f"ÉCHEC téléchargement mairie : {e}"); sys.exit(1)
    salida = simplifier(eventos, hoy, fin)
    meta = {"generado": datetime.datetime.now().isoformat(timespec="minutes"),
            "desde": hoy, "hasta": fin, "filtro_fechas_api": filtro,
            "total": len(salida),
            "fuente": "Ayuntamiento de Zaragoza - Datos abiertos (Agenda de Zaragoza)"}
    try:
        publier(token, "data/agenda.json",
                json.dumps({"meta": meta, "eventos": salida}, ensure_ascii=False, indent=1),
                f"Agenda {hoy} ({len(salida)} eventos)")
        if primera is not None:
            ech = dict(primera); ech["result"] = as_list(primera.get("result"))[:3]
            publier(token, "data/agenda-muestra.json",
                    json.dumps(ech, ensure_ascii=False, indent=1), f"Muestra {hoy}")
    except Exception as e:
        log(f"ÉCHEC envoi GitHub : {e}"); sys.exit(1)
    open(STAMP, "w").write(hoy)
    log(f"OK : {len(salida)} événements publiés ({hoy} → {fin})")

if __name__ == "__main__":
    main()
