"""Cruza INSS, CAGED e RAIS e exporta os JSON que o site lê (site/public/data)."""
import datetime as dt
import json

import duckdb
import numpy as np
import pandas as pd

from pipeline.config import (AFASTAMENTO, BPC_PCD, CAGED_A_PEDIDO, CAGED_SEM_JUSTA_CAUSA,
                             CLEAN, GRUPOS_CID, SAIDA, SETORES)

GRUPO_SQL = "CASE " + " ".join(
    "WHEN " + " OR ".join(f"cid LIKE '{p}%'" for p in prefixos) + f" THEN '{chave}'"
    for chave, _, prefixos in GRUPOS_CID
) + " ELSE 'outros' END"

FAIXAS_SQL = """CASE WHEN idade < 25 THEN 'até 24' WHEN idade < 35 THEN '25 a 34'
    WHEN idade < 45 THEN '35 a 44' WHEN idade < 55 THEN '45 a 54' ELSE '55 ou mais' END"""

LISTA = lambda t: "(" + ",".join(str(x) for x in t) + ")"  # noqa: E731


def _mes(comp: pd.Series) -> pd.Series:
    return comp.str[:4] + "-" + comp.str[4:6]


def _vinculos_por_mes(con, meses: list[str], por: str) -> pd.DataFrame:
    """Usa a RAIS mais recente disponível até o ano de cada mês (ou a mais antiga, se não houver)."""
    anos = sorted(con.sql("SELECT DISTINCT ano FROM rais").df().ano.tolist())
    linhas = []
    for mes in meses:
        y = int(mes[:4])
        ano = max([a for a in anos if a <= y], default=anos[0])
        linhas.append((mes, ano))
    ref = pd.DataFrame(linhas, columns=["mes", "ano"])
    con.register("ref", ref)
    return con.sql(f"""
        SELECT ref.mes, {por}, sum(vinculos) AS vinculos
        FROM ref JOIN rais USING (ano) GROUP BY ALL
    """).df()


def serie(con) -> pd.DataFrame:
    grupos = [g for g, _, _ in GRUPOS_CID]
    afast = con.sql(f"""
        SELECT competencia, uf,
               count(*) AS afast_total,
               count(*) FILTER (grupo <> 'outros') AS afast_mental,
               count(*) FILTER (grupo <> 'outros' AND especie = 91) AS afast_mental_acid,
               {", ".join(f"count(*) FILTER (grupo = '{g}') AS {g}" for g in grupos)}
        FROM (SELECT *, {GRUPO_SQL} AS grupo FROM inss WHERE especie IN {LISTA(AFASTAMENTO)} AND uf IS NOT NULL)
        GROUP BY ALL
    """).df()
    dem = con.sql(f"""
        SELECT competencia, uf,
               sum(n) FILTER (tipo_mov IN {LISTA(CAGED_SEM_JUSTA_CAUSA)}) AS demissoes_sjc,
               sum(n) FILTER (tipo_mov IN {LISTA(CAGED_A_PEDIDO)}) AS pedidos,
               sum(n) FILTER (saldo < 0) AS desligamentos,
               sum(n) FILTER (saldo > 0) AS admissoes
        FROM caged GROUP BY ALL
    """).df()
    df = afast.merge(dem, on=["competencia", "uf"], how="outer")
    df["mes"] = _mes(df.competencia)
    df = df.drop(columns="competencia")
    vinc = _vinculos_por_mes(con, sorted(df.mes.unique()), "uf")
    df = df.merge(vinc, on=["mes", "uf"], how="left")
    br = df.drop(columns="uf").groupby("mes", as_index=False).sum(min_count=1)
    br["uf"] = "BR"
    out = pd.concat([br, df], ignore_index=True).sort_values(["uf", "mes"])
    num = out.columns.difference(["uf", "mes"])
    out[num] = out[num].astype("Int64")
    return out


def perfil(con, ultimos: list[str]) -> pd.DataFrame:
    comps = ",".join(f"'{m.replace('-', '')}'" for m in ultimos)
    return con.sql(f"""
        SELECT grupo, coalesce(sexo, '?') AS sexo, {FAIXAS_SQL} AS faixa, count(*) AS n
        FROM (SELECT *, {GRUPO_SQL} AS grupo FROM inss)
        WHERE especie IN {LISTA(AFASTAMENTO)} AND grupo <> 'outros' AND idade IS NOT NULL
          AND competencia IN ({comps})
        GROUP BY ALL ORDER BY ALL
    """).df()


def setores(con, ultimos: list[str]) -> pd.DataFrame:
    comps = ",".join(f"'{m.replace('-', '')}'" for m in ultimos)
    linhas = []
    vinc = _vinculos_por_mes(con, ultimos, "secao")
    for chave, (nome, secoes, ramos) in SETORES.items():
        cond_ramo = " OR ".join(f"ramo LIKE '%{r}%'" for r in ramos)
        sec = ",".join(f"'{s}'" for s in secoes)
        afast = con.sql(f"""
            SELECT count(*) FROM (SELECT *, {GRUPO_SQL} AS grupo FROM inss)
            WHERE especie IN {LISTA(AFASTAMENTO)} AND grupo <> 'outros'
              AND competencia IN ({comps}) AND ({cond_ramo})""").fetchone()[0]
        dem = con.sql(f"""
            SELECT coalesce(sum(n), 0) FROM caged
            WHERE tipo_mov IN {LISTA(CAGED_SEM_JUSTA_CAUSA)} AND secao IN ({sec})
              AND competencia IN ({comps})""").fetchone()[0]
        v = vinc[vinc.secao.isin(secoes)].groupby("mes").vinculos.sum().mean()
        linhas.append({"setor": chave, "nome": nome, "afast_mental": int(afast),
                       "demissoes_sjc": int(dem), "vinculos_medio": int(v) if pd.notna(v) else None})
    return pd.DataFrame(linhas)


def bpc_autismo(con) -> pd.DataFrame:
    df = con.sql(f"""
        SELECT competencia,
               count(*) FILTER (especie IN {LISTA(BPC_PCD)}) AS bpc,
               count(*) FILTER (especie IN {LISTA(AFASTAMENTO)}) AS afastamento
        FROM inss WHERE cid LIKE 'F84%' GROUP BY ALL ORDER BY 1
    """).df()
    df["mes"] = _mes(df.competencia)
    return df.drop(columns="competencia")


def correlacoes(s: pd.DataFrame, ultimos: list[str]) -> dict:
    br = s[s.uf == "BR"].drop(columns="uf").set_index("mes").astype(float)
    ta = br.afast_mental / br.vinculos * 1e5
    td = br.demissoes_sjc / br.vinculos * 1e5
    defasagens = []
    for k in (0, 3, 6, 12):
        par = pd.concat([td, ta.shift(-k)], axis=1).dropna()
        r = float(np.corrcoef(par.iloc[:, 0], par.iloc[:, 1])[0, 1]) if len(par) >= 6 else None
        defasagens.append({"defasagem_meses": k, "r": r, "n_meses": int(len(par))})
    uf = s[(s.uf != "BR") & s.mes.isin(ultimos)].groupby("uf")[["afast_mental", "demissoes_sjc", "vinculos"]].sum().astype(float)
    pontos = pd.DataFrame({
        "uf": uf.index,
        # média mensal: soma dos casos / soma dos estoques mensais
        "taxa_afast_mental": uf.afast_mental / uf.vinculos * 1e5,
        "taxa_demissao": uf.demissoes_sjc / uf.vinculos * 1e5,
    }).dropna()
    r_uf = float(np.corrcoef(pontos.taxa_demissao, pontos.taxa_afast_mental)[0, 1]) if len(pontos) > 2 else None
    return {"serie_nacional": defasagens, "entre_ufs": {"r": r_uf, "n_ufs": int(len(pontos)), "meses": ultimos}}


def _json(nome: str, dados) -> None:
    if isinstance(dados, pd.DataFrame):
        dados = json.loads(dados.to_json(orient="records", force_ascii=False))
    (SAIDA / nome).write_text(json.dumps(dados, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  {nome}")


def agregar(exemplo: bool = False) -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    for t in ("inss", "caged", "rais"):
        con.sql(f"CREATE VIEW {t} AS SELECT * FROM '{CLEAN / (t + '.parquet')}'")
    s = serie(con)
    br = s[(s.uf == "BR") & s.afast_mental.notna() & s.demissoes_sjc.notna()]
    meses = sorted(br.mes)
    ultimos = meses[-12:]
    print("Exportando")
    _json("serie.json", s)
    _json("perfil.json", perfil(con, ultimos))
    _json("setores.json", setores(con, ultimos))
    _json("bpc_autismo.json", bpc_autismo(con))
    _json("correlacao.json", correlacoes(s, ultimos))
    _json("meta.json", {
        "gerado_em": dt.datetime.now().isoformat(timespec="minutes"),
        "exemplo": exemplo,
        "periodo": {"inicio": meses[0], "fim": meses[-1]},
        "ultimos_12_meses": ultimos,
        "grupos_cid": [{"chave": c, "nome": n, "cids": list(p)} for c, n, p in GRUPOS_CID],
    })


if __name__ == "__main__":
    agregar()
