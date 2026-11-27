import unittest, sqlite3
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
class Checks(unittest.TestCase):
    def test_h1(self):
        d=pd.read_csv(ROOT/'results/h1.csv'); self.assertEqual(len(d),152); self.assertTrue((d.erro_pp<=.1).all())
    def test_h2(self):
        d=pd.read_csv(ROOT/'results/revisoes.csv'); self.assertEqual(len(d),128); self.assertTrue(d.rastreavel.all())
    def test_sql(self):
        with sqlite3.connect(ROOT/'data/warehouse/pim.sqlite') as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM vw_fatos').fetchone()[0],741); self.assertEqual(con.execute('PRAGMA foreign_key_check').fetchall(),[])
        self.assertTrue(pd.read_csv(ROOT/'results/h3.csv').aprovado.all())
    def test_forecast(self):
        d=pd.read_csv(ROOT/'results/previsao.csv'); self.assertEqual(len(d),6); self.assertTrue((d.previsto>0).all())
if __name__=='__main__': unittest.main()
