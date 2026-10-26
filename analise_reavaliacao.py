"""Análise do PROTOCOLO.md sobre a coleta do crawl.py.

uso: python3 analise_reavaliacao.py <pasta com os *.jsonl> [--margem N] [--B 2000] [--Be3 200] [--saida resultado.json]
"""
import argparse, collections, glob, hashlib, json, os, subprocess
import numpy as np

H = 3600
CORTES = {"17h": 17 * H, "17h05": 17 * H + 300, "17h15": 17 * H + 900}
GS = (60, 120, 300, 600)
DIGITACAO = 15  # segundos para o mesário digitar o identificador
SEED = 20261025
FUSO_OK = {"ac": {2}, "am": {1, 2}, "mt": {1}, "ms": {1}, "ro": {1}, "rr": {1}, "pe": {0, -1}}


def seg(t):
    h, m, s = map(int, t.split(":"))
    return h * 3600 + m * 60 + s


def linhas(pasta):
    for p in sorted(glob.glob(os.path.join(pasta, "*.jsonl"))):
        with open(p) as f:
            for l in f:
                try:
                    r = json.loads(l)
                except json.JSONDecodeError:
                    continue
                if not str(r.get("erro", "")).startswith("excecao"):
                    yield r


def escolhe(r, modo):
    ls = [l for l in r.get("logs", []) if "t2" in l]
    if not ls:
        return None
    return ls[-1] if modo == "ultimo" else max(ls, key=lambda l: l["t2"]["n"])


def resumo(T, f):
    """Métricas de um turno de uma urna, em segundos de Brasília (f = Brasília menos hora local, em horas)."""
    v = np.array(T["v"], dtype=float).reshape(-1, 4)
    v = v[np.argsort(v[:, 0], kind="stable")]
    tv = v[:, 0] + f * H
    idle, idh, hv = v[:, 1], v[:, 2], v[:, 3]
    tid = np.where((hv >= 0) & (idh >= 0), tv - hv - idh, np.nan)
    m = len(tv)
    o = {"n": T["n"]}
    for nome, c in CORTES.items():
        o[f"U_{nome}"] = int((tv >= c).sum())
        for g in GS:
            cond = (idle > g) & (tid - DIGITACAO >= c)
            o[f"L_{nome}_g{g}"] = int(m - np.argmax(cond)) if cond.any() else 0
    o["Uini_17h"] = int((np.where(np.isnan(tid), tv, tid) >= 17 * H).sum())
    o["r1617"] = int(((tv >= 16 * H) & (tv < 17 * H)).sum())
    ok = (tv >= 16.5 * H) & (tv < 17 * H) & (idle >= 0)
    o["ocios"] = float(np.minimum(idle[ok], 600).mean()) if ok.any() else 600.0
    o["ocup1645"] = int(((tv >= 16.75 * H) & (tv < 17 * H) & (idle >= 0) & (idle <= 30)).sum())
    for k, ch in (("enc", "enc"), ("ini_enc", "ini_enc"), ("abertura", "pronta")):
        o[k] = seg(T[ch][-1] if k != "abertura" else T[ch][0]) + f * H if T[ch] else np.nan
    return o


def carrega(pasta):
    """Passagem 1: fuso por município. Passagem 2: colunas por seção. Devolve (tabela, cobertura)."""
    abre = {k: collections.defaultdict(collections.Counter) for k in ("t1", "t2")}
    vistos = set()
    for r in linhas(pasta):
        lg = escolhe(r, "ultimo")
        if lg:
            for k in abre:
                if lg[k]["pronta"]:
                    abre[k][(r["uf"], r["cd_mun"])][round((seg(lg[k]["pronta"][0]) - 8 * H) / H)] += 1
    fuso = {k: {m: -c.most_common(1)[0][0] for m, c in d.items()} for k, d in abre.items()}
    cob = collections.defaultdict(collections.Counter)
    meta, cols, vistos = [], [], set()
    modelos = collections.Counter()
    for r in linhas(pasta):
        chave = (r["uf"], r["cd_mun"], r["zona"], r["secao"])
        if chave in vistos:
            continue
        vistos.add(chave)
        c = cob[r["uf"]]
        c["linhas"] += 1
        if r.get("erro"):
            c[r["erro"]] += 1
            continue
        lg, alt = escolhe(r, "ultimo"), escolhe(r, "maisvotos")
        if lg is None:
            c["sem log"] += 1
            continue
        c["com_log"] += 1
        c["multiplos_conjuntos"] += r["n_hashes"] > 1
        c["votos_em_outras_datas"] += lg["fora"] > 0
        mun = (r["uf"], r["cd_mun"])
        f = fuso["t2"].get(mun, 0)
        a, b = resumo(lg["t2"], f), resumo(lg["t1"], f)
        a2 = resumo(alt["t2"], f) if alt is not lg else a
        modelos[lg["modelo"]] += 1
        meta.append((r["uf"], r["cd_mun"], lg["modelo"]))
        cols.append([f, fuso["t1"].get(mun, f), r["n_hashes"], lg["fora"], a2["U_17h"], a2["L_17h_g120"]]
                    + [a[k] for k in CHAVES_TURNO] + [b[k] for k in CHAVES_TURNO])
    return meta, np.array(cols, dtype=float), cob, modelos


CHAVES_TURNO = ["n", "enc", "ini_enc", "abertura", "Uini_17h", "r1617", "ocios", "ocup1645"] + \
    [f"U_{c}" for c in CORTES] + [f"L_{c}_g{g}" for c in CORTES for g in GS]
NOMES = ["f2", "f1", "n_hashes", "fora", "alt_U", "alt_L"] + [f"{k}_t2" for k in CHAVES_TURNO] + [f"{k}_t1" for k in CHAVES_TURNO]
IDX = {n: i for i, n in enumerate(NOMES)}


def poisson(X, y, w, it=40):
    b = np.zeros(X.shape[1])
    b[0] = np.log(max((w * y).sum() / w.sum(), 1e-9))
    ll = lambda b: (w * (y * (X @ b) - np.exp(np.clip(X @ b, -30, 30)))).sum()
    atual = ll(b)
    for _ in range(it):
        mu = np.exp(np.clip(X @ b, -30, 30))
        g = X.T @ (w * (y - mu))
        Hs = X.T @ (X * (w * mu)[:, None]) + 1e-6 * np.eye(X.shape[1])
        passo, d = 1.0, np.linalg.solve(Hs, g)
        while passo > 1e-4 and ll(b + passo * d) < atual:
            passo /= 2
        nb = b + passo * d
        novo = ll(nb)
        b, parar = nb, abs(novo - atual) < 1e-7 * (1 + abs(atual))
        atual = novo
        if parar:
            break
    return b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pasta")
    ap.add_argument("--margem", type=int)
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--Be3", type=int, default=200)
    ap.add_argument("--saida")
    a = ap.parse_args()
    rng = np.random.default_rng(SEED)

    meta, M, cob, modelos = carrega(a.pasta)
    uf = np.array([m[0] for m in meta])
    dom = uf != "zz"
    meta, M, uf = [m for m, d in zip(meta, dom) if d], M[dom], uf[dom]
    col = lambda n: M[:, IDX[n]]
    N = len(M)

    print(f"# Resultados (protocolo, semente {SEED})\n")
    print(f"Código: {subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()}  |  urnas no país com log: {N}\n")
    for p in sorted(glob.glob(os.path.join(a.pasta, "*.jsonl"))):
        print(f"sha256 {os.path.basename(p)}: {hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16]}")

    print("\n## Portões de qualidade\n")
    print("| UF | linhas | com log | sem arquivo (404) | sem log | erro | >1 conjunto | votos em outras datas |")
    print("|---|---|---|---|---|---|---|---|")
    for u, c in sorted(cob.items()):
        outros = sum(v for k, v in c.items() if k not in ("linhas", "com_log", "multiplos_conjuntos", "votos_em_outras_datas", "aux 404", "sem log"))
        print(f"| {u.upper()} | {c['linhas']} | {c['com_log']} | {c['aux 404']} | {c['sem log']} | {outros} | {c['multiplos_conjuntos']} | {c['votos_em_outras_datas']} |")
    fuso_ruim = np.array([col("f2")[i] not in FUSO_OK.get(uf[i], {0}) for i in range(N)])
    ab = col("abertura_t2")
    ab_ruim = ~((ab >= 7.5 * H) & (ab <= 8.5 * H))
    nor = (uf == "pe") & (col("f2") == -1)  # Fernando de Noronha
    modelo_top = modelos.most_common(1)[0][0] if modelos else None
    is_top = np.array([m[2] == modelo_top for m in meta])
    print(f"\nFuso fora do esperado para a UF: {int(fuso_ruim.sum())} | fuso do 1º turno diferente do 2º: {int((col('f1') != col('f2')).sum())} | abertura fora de 7h30 a 8h30 de Brasília: {int(ab_ruim.sum())} | modelo mais comum: {modelo_top} ({int(is_top.sum())} urnas)\n")

    # colunas aditivas por seção
    A = {"secoes": np.ones(N)}
    for t in ("t2", "t1"):
        A[f"votos_{t}"] = col(f"n_{t}")
        for c in CORTES:
            A[f"U_{c}_{t}"] = col(f"U_{c}_{t}")
            for g in GS:
                A[f"L_{c}_g{g}_{t}"] = col(f"L_{c}_g{g}_{t}")
        A[f"Uini_{t}"] = col(f"Uini_17h_{t}")
        A[f"Nac_{t}"] = (col(f"U_17h_{t}") > 0).astype(float)
    for nome, lim in (("15", 17.25), ("45", 17.75), ("18", 18.0)):
        e = np.nan_to_num(col("enc_t2"), nan=0) >= lim * H
        A[f"est{nome}"] = e.astype(float)
        A[f"U_est{nome}"] = col("U_17h_t2") * e
    A["alt_U"], A["alt_L"] = col("alt_U"), col("alt_L")
    nomes = list(A)
    mat = np.column_stack([A[n] for n in nomes])
    ix = {n: i for i, n in enumerate(nomes)}

    muns = np.array([f"{m[0]}/{m[1]}" for m in meta])
    um, inv = np.unique(muns, return_inverse=True)
    G = np.zeros((len(um), mat.shape[1]))
    np.add.at(G, inv, mat)

    def derivadas(t):
        g = lambda n: t[ix[n]]
        p = g("L_17h_g120_t1") / max(g("Nac_t1"), 1)
        return {"U (teto): votos depois das 17h": g("U_17h_t2"),
                "U nas urnas estendidas (> 17h45), reproduz o método original": g("U_est45"),
                "L (piso, g=120 s)": g("L_17h_g120_t2"),
                "placebo: L no 1º turno": g("L_17h_g120_t1"),
                "p (falso positivo por urna com voto depois das 17h)": p,
                "L líquido = L2 - p*N2": g("L_17h_g120_t2") - p * g("Nac_t2")}

    tot = G.sum(0)
    base = derivadas(tot)
    bs = [derivadas(G[rng.integers(0, len(um), len(um))].sum(0)) for _ in range(a.B)]
    print("## Resultado principal (municípios como cluster no bootstrap)\n")
    print("| Medida | Estimativa | IC 95% |\n|---|---|---|")
    for k, v in base.items():
        s = np.array([b[k] for b in bs])
        fmt = (lambda x: f"{x:.5f}") if k.startswith("p ") else (lambda x: f"{x:,.0f}".replace(",", "."))
        print(f"| {k} | {fmt(v)} | {fmt(np.percentile(s, 2.5))} a {fmt(np.percentile(s, 97.5))} |")
    U = base["U (teto): votos depois das 17h"]
    if a.margem:
        print(f"\nMargem informada: {a.margem:,}".replace(",", ".") + f". Margem / U = {a.margem / U:,.0f}x. U / margem = {100 * U / a.margem:.3f}%.")
    print(f"\nUrnas: {N} | estendidas (> 17h45): {int(tot[ix['est45']])} | com voto depois das 17h no 2º turno: {int(tot[ix['Nac_t2']])} | no 1º turno: {int(tot[ix['Nac_t1']])}")

    print("\n## Placebo do 1º turno por limiar g (L no 1º turno, sem prorrogação)\n")
    print("| g (s) | L 2º turno | L 1º turno (placebo) | urnas com voto > 17h (2T / 1T) | L líquido 2º turno |\n|---|---|---|---|---|")
    for g in GS:
        l2, l1 = tot[ix[f"L_17h_g{g}_t2"]], tot[ix[f"L_17h_g{g}_t1"]]
        p = l1 / max(tot[ix["Nac_t1"]], 1)
        print(f"| {g} | {l2:.0f} | {l1:.0f} | {tot[ix['Nac_t2']]:.0f} / {tot[ix['Nac_t1']]:.0f} | {l2 - p * tot[ix['Nac_t2']]:.0f} |")

    print("\n## Sensibilidade (estimativas pontuais)\n")
    print("| Variação | U | L | L placebo | L líquido |\n|---|---|---|---|---|")

    def linha(nome, mask=None, c="17h", g=120, u=None, l=None):
        m = np.ones(N, bool) if mask is None else mask
        s = lambda n: float(A[n][m].sum()) if n in A else float(M[m, IDX[n]].sum())
        U_ = s(u or f"U_{c}_t2"); L2 = s(l or f"L_{c}_g{g}_t2"); L1 = s(f"L_{c}_g{g}_t1")
        p = L1 / max((M[m, IDX[f"U_{c}_t1"]] > 0).sum(), 1)
        n2 = (M[m, IDX[f"U_{c}_t2"]] > 0).sum()
        print(f"| {nome} | {U_:.0f} | {L2:.0f} | {L1:.0f} | {L2 - p * n2:.0f} |")

    linha("principal (17h, g=120 s)")
    for g in (60, 300, 600):
        linha(f"g = {g} s", g=g)
    for c in ("17h05", "17h15"):
        linha(f"corte {c}", c=c)
    linha("início do atendimento no lugar da hora do voto (só U)", u="Uini_t2")
    linha("log com mais votos no lugar do último", u="alt_U", l="alt_L")
    for nome in ("est15", "est45", "est18"):
        print(f"| classe estendida {nome} (só U nelas) | {tot[ix['U_' + nome]]:.0f} | | | |")
    linha("sem fuso fora do esperado", ~fuso_ruim)
    linha("sem abertura fora do portão", ~ab_ruim)
    linha("sem Fernando de Noronha", ~nor)
    linha("só o modelo de urna mais comum", is_top)

    print("\n## Por UF (exploratório)\n")
    print("| UF | urnas | estendidas | U | L (g=120) |\n|---|---|---|---|---|")
    for u in sorted(set(uf)):
        m = uf == u
        print(f"| {u.upper()} | {int(m.sum())} | {int(A['est45'][m].sum())} | {int(A['U_17h_t2'][m].sum())} | {int(A['L_17h_g120_t2'][m].sum())} |")

    # E3: Poisson ajustado no 1º turno, aplicado ao 2º
    ufs = sorted(set(uf))
    def X_de(t):
        d = [np.ones(N), np.log1p(col(f"r1617_{t}")), col(f"ocios_{t}") / 600, np.log1p(col(f"ocup1645_{t}")), np.log1p(col(f"n_{t}"))]
        return np.column_stack(d + [(uf == u).astype(float) for u in ufs[1:]])

    X1, X2 = X_de("t1"), X_de("t2")
    y1, y2 = col("U_17h_t1"), col("U_17h_t2")
    print("\n## E3 calibrada (secundária, depende do modelo)\n")
    fora = rng.random(len(um)) < 0.5
    teste = fora[inv]
    b_tr = poisson(X1[~teste], y1[~teste], np.ones((~teste).sum()))
    mu_te = np.exp(np.clip(X1[teste] @ b_tr, -30, 30))
    razao = y1[teste].sum() / mu_te.sum()
    print(f"Validação com municípios retidos do 1º turno: observado / predito = {razao:.3f} (critério do protocolo: entre 0,75 e 1,25 -> {'passa' if 0.75 <= razao <= 1.25 else 'REPROVA, E3 é só exploratória'}).")
    dec = np.digitize(mu_te, np.quantile(mu_te, np.linspace(0, 1, 11)[1:-1]))
    print("\n| decil de predição | observado | predito |\n|---|---|---|")
    for d in range(10):
        s = dec == d
        print(f"| {d + 1} | {y1[teste][s].sum():.0f} | {mu_te[s].sum():.0f} |")
    b = poisson(X1, y1, np.ones(N))
    mu2 = np.exp(np.clip(X2 @ b, -30, 30))
    e3 = float((y2 - mu2).sum())
    cedo = np.nan_to_num(col("enc_t2"), nan=0) < 17 * H + 600
    print(f"\nVerificação secundária (urnas do 2º turno que fecharam até 17h10, selecionadas pelo desfecho): observado {y2[cedo].sum():.0f} / predito {mu2[cedo].sum():.0f}")
    es = []
    if a.Be3:
        for _ in range(a.Be3):
            w = np.bincount(rng.integers(0, len(um), len(um)), minlength=len(um))[inv].astype(float)
            bb = poisson(X1, y1, w)
            es.append(float((w * (y2 - np.exp(np.clip(X2 @ bb, -30, 30)))).sum()))
    ic = f"{np.percentile(es, 2.5):.0f} a {np.percentile(es, 97.5):.0f}" if es else "n/d"
    print(f"\nE3 = soma(observado - predito pela fila do 1º turno) no 2º turno: {e3:.0f} (IC 95%: {ic}). Predito (fila esperada): {mu2.sum():.0f}; observado: {y2.sum():.0f}.")

    if a.saida:
        json.dump({"base": base, "E3": e3, "E3_ic": [float(np.percentile(es, 2.5)), float(np.percentile(es, 97.5))] if es else None,
                   "totais": dict(zip(nomes, map(float, tot)))}, open(a.saida, "w"), indent=1)


if __name__ == "__main__":
    main()
