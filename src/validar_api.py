"""Auditoria reproduzível dos snapshots nacionais; não modifica o painel homologado."""
from pathlib import Path
import hashlib,json,sqlite3,re
import numpy as np
import pandas as pd
from pipeline import predict
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/api'; SNAP=ROOT/'data/api_snapshots'; DB=ROOT/'data/warehouse/pim_api.sqlite'
KEY=['tabela','periodo','local_id','segmento_id','indicador']
VARS={12606:'indice_sem_sa',12607:'indice_sa',11601:'mom',11602:'yoy',11603:'ytd',11604:'l12'}
MODELS=['Naive sazonal','Regressão linear','Random Forest','ARIMA(1,0,0)']

def save(df,name): df.to_csv(OUT/(name+'.csv'),index=False)
def snapshot(folder):
    manifest=json.loads((folder/'manifesto.json').read_text()); hashes=[]; rows=[]
    for item in manifest:
        p=folder/item['arquivo']; good=hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256']; hashes.append({'versao':folder.name,'arquivo':p.name,'aprovado':good}); assert good,p
        m=re.fullmatch(r'(\d+)_(\d+)_(\d+)\.json',p.name)
        if not m: continue
        table,year,var=map(int,m.groups())
        for obj in json.loads(p.read_text()):
            assert int(obj['id'])==var
            for result in obj['resultados']:
                code,label=next(iter(result['classificacoes'][0]['categoria'].items()))
                for ser in result['series']:
                    l=ser['localidade']
                    for period,value in ser['serie'].items(): rows.append([table,int(period),int(l['id']),int(code),VARS[var],l['nome'],label,str(value)])
    raw=pd.DataFrame(rows,columns=KEY+['local','segmento','valor_original']); d=pd.read_csv(folder/'normalizado.csv',dtype={'valor_original':str}); assert not raw.duplicated(KEY).any() and not d.duplicated(KEY).any()
    chk=raw.merge(d,on=KEY,how='outer',suffixes=('_raw','_csv'),indicator=True,validate='one_to_one'); assert len(chk)==len(raw)==len(d) and chk._merge.eq('both').all()
    for col in ['local','segmento','valor_original']: assert chk[col+'_raw'].eq(chk[col+'_csv']).all(),col
    assert np.isclose(pd.to_numeric(d.valor_original,errors='coerce'),d.valor,rtol=0,atol=1e-10,equal_nan=True).all(); assert d.versao_extracao.eq(folder.name).all()
    return d,pd.DataFrame(hashes)

def main():
    OUT.mkdir(parents=True,exist_ok=True); folders=[SNAP/'20261127T010233165300Z', SNAP/'20261127T010455230418Z']; pairs=[snapshot(p) for p in folders]; all_data=pd.concat([d for d,h in pairs],ignore_index=True); d=pairs[-1][0].copy(); hashes=pd.concat([h for d,h in pairs]); save(hashes,'hashes'); save(d.groupby(['tabela','indicador']).valor.agg(registros='size',validos='count').reset_index(),'completude'); missing=d[d.valor.isna()].groupby(['tabela','segmento','indicador','valor_original']).size().reset_index(name='ausentes'); save(missing,'ausencias')
    # H1: use consecutive monthly calendar, no imputation. Rates require complete windows.
    rows=[]
    for (table,local,seg),g in d.groupby(['tabela','local_id','segmento_id']):
        w=g.pivot(index='periodo',columns='indicador',values='valor'); w.index=pd.to_datetime(w.index.astype(str),format='%Y%m'); w=w.asfreq('MS'); a=w.indice_sa; b=w.indice_sem_sa; cumul=b.groupby(b.index.year).cumsum(); cnt=b.notna().groupby(b.index.year).cumsum(); cumul=cumul.where(cnt==b.index.month); r12=b.rolling(12,min_periods=12).sum()
        formulas={'mom':100*(a/a.shift(1)-1),'yoy':100*(b/b.shift(12)-1),'ytd':100*(cumul/cumul.shift(12)-1),'l12':100*(r12/r12.shift(12)-1)}
        for metric,calc in formulas.items():
            for date,v in calc.items():
                of=w.loc[date,metric]; err=abs(v-of) if pd.notna(v) and pd.notna(of) else np.nan; rows.append([table,local,seg,date.strftime('%Y%m'),metric,v,of,err,pd.notna(err),bool(pd.notna(err) and err<=.1+1e-10)])
    h1=pd.DataFrame(rows,columns=['tabela','local_id','segmento_id','periodo','indicador','calculado','oficial','erro_pp','elegivel','aprovado']); save(h1,'h1'); summary=h1.groupby('indicador').agg(total=('elegivel','size'),elegiveis=('elegivel','sum'),aprovados=('aprovado','sum'),max_pp=('erro_pp','max')).reset_index(); save(summary,'h1_resumo')
    # H2: compare intersecting keys of successive extraction snapshots, retain null equality.
    a,b=pairs[-2][0],d; overlap=a.merge(b,on=KEY,suffixes=('_anterior','_atual'),validate='one_to_one'); overlap['alterado']=~np.isclose(overlap.valor_anterior,overlap.valor_atual,rtol=0,atol=1e-10,equal_nan=True); overlap['delta']=overlap.valor_atual-overlap.valor_anterior; overlap['rastreavel']=overlap.versao_extracao_anterior.notna()&overlap.versao_extracao_atual.notna(); save(overlap,'h2')
    # Separate dimensional mart: raw API source and versions preserved; frozen reference remains unchanged.
    if DB.exists(): DB.unlink()
    f=all_data.copy(); f['periodo']=pd.to_datetime(f.periodo.astype(str),format='%Y%m').dt.strftime('%Y-%m-%d'); f['grupo']=f.tabela.astype(str); f['segmento']=f.segmento_id.astype(str)+' | '+f.segmento; f['versao']=f.versao_extracao; f['arquivo']=f.tabela.astype(str)+'_'+f.periodo.str[:4]+'_'+f.indicador.map({v:str(k) for k,v in VARS.items()})+'.json'
    cols=['periodo','local','grupo','segmento','indicador','versao','arquivo','valor']; original=f[cols].copy(); f=original.copy(); save(original,'fatos_api');
    with sqlite3.connect(DB) as con:
        con.executescript((ROOT/'sql/schema.sql').read_text()); dims={'tempo':['periodo'],'local':['local'],'segmento':['grupo','segmento'],'indicador':['indicador'],'versao':['versao','arquivo']}
        for name,columns in dims.items():
            dim=f[columns].drop_duplicates().sort_values(columns).reset_index(drop=True); dim.insert(0,'id',range(1,len(dim)+1)); dim.to_sql('dim_'+name,con,if_exists='append',index=False); f=f.merge(dim,on=columns,validate='many_to_one').rename(columns={'id':name+'_id'})
        f[['tempo_id','local_id','segmento_id','indicador_id','versao_id','valor']].to_sql('fato_producao',con,if_exists='append',index=False); assert con.execute('PRAGMA foreign_key_check').fetchall()==[]; sql=pd.read_sql_query('SELECT * FROM vw_fatos',con)
        h1.to_sql('reconciliacao',con,index=False); overlap.to_sql('revisoes',con,index=False); missing.to_sql('ausencias',con,index=False); hashes.to_sql('hashes',con,index=False)
    chk=original.merge(sql,on=cols[:-1],how='outer',indicator=True,suffixes=('_csv','_sql'),validate='one_to_one'); chk['aprovado']=chk._merge.eq('both')&np.isclose(chk.valor_csv,chk.valor_sql,rtol=0,atol=1e-10,equal_nan=True); assert len(chk)==len(original)==len(sql); save(chk,'h3')
    # Cross-check the five headline dashboard KPIs against the actual API, with displayed rounding.
    headline=d[(d.tabela==8888)&(d.segmento_id==129314)&(d.periodo==202609)].set_index('indicador').valor
    with sqlite3.connect(ROOT/'data/warehouse/pim.sqlite') as con: ref=pd.read_sql_query("SELECT indicador,valor FROM vw_fatos WHERE local='Brasil' AND grupo='Geral' AND periodo='2026-09-01' AND versao='2026-09'",con).set_index('indicador').valor
    html=(ROOT/'dashboards/painel.html').read_text(encoding='utf-8'); match=re.search(r'Índice SA: ([^ |<]+) \| Mensal: ([^ |<]+)% \| Interanual: ([^ |<]+)% \| Ano: ([^ |<]+)% \| 12 meses: ([^<]+)%',html); assert match, 'KPIs não encontrados no HTML'; displayed=dict(zip(['indice_sa','mom','yoy','ytd','l12'],[float(x.replace('−','-').replace(',','.')) for x in match.groups()])); kpi=pd.DataFrame([{'indicador':m,'api':headline[m],'sql_referencia':ref[m],'html_exibido':v,'aprovado':bool(np.isclose(round(headline[m],2 if m=='indice_sa' else 1),v) and np.isclose(ref[m],headline[m],atol=1e-5,rtol=0))} for m,v in displayed.items()]); save(kpi,'h3_kpis')
    # Forecast: 3 validation origins (33,39,45) then independent last six months holdout (51); all revised vintage.
    s=d[(d.tabela==8888)&(d.segmento_id==129314)&(d.indicador=='indice_sa')].sort_values('periodo'); y=s.valor.to_numpy(); assert len(y)==57 and np.isfinite(y).all(); back=[]
    for origin in (33,39,45):
        for model in MODELS:
            for i,v in enumerate(predict(y[:origin],6,model)): back.append([model,int(s.periodo.iloc[origin-1]),int(s.periodo.iloc[origin+i]),y[origin+i],v])
    back=pd.DataFrame(back,columns=['modelo','origem','periodo','real','previsto']); back['erro']=back.real-back.previsto; save(back,'backtest'); scores=back.groupby('modelo')[['erro','real']].apply(lambda x:pd.Series({'MAE':x.erro.abs().mean(),'RMSE':np.sqrt(np.mean(x.erro**2)),'MAPE':100*np.mean(x.erro.abs()/x.real)})).sort_values('MAE').reset_index(); save(scores,'modelos'); best=scores.modelo.iloc[0]; hold=predict(y[:51],6,best); holdout=pd.DataFrame({'periodo':s.periodo.iloc[51:].to_numpy(),'real':y[51:],'previsto':hold,'modelo':best}); save(holdout,'holdout'); dates=pd.date_range('2026-10-01',periods=6,freq='MS'); fc=pd.DataFrame({'periodo':dates.strftime('%Y-%m-%d'),'previsto':predict(y,6,best),'modelo':best}); save(fc,'previsao');
    result={'snapshots':len(pairs),'hashes':int(hashes.aprovado.sum()),'registros':len(d),'validos':int(d.valor.notna().sum()),'ausentes':int(d.valor.isna().sum()),'duplicados':int(d.duplicated(KEY).sum()),'h1_n':int(h1.elegivel.sum()),'h1_ok':int(h1.aprovado.sum()),'h2_n':len(overlap),'h2_alterados':int(overlap.alterado.sum()),'h3_n':len(chk),'h3_ok':int(chk.aprovado.sum()),'h3_kpi_ok':int(kpi.aprovado.sum()),'best':best,'holdout_mae':float(np.abs(y[51:]-hold).mean()),'previsao_mar2027':float(fc.previsto.iloc[-1])}; (OUT/'resumo.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)); print(json.dumps(result,ensure_ascii=False,indent=2)); print(summary.to_string(index=False)); print(scores.to_string(index=False)); print(fc.to_string(index=False)); print(kpi.to_string(index=False))
if __name__=='__main__': main()
