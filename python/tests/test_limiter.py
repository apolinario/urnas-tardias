import unittest
from unittest import mock

import crawl


class LimiterTest(unittest.TestCase):
    def setUp(self):
        self.lim = crawl.Limiter(12)
        patch = mock.patch.object(crawl, "log")
        patch.start()
        self.addCleanup(patch.stop)

    def test_cai_30_por_cento_a_cada_reclamacao_e_tem_piso(self):
        self.lim.slow()
        self.assertAlmostEqual(self.lim.rps, 8.4)
        for _ in range(30):
            self.lim.slow()
        self.assertEqual(self.lim.rps, 2)

    def test_recupera_15_por_cento_a_cada_300_respostas_boas_ate_o_teto(self):
        self.lim.slow()
        for _ in range(299):
            self.lim.ok()
        self.assertAlmostEqual(self.lim.rps, 8.4)
        self.lim.ok()
        self.assertAlmostEqual(self.lim.rps, 8.4 * 1.15)
        for _ in range(300 * 10):
            self.lim.ok()
        self.assertEqual(self.lim.rps, 12)

    def test_reclamacao_zera_a_contagem_de_respostas_boas(self):
        self.lim.slow()
        for _ in range(250):
            self.lim.ok()
        self.lim.slow()
        for _ in range(250):
            self.lim.ok()
        self.assertAlmostEqual(self.lim.rps, 12 * 0.7 * 0.7)


if __name__ == "__main__":
    unittest.main()
