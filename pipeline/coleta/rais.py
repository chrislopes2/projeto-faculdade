"""Baixa a RAIS de vínculos e guarda só o estoque de vínculos ativos por UF e seção CNAE.

Os arquivos da RAIS são grandes (vários GB por ano). Cada arquivo é baixado,
resumido com DuckDB e apagado em seguida, para caber no disco do GitHub Actions.
"""
import argparse
import re
import urllib.request

import duckdb

from pipeline.config import RAIS_DIR, RAW
from pipeline.util import baixar, extrair_7z

RESUMO_SQL = """
SELECT {ano} AS ano,
       substr(lpad(CAST("Município" AS VARCHAR), 6, '0'), 1, 2)::INT AS uf_cod,
       substr(lpad(CAST("CNAE 2.0 Classe" AS VARCHAR), 5, '0'), 1, 2)::INT AS divisao,
       count(*) AS vinculos
FROM read_csv('{arquivo}', delim=';', header=true, encoding='latin-1', all_varchar=true)
WHERE "Vínculo Ativo 31/12" = '1'
GROUP BY ALL
"""


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
        for txt in extrair_7z(arq, pasta / "tmp"):
            partes.append(con.sql(RESUMO_SQL.format(ano=ano, arquivo=txt)).df())
            txt.unlink()
        arq.unlink()
    import pandas as pd

    pd.concat(partes).groupby(["ano", "uf_cod", "divisao"], as_index=False)["vinculos"].sum().to_csv(saida, index=False)
    print(f"RAIS {ano}: resumo salvo em {saida}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("anos", nargs="+", type=int)
    for ano in p.parse_args().anos:
        coletar(ano)
