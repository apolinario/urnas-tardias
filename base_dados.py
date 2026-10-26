"""Empacota a pasta de coleta (um .jsonl por UF) e baixa uma base publicada, sempre conferindo sha256."""
import gzip, hashlib, json, os, pathlib, re, shutil, urllib.request

MANIFESTO = "MANIFESTO.json"
NOME = re.compile(r"[a-z]{2}\.jsonl")
SHA = re.compile(r"[0-9a-f]{64}")
MAX_BYTES = 4 << 30  # teto fixo por arquivo, independente do que o manifesto declarar


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def empacotar(pasta, destino):
    """Gera `destino/{uf}.jsonl.gz` (gzip determinístico) e o MANIFESTO.json com tamanho e sha256 de cada arquivo."""
    os.makedirs(destino, exist_ok=True)
    arquivos = {}
    for p in sorted(pathlib.Path(pasta).glob("*.jsonl")):
        gz = os.path.join(destino, p.name + ".gz")
        with open(p, "rb") as src, open(gz, "wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as dst:
            shutil.copyfileobj(src, dst)
        arquivos[p.name] = {"gz": os.path.basename(gz), "bytes": p.stat().st_size, "sha256": sha256(p),
                            "bytes_gz": os.path.getsize(gz), "sha256_gz": sha256(gz)}
    with open(os.path.join(destino, MANIFESTO), "w") as f:
        json.dump({"arquivos": arquivos}, f, indent=1)
    return arquivos


def _abre(url):
    if "://" not in url:
        url = pathlib.Path(url).resolve().as_uri()
    return urllib.request.urlopen(url, timeout=120)


def baixar(origem, pasta, ufs=None, log=print):
    """Baixa os `.jsonl.gz` listados no manifesto (URL ou caminho do MANIFESTO.json) para `pasta`.

    Cada arquivo só vira `{uf}.jsonl` depois de bater o sha256 do comprimido e o do conteúdo; se algo não bater, nada é gravado.
    UF que já tem arquivo na pasta é mantida (use --refazer para trocá-la)."""
    base = origem.rsplit("/", 1)[0] if "://" in origem else os.path.dirname(os.path.abspath(origem))
    with _abre(origem) as r:
        man = json.load(r)["arquivos"]
    os.makedirs(pasta, exist_ok=True)
    for nome, m in sorted(man.items()):
        # o manifesto vem de uma URL: nada dele pode escolher caminho fora de `pasta`
        if not NOME.fullmatch(nome) or m.get("gz") != nome + ".gz" or not all(SHA.fullmatch(str(m.get(k))) for k in ("sha256", "sha256_gz")) \
                or type(m.get("bytes")) is not int or not 0 <= m["bytes"] <= MAX_BYTES:
            raise ValueError(f"entrada inválida no manifesto: {nome!r}")
        if ufs and nome[:-len(".jsonl")] not in ufs:
            continue
        destino = os.path.join(pasta, nome)
        if os.path.exists(destino):
            log(f"{nome}: já existe, mantido")
            continue
        tmp_gz, tmp = destino + ".baixando.gz", destino + ".baixando"
        try:
            with _abre(f"{base}/{m['gz']}") as r, open(tmp_gz, "wb") as f:
                shutil.copyfileobj(r, f)
            if sha256(tmp_gz) != m["sha256_gz"]:
                raise ValueError(f"{nome}: sha256 do arquivo comprimido não confere")
            with gzip.open(tmp_gz, "rb") as src, open(tmp, "wb") as dst:
                total = 0
                for bloco in iter(lambda: src.read(1 << 20), b""):
                    total += len(bloco)
                    if total > m["bytes"]:
                        raise ValueError(f"{nome}: conteúdo maior que o declarado no manifesto")
                    dst.write(bloco)
            if sha256(tmp) != m["sha256"]:
                raise ValueError(f"{nome}: sha256 do conteúdo não confere")
            os.replace(tmp, destino)
            log(f"{nome}: baixado e conferido ({m['bytes']} bytes)")
        finally:
            for t in (tmp_gz, tmp):
                if os.path.exists(t):
                    os.remove(t)


def preparar_refazer(pasta, ufs):
    """Move `{uf}.jsonl` para `{uf}.jsonl.anterior` para que a coleta recomece do zero sem apagar nada."""
    for uf in ufs:
        p = os.path.join(pasta, f"{uf}.jsonl")
        if os.path.exists(p):
            os.replace(p, p + ".anterior")
