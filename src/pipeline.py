from pathlib import Path
import json, sqlite3, hashlib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from statsmodels.tsa.statespace.sarimax import SARIMAX
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw'; OUT=ROOT/'data/processed'; RES=ROOT/'results'; DASH=ROOT/'dashboards'; DB=ROOT/'data/warehouse/pim.sqlite'
for p in (OUT,RES,DASH,DB.parent): p.mkdir(parents=True,exist_ok=True)
BASE='https://ftp.ibge.gov.br/Industrias_Extrativas_e_de_Transformacao/Pesquisa_Industrial_Mensal_Producao_Fisica/Fasciculos/Fasciculo_Indicadores_IBGE_Regional/2026/'
SPE='https://www.gov.br/fazenda/pt-br/central-de-conteudo/publicacoes/conjuntura-economica/atividade-economica/2026/informativo-pim-set2026.html'

def parse(name,version,metric):
    records=[]
    for line in (RAW/name).read_text().splitlines():
        local,year,values=line.split('|')
        for m,v in enumerate(values.split(),1): records.append((f'{year}-{m:02d}-01',local,'Geral','Indústria geral',metric,version,float(v),name))
    return pd.DataFrame(records,columns=['periodo','local','grupo','segmento','indicador','versao','valor','arquivo'])

def row(period,local,group,seg,metric,v,filename): return (period,local,group,seg,metric,'2026-09',v,filename)

def load():
    a=parse('indices_set2026.txt','2026-09','indice_sa'); b=parse('indices_ago2026.txt','2026-08','indice_sa'); m=parse('mom_set2026.txt','2026-09','mom')
    regional=pd.read_csv(RAW/'regional.csv'); setores=pd.read_csv(RAW/'setores.csv')
    extra=[]
    for r in regional.itertuples():
        for k in ('mom','yoy','ytd','l12'):
            if k=='mom' and r.local in m.local.unique(): continue
            extra.append(row('2026-09-01',r.local,'Geral','Indústria geral',k,getattr(r,k),'regional.csv'))
    for r in setores.itertuples():
        for k in ('mom','yoy'):
            for i,s in enumerate(('jul','ago','set'),7): extra.append(row(f'2026-{i:02d}-01','Brasil',r.grupo,r.segmento,k,getattr(r,k+'_'+s),'setores.csv'))
        extra.append(row('2026-09-01','Brasil',r.grupo,r.segmento,'l12',r.l12,'setores.csv'))
    f=pd.concat([a,b,m,pd.DataFrame(extra,columns=a.columns)],ignore_index=True)
    key=['periodo','local','grupo','segmento','indicador','versao']
    quality=pd.DataFrame([('Chaves únicas',len(f),int((~f.duplicated(key,keep=False)).sum())),('Datas válidas',len(f),int(pd.to_datetime(f.periodo,errors='coerce').notna().sum())),('Índices positivos',len(a)+len(b),int((pd.concat([a,b]).valor>0).sum())),('Série Brasil contínua',33,len(a[a.local=='Brasil'])),('Valores esperados presentes',len(f)-3,int(f.valor.notna().sum())),('Ausências estruturais preservadas',3,int(f.valor.isna().sum()))],columns=['regra','avaliados','aprovados'])
    quality['taxa']=100*quality.aprovados/quality.avaliados
    calc=a.sort_values('periodo').copy(); calc['calculado']=calc.groupby('local').valor.pct_change(fill_method=None)*100
    h1=calc.merge(m,on=['periodo','local'],suffixes=('_idx','_of')).dropna(subset=['calculado']); h1=h1[['periodo','local','calculado','valor_of']].rename(columns={'valor_of':'oficial'}); h1['erro_pp']=(h1.calculado-h1.oficial).abs(); h1['aprovado']=h1.erro_pp<=.1+1e-10
    rev=b.merge(a,on=['periodo','local','indicador'],suffixes=('_ago','_set')); rev=rev[['periodo','local','indicador','versao_ago','versao_set','valor_ago','valor_set']]; rev['delta']=rev.valor_set-rev.valor_ago; rev['abs_delta']=rev.delta.abs(); rev['rastreavel']=rev.versao_ago.notna()&rev.versao_set.notna()
    f.to_csv(OUT/'fatos.csv',index=False); quality.to_csv(RES/'qualidade.csv',index=False); h1.to_csv(RES/'h1.csv',index=False); rev.to_csv(RES/'revisoes.csv',index=False)
    if DB.exists(): DB.unlink()
    with sqlite3.connect(DB) as con:
        con.executescript((ROOT/'sql/schema.sql').read_text())
        dims={'tempo':['periodo'],'local':['local'],'segmento':['grupo','segmento'],'indicador':['indicador'],'versao':['versao','arquivo']}
        for name,cols in dims.items():
            d=f[cols].drop_duplicates().sort_values(cols).reset_index(drop=True); d.insert(0,'id',range(1,len(d)+1)); d.to_sql('dim_'+name,con,if_exists='append',index=False); f=f.merge(d,on=cols).rename(columns={'id':name+'_id'})
        f[['tempo_id','local_id','segmento_id','indicador_id','versao_id','valor']].to_sql('fato_producao',con,if_exists='append',index=False)
        quality.to_sql('qualidade',con,index=False); h1.to_sql('reconciliacao',con,index=False); rev.to_sql('revisoes',con,index=False)
        data=pd.read_sql_query('SELECT * FROM vw_fatos',con)
        original=pd.read_csv(OUT/'fatos.csv'); check=original.merge(data,on=key+['arquivo'],suffixes=('_csv','_sql')); check['aprovado']=np.isclose(check.valor_csv,check.valor_sql,equal_nan=True); assert len(check)==len(original)==len(data); check.to_csv(RES/'h3.csv',index=False)
    return a,regional,setores,quality,h1,rev,check,data

def predict(y,n,model):
    y=np.asarray(y,float)
    if model=='Naive sazonal': return np.resize(y[-12:],n)
    if model=='Regressão linear': return LinearRegression().fit(np.arange(len(y)).reshape(-1,1),y).predict(np.arange(len(y),len(y)+n).reshape(-1,1))
    if model=='ARIMA(1,0,0)': return np.asarray(SARIMAX(y,order=(1,0,0),trend='c').fit(disp=False,method='powell',maxiter=200).forecast(n))
    lag=3; X=np.array([y[i-lag:i] for i in range(lag,len(y))]); rf=RandomForestRegressor(n_estimators=200,max_depth=3,min_samples_leaf=2,random_state=42,n_jobs=1).fit(X,y[lag:]); seq=list(y)
    for _ in range(n): seq.append(float(rf.predict([seq[-lag:]])[0]))
    return np.array(seq[-n:])

def forecast(a):
    s=a[a.local=='Brasil'].sort_values('periodo').set_index('periodo').valor; y=s.to_numpy(); models=['Naive sazonal','Regressão linear','Random Forest','ARIMA(1,0,0)']; rows=[]
    for origin in (21,27):
        for model in models:
            pred=predict(y[:origin],6,model)
            for i,v in enumerate(pred): rows.append((model,s.index[origin-1],s.index[origin+i],i+1,y[origin+i],v))
    back=pd.DataFrame(rows,columns=['modelo','origem','periodo','horizonte','real','previsto']); back['erro']=back.real-back.previsto
    scores=back.groupby('modelo').apply(lambda x:pd.Series({'MAE':x.erro.abs().mean(),'RMSE':np.sqrt(np.mean(x.erro**2)),'MAPE':100*np.mean(x.erro.abs()/x.real)})).sort_values('MAE').reset_index()
    best=scores.modelo.iloc[0]; pred=predict(y,6,best); dates=pd.date_range(pd.Timestamp(s.index[-1])+pd.offsets.MonthBegin(),periods=6,freq='MS'); fc=pd.DataFrame({'periodo':dates.strftime('%Y-%m-%d'),'previsto':pred,'modelo':best}); back.to_csv(RES/'backtest.csv',index=False); scores.to_csv(RES/'modelos.csv',index=False); fc.to_csv(RES/'previsao.csv',index=False)
    return s,scores,fc

def charts(a,regional,setores,q,h1,rev,h3,data,s,scores,fc):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','axes.labelcolor':'#334155','text.color':'#16283f','axes.edgecolor':'#b5c2d0','grid.color':'#e4eaf0','figure.facecolor':'white'})
    blue='#2469a0'; teal='#00877e'; red='#b85040'
    def save(fig,name): fig.tight_layout(); fig.savefig(DASH/(name+'.png'),dpi=170,bbox_inches='tight'); plt.close(fig)
    def bars(df,label,metric,title,name):
        df=df.sort_values(metric); fig,ax=plt.subplots(figsize=(9,max(3.0,len(df)*.26+1))); ax.barh(df[label],df[metric],color=[teal if v>=0 else red for v in df[metric]]); ax.axvline(0,color='#667788',lw=.8); ax.set_title(title,loc='left'); ax.set_xlabel('%'); ax.grid(axis='x',alpha=.5); ax.set_axisbelow(True); save(fig,name)
    fig,ax=plt.subplots(figsize=(9,3.3)); ax.plot(pd.to_datetime(s.index),s,color=blue,lw=2.2); ax.axhline(100,color='#8194a6',ls='--'); ax.set_title('Brasil | produção industrial com ajuste sazonal',loc='left'); ax.set_ylabel('Índice (2022 = 100)'); ax.grid(axis='y'); save(fig,'01_geral')
    bars(setores[(setores.grupo=='Categoria') & (setores.segmento!='Bens de consumo')],'segmento','yoy_set','Categorias | setembro de 2026 × setembro de 2025','02_categorias')
    bars(setores[setores.grupo=='Atividade'],'segmento','yoy_set','Atividades | variação interanual, setembro de 2026','03_atividades')
    bars(regional[regional.local!='Brasil'],'local','yoy','Regiões | variação interanual, setembro de 2026','04_regional')
    fig,ax=plt.subplots(figsize=(9,4)); d=rev.groupby('local').abs_delta.mean().sort_values(); ax.barh(d.index,d,color=blue); ax.set_title('Revisão média absoluta | agosto → setembro de 2026',loc='left'); ax.set_xlabel('Pontos de índice'); save(fig,'05_confiabilidade')
    fig,ax=plt.subplots(figsize=(9,3.6)); ax.plot(pd.to_datetime(s.index),s,color=blue,label='Realizado'); ax.plot(pd.to_datetime([s.index[-1]]+fc.periodo.tolist()),[s.iloc[-1]]+fc.previsto.tolist(),color=teal,ls='--',marker='o',label='Previsão'); ax.axvline(pd.Timestamp(s.index[-1]),color='#8c9ba9',ls=':'); ax.set_title('Brasil | projeção de seis meses',loc='left'); ax.set_ylabel('Índice (2022 = 100)'); ax.legend(frameon=False); ax.grid(axis='y'); save(fig,'06_previsao')
    # Interactive Plotly charts, embedded in the Colab notebook and exported standalone.
    figs=[]
    figs.append(px.line(data[(data.grupo=='Geral')&(data.local=='Brasil')&(data.indicador=='indice_sa')],x='periodo',y='valor',color='versao',markers=True,title='01 | Brasil: índice dessazonalizado por versão'))
    for group,title in [('Categoria','02 | Categorias econômicas'),('Atividade','03 | Atividades industriais')]:
        d=data[(data.grupo==group)&(data.indicador.isin(['mom','yoy']))]; figs.append(px.bar(d,x='valor',y='segmento',color='indicador',facet_col='indicador',animation_frame='periodo',orientation='h',title=title,height=850 if group=='Atividade' else 480))
    figs.append(px.bar(data[(data.local!='Brasil')&(data.periodo=='2026-09-01')&(data.indicador.isin(['mom','yoy','ytd','l12']))].dropna(subset=['valor']),x='valor',y='local',color='indicador',facet_col='indicador',orientation='h',title='04 | Regional: setembro de 2026',height=650))
    figs.append(px.bar(rev,x='periodo',y='delta',color='local',barmode='group',title='05 | Revisões: edição set menos edição ago'))
    g=go.Figure(); g.add_scatter(x=s.index,y=s,mode='lines+markers',name='Realizado'); g.add_scatter(x=fc.periodo,y=fc.previsto,mode='lines+markers',name='Previsão',line={'dash':'dash'}); g.update_layout(title='06 | Previsão de seis meses'); figs.append(g)
    fragments=[]
    for i,g in enumerate(figs):
        g.update_layout(template='plotly_white',font={'family':'Arial','color':'#16283f'},margin={'l':30,'r':30,'t':65,'b':35}); fragments.append(g.to_html(full_html=False,include_plotlyjs=True if i==0 else False))
    html='<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>PIM-PF | Painel executivo</title><style>body{font:16px Arial;color:#16283f;background:#eff4f8;margin:30px}section{background:white;padding:20px;margin:18px 0;border-radius:10px}a{color:#2469a0}table{border-collapse:collapse}td,th{padding:8px;border-bottom:1px solid #ddd}</style><h1>PIM-PF | Painel executivo</h1><p>IBGE / SPE · edição de setembro de 2026 · amostra de fascículos transcritos. Fonte e limitações no README. Filtros via legendas e controles de período.</p><section><h2>Brasil · setembro de 2026</h2><p>Índice SA: 102,14 | Mensal: −0,8% | Interanual: −2,5% | Ano: +0,4% | 12 meses: +0,2%</p></section>'
    for i,fragment in enumerate(fragments):
        html+=f'<section id="p{i+1}">'+fragment
        if i==4: html+=f'<p>H1 mensal: {h1.aprovado.sum()}/{len(h1)} · H2: {rev.rastreavel.sum()}/{len(rev)} pares · H3 SQL/CSV: {h3.aprovado.sum()}/{len(h3)}.</p>'+q.to_html(index=False,float_format=lambda x:f'{x:.2f}')
        if i==5: html+=scores.to_html(index=False,float_format=lambda x:f'{x:.3f}')+'<p>Backtest de dois blocos de seis meses; sem intervalo probabilístico validado.</p>'
        html+='</section>'
    (DASH/'painel.html').write_text(html,encoding='utf-8')

def main():
    a,r,t,q,h1,rev,h3,data=load(); s,scores,fc=forecast(a); charts(a,r,t,q,h1,rev,h3,data,s,scores,fc)
    manifest=[{'arquivo':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'origem':SPE if p.name=='setores.csv' else BASE+('pim-pf-regional_202608.pdf' if 'ago2026' in p.name else 'pim-pf-regional_202609.pdf')} for p in sorted(RAW.glob('*')) if p.is_file()]
    pd.DataFrame(manifest).to_csv(RES/'manifesto.csv',index=False)
    result={'fatos':len(data),'h1_n':len(h1),'h1_ok':int(h1.aprovado.sum()),'h1_max':float(h1.erro_pp.max()),'h2_n':len(rev),'h2_changes':int((rev.abs_delta>1e-9).sum()),'h2_mean':float(rev.abs_delta.mean()),'h2_max':float(rev.abs_delta.max()),'h3_n':len(h3),'h3_ok':int(h3.aprovado.sum()),'quality':float(q.aprovados.sum()/q.avaliados.sum()*100),'best':scores.iloc[0].to_dict(),'prediction':fc.previsto.round(3).tolist()}
    (RES/'resumo.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)); print(json.dumps(result,ensure_ascii=False,indent=2)); return result
if __name__=='__main__': main()
