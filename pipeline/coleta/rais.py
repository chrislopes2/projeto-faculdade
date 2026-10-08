"""Baixa a RAIS de vínculos e guarda só o estoque de vínculos ativos por UF e seção CNAE.

Os arquivos da RAIS são grandes (vários GB por ano). Cada arquivo é baixado,
resumido com DuckDB e apagado em seguida, para caber no disco do GitHub Actions.
"""
import argparse
import re
import shutil
import urllib.request

import duckdb
import pandas as pd

from pipeline.config import RAIS_DIR, RAW
from pipeline.util import baixar, extrair_7z

RESUMO_SQL = """
SELECT {ano} AS ano,
       substr(lpad(CAST("{municipio}" AS VARCHAR), 6, '0'), 1, 2)::INT AS uf_cod,
       substr(lpad(CAST("{cnae}" AS VARCHAR), 5, '0'), 1, 2)::INT AS divisao,
       count(*) AS vinculos
FROM read_csv('{arquivo}', header=true, encoding='latin-1', all_varchar=true)
WHERE trim("{ativo}") = '1'
GROUP BY ALL
"""


def _achar(colunas: list[str], *partes: str) -> str:
    """Nome exato da coluna que contém todas as partes (os nomes mudam entre anos:
    "Vínculo Ativo 31/12" virou "Ind Vínculo Ativo 31/12 - Código")."""
    for c in colunas:
        if all(p.lower() in c.lower() for p in partes):
            return c
    raise KeyError(f"coluna com {partes} não encontrada; colunas: {colunas}")


def resumir(con: duckdb.DuckDBPyConnection, ano: int, txt) -> "pd.DataFrame":
    # O separador mudou entre anos (';' antes, ',' com aspas em 2023): deixamos o DuckDB detectar.
    colunas = con.sql(f"SELECT * FROM read_csv('{txt}', header=true, "
                      f"encoding='latin-1', all_varchar=true) LIMIT 0").columns
    municipio = next((c for c in colunas if c.lower().startswith("munic") and "trab" not in c.lower()), None) \
        or _achar(colunas, "munic")
    sql = RESUMO_SQL.format(ano=ano, arquivo=txt, municipio=municipio,
                            cnae=_achar(colunas, "cnae 2.0 classe"),
                            ativo=_achar(colunas, "ativo 31/12"))
    return con.sql(sql).df()


def arquivos_do_ano(ano: int) -> list[str]:
    with urllib.request.urlopen(RAIS_DIR.format(ano=ano), timeout=120) as resp:
        listagem = resp.read().decode("latin-1")
    return sorted(set(re.findall(r"RAIS_VINC_PUB_[A-Z_]+\.7z", listagem)))


def coletar(ano: int) -> None:
    pasta = RAW / "rais"
    saida = pasta / f"rais_estoque_{ano}.csv"
    if saida.exists():
        print(f"RAIS {ano}: resumo já existe")
        return
    con = duckdb.connect()
    partes = []
    for nome in arquivos_do_ano(ano):
        arq = baixar(RAIS_DIR.format(ano=ano) + nome, pasta / "tmp" / nome)
        destino = pasta / "tmp" / arq.stem  # pasta limpa por arquivo, para não pegar sobras de um run que falhou
        shutil.rmtree(destino, ignore_errors=True)
        for txt in extrair_7z(arq, destino):
            partes.append(resumir(con, ano, txt))
            txt.unlink()
        arq.unlink()
    pd.concat(partes).groupby(["ano", "uf_cod", "divisao"], as_index=False)["vinculos"].sum().to_csv(saida, index=False)
    print(f"RAIS {ano}: resumo salvo em {saida}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("anos", nargs="+", type=int)
    for ano in p.parse_args().anos:
        coletar(ano)
