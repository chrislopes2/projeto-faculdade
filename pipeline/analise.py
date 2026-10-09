"""Análises estatísticas e de aprendizado de máquina sobre os JSON já agregados.

Lê site/public/data (serie.json etc.) e grava analise.json. Não precisa das bases brutas,
então dá para rodar de novo só com os JSON:  python -m pipeline.analise

1. Regressão com defasagem (statsmodels): a taxa de demissão de k meses antes explica a de afastamento?
2. Causalidade de Granger (statsmodels): demissões ajudam a prever afastamentos além do próprio passado?
3. Painel com efeitos fixos (statsmodels): dentro de cada estado, meses com mais demissões têm mais afastamentos?
4. Random Forest (scikit-learn): quanto as variáveis do mercado de trabalho ajudam a prever a taxa de cada estado.
5. Agrupamento K-means (scikit-learn): perfis de estados parecidos.
6. Previsão Holt-Winters (statsmodels): próximos 6 meses de afastamentos por saúde mental no Brasil.
7. Isolation Forest (scikit-learn): meses e estados fora do padrão.
"""
import json
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error, r2_score, silhouette_score
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.stattools import grangercausalitytests

from pipeline.config import SAIDA

warnings.filterwarnings("ignore")
SEMENTE = 42
POR = 1e5


def _f(x, casas=4):
    """Número JSON-safe (None no lugar de NaN/inf)."""
    if x is None:
        return None
    x = float(x)
    return None if not np.isfinite(x) else round(x, casas)


def _ler(nome: str):
    return json.loads((SAIDA / nome).read_text(encoding="utf-8"))


def _mensal(df: pd.DataFrame) -> pd.DataFrame:
    """Reindexa por mês do calendário, deixando buracos como NaN (as defasagens contam meses de verdade)."""
    df = df.copy()
    df["data"] = pd.PeriodIndex(df.mes, freq="M")
    idx = pd.period_range(df.data.min(), df.data.max(), freq="M")
    return df.set_index("data").reindex(idx)


def preparar(serie: list[dict]) -> pd.DataFrame:
    s = pd.DataFrame(serie)
    num = s.columns.difference(["uf", "mes"])
    s[num] = s[num].astype(float)
    s = s[s.vinculos > 0]
    s["ta"] = s.afast_mental / s.vinculos * POR      # afastamentos por saúde mental / 100 mil vínculos
    s["td"] = s.demissoes_sjc / s.vinculos * POR     # demissões sem justa causa / 100 mil vínculos
    s["tp"] = s.pedidos / s.vinculos * POR           # pedidos de demissão / 100 mil
    s["tadm"] = s.admissoes / s.vinculos * POR       # admissões / 100 mil
    s["part"] = s.afast_mental / s.afast_total       # parte dos afastamentos que é saúde mental
    return s


# 1 ------------------------------------------------------------------------------
def regressao_defasada(br: pd.DataFrame) -> dict:
    """ta_t = a + b·td_(t-k) + c·tendência, para k = 0..6. Erros robustos (HAC, Newey-West)."""
    m = _mensal(br)
    m["t"] = np.arange(len(m))
    linhas = []
    for k in range(0, 7):
        d = pd.DataFrame({"ta": m.ta, "td": m.td.shift(k), "t": m.t}).dropna()
        if len(d) < 12:
            continue
        X = sm.add_constant(d[["td", "t"]])
        r = sm.OLS(d.ta, X).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
        linhas.append({
            "defasagem_meses": k, "coef": _f(r.params.td), "p_valor": _f(r.pvalues.td),
            "ic95": [_f(v) for v in r.conf_int().loc["td"]], "r2": _f(r.rsquared), "n": int(r.nobs),
            # elasticidade no ponto médio: +1% na taxa de demissão → +e% na de afastamento
            "elasticidade": _f(r.params.td * d.td.mean() / d.ta.mean()),
        })
    melhor = min(linhas, key=lambda x: x["p_valor"] if x["p_valor"] is not None else 1) if linhas else None
    return {"modelos": linhas, "melhor": melhor,
            "formula": "taxa_afastamento(t) = a + b × taxa_demissao(t−k) + c × t"}


# 2 ------------------------------------------------------------------------------
def granger(br: pd.DataFrame, maxlag: int = 6) -> dict:
    """Testa nas primeiras diferenças (séries estacionárias). H0: X não ajuda a prever Y."""
    m = _mensal(br)[["ta", "td"]].interpolate(limit=1).diff().dropna()
    maxlag = min(maxlag, max(1, len(m) // 5))
    out = {}
    for nome, cols in {"demissao_para_afastamento": ["ta", "td"], "afastamento_para_demissao": ["td", "ta"]}.items():
        try:
            res = grangercausalitytests(m[cols], maxlag=maxlag)
            out[nome] = [{"defasagem_meses": int(k), "p_valor": _f(v[0]["ssr_ftest"][1]), "f": _f(v[0]["ssr_ftest"][0])}
                         for k, v in res.items()]
        except Exception as e:  # série curta demais
            out[nome] = {"erro": str(e)}
    return {"testes": out, "n_meses": int(len(m))}


# 3 ------------------------------------------------------------------------------
def painel(ufs: pd.DataFrame) -> dict:
    """ta_(uf,t) = b·td_(uf,t) + efeito do estado + efeito do mês. Erros agrupados por estado."""
    d = ufs.dropna(subset=["ta", "td"]).copy()
    out = {}
    for nome, formula in {"sem_controles": "ta ~ td",
                          "efeitos_fixos": "ta ~ td + C(uf) + C(mes)",
                          "efeitos_fixos_com_admissoes": "ta ~ td + tadm + C(uf) + C(mes)"}.items():
        r = smf.ols(formula, data=d).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d.uf)[0]})
        out[nome] = {"coef_td": _f(r.params.td), "p_valor": _f(r.pvalues.td),
                     "ic95": [_f(v) for v in r.conf_int().loc["td"]], "r2": _f(r.rsquared), "n": int(r.nobs)}
    out["n_ufs"] = int(d.uf.nunique())
    out["n_meses"] = int(d.mes.nunique())
    return out


# 4 ------------------------------------------------------------------------------
VARS_RF = {
    "td": "Taxa de demissão sem justa causa (mesmo mês)",
    "td_l1": "Taxa de demissão (1 mês antes)",
    "td_l3": "Taxa de demissão (3 meses antes)",
    "td_l6": "Taxa de demissão (6 meses antes)",
    "tp": "Taxa de pedidos de demissão",
    "tadm": "Taxa de admissão",
    "ta_l12": "Afastamentos do mesmo mês um ano antes",
    "mes_ano": "Mês do ano (sazonalidade)",
}


def floresta(ufs: pd.DataFrame, meses_teste: int = 6) -> dict:
    """Treina com os meses mais antigos e testa nos últimos (validação temporal, sem olhar o futuro)."""
    partes = []
    for uf, g in ufs.groupby("uf"):
        m = _mensal(g)
        m["uf"] = uf
        for k in (1, 3, 6):
            m[f"td_l{k}"] = m.td.shift(k)
        m["ta_l12"] = m.ta.shift(12)
        m["mes_ano"] = m.index.month
        m["mes"] = m.index.astype(str)
        partes.append(m)
    d = pd.concat(partes).dropna(subset=["ta", "td", "td_l1", "td_l3", "td_l6", "tp", "tadm"])
    usa_l12 = d.ta_l12.notna().mean() > 0.6
    cols = [c for c in VARS_RF if c != "ta_l12" or usa_l12]
    d = d.dropna(subset=cols)
    meses = sorted(d.mes.unique())
    if len(meses) < meses_teste + 6:
        return {"erro": "série curta demais para treinar e testar"}
    corte = meses[-meses_teste]
    tr, te = d[d.mes < corte], d[d.mes >= corte]
    X_tr = pd.get_dummies(tr[cols + ["uf"]], columns=["uf"], dtype=float)
    X_te = pd.get_dummies(te[cols + ["uf"]], columns=["uf"], dtype=float).reindex(columns=X_tr.columns, fill_value=0)
    rf = RandomForestRegressor(n_estimators=400, min_samples_leaf=3, random_state=SEMENTE, n_jobs=-1)
    rf.fit(X_tr, tr.ta)
    prev = rf.predict(X_te)
    # Linha de base: a média de cada estado no treino (o "chute" mais simples).
    base = te.uf.map(tr.groupby("uf").ta.mean()).fillna(tr.ta.mean())
    # Sem as variáveis do mercado de trabalho: só estado, mês do ano e (se houver) o ano anterior.
    so_cols = [c for c in X_tr.columns if not c.startswith(("td", "tp", "tadm"))]
    rf2 = RandomForestRegressor(n_estimators=400, min_samples_leaf=3, random_state=SEMENTE, n_jobs=-1)
    rf2.fit(X_tr[so_cols], tr.ta)
    prev2 = rf2.predict(X_te[so_cols])
    imp = permutation_importance(rf, X_te, te.ta, n_repeats=20, random_state=SEMENTE, n_jobs=-1)
    imp = pd.Series(imp.importances_mean, index=X_te.columns)
    imp_uf = imp[imp.index.str.startswith("uf_")].sum()
    imp = imp[~imp.index.str.startswith("uf_")]
    imp["uf"] = imp_uf
    nomes = {**VARS_RF, "uf": "Estado (nível típico de cada UF)"}
    importancias = [{"variavel": k, "nome": nomes[k], "importancia": _f(v)} for k, v in imp.sort_values(ascending=False).items()]
    return {
        "treino": {"de": meses[0], "ate": max(tr.mes), "linhas": int(len(tr))},
        "teste": {"de": corte, "ate": meses[-1], "linhas": int(len(te))},
        "r2": _f(r2_score(te.ta, prev)), "mae": _f(mean_absolute_error(te.ta, prev), 2),
        "r2_sem_mercado": _f(r2_score(te.ta, prev2)), "mae_sem_mercado": _f(mean_absolute_error(te.ta, prev2), 2),
        "r2_base": _f(r2_score(te.ta, base)), "mae_base": _f(mean_absolute_error(te.ta, base), 2),
        "media_taxa_teste": _f(te.ta.mean(), 2),
        "importancias": importancias,
    }


# 5 ------------------------------------------------------------------------------
def agrupamento(ufs: pd.DataFrame, ultimos: list[str]) -> dict:
    u = ufs[ufs.mes.isin(ultimos)].groupby("uf")[["afast_mental", "afast_total", "demissoes_sjc", "admissoes", "vinculos"]].sum()
    ant = ufs[ufs.mes < min(ultimos)].sort_values("mes").groupby("uf").tail(12).groupby("uf").afast_mental.sum()
    f = pd.DataFrame({
        "taxa_afastamento": u.afast_mental / u.vinculos * POR,
        "taxa_demissao": u.demissoes_sjc / u.vinculos * POR,
        "parte_mental": u.afast_mental / u.afast_total * 100,
        "crescimento": (u.afast_mental / ant - 1) * 100,
    }).replace([np.inf, -np.inf], np.nan).dropna()
    X = StandardScaler().fit_transform(f)
    melhor, notas = None, []
    for k in range(2, min(6, len(f) - 1)):
        km = KMeans(n_clusters=k, n_init=20, random_state=SEMENTE).fit(X)
        sil = silhouette_score(X, km.labels_)
        notas.append({"k": k, "silhueta": _f(sil)})
        if melhor is None or sil > melhor[1]:
            melhor = (km, sil, k)
    km, sil, k = melhor
    f["grupo"] = km.labels_
    media = f.drop(columns="grupo").mean()
    grupos = []
    for g, sub in f.groupby("grupo"):
        c = sub.drop(columns="grupo").mean()
        desc = []
        for col, nome in (("taxa_afastamento", "afastamento"), ("taxa_demissao", "demissão")):
            rel = c[col] / media[col]
            desc.append(f"{nome} {'alto' if rel > 1.1 else 'baixo' if rel < 0.9 else 'médio'}")
        grupos.append({
            "grupo": int(g), "descricao": ", ".join(desc), "ufs": sorted(sub.index.tolist()),
            "media": {kk: _f(v, 2) for kk, v in c.items()},
        })
    grupos.sort(key=lambda x: -x["media"]["taxa_afastamento"])
    for i, g in enumerate(grupos):
        g["nome"] = f"Grupo {chr(65 + i)}"
    return {
        "k": int(k), "silhueta": _f(sil), "testados": notas, "variaveis": list(f.columns.drop("grupo")),
        "grupos": grupos,
        "ufs": [{"uf": uf, **{kk: _f(v, 2) for kk, v in r.drop("grupo").items()},
                 "grupo": next(g["nome"] for g in grupos if uf in g["ufs"])} for uf, r in f.iterrows()],
    }


# 6 ------------------------------------------------------------------------------
def previsao(br: pd.DataFrame, passos: int = 6) -> dict:
    m = _mensal(br)
    y = m.afast_mental
    faltando = [str(p) for p in y[y.isna()].index]
    y = y.interpolate(limit_direction="both")
    sazonal = len(y) >= 24
    mod = ExponentialSmoothing(y.values, trend="add", damped_trend=True,
                               seasonal="add" if sazonal else None, seasonal_periods=12 if sazonal else None,
                               initialization_method="estimated").fit()
    prev = mod.forecast(passos)
    # Intervalo de 80% por simulação dos resíduos (bootstrap).
    sim = mod.simulate(passos, repetitions=2000, error="add", anchor="end", random_state=SEMENTE)
    lo, hi = np.percentile(sim, [10, 90], axis=1)
    futuro = pd.period_range(y.index[-1] + 1, periods=passos, freq="M")
    # Erro fora da amostra: ajusta sem os últimos 6 meses e compara.
    teste = None
    if len(y) >= 30:
        m2 = ExponentialSmoothing(y.values[:-passos], trend="add", damped_trend=True,
                                  seasonal="add" if len(y) - passos >= 24 else None,
                                  seasonal_periods=12 if len(y) - passos >= 24 else None,
                                  initialization_method="estimated").fit()
        p2 = m2.forecast(passos)
        teste = {"mape": _f(np.mean(np.abs(p2 - y.values[-passos:]) / y.values[-passos:]) * 100, 2)}
    return {
        "modelo": "Holt-Winters aditivo com tendência amortecida" + (" e sazonalidade de 12 meses" if sazonal else ""),
        "historico": [{"mes": str(p), "valor": _f(v, 0)} for p, v in y.items()],
        "meses_interpolados": faltando,
        "previsao": [{"mes": str(p), "valor": _f(v, 0), "min80": _f(a, 0), "max80": _f(b, 0)}
                     for p, v, a, b in zip(futuro, prev, lo, hi)],
        "validacao": teste,
    }


# 7 ------------------------------------------------------------------------------
def anomalias(ufs: pd.DataFrame, n: int = 10) -> dict:
    """Desvio de cada mês em relação ao padrão do próprio estado (z-score), e Isolation Forest sobre isso."""
    d = ufs.dropna(subset=["ta", "td"]).copy()
    for c in ("ta", "td"):
        d[f"z_{c}"] = d.groupby("uf")[c].transform(lambda x: (x - x.mean()) / (x.std() or 1))
    iso = IsolationForest(n_estimators=300, contamination=0.02, random_state=SEMENTE).fit(d[["z_ta", "z_td"]])
    d["score"] = -iso.score_samples(d[["z_ta", "z_td"]])
    d["anomalo"] = iso.predict(d[["z_ta", "z_td"]]) == -1
    top = d.sort_values("score", ascending=False).head(n)
    return {
        "total_anomalos": int(d.anomalo.sum()), "n": int(len(d)),
        "lista": [{"uf": r.uf, "mes": r.mes, "taxa_afastamento": _f(r.ta, 2), "taxa_demissao": _f(r.td, 2),
                   "z_afastamento": _f(r.z_ta, 2), "z_demissao": _f(r.z_td, 2)} for r in top.itertuples()],
    }


def memoria_kpis(br: pd.DataFrame, ultimos: list[str]) -> dict:
    """Refaz, passo a passo, a conta dos indicadores da página inicial (Brasil, últimos 12 meses)."""
    ok = br.dropna(subset=["afast_mental", "demissoes_sjc", "vinculos"]).sort_values("mes")
    ult = ok[ok.mes.isin(ultimos)]
    ant = ok[ok.mes < min(ultimos)].tail(12)
    soma = lambda df, c: float(df[c].sum())  # noqa: E731
    a12, aant, at12 = soma(ult, "afast_mental"), soma(ant, "afast_mental"), soma(ult, "afast_total")
    d12, v12 = soma(ult, "demissoes_sjc"), soma(ult, "vinculos")
    return {
        "meses": ultimos, "meses_anteriores": ant.mes.tolist(),
        "afast_mental_12m": a12, "afast_mental_12m_anteriores": aant,
        "variacao_pct": _f((a12 / aant - 1) * 100, 2) if aant else None,
        "afast_total_12m": at12, "parte_mental_pct": _f(a12 / at12 * 100, 2),
        "vinculos_soma_12m": v12, "vinculos_medio": _f(v12 / len(ult), 0),
        "taxa_afast_mes": _f(a12 / v12 * POR, 2),
        "demissoes_12m": d12, "taxa_demissao_mes": _f(d12 / v12 * POR, 2),
        "por_mes": [{"mes": r.mes, "afast_mental": _f(r.afast_mental, 0), "afast_total": _f(r.afast_total, 0),
                     "demissoes_sjc": _f(r.demissoes_sjc, 0), "vinculos": _f(r.vinculos, 0),
                     "taxa_afast": _f(r.ta, 2), "taxa_demissao": _f(r.td, 2)} for r in ult.itertuples()],
    }


def analisar() -> dict:
    meta = _ler("meta.json")
    s = preparar(_ler("serie.json"))
    br = s[s.uf == "BR"].dropna(subset=["ta", "td"]).sort_values("mes")
    ufs = s[s.uf != "BR"]
    ultimos = meta["ultimos_12_meses"]
    etapas = {
        "kpis": lambda: memoria_kpis(s[s.uf == "BR"], ultimos),
        "regressao": lambda: regressao_defasada(br),
        "granger": lambda: granger(br),
        "painel": lambda: painel(ufs),
        "floresta": lambda: floresta(ufs),
        "agrupamento": lambda: agrupamento(ufs, ultimos),
        "previsao": lambda: previsao(br),
        "anomalias": lambda: anomalias(ufs),
    }
    out = {"exemplo": meta["exemplo"], "gerado_em": meta["gerado_em"]}
    for nome, f in etapas.items():
        try:
            out[nome] = f()
            print(f"  análise: {nome}")
        except Exception as e:  # uma análise que falha não derruba as outras
            out[nome] = {"erro": f"{type(e).__name__}: {e}"}
            print(f"  análise: {nome} FALHOU ({e})")
    from pipeline.textos import interpretar
    out["textos"] = interpretar(out)
    (SAIDA / "analise.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return out


if __name__ == "__main__":
    analisar()
