"""Coleta online opcional. Mantém snapshots independentes; não altera a entrega congelada."""
import argparse, hashlib, json, datetime as dt
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
API='https://servicodados.ibge.gov.br/api/v3/agregados'
VARS={12606:'indice_sem_sa',12607:'indice_sa',11601:'mom',11602:'yoy',11603:'ytd',11604:'l12'}
def main():
    p=argparse.ArgumentParser(); p.add_argument('--inicio',type=int,default=2022); p.add_argument('--fim',type=int,default=2026); p.add_argument('--divulgacao',help='Data de divulgação oficial, se conhecida; não inferida'); a=p.parse_args()
    if a.fim<a.inicio: p.error('Intervalo inválido')
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'); folder=ROOT/'data'/'api_snapshots'/stamp; folder.mkdir(parents=True)
    ses=requests.Session(); ses.mount('https://',HTTPAdapter(max_retries=Retry(total=3,backoff_factor=1,status_forcelist=[429,500,502,503,504])))
    manifest=[]; rows=[]
    def fetch(url,name,params=None):
        r=ses.get(url,params=params,timeout=60); r.raise_for_status(); data=r.json(); path=folder/name; path.write_bytes(r.content); manifest.append({'url':r.url,'arquivo':name,'sha256':hashlib.sha256(r.content).hexdigest(),'extraido_utc':stamp,'divulgacao':a.divulgacao}); (folder/'manifesto.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)); return data
    for table in [8888,8887]:
        meta=fetch(f'{API}/{table}/metadados',f'{table}_meta.json'); cl=meta['classificacoes'][0]['id']; levels=meta['nivelTerritorial'].get('administrativo',[]); loc='N1[all]'; loc+='|N3[all]' if 'N3' in levels else ''; loc+='|N2[all]' if 'N2' in levels else ''
        for year in range(a.inicio,a.fim+1):
            months='|'.join(f'{year}{m:02d}' for m in range(1,13)); available=fetch(f'{API}/{table}/periodos',f'{table}_{year}_periodos.json'); periods='|'.join(str(x['id']) for x in available if str(x['id']) in months.split('|'))
            if not periods: continue
            for var,name in VARS.items():
                payload=fetch(f'{API}/{table}/periodos/{periods}/variaveis/{var}',f'{table}_{year}_{var}.json',{'localidades':loc,'classificacao':f'{cl}[all]'})
                for item in payload:
                    for result in item['resultados']:
                        c=result['classificacoes'][0]; code,label=next(iter(c['categoria'].items()))
                        for serie in result['series']:
                            l=serie['localidade']
                            for period,value in serie['serie'].items(): rows.append({'tabela':table,'periodo':period,'local_id':l['id'],'local':l['nome'],'segmento_id':code,'segmento':label,'indicador':name,'valor_original':value,'valor':pd.to_numeric(value,errors='coerce'),'versao_extracao':stamp,'divulgacao':a.divulgacao})
    pd.DataFrame(rows).to_csv(folder/'normalizado.csv',index=False); print(folder)
if __name__=='__main__': main()
