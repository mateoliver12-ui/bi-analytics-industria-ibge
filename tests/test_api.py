import unittest, sqlite3, json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]; RES=ROOT/'results/api'
class TestAPI(unittest.TestCase):
    def test_integridade(self):
        d=pd.read_csv(RES/'hashes.csv'); self.assertEqual(len(d),88); self.assertTrue(d.aprovado.all())
        r=json.loads((RES/'resumo.json').read_text()); self.assertEqual(r['registros'],17442); self.assertEqual(r['duplicados'],0); self.assertEqual(r['ausentes'],2213)
    def test_reconciliacao(self):
        h=pd.read_csv(RES/'h1.csv'); e=h[h.elegivel]; self.assertEqual(len(e),8116); self.assertTrue(e.aprovado.all()); self.assertLessEqual(e.erro_pp.max(),.1)
    def test_versoes(self):
        h=pd.read_csv(RES/'h2.csv'); self.assertEqual(len(h),2754); self.assertTrue(h.rastreavel.all()); self.assertFalse(h.alterado.any())
    def test_sql_api(self):
        with sqlite3.connect(ROOT/'data/warehouse/pim_api.sqlite') as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM vw_fatos').fetchone()[0],20196); self.assertEqual(con.execute('PRAGMA foreign_key_check').fetchall(),[])
        self.assertTrue(pd.read_csv(RES/'h3.csv').aprovado.all()); self.assertTrue(pd.read_csv(RES/'h3_kpis.csv').aprovado.all())
    def test_previsao_api(self):
        self.assertEqual(len(pd.read_csv(RES/'holdout.csv')),6); self.assertEqual(len(pd.read_csv(RES/'previsao.csv')),6)
        self.assertEqual(len(pd.read_csv(RES/'backtest.csv')),72)
if __name__=='__main__': unittest.main()
