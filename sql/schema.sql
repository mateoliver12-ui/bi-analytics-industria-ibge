PRAGMA foreign_keys=ON;
CREATE TABLE dim_tempo(id INTEGER PRIMARY KEY, periodo TEXT UNIQUE NOT NULL);
CREATE TABLE dim_local(id INTEGER PRIMARY KEY, local TEXT UNIQUE NOT NULL);
CREATE TABLE dim_segmento(id INTEGER PRIMARY KEY, grupo TEXT NOT NULL, segmento TEXT NOT NULL, UNIQUE(grupo,segmento));
CREATE TABLE dim_indicador(id INTEGER PRIMARY KEY, indicador TEXT UNIQUE NOT NULL);
CREATE TABLE dim_versao(id INTEGER PRIMARY KEY, versao TEXT NOT NULL, arquivo TEXT NOT NULL, UNIQUE(versao,arquivo));
CREATE TABLE fato_producao(tempo_id INTEGER REFERENCES dim_tempo(id), local_id INTEGER REFERENCES dim_local(id), segmento_id INTEGER REFERENCES dim_segmento(id), indicador_id INTEGER REFERENCES dim_indicador(id), versao_id INTEGER REFERENCES dim_versao(id), valor REAL, PRIMARY KEY(tempo_id,local_id,segmento_id,indicador_id,versao_id));
CREATE VIEW vw_fatos AS SELECT t.periodo,l.local,s.grupo,s.segmento,i.indicador,v.versao,v.arquivo,f.valor FROM fato_producao f JOIN dim_tempo t ON t.id=f.tempo_id JOIN dim_local l ON l.id=f.local_id JOIN dim_segmento s ON s.id=f.segmento_id JOIN dim_indicador i ON i.id=f.indicador_id JOIN dim_versao v ON v.id=f.versao_id;
