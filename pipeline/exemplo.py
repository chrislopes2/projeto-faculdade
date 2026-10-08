"""Gera dados FICTÍCIOS no mesmo formato dos arquivos brutos reais.

Serve para testar o pipeline e o site sem baixar nada. Os números seguem ordens de
grandeza plausíveis, em escala reduzida (1:50), mas não são dados reais.
"""
import numpy as np
import pandas as pd

from pipeline.config import RAW, UFS

ESCALA = 50
rng = np.random.default_rng(42)

# Peso aproximado de cada UF no emprego formal (soma 1)
PESO_UF = {"SP": .29, "MG": .10, "RJ": .08, "PR": .065, "RS": .06, "SC": .05, "BA": .045,
           "GO": .033, "PE": .033, "CE": .028, "DF": .025, "PA": .022, "ES": .019, "MT": .018,
           "AM": .014, "MS": .013, "MA": .012, "RN": .01, "PB": .01, "AL": .008, "PI": .008,
           "SE": .006, "RO": .006, "TO": .005, "AP": .002, "AC": .002, "RR": .002}
COD_UF = {v: k for k, v in UFS.items()}
SECOES = list("ABCDEFGHIJKLMNOPQRS")
PESO_SEC = np.array([3, .5, 15, .3, 1, 5, 20, 5, 4, 2, 2, 1, 4, 10, 8, 4, 5, 1, 3], float)
PESO_SEC /= PESO_SEC.sum()
DIV_SEC = {"A": 1, "B": 5, "C": 10, "D": 35, "E": 36, "F": 41, "G": 47, "H": 49, "I": 56, "J": 62,
           "K": 64, "L": 68, "M": 69, "N": 78, "O": 84, "P": 85, "Q": 86, "R": 90, "S": 94}
RAMO_SEC = {"A": "Rural", "B": "Industriário", "C": "Industriário", "D": "Industriário", "E": "Industriário",
            "F": "Industriário", "G": "Comerciário", "H": "Transportes e Cargas", "K": "Bancário"}
CIDS = [("F32.9", .20), ("F33.2", .07), ("F41.1", .17), ("F41.2", .12), ("F43.1", .08), ("F43.2", .07),
        ("Z73.0", .02), ("F84.0", .01), ("F31.1", .08), ("F20.0", .05), ("F10.2", .13)]
OUTROS_CIDS = ["M54.5", "S82.0", "M51.1", "S52.5", "I10", "C50.9", "O20.0", "K80.2", "M75.1", "J18.9"]
ESPECIES = {31: "Auxílio por Incapacidade Temporária Previdenciário",
            91: "Auxílio por Incapacidade Temporária Acidentário",
            87: "Amparo Social Pessoa Portadora Deficiência"}

MESES = pd.period_range("2023-06", "2026-08", freq="M")
VINCULOS_BR = 47_000_000
# Efeito de cada UF (fictício): UFs com mais demissão têm um pouco mais de afastamento
EFEITO_UF = {uf: rng.normal(0, .15) for uf in PESO_UF}


def gerar_rais() -> None:
    pasta = RAW / "rais"
    pasta.mkdir(parents=True, exist_ok=True)
    for ano, fator in ((2023, 1.0), (2024, 1.03)):
        linhas = []
        for uf, p in PESO_UF.items():
            for sec, ps in zip(SECOES, PESO_SEC):
                linhas.append((ano, COD_UF[uf], DIV_SEC[sec], int(VINCULOS_BR * fator * p * ps / ESCALA)))
        pd.DataFrame(linhas, columns=["ano", "uf_cod", "divisao", "vinculos"]).to_csv(
            pasta / f"rais_estoque_{ano}.csv", index=False)


def gerar_caged() -> None:
    pasta = RAW / "caged"
    pasta.mkdir(parents=True, exist_ok=True)
    for i, per in enumerate(MESES):
        sazonal = 1 + .08 * np.sin((per.month - 3) / 12 * 2 * np.pi)
        n_desl = int(VINCULOS_BR * .043 * sazonal * (1 + .002 * i) / ESCALA)
        ufs = rng.choice(list(PESO_UF), n_desl, p=np.array(list(PESO_UF.values())) / sum(PESO_UF.values()))
        efeito = np.array([EFEITO_UF[u] for u in ufs])
        p_sjc = np.clip(.40 + .25 * efeito, .1, .8)
        sorteio = rng.random(n_desl)
        tipo = np.where(sorteio < p_sjc, 31, np.where(sorteio < p_sjc + .33, 40, 43))
        desl = pd.DataFrame({"tipomovimentação": tipo, "saldomovimentação": -1})
        adm = pd.DataFrame({"tipomovimentação": rng.choice([10, 20], int(n_desl * 1.04)), "saldomovimentação": 1})
        df = pd.concat([desl.assign(uf=ufs), adm.assign(uf=rng.choice(ufs, len(adm)))])
        df.insert(0, "competênciamov", per.strftime("%Y%m"))
        df["uf"] = df.uf.map(COD_UF)
        df["seção"] = rng.choice(SECOES, len(df), p=PESO_SEC)
        df["sexo"] = rng.choice([1, 3], len(df))
        df["idade"] = rng.integers(18, 65, len(df))
        df[["competênciamov", "uf", "seção", "saldomovimentação", "tipomovimentação", "sexo", "idade"]].to_csv(
            pasta / f"CAGEDMOV{per.strftime('%Y%m')}.txt", sep=";", index=False)


def gerar_inss() -> None:
    pasta = RAW / "inss"
    pasta.mkdir(parents=True, exist_ok=True)
    nomes_uf = {v: k for k, v in __import__("pipeline.config", fromlist=["UF_NOMES"]).UF_NOMES.items()}
    for i, per in enumerate(MESES):
        crescimento = 1 + .018 * i  # tendência de alta ao longo do período
        n_mental = int(39_000 * crescimento / ESCALA)
        n_outros = int(250_000 / ESCALA)
        ufs_m = rng.choice(list(PESO_UF), n_mental, p=np.array(list(PESO_UF.values())) / sum(PESO_UF.values()))
        manter = rng.random(n_mental) < np.clip(.85 + .6 * np.array([EFEITO_UF[u] for u in ufs_m]), .3, 1.4) / 1.4
        ufs_m = ufs_m[manter]
        cid_m = rng.choice([c for c, _ in CIDS], len(ufs_m), p=np.array([p for _, p in CIDS]) / sum(p for _, p in CIDS))
        ufs_o = rng.choice(list(PESO_UF), n_outros, p=np.array(list(PESO_UF.values())) / sum(PESO_UF.values()))
        cid_o = rng.choice(OUTROS_CIDS, n_outros)
        ufs = np.concatenate([ufs_m, ufs_o])
        cid = np.concatenate([cid_m, cid_o])
        esp = np.where(rng.random(len(ufs)) < .04, 91, 31)
        n_bpc = int(9_000 / ESCALA)
        ufs = np.concatenate([ufs, rng.choice(list(PESO_UF), n_bpc)])
        cid = np.concatenate([cid, rng.choice(["F84.0", "F84.1", "F70", "G80.9", "Q90.9"], n_bpc, p=[.35, .1, .25, .15, .15])])
        esp = np.concatenate([esp, np.full(n_bpc, 87)])
        idade = np.clip(rng.normal(41, 11, len(ufs)), 18, 75).astype(int)
        nasc = [pd.Timestamp(per.year - a, rng.integers(1, 13), rng.integers(1, 28)) for a in idade]
        sec = rng.choice(SECOES, len(ufs), p=PESO_SEC)
        df = pd.DataFrame({
            "Competência concessão": per.strftime("%Y%m"),
            "Espécie": [f"{e} - {ESPECIES[e]}" for e in esp],
            "CID": cid,
            "Despacho": "Concessão Normal",
            "Dt Nascimento": [d.strftime("%d/%m/%Y") for d in nasc],
            "Sexo": rng.choice(["Masculino", "Feminino"], len(ufs), p=[.38, .62]),
            "Clientela": "Urbano",
            "UF": [nomes_uf[u].title() if rng.random() < .5 else u for u in ufs],
            "Ramo Atividade": [RAMO_SEC.get(s, "Outros") for s in sec],
            "Forma Filiação": rng.choice(["Empregado", "Desempregado", "Autônomo", "Segurado Especial"], len(ufs), p=[.55, .2, .17, .08]),
            "Mun Resid": [f"00000-{u}-Exemplo" for u in ufs],
        })
        df.to_csv(pasta / f"concedidos_{per.strftime('%Y%m')}.csv", sep=";", index=False, encoding="utf-8")


def gerar() -> None:
    print("Gerando dados de exemplo (fictícios)")
    gerar_rais()
    gerar_caged()
    gerar_inss()


if __name__ == "__main__":
    gerar()
