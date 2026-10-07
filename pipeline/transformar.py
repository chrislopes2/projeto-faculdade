"""Lê os arquivos brutos e grava tabelas limpas em Parquet (data/clean).

Os arquivos do INSS não têm um layout 100% estável (nomes de coluna e formato
dos valores mudam entre meses), então a leitura procura cada campo por palavra-chave
e normaliza os valores.
"""
import re
from pathlib import Path

import duckdb
import pandas as pd

from pipeline.config import CLEAN, RAW, UF_NOMES, UFS, secao_cnae
from pipeline.util import nome_coluna, sem_acento

RE_CID = re.compile(r"\b([A-Z])\s?(\d{2})\.?(\d)?")
SIGLAS = set(UFS.values())


# --- INSS ---------------------------------------------------------------------

def _ler_tabela(arq: Path) -> pd.DataFrame:
    if arq.suffix in (".xlsx", ".xls"):
        bruto = pd.read_excel(arq, header=None, nrows=20, dtype=str)
        linha = next(
            (i for i, r in bruto.iterrows()
             if any("esp" in nome_coluna(v) for v in r.dropna())), 0)
        df = pd.read_excel(arq, header=linha, dtype=str)
    else:
        for enc in ("utf-8", "latin-1"):
            try:
                df = pd.read_csv(arq, sep=None, engine="python", dtype=str, encoding=enc)
                break
            except UnicodeDecodeError:
                continue
    df.columns = [nome_coluna(c) for c in df.columns]
    return df


def _coluna(df: pd.DataFrame, *chaves: str, validar=None) -> str | None:
    for c in df.columns:
        if any(k in c for k in chaves):
            if validar is None or validar(df[c].dropna().head(200)):
                return c
    return None


def _especie(valor: str) -> int | None:
    if not isinstance(valor, str):
        return None
    m = re.match(r"\s*(\d{1,3})\b", valor)
    if m:
        return int(m.group(1))
    v = sem_acento(valor).lower()
    acid = "acident" in v
    if "doenca" in v or "temporaria" in v:
        return 91 if acid else 31
    if "invalidez" in v or "permanente" in v:
        return 92 if acid else 32
    if "deficien" in v or "assistencial" in v or "amparo" in v:
        return 87
    return None


def _cid(valor: str) -> str | None:
    if not isinstance(valor, str):
        return None
    m = RE_CID.search(valor.upper())
    return f"{m.group(1)}{m.group(2)}{m.group(3) or ''}" if m else None


def _uf(valor: str) -> str | None:
    if not isinstance(valor, str):
        return None
    v = sem_acento(valor).upper().strip()
    if v in SIGLAS:
        return v
    if v.isdigit() and int(v) in UFS:
        return UFS[int(v)]
    return UF_NOMES.get(v)


def _competencia(valor, padrao: str) -> str:
    if isinstance(valor, str):
        m = re.search(r"(20\d{2})[-/]?(0[1-9]|1[0-2])", valor)
        if m:
            return m.group(1) + m.group(2)
        m = re.search(r"(0[1-9]|1[0-2])/(20\d{2})", valor)
        if m:
            return m.group(2) + m.group(1)
    return padrao


def limpar_inss() -> pd.DataFrame:
    partes = []
    for arq in sorted((RAW / "inss").glob("concedidos_*")):
        padrao = re.search(r"(\d{6})", arq.name).group(1)
        df = _ler_tabela(arq)
        c_esp = _coluna(df, "especie")
        c_cid = _coluna(df, "cid", validar=lambda s: s.astype(str).str.contains(r"[A-Z]\d{2}").mean() > 0.5)
        c_uf = _coluna(df, "uf")
        c_comp = _coluna(df, "competencia")
        c_sexo = _coluna(df, "sexo")
        c_nasc = _coluna(df, "nasc")
        c_ramo = _coluna(df, "ramo")
        faltando = [n for n, c in (("espécie", c_esp), ("CID", c_cid), ("UF", c_uf)) if c is None]
        if faltando:
            print(f"  {arq.name}: colunas não encontradas {faltando}; colunas: {list(df.columns)}")
            continue
        limpo = pd.DataFrame({
            "competencia": df[c_comp].map(lambda v: _competencia(v, padrao)) if c_comp else padrao,
            "especie": df[c_esp].map(_especie),
            "cid": df[c_cid].map(_cid),
            "uf": df[c_uf].map(_uf),
            "sexo": df[c_sexo].str.strip().str[0].str.upper() if c_sexo else None,
            "nascimento": pd.to_datetime(df[c_nasc], errors="coerce", dayfirst=True) if c_nasc else pd.NaT,
            "ramo": df[c_ramo].map(lambda v: sem_acento(v).upper().strip() if isinstance(v, str) else None) if c_ramo else None,
        })
        ref = pd.to_datetime(limpo["competencia"] + "01", format="%Y%m%d")
        limpo["idade"] = ((ref - limpo["nascimento"]).dt.days // 365.25).astype("Int64")
        limpo = limpo.drop(columns="nascimento")
        print(f"  {arq.name}: {len(limpo):,} linhas")
        partes.append(limpo)
    if not partes:
        raise SystemExit("Nenhum arquivo do INSS em data/raw/inss")
    return pd.concat(partes, ignore_index=True)


# --- CAGED e RAIS -------------------------------------------------------------

def limpar_caged(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    arquivos = sorted((RAW / "caged").glob("CAGEDMOV*.txt"))
    if not arquivos:
        raise SystemExit("Nenhum arquivo do CAGED em data/raw/caged")
    # Os cabeçalhos do CAGED têm acento (competênciamov); normalizamos antes de usar.
    partes = []
    for arq in arquivos:
        cab = con.sql(f"SELECT * FROM read_csv('{arq}', delim=';', header=true, all_varchar=true) LIMIT 0")
        mapa = {c: nome_coluna(c).replace("_", "") for c in cab.columns}
        sel = ", ".join(f'"{c}" AS {mapa[c]}' for c in cab.columns)
        df = con.sql(f"""
            WITH t AS (SELECT {sel} FROM read_csv('{arq}', delim=';', header=true, all_varchar=true))
            SELECT competenciamov AS competencia, CAST(uf AS INT) AS uf_cod, secao,
                   CAST(tipomovimentacao AS INT) AS tipo_mov,
                   CAST(saldomovimentacao AS INT) AS saldo, count(*) AS n
            FROM t GROUP BY ALL
        """).df()
        print(f"  {arq.name}: {int(df.n.sum()):,} movimentações")
        partes.append(df)
    df = pd.concat(partes, ignore_index=True)
    df["uf"] = df.uf_cod.map(UFS)
    return df.drop(columns="uf_cod").dropna(subset=["uf"])


def limpar_rais() -> pd.DataFrame:
    arquivos = sorted((RAW / "rais").glob("rais_estoque_*.csv"))
    if not arquivos:
        raise SystemExit("Nenhum resumo da RAIS em data/raw/rais")
    df = pd.concat(pd.read_csv(a) for a in arquivos)
    df["uf"] = df.uf_cod.map(UFS)
    df["secao"] = df.divisao.map(secao_cnae)
    return df.dropna(subset=["uf"]).groupby(["ano", "uf", "secao"], as_index=False)["vinculos"].sum()


def transformar() -> None:
    CLEAN.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    print("INSS")
    limpar_inss().to_parquet(CLEAN / "inss.parquet", index=False)
    print("CAGED")
    limpar_caged(con).to_parquet(CLEAN / "caged.parquet", index=False)
    print("RAIS")
    limpar_rais().to_parquet(CLEAN / "rais.parquet", index=False)


if __name__ == "__main__":
    transformar()
