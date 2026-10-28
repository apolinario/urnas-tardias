import io, zipfile, unittest

import crawl


def zip_log(linhas):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("logd.dat", "\n".join("\t".join([d, "INFO", "1", "VOTA", ev, "X"]) for d, ev in linhas).encode("latin1"))
    return b.getvalue()


ESPERA, ID, HAB, VOTO = ("Aguardando digitação do identificador do eleitor", "Identificador do eleitor digitado pelo mesário",
                         "Eleitor foi habilitado", "O voto do eleitor foi computado")


class ParseTest(unittest.TestCase):
    def test_turnos_e_ociosidade(self):
        r = crawl.parse(zip_log([
            ("03/10/2026 15:00:00", VOTO),  # fora dos turnos: so conta em `fora`
            ("04/10/2026 08:00:00", "Urna pronta para receber votos"),
            ("04/10/2026 16:00:00", ESPERA), ("04/10/2026 16:00:11", ID), ("04/10/2026 16:00:20", HAB), ("04/10/2026 16:01:00", VOTO),
            ("25/10/2026 08:00:01", "Urna pronta para receber votos"),
            ("25/10/2026 16:59:50", ESPERA), ("25/10/2026 17:00:02", ID),
            ("25/10/2026 17:00:05", "Tipo de habilitação do eleitor [biométrica]"), ("25/10/2026 17:00:05", HAB),
            ("25/10/2026 17:00:35", VOTO),
            ("25/10/2026 17:00:37", ESPERA), ("25/10/2026 17:20:37", ID),  # urna ociosa 20 min
            ("25/10/2026 17:20:40", HAB), ("25/10/2026 17:21:10", VOTO),
            ("25/10/2026 17:21:30", "Inicio do Encerramento"),
            ("25/10/2026 17:30:00", "Procedimento de encerramento confirmado"),
        ]))
        self.assertEqual((r["t1"]["n"], r["t2"]["n"], r["fora"]), (1, 2, 1))
        self.assertEqual(r["t1"]["v"], [[16 * 3600 + 60, 11, 9, 40]])
        self.assertEqual(r["t2"]["v"], [[17 * 3600 + 35, 12, 3, 30], [17 * 3600 + 21 * 60 + 10, 1200, 3, 30]])
        self.assertEqual((r["t2"]["bio"], r["t2"]["ini_enc"], r["t2"]["enc"]), (1, ["17:21:30"], ["17:30:00"]))
        self.assertEqual(r["t2"]["hist"][34], 2)  # 17:00 a 17:30 -> bloco de meia hora 34

    def test_voto_antes_da_janela_so_entra_no_total(self):
        r = crawl.parse(zip_log([("25/10/2026 10:00:00", VOTO)]))
        self.assertEqual((r["t2"]["n"], r["t2"]["v"]), (1, []))

    def test_evento_faltando_vira_menos_um(self):
        r = crawl.parse(zip_log([("25/10/2026 15:00:00", VOTO)]))
        self.assertEqual(r["t2"]["v"], [[15 * 3600, -1, -1, -1]])


if __name__ == "__main__":
    unittest.main()
