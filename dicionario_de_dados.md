# Dicionário e glossário
Granularidade: um indicador por período mensal, local, grupo, segmento e edição do fascículo. Versão representa o mês de referência da edição, não a data exata da divulgação. Não somar índices ou percentuais entre recortes.

| Campo | Tipo | Definição |
|---|---|---|
| periodo | TEXT ISO | Primeiro dia do mês de referência |
| local | TEXT | Brasil, UF ou Região Nordeste |
| grupo | TEXT | Geral, Categoria, Seção ou Atividade |
| segmento | TEXT | Rótulo resumido do recorte |
| indicador | TEXT | indice_sa, mom, yoy, ytd ou l12 |
| versao | TEXT YYYY-MM | Edição de referência |
| arquivo | TEXT | Transcrição de origem; URL/hash no manifesto |
| valor | REAL/null | Índice ou percentual; nulo não equivale a zero |

## Indicadores
- indice_sa (12607): índice com ajuste sazonal, média de 2022 = 100.
- indice_sem_sa (12606): índice sem ajuste, previsto na coleta online, não incorporado à amostra congelada.
- mom (11601): 100 × (índice SA atual / índice SA anterior − 1).
- yoy (11602): 100 × (índice sem SA atual / índice sem SA de 12 meses antes − 1).
- ytd (11603): 100 × (soma dos índices sem SA jan–mês / soma jan–mês do ano anterior − 1).
- l12 (11604): 100 × (soma dos 12 índices sem SA recentes / soma dos 12 anteriores − 1).
- Qualidade: aprovados/avaliados em cada regra; taxa agregada ponderada pelas verificações, não medida de acurácia externa.
- Reconciliação: |calculado − oficial| em p.p.; aprovação ≤ 0,1 p.p.
- Revisão: índice da edição set menos índice da edição ago, em pontos de índice, não p.p. de taxa.
- MAE e RMSE em pontos de índice; MAPE em %.

## Warehouse
`dim_tempo`, `dim_local`, `dim_segmento`, `dim_indicador`, `dim_versao` (PK id); `fato_producao` (FKs e valor), `vw_fatos` (junção analítica), `qualidade`, `reconciliacao`, `revisoes`. Dimensão segmento reúne atividade/categoria, mutuamente exclusivas por registro. As taxas são não aditivas.
