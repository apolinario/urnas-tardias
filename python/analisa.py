import json, glob, csv, collections, sys, os, urllib.request

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # raiz do repositório


def seg(t):
    h, m, s = map(int, t.split(":"))
    return h * 3600 + m * 60 + s


def hms(x):
    return f"{x // 3600:02d}:{x % 3600 // 60:02d}:{x % 60:02d}"


def normaliza(r):
    """Aceita o formato atual do crawl.py (logs por conjunto de arquivos, um dicionário por turno) e devolve o antigo."""
    if "logs" not in r:
        return r
    r = dict(r)
    lg = [l for l in r.pop("logs") if "t2" in l]
    if lg:
        t = lg[-1]["t2"]
        r.update(pronta=t["pronta"], encerramento=t["enc"], votos=t["n"], votos_tarde=[hms(v[0]) for v in t["v"]])
    return r


linhas, porbuf = [], collections.defaultdict(collections.Counter)
vistos = {}
for path in sorted(glob.glob(f"{DIR}/dados/*.jsonl")):
    for l in open(path):
        try:
            r = normaliza(json.loads(l))
        except json.JSONDecodeError:
            continue
        k = (r["uf"], r["cd_mun"], r["zona"], r["secao"])
        if k not in vistos or "erro" in vistos[k]:
            vistos[k] = r
modo = collections.defaultdict(collections.Counter)
for r in vistos.values():
    if r.get("pronta"):
        modo[(r["uf"], r["cd_mun"])][round((seg(r["pronta"][0]) - 8 * 3600) / 3600)] += 1
modo = {k: c.most_common(1)[0][0] for k, c in modo.items()}
for r in vistos.values():
    uf = r["uf"]
    if r.get("erro") == "aux 404":
        continue
    if r.get("erro") or not r.get("pronta") or not r.get("encerramento"):
        porbuf[uf]["sem_dado"] += 1
        continue
    off = modo[(r["uf"], r["cd_mun"])]
    enc = seg(r["encerramento"][-1]) - off * 3600
    tarde = [seg(t) - off * 3600 for t in r["votos_tarde"]]
    v17 = sum(t >= 17 * 3600 for t in tarde)
    v1720 = sum(t >= 17 * 3600 + 20 * 60 for t in tarde)
    cl = "estendida" if enc >= 17 * 3600 + 45 * 60 else "normal"
    porbuf[uf][cl] += 1
    linhas.append({"uf": uf.upper(), "cd_mun": r["cd_mun"], "municipio": r["municipio"], "zona": r["zona"], "secao": r["secao"],
                   "fuso_h": -off, "abertura_brt": hms(seg(r["pronta"][0]) - off * 3600), "encerramento_brt": hms(enc),
                   "ultimo_voto_brt": hms(max(tarde)) if tarde else "", "votos_apos_17h": v17, "votos_apos_17h20": v1720,
                   "votos_total": r["votos"], "classe": cl})

linhas.sort(key=lambda x: (x["uf"], x["municipio"], x["zona"], x["secao"]))
with open(f"{DIR}/secoes.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(linhas[0]))
    w.writeheader(); w.writerows(linhas)

agg = collections.defaultdict(collections.Counter)
mun = collections.defaultdict(collections.Counter)
for x in linhas:
    if x["uf"] == "ZZ":
        continue
    m = mun[(x["uf"], x["municipio"])]
    m["urnas"] += 1
    if x["classe"] == "estendida":
        m["est"] += 1
        m["est_c17"] += x["votos_apos_17h"] > 0
        m["est_v17"] += x["votos_apos_17h"]
    a = agg[x["uf"]]
    e = x["classe"] == "estendida"
    a["urnas"] += 1
    a["est"] += e
    a["est_c17"] += e and x["votos_apos_17h"] > 0
    a["est_v17"] += x["votos_apos_17h"] if e else 0
agg["BR"] = sum(agg.values(), collections.Counter())
print(f"{'UF':4}{'urnas':>8}{'estendidas':>17}{'c/ voto >17h':>14}{'votos >17h':>12}")
for uf, a in sorted(agg.items(), key=lambda kv: (kv[0] == "BR", -kv[1]["est"] / max(kv[1]["urnas"], 1))):
    print(f"{uf:4}{a['urnas']:8}{a['est']:9} {100 * a['est'] / max(a['urnas'], 1):5.1f}%{a['est_c17']:14}{a['est_v17']:12}")

with open(f"{DIR}/municipios.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["uf", "municipio", "urnas", "estendidas", "pct_estendidas", "estendidas_com_voto_apos_17h", "votos_apos_17h_nas_estendidas"])
    for (uf, nm), m in sorted(mun.items(), key=lambda kv: (-kv[1]["est"], kv[0])):
        if m["est"]:
            w.writerow([uf, nm, m["urnas"], m["est"], round(100 * m["est"] / m["urnas"], 1), m["est_c17"], m["est_v17"]])

# Votos até e depois das 17h por município, lidos pelo app em app/assets/votos.json:
# {uf: {cd_mun: [municipio, urnas, estendidas, votos até 17h, votos depois das 17h, votos depois das 17h nas estendidas]}}
vm = collections.defaultdict(lambda: [None, 0, 0, 0, 0, 0])
for x in linhas:
    if x["uf"] == "ZZ":
        continue
    v, e = vm[(x["uf"], x["cd_mun"])], x["classe"] == "estendida"
    v[0] = x["municipio"]
    v[1] += 1
    v[2] += e
    v[3] += x["votos_total"] - x["votos_apos_17h"]
    v[4] += x["votos_apos_17h"]
    v[5] += x["votos_apos_17h"] if e else 0
votos = collections.defaultdict(dict)
for (uf, cd), v in sorted(vm.items(), key=lambda kv: (kv[0][0], kv[1][0])):
    votos[uf][cd] = v
with open(f"{DIR}/app/assets/votos.json", "w") as f:
    json.dump(votos, f, ensure_ascii=False, separators=(",", ":"))

# Números do card, lidos pelo app em app/assets/card.json
RES = "https://resultados.tse.jus.br/oficial/ele2026/6258/dados/br/br-c0001-e006258-u.json"
res = json.load(urllib.request.urlopen(urllib.request.Request(RES, headers={"User-Agent": "Mozilla/5.0"}), timeout=60))
vap = sorted((int(c["vap"]) for a in res["carg"][0]["agr"] for p in a["par"] for c in p["cand"]), reverse=True)
br = agg["BR"]
with open(f"{DIR}/app/assets/card.json", "w") as f:
    json.dump({"urnas": br["urnas"], "estendidas": br["est"], "votos_apos_17h": br["est_v17"],
               "votos_total": sum(x["votos_total"] for x in linhas if x["uf"] != "ZZ"), "vantagem": vap[0] - vap[1]}, f, indent=2)
