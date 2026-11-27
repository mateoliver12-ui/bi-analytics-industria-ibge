# PIM-PF | Painel executivo de produção industrial
Projeto acadêmico PUCRS — Fase 2. Mateus de Oliveira Ferreira.

## Executar
Python 3.11–3.13. No terminal, na raiz do repositório:
```bash
pip install -r requirements.txt
python src/pipeline.py
python -m unittest discover -s tests
```
Abra `dashboards/painel.html` no navegador (offline, Plotly incorporado) ou use o notebook `notebooks/PIM_PF_Colab.ipynb` no Google Colab. Os gráficos são interativos, com zoom, legendas e controles temporais nos painéis setoriais. O notebook inclui os resultados executados. A plataforma escolhida é Google Colab, em substituição ao Power BI previsto na Fase 1, porque não há acesso ao serviço Power BI ou conta externa. Não há PBIX. Os seis painéis foram publicados e validados visualmente pelo estudante.

## Dados, proveniência e escopo
Os arquivos `data/raw/*.txt` e `*.csv` são transcrições de tabelas públicas (não respostas da API nem PDFs originais), consultadas em 26/11/2026. A API direta estava indisponível no ambiente de execução. `results/manifesto.csv` registra URLs e hashes das transcrições. Edição refere-se ao mês de referência, não à data de extração original do IBGE.
- IBGE, PIM-PF Regional setembro/2026, tabela 1 (p. 13), 3.1–3.3 (p. 68–70), 4.1–4.3 (p. 71–73): https://ftp.ibge.gov.br/Industrias_Extrativas_e_de_Transformacao/Pesquisa_Industrial_Mensal_Producao_Fisica/Fasciculos/Fasciculo_Indicadores_IBGE_Regional/2026/pim-pf-regional_202609.pdf
- IBGE, PIM-PF Regional agosto/2026, tabela 3.3 (p. 70): https://ftp.ibge.gov.br/Industrias_Extrativas_e_de_Transformacao/Pesquisa_Industrial_Mensal_Producao_Fisica/Fasciculos/Fasciculo_Indicadores_IBGE_Regional/2026/pim-pf-regional_202608.pdf
- Ministério da Fazenda/SPE, Informativo PIM set/2026 (fonte IBGE), tabelas SAI, GCE e anexo 1: https://www.gov.br/fazenda/pt-br/central-de-conteudo/publicacoes/conjuntura-economica/atividade-economica/2026/informativo-pim-set2026.html
A série Brasil SA contém 33 meses, jan/2024 a set/2026; demais locais SA, jan–set/2026 (15 locais); edição anterior jan–ago/2026. Regional: 18 locais e Brasil, set/2026. Setores: 24 atividades, duas seções, cinco categorias (inclui agregado de consumo), jul–set/2026; 12 meses em setembro. Carry-over não é acumulado no ano e não foi importado. Maranhão, RN e MS não têm taxa mensal SA na tabela 1; nulos preservados.

## Coleta online (executada no Colab)
`python src/extract.py --inicio 2022 --fim 2026` consulta metadados e dados oficiais das tabelas SIDRA 8888/8887, salva JSON sem alteração, manifesto de URL/hash e CSV normalizado por extração. A data de divulgação, quando conhecida, pode ser passada com `--divulgacao AAAA-MM-DD`. Não substitui silenciosamente a base congelada; validar cobertura, códigos e integrar a nova extração antes de atualizar relatório. A coleta nacional foi executada pelo estudante no Colab em 26/11/2026 (27/11 UTC). O escopo padrão do script é explicitamente N1 (Brasil); a coleta regional não foi testada. O parâmetro de data de divulgação não foi informado, de modo que esse campo permanece nulo.

## Resultados e limites
741 registros (incluindo três nulos estruturais); seis regras de qualidade; H1 mensal 152/152, H2 128/128 pares com versões identificáveis, H3 741/741 valores SQL/CSV. H1 não cobre outras três taxas; H2 prova rastreabilidade da amostra, não a causa das divergências internas do cliente; H3 não é teste visual independente de Power BI. Modelo ARIMA(1,0,0) selecionado por MAE em dois blocos cronológicos de seis meses; modelos comparados: naive sazonal, regressão linear e Random Forest (lags 1–3). Backtest na mesma edição revisada (pseudo fora da amostra); não há teste final independente nem intervalo probabilístico calibrado. Não usar previsão como demanda da empresa.

## Publicação e validação complementar
- GitHub: https://github.com/mateoliver12-ui/bi-analytics-industria-ibge
- Painéis: https://mateoliver12-ui.github.io/bi-analytics-industria-ibge/dashboards/painel.html
- Colab: https://colab.research.google.com/drive/1GWqLCAxJLXd6fyD73LoVRqG3Qy9fy16J?usp=sharing

O painel publicado continua utilizando a base de referência de 741 registros e o ARIMA apresentado na versão homologada. A auditoria complementar, em `results/api/`, usa os dois snapshots reais em `data/api_snapshots/` e um segundo data mart dimensional `data/warehouse/pim_api.sqlite`. Não misture edições/versões ao agregar os dados. Para reproduzir (sem rede):

```bash
python src/validar_api.py
python -m unittest discover -s tests -v
```

Resultados: 88/88 hashes dos JSON; 17.442 registros na extração histórica, 15.229 valores numéricos, 2.213 marcados com `-` na origem, 0 duplicidades. 19 categorias não disponibilizam SA/MoM em todo o período; outras 47 ausências concentram-se em uma categoria. Nulos preservados. H1: 8.116/8.116 elegíveis dentro de 0,1 p.p. (3.512 não elegíveis por janela incompleta ou ausência de valor oficial/base). H2: 2.754 chaves coincidentes nas duas extrações do mesmo dia; nenhuma alteração; evidência de rastreabilidade, não de revisões entre divulgações. H3: 20.196/20.196 fatos das duas versões conciliados CSV/SQL; cinco KPIs do HTML conferidos contra API e SQL. A inspeção visual independente de todos os filtros continua fora do teste automatizado. A execução local de 9 testes foi aprovada; os 4 testes originais já tinham sido reproduzidos pelo estudante no Colab.

Analytics complementar: 57 meses da série nacional SA, 3 origens cronológicas (33,39,45 meses de treino), 18 previsões de validação por modelo e holdout final de 6 meses (abr–set/2026), não usado na seleção. Regressão linear: MAE de validação 0,663; MAE holdout 1,849; projeção mar/2027 105,74 após reajuste nos 57 meses. Dados de uma edição revisada, sem teste em tempo real ou intervalo calibrado. Esta é uma análise de sensibilidade, não substituição da previsão ARIMA 103,58 no painel aprovado. Não é previsão de demanda da empresa.

Evidências: `results/api/testes.txt`, `results/api/resumo.json`, CSVs detalhados, screenshots em `docs/evidencias/`. `notebooks/Validacao_API.ipynb` permite reproduzir a auditoria em Colab após publicar esta atualização. O arquivo original de painel foi preservado byte a byte.
