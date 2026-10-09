"""Cruza INSS, CAGED e RAIS e exporta os JSON que o site lê (site/public/data)."""
import datetime as dt
import json

import duckdb
import numpy as np
import pandas as pd

from pipeline.config import (AFASTAMENTO, BPC_PCD, CAGED_A_PEDIDO, CAGED_SEM_JUSTA_CAUSA,
                             CLEAN, FILIACOES, GRUPOS_CID, SAIDA)

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


def filiacao(con) -> pd.DataFrame:
    """Afastamentos por saúde mental no Brasil, por mês e forma de filiação do segurado."""
    cols = ", ".join(f"count(*) FILTER (filiacao = '{c}') AS {c}" for c, _, _ in FILIACOES)
    df = con.sql(f"""
        SELECT competencia, {cols}
        FROM (SELECT *, {GRUPO_SQL} AS grupo FROM inss)
        WHERE especie IN {LISTA(AFASTAMENTO)} AND grupo <> 'outros'
        GROUP BY ALL ORDER BY 1
    """).df()
    df["mes"] = _mes(df.competencia)
    return df.drop(columns="competencia")


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


def memoria(con, ultimos: list[str]) -> dict:
    """Contagens de cada etapa do cruzamento, para a memória de cálculo."""
    comps = ",".join(f"'{m.replace('-', '')}'" for m in ultimos)
    por_especie = con.sql(f"""
        SELECT especie, count(*) AS n, count(*) FILTER (uf IS NULL) AS sem_uf,
               count(*) FILTER ({GRUPO_SQL} <> 'outros') AS mental
        FROM inss WHERE competencia IN ({comps}) GROUP BY ALL ORDER BY 1
    """).df()
    grupos = con.sql(f"""
        SELECT {GRUPO_SQL} AS grupo, count(*) AS n FROM inss
        WHERE competencia IN ({comps}) AND especie IN {LISTA(AFASTAMENTO)} AND uf IS NOT NULL
        GROUP BY ALL ORDER BY 2 DESC
    """).df()
    caged = con.sql(f"""
        SELECT CASE WHEN tipo_mov IN {LISTA(CAGED_SEM_JUSTA_CAUSA)} THEN 'sem_justa_causa'
                    WHEN tipo_mov IN {LISTA(CAGED_A_PEDIDO)} THEN 'a_pedido'
                    WHEN saldo < 0 THEN 'outros_desligamentos' ELSE 'admissoes' END AS tipo,
               sum(n) AS n
        FROM caged WHERE competencia IN ({comps}) GROUP BY ALL ORDER BY 2 DESC
    """).df()
    rais = con.sql("SELECT ano, sum(vinculos) AS vinculos FROM rais GROUP BY 1 ORDER BY 1").df()
    meses_inss = con.sql("SELECT DISTINCT competencia FROM inss ORDER BY 1").df().competencia.tolist()
    meses_caged = con.sql("SELECT DISTINCT competencia FROM caged ORDER BY 1").df().competencia.tolist()
    rec = lambda d: json.loads(d.to_json(orient="records", force_ascii=False))  # noqa: E731
    return {
        "meses": ultimos,
        "inss_por_especie": rec(por_especie),
        "inss_grupos_afastamento": rec(grupos),
        "caged_movimentos": rec(caged),
        "rais_vinculos": rec(rais),
        "meses_inss": [m[:4] + "-" + m[4:] for m in meses_inss],
        "meses_caged": [m[:4] + "-" + m[4:] for m in meses_caged],
    }


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
    _json("filiacao.json", filiacao(con))
    _json("bpc_autismo.json", bpc_autismo(con))
    _json("correlacao.json", correlacoes(s, ultimos))
    _json("memoria.json", memoria(con, ultimos))
    _json("meta.json", {
        "gerado_em": dt.datetime.now().isoformat(timespec="minutes"),
        "exemplo": exemplo,
        "periodo": {"inicio": meses[0], "fim": meses[-1]},
        "ultimos_12_meses": ultimos,
        "grupos_cid": [{"chave": c, "nome": n, "cids": list(p)} for c, n, p in GRUPOS_CID],
        "filiacoes": [{"chave": c, "nome": n} for c, n, _ in FILIACOES],
    })


if __name__ == "__main__":
    agregar()
