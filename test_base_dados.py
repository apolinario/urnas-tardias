import gzip, json, os, pathlib, tempfile, unittest

import base_dados


def cria(pasta, **ufs):
    for uf, n in ufs.items():
        with open(os.path.join(pasta, f"{uf}.jsonl"), "w") as f:
            for i in range(n):
                f.write(json.dumps({"uf": uf, "secao": f"{i:04d}", "t2": {"v": [[61000 + i, 5, 3, 40]]}}) + "\n")


class BaseDadosTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = pathlib.Path(self.tmp.name)
        self.orig, self.pub, self.novo = t / "orig", t / "pub", t / "novo"
        self.orig.mkdir()
        cria(self.orig, rj=50, ac=7)
        base_dados.empacotar(self.orig, self.pub)
        self.manifesto = str(self.pub / base_dados.MANIFESTO)

    def tearDown(self):
        self.tmp.cleanup()

    def test_ciclo_empacotar_e_baixar_devolve_bytes_identicos(self):
        base_dados.baixar(self.manifesto, self.novo, log=lambda *_: None)
        for nome in ("rj.jsonl", "ac.jsonl"):
            self.assertEqual((self.orig / nome).read_bytes(), (self.novo / nome).read_bytes())

    def test_empacotar_e_deterministico(self):
        a = base_dados.empacotar(self.orig, self.pub)
        b = base_dados.empacotar(self.orig, self.pub.parent / "pub2")
        self.assertEqual({k: v["sha256_gz"] for k, v in a.items()}, {k: v["sha256_gz"] for k, v in b.items()})

    def test_arquivo_corrompido_falha_sem_gravar(self):
        gz = self.pub / "rj.jsonl.gz"
        b = bytearray(gz.read_bytes())
        b[len(b) // 2] ^= 0xFF
        gz.write_bytes(bytes(b))
        with self.assertRaisesRegex(ValueError, "rj.jsonl"):
            base_dados.baixar(self.manifesto, self.novo, log=lambda *_: None)
        self.assertFalse((self.novo / "rj.jsonl").exists())
        self.assertEqual([p.name for p in self.novo.iterdir() if p.name.startswith("rj")], [])

    def test_conteudo_adulterado_com_gz_valido_falha(self):
        with open(self.manifesto) as f:
            man = json.load(f)
        with gzip.open(self.pub / "rj.jsonl.gz", "wb") as f:
            f.write(b"outro conteudo\n")
        man["arquivos"]["rj.jsonl"]["sha256_gz"] = base_dados.sha256(self.pub / "rj.jsonl.gz")
        with open(self.manifesto, "w") as f:
            json.dump(man, f)
        with self.assertRaisesRegex(ValueError, "conteúdo"):
            base_dados.baixar(self.manifesto, self.novo, log=lambda *_: None)
        self.assertFalse((self.novo / "rj.jsonl").exists())

    def test_manifesto_malicioso_nao_escreve_fora_da_pasta(self):
        with open(self.manifesto) as f:
            man = json.load(f)
        ok = man["arquivos"]["rj.jsonl"]
        for nome, gz in (("../fora.jsonl", "../fora.jsonl.gz"), ("rj.jsonl", "../rj.jsonl.gz"), ("/tmp/x.jsonl", "/tmp/x.jsonl.gz")):
            with open(self.manifesto, "w") as f:
                json.dump({"arquivos": {nome: {**ok, "gz": gz}}}, f)
            with self.assertRaisesRegex(ValueError, "inválida"):
                base_dados.baixar(self.manifesto, self.novo, log=lambda *_: None)
        with open(self.manifesto, "w") as f:
            json.dump({"arquivos": {"rj.jsonl": {**ok, "sha256": "zz"}}}, f)
        with self.assertRaisesRegex(ValueError, "inválida"):
            base_dados.baixar(self.manifesto, self.novo, log=lambda *_: None)
        self.assertFalse((self.pub.parent / "fora.jsonl").exists())
        self.assertEqual(list(self.novo.iterdir()) if self.novo.exists() else [], [])

    def test_tamanho_declarado_invalido_e_recusado(self):
        with open(self.manifesto) as f:
            man = json.load(f)
        ok = man["arquivos"]["rj.jsonl"]
        for ruim in (-1, True, 2.5, "10", base_dados.MAX_BYTES + 1):
            with open(self.manifesto, "w") as f:
                json.dump({"arquivos": {"rj.jsonl": {**ok, "bytes": ruim}}}, f)
            with self.assertRaisesRegex(ValueError, "inválida", msg=repr(ruim)):
                base_dados.baixar(self.manifesto, self.novo, log=lambda *_: None)
        self.assertEqual(list(self.novo.iterdir()) if self.novo.exists() else [], [])

    def test_bomba_de_gzip_e_barrada_pelo_tamanho_declarado(self):
        with open(self.manifesto) as f:
            man = json.load(f)
        with gzip.open(self.pub / "rj.jsonl.gz", "wb") as f:
            f.write(b"x" * 5000)
        m = man["arquivos"]["rj.jsonl"]
        m["sha256_gz"], m["bytes"] = base_dados.sha256(self.pub / "rj.jsonl.gz"), 100
        with open(self.manifesto, "w") as f:
            json.dump(man, f)
        with self.assertRaisesRegex(ValueError, "maior"):
            base_dados.baixar(self.manifesto, self.novo, log=lambda *_: None)
        self.assertEqual([p.name for p in self.novo.iterdir()], ["ac.jsonl"])  # o arquivo válido anterior fica; o ruim e os temporários não

    def test_uf_ja_existente_e_mantida_e_filtro_de_uf(self):
        self.novo.mkdir()
        (self.novo / "ac.jsonl").write_text("local\n")
        base_dados.baixar(self.manifesto, self.novo, log=lambda *_: None)
        self.assertEqual((self.novo / "ac.jsonl").read_text(), "local\n")
        outro = self.novo.parent / "so_rj"
        base_dados.baixar(self.manifesto, outro, ufs={"rj"}, log=lambda *_: None)
        self.assertEqual(sorted(p.name for p in outro.iterdir()), ["rj.jsonl"])

    def test_refazer_move_para_anterior_sem_apagar(self):
        base_dados.preparar_refazer(self.orig, ["rj", "sp"])  # sp não existe: ignorado
        self.assertFalse((self.orig / "rj.jsonl").exists())
        self.assertEqual(len((self.orig / "rj.jsonl.anterior").read_text().splitlines()), 50)
        self.assertTrue((self.orig / "ac.jsonl").exists())
        (self.orig / "rj.jsonl").write_text("segunda coleta\n")
        base_dados.preparar_refazer(self.orig, ["rj"])
        self.assertEqual((self.orig / "rj.jsonl.anterior").read_text(), "segunda coleta\n")


if __name__ == "__main__":
    unittest.main()
