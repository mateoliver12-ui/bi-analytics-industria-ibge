-- Executar no SQLite da entrega, somente leitura.
SELECT * FROM vw_fatos WHERE local='Brasil' AND grupo='Geral' AND periodo='2026-09-01' AND versao='2026-09';
SELECT COUNT(*) AS fatos FROM fato_producao;
SELECT COUNT(*) AS n, SUM(aprovado) AS aprovados, MAX(erro_pp) AS maior_erro FROM reconciliacao;
SELECT COUNT(*) AS n, AVG(abs_delta) AS revisao_media, MAX(abs_delta) AS maior_revisao FROM revisoes;
SELECT * FROM qualidade;
