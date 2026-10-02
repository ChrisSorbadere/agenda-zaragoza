"""Descarga la agenda oficial del Ayuntamiento de Zaragoza (datos abiertos)
para los próximos 16 días y la guarda en data/agenda.json (simplificada)
y data/agenda-raw.json (respuesta bruta, para depurar)."""
import json, datetime, urllib.request, urllib.parse, sys

BASE = "https://www.zaragoza.es/sede/servicio/cultura/evento/list.json"
hoy = datetime.date.today()
fin = hoy + datetime.timedelta(days=16)

def get(params):
    url = BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/json",
                                               "User-Agent": "agenda-zaragoza-bot"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def pick(d, *keys):
    for k in keys:
        v = d.get(k) if isinstance(d, dict) else None
        if v not in (None, "", []):
            return v
    return None

def lugar(ev):
    subs = ev.get("subEvent") or []
    if isinstance(subs, dict): subs = [subs]
    for s in subs:
        loc = s.get("location") or {}
        if isinstance(loc, dict):
            n = pick(loc, "title", "name")
            if n: return n
    loc = ev.get("location") or {}
    return pick(loc, "title", "name") if isinstance(loc, dict) else None

def horario(ev):
    subs = ev.get("subEvent") or []
    if isinstance(subs, dict): subs = [subs]
    for s in subs:
        h = pick(s, "horario", "openingHours")
        if h: return h
    return pick(ev, "horario", "openingHours")

eventos, raw_pages, start, rows = [], [], 0, 500
fq = f"startDate:[* TO {fin.isoformat()}T23:59:59Z] AND endDate:[{hoy.isoformat()}T00:00:00Z TO *]"
filtro_ok = True
while True:
    params = {"rows": rows, "start": start}
    if filtro_ok:
        params["fq"] = fq
    try:
        data = get(params)
    except Exception as e:
        if filtro_ok and start == 0:
            print("Filtro de fechas rechazado, se reintenta sin filtro:", e)
            filtro_ok = False
            continue
        print("ERROR al descargar:", e); sys.exit(1)
    raw_pages.append(data)
    res = data.get("result") or data.get("results") or []
    eventos.extend(res)
    total = data.get("totalCount") or 0
    start += rows
    if not res or start >= total or start >= 5000:
        break

def en_rango(ev):
    ini = (pick(ev, "startDate") or "")[:10]
    fn = (pick(ev, "endDate") or ini)[:10]
    if not ini: return True
    return ini <= fin.isoformat() and fn >= hoy.isoformat()

salida = []
for ev in eventos:
    if not en_rango(ev): continue
    cats = ev.get("category") or []
    if isinstance(cats, dict): cats = [cats]
    salida.append({
        "titulo": pick(ev, "title"),
        "inicio": (pick(ev, "startDate") or "")[:10],
        "fin": (pick(ev, "endDate") or "")[:10],
        "horario": horario(ev),
        "lugar": lugar(ev),
        "categorias": [pick(c, "title", "name") for c in cats if isinstance(c, dict)],
        "precio": pick(ev, "price", "precio"),
        "descripcion": (pick(ev, "description") or "")[:300],
        "url": f"https://www.zaragoza.es/sede/servicio/cultura/evento/{ev.get('id')}" if ev.get("id") else pick(ev, "web", "url"),
    })
salida.sort(key=lambda e: (e["inicio"] or "", e["titulo"] or ""))

meta = {"generado": datetime.datetime.utcnow().isoformat() + "Z",
        "desde": hoy.isoformat(), "hasta": fin.isoformat(),
        "filtro_fechas_api": filtro_ok, "total": len(salida),
        "fuente": "Ayuntamiento de Zaragoza - Datos abiertos (Agenda de Zaragoza)"}
json.dump({"meta": meta, "eventos": salida},
          open("data/agenda.json", "w"), ensure_ascii=False, indent=1)
json.dump(raw_pages[:1], open("data/agenda-raw.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(meta, ensure_ascii=False))
