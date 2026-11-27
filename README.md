# PIM-PF | Painel executivo de produção industrial
Projeto acadêmico PUCRS — Fase 2. Mateus de Oliveira Ferreira.

## Executar
Python 3.11–3.13. No terminal, na raiz do repositório:
```bash
pip install -r requirements.txt
python src/pipeline.py
python -m unittest discover -s tests
```
Abra `dashboards/painel.html` no navegador (offline, Plotly incorporado) ou use o notebook `notebooks/PIM_PF_Colab.ipynb` no Google Colab. Os gráficos são interativos, com zoom, legendas e controles temporais nos painéis setoriais. O notebook inclui os resultados executados. A plataforma escolhida é Google Colab, em substituição ao Power BI previsto na Fase 1, porque não há acesso ao serviço Power BI ou conta externa. Não há PBIX nem link publicado nesta entrega.

## Dados, proveniência e escopo
Os arquivos `data/raw/*.txt` e `*.csv` são transcrições de tabelas públicas (não respostas da API nem PDFs originais), consultadas em 26/11/2026. A API direta estava indisponível no ambiente de execução. `results/manifesto.csv` registra URLs e hashes das transcrições. Edição refere-se ao mês de referência, não à data de extração original do IBGE.
- IBGE, PIM-PF Regional setembro/2026, tabela 1 (p. 13), 3.1–3.3 (p. 68–70), 4.1–4.3 (p. 71–73): https://ftp.ibge.gov.br/Industrias_Extrativas_e_de_Transformacao/Pesquisa_Industrial_Mensal_Producao_Fisica/Fasciculos/Fasciculo_Indicadores_IBGE_Regional/2026/pim-pf-regional_202609.pdf
- IBGE, PIM-PF Regional agosto/2026, tabela 3.3 (p. 70): https://ftp.ibge.gov.br/Industrias_Extrativas_e_de_Transformacao/Pesquisa_Industrial_Mensal_Producao_Fisica/Fasciculos/Fasciculo_Indicadores_IBGE_Regional/2026/pim-pf-regional_202608.pdf
- Ministério da Fazenda/SPE, Informativo PIM set/2026 (fonte IBGE), tabelas SAI, GCE e anexo 1: https://www.gov.br/fazenda/pt-br/central-de-conteudo/publicacoes/conjuntura-economica/atividade-economica/2026/informativo-pim-set2026.html
A série Brasil SA contém 33 meses, jan/2024 a set/2026; demais locais SA, jan–set/2026 (15 locais); edição anterior jan–ago/2026. Regional: 18 locais e Brasil, set/2026. Setores: 24 atividades, duas seções, cinco categorias (inclui agregado de consumo), jul–set/2026; 12 meses em setembro. Carry-over não é acumulado no ano e não foi importado. Maranhão, RN e MS não têm taxa mensal SA na tabela 1; nulos preservados.

## Coleta online (não executada nesta entrega)
`python src/extract.py --inicio 2022 --fim 2026` consulta metadados e dados oficiais das tabelas SIDRA 8888/8887, salva JSON sem alteração, manifesto de URL/hash e CSV normalizado por extração. A data de divulgação, quando conhecida, pode ser passada com `--divulgacao AAAA-MM-DD`. Não substitui silenciosamente a base congelada; validar cobertura, códigos e integrar a nova extração antes de atualizar relatório. O script foi preparado, mas não testado contra a API real por indisponibilidade de rede. Para reconciliação integral futura, usar as fórmulas no dicionário, com série sem ajuste e janelas completas.

## Resultados e limites
741 registros (incluindo três nulos estruturais); seis regras de qualidade; H1 mensal 152/152, H2 128/128 pares com versões identificáveis, H3 741/741 valores SQL/CSV. H1 não cobre outras três taxas; H2 prova rastreabilidade da amostra, não a causa das divergências internas do cliente; H3 não é teste visual independente de Power BI. Modelo ARIMA(1,0,0) selecionado por MAE em dois blocos cronológicos de seis meses; modelos comparados: naive sazonal, regressão linear e Random Forest (lags 1–3). Backtest na mesma edição revisada (pseudo fora da amostra); não há teste final independente nem intervalo probabilístico calibrado. Não usar previsão como demanda da empresa.

## Publicação
1. Crie um repositório GitHub vazio e envie esta pasta inteira (sem credenciais). Ex.: `git init`, `git add .`, `git commit -m "Fase 2"`, `git branch -M main`, `git remote add origin <URL DO SEU REPOSITORIO>`, `git push -u origin main`.
2. Abra o notebook no Colab pela aba GitHub ou faça upload do notebook; siga a célula de execução. Selecione Compartilhar e configure acesso para avaliação. Opcional: GitHub Pages a partir de branch que contenha o HTML, ou hospede o painel com outro serviço permitido.
3. Insira URLs reais no relatório Word, exporte novamente a PDF e atualize o slide final antes de entregar. Não envie a versão atual como se já estivesse publicada.
