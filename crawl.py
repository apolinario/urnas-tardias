# /// script
# requires-python = ">=3.10"
# ///
import argparse, json, os, sys, io, glob, zipfile, time, threading, random, urllib.request, urllib.error, concurrent.futures as cf

import base_dados

BASE = "https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3221"
DIR = os.environ.get("OUT_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados")
UFS = "rj pr sc sp mg rs ba pe ce go pa ma pb rn al se pi es df mt ms am ro to ac ap rr zz".split()
RPS = float(os.environ.get("RPS", "10"))
WORKERS = int(os.environ.get("WORKERS", "24"))


class Limiter:
    """Limita a taxa. Cai 30% a cada reclamação do servidor e sobe 15% a cada 300 respostas boas, até o `RPS` pedido."""

    def __init__(self, rps):
        self.rps, self.teto, self.bons, self.lock, self.next = rps, rps, 0, threading.Lock(), time.monotonic()

    def wait(self):
        with self.lock:
            now = time.monotonic()
            self.next = max(self.next, now) + 1 / self.rps
            d = self.next - now - 1 / self.rps
        if d > 0:
            time.sleep(d)

    def slow(self):
        with self.lock:
            self.rps, self.bons = max(2, self.rps * 0.7), 0
            self.next = time.monotonic() + 30
        log(f"backoff: rps={self.rps:.1f}")

    def ok(self):
        with self.lock:
            self.bons += 1
            if self.bons < 300 or self.rps >= self.teto:
                return
            self.rps, self.bons = min(self.teto, self.rps * 1.15), 0
            novo = self.rps
        log(f"recuperando: rps={novo:.1f}")


lim = Limiter(RPS)
plock = threading.Lock()


def log(msg):
    with plock:
        print(time.strftime("%H:%M:%S"), msg, flush=True)


def get(url):
    for i in range(8):
        lim.wait()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            dados = urllib.request.urlopen(req, timeout=60).read()
            lim.ok()
            return dados
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise
            if e.code in (403, 429):
                lim.slow()
            time.sleep(min(60, 2 ** i) + random.random())
        except Exception:
            if i >= 2:
                lim.slow()
            time.sleep(min(60, 2 ** i) + random.random())
    raise RuntimeError(f"falhou: {url}")


TURNOS = {"04/10/2026": "t1", "25/10/2026": "t2"}
JANELA = 14 * 3600  # hora local da urna a partir da qual se guarda cada voto (cobre 16h de Brasília no Acre)


def seg(t):
    h, m, s = map(int, t.split(":"))
    return h * 3600 + m * 60 + s


def novo_turno():
    return {"pronta": [], "ini_enc": [], "enc": [], "n": 0, "bio": 0, "hist": [0] * 48, "v": []}


def parse(raw):
    """Um dicionário por turno (t1 = 04/10, t2 = 25/10), horários locais da urna.

    `v` traz um item por voto a partir de JANELA: [hora do voto, ociosidade, identificador->habilitação,
    habilitação->voto], em segundos (-1 se faltou evento). Ociosidade é o tempo entre a urna ficar livre
    ("Aguardando digitação do identificador") e o mesário digitar o eleitor seguinte.
    """
    z = zipfile.ZipFile(io.BytesIO(raw))
    r = {"arquivos": z.namelist(), "modelo": None, "t1": novo_turno(), "t2": novo_turno(), "fora": 0}
    est = {k: {} for k in TURNOS.values()}
    for nm in z.namelist():
        for line in z.read(nm).decode("latin1").splitlines():
            p = line.split("\t")
            if len(p) < 5:
                continue
            ev = p[4]
            k = TURNOS.get(p[0][:10])
            if k is None:
                r["fora"] += ev == "O voto do eleitor foi computado"
                continue
            T, e, hora = r[k], est[k], p[0][11:]
            if ev == "Aguardando digitação do identificador do eleitor":
                e.setdefault("w", seg(hora))
            elif ev == "Identificador do eleitor digitado pelo mesário":
                e.setdefault("id", seg(hora))
            elif ev == "Eleitor foi habilitado":
                e["hab"] = seg(hora)
            elif ev == "Tipo de habilitação do eleitor [biométrica]":
                e["bio"] = 1
            elif ev == "O voto do eleitor foi computado":
                t = seg(hora)
                T["n"] += 1
                T["bio"] += e.get("bio", 0)
                T["hist"][min(t // 1800, 47)] += 1
                if t >= JANELA:
                    w, i, h = e.get("w"), e.get("id"), e.get("hab")
                    T["v"].append([t, i - w if w is not None and i is not None else -1,
                                   h - i if h is not None and i is not None else -1, t - h if h is not None else -1])
                est[k] = {}
            elif ev == "Urna pronta para receber votos":
                T["pronta"].append(hora)
            elif ev == "Inicio do Encerramento":
                T["ini_enc"].append(hora)
            elif ev == "Procedimento de encerramento confirmado":
                T["enc"].append(hora)
            elif ev.startswith("Identificação do Modelo de Urna"):
                r["modelo"] = ev.split(":")[-1].strip()
    return r


def secao(uf, mu, nm, zo, se):
    d = f"{BASE}/dados/{uf}/{mu}/{zo}/{se}"
    out = {"uf": uf, "cd_mun": mu, "municipio": nm, "zona": zo, "secao": se}
    try:
        aux = json.loads(get(f"{d}/p003221-{uf}-m{mu}-z{zo}-s{se}-aux.json"))
    except urllib.error.HTTPError as e:
        return {**out, "erro": f"aux {e.code}"}
    out["st"] = aux.get("st")
    hs = aux.get("hashes", [])
    if not hs:
        return {**out, "erro": "sem hashes"}
    out["n_hashes"], out["logs"] = len(hs), []
    for h in hs:
        lg = [a["nm"] for a in h.get("arq", []) if a.get("tp") == "log"]
        if not lg:
            out["logs"].append({"hash_st": h.get("st"), "recebido": h.get("hr"), "sem_log": [a.get("tp") for a in h.get("arq", [])]})
            continue
        try:
            out["logs"].append({"hash_st": h.get("st"), "recebido": h.get("hr"), **parse(get(f"{d}/{h['hash']}/{lg[0]}"))})
        except urllib.error.HTTPError as e:
            return {**out, "erro": f"log {e.code}"}
        except zipfile.BadZipFile:
            return {**out, "erro": "zip invalido"}
    if not any("t2" in l for l in out["logs"]):
        return {**out, "erro": "sem log"}
    return out


def main():
    ap = argparse.ArgumentParser(description="Coleta os logs das urnas. Sem flags, reaproveita o que já está em OUT_DIR e baixa só o que falta.")
    ap.add_argument("ufs", nargs="*", help="UFs em minúsculas (padrão: todas)")
    ap.add_argument("--refazer", action="store_true", help="baixa tudo de novo do TSE (o arquivo antigo vira .anterior)")
    ap.add_argument("--publicado", metavar="MANIFESTO", help="antes de coletar, baixa a base publicada (URL ou caminho do MANIFESTO.json) e confere o sha256")
    ap.add_argument("--empacotar", metavar="DESTINO", help="só gera os .jsonl.gz e o MANIFESTO.json de OUT_DIR em DESTINO")
    a = ap.parse_args()
    if a.refazer and a.publicado:
        ap.error("--refazer e --publicado não combinam")
    if a.empacotar:
        for nome, m in base_dados.empacotar(DIR, a.empacotar).items():
            log(f"{nome}: {m['bytes']} -> {m['bytes_gz']} bytes")
        return
    ufs = a.ufs or UFS
    os.makedirs(DIR, exist_ok=True)
    if a.refazer:
        base_dados.preparar_refazer(DIR, ufs)
    if a.publicado:
        base_dados.baixar(a.publicado, DIR, set(a.ufs) or None, log)
    excecoes = 0
    with cf.ThreadPoolExecutor(WORKERS) as ex:
        for uf in ufs:
            path = os.path.join(DIR, f"{uf}.jsonl")
            feito = set()
            if os.path.exists(path):
                for l in open(path):
                    try:
                        r = json.loads(l)
                    except json.JSONDecodeError:
                        continue
                    if not str(r.get("erro", "")).startswith("excecao"):
                        feito.add((r["cd_mun"], r["zona"], r["secao"]))
            cs = json.loads(get(f"{BASE}/config/{uf}/{uf}-p003221-cs.json"))
            todas = [(m["cd"], m["nm"], z["cd"], s["ns"]) for m in cs["abr"][0]["mu"] for z in m["zon"] for s in z["sec"]]
            falta = [t for t in todas if (t[0], t[2], t[3]) not in feito]
            log(f"{uf}: {len(todas)} seções, {len(falta)} a baixar")
            t0 = time.time()
            with open(path, "a") as f:
                futs = {ex.submit(secao, uf, *t): t for t in falta}
                for i, fu in enumerate(cf.as_completed(futs), 1):
                    try:
                        r = fu.result()
                    except Exception as e:
                        mu, nm, zo, se = futs[fu]
                        r = {"uf": uf, "cd_mun": mu, "municipio": nm, "zona": zo, "secao": se, "erro": f"excecao {e}"}
                    excecoes += str(r.get("erro", "")).startswith("excecao")
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
                    if i % 2000 == 0:
                        f.flush()
                        log(f"{uf}: {i}/{len(falta)} ({i / (time.time() - t0):.1f} seç/s)")
            log(f"{uf}: concluído")
    if excecoes:
        log(f"{excecoes} seções falharam por rede ou servidor; rode de novo para refazê-las (coletar.sh faz isso sozinho)")
    return excecoes


if __name__ == "__main__":
    sys.exit(3 if main() else 0)
