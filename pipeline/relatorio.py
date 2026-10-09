"""Gera o relatório acadêmico em PDF a partir dos JSON do site (site/public/relatorio.pdf).

    python -m pipeline.relatorio

Os textos de resultado são montados a partir dos números, então o relatório se atualiza sozinho a cada carga.
"""
import io
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,  # noqa: E402
                                Spacer, Table, TableStyle)

from pipeline.config import ESPECIES, SAIDA  # noqa: E402
from pipeline.textos import (br, mes, pval, txt_agrupamento, txt_floresta, txt_granger,  # noqa: E402
                             txt_painel, txt_previsao, txt_regressao)

DESTINO = SAIDA.parent / "relatorio.pdf"
AUTOR = "Cristhofer Maciel"
SITE = "https://chrislopes2.github.io/projeto-faculdade/"
REPO = "https://github.com/chrislopes2/projeto-faculdade"

COR = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
TEXTO, TEXTO2, GRADE = "#0b0b0b", "#52514e", "#e1e0d9"

# --- Fontes (DejaVu vem junto com o matplotlib, então funciona em qualquer máquina) ---------------
_TTF = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
pdfmetrics.registerFont(TTFont("DV", str(_TTF / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DV-B", str(_TTF / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DV-I", str(_TTF / "DejaVuSans-Oblique.ttf")))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV-I", boldItalic="DV-B")

E = {
    "corpo": ParagraphStyle("corpo", fontName="DV", fontSize=9.6, leading=14, alignment=TA_JUSTIFY, spaceAfter=6),
    "h1": ParagraphStyle("h1", fontName="DV-B", fontSize=15, leading=19, spaceBefore=6, spaceAfter=10),
    "h2": ParagraphStyle("h2", fontName="DV-B", fontSize=11.5, leading=15, spaceBefore=10, spaceAfter=5),
    "legenda": ParagraphStyle("legenda", fontName="DV", fontSize=8, leading=11, textColor=colors.HexColor(TEXTO2), spaceAfter=10),
    "formula": ParagraphStyle("formula", fontName="DV", fontSize=9.4, leading=14, leftIndent=18, spaceAfter=6,
                              backColor=colors.HexColor("#f4f3ef"), borderPadding=5),
    "item": ParagraphStyle("item", fontName="DV", fontSize=9.6, leading=14, leftIndent=14, bulletIndent=4, spaceAfter=3),
    "capa_t": ParagraphStyle("capa_t", fontName="DV-B", fontSize=22, leading=28, alignment=TA_CENTER),
    "capa_s": ParagraphStyle("capa_s", fontName="DV", fontSize=12, leading=17, alignment=TA_CENTER, textColor=colors.HexColor(TEXTO2)),
    "cel": ParagraphStyle("cel", fontName="DV", fontSize=8, leading=10),
    "celb": ParagraphStyle("celb", fontName="DV-B", fontSize=8, leading=10),
}


def P(txt, estilo="corpo"):
    return Paragraph(txt, E[estilo])


def itens(lista):
    return [Paragraph(t, E["item"], bulletText="•") for t in lista]


def tabela(linhas, larguras, cabecalho=True, alinhar_dir=()):
    dados = [[Paragraph(str(c), E["celb" if (i == 0 and cabecalho) else "cel"]) for c in lin] for i, lin in enumerate(linhas)]
    t = Table(dados, colWidths=[w * cm for w in larguras], repeatRows=1 if cabecalho else 0)
    estilo = [
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.HexColor(TEXTO)),
        ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor(GRADE)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    t.setStyle(TableStyle(estilo))
    return t


# --- Gráficos ----------------------------------------------------------------------------------
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8.5, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": TEXTO2,
    "xtick.color": TEXTO2, "ytick.color": TEXTO2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRADE, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "legend.frameon": False, "figure.dpi": 200,
})


def fig_img(fig, largura_cm=16):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    w, h = fig.get_size_inches()
    return Image(buf, width=largura_cm * cm, height=largura_cm * cm * h / w)


def _eixo_meses(ax, meses, passo=3):
    ax.set_xticks(range(0, len(meses), passo))
    ax.set_xticklabels([mes(m) for m in meses[::passo]], rotation=0)


def graf_indices(br_):
    ta = br_.ta.values
    td = br_.td.values
    ia, idm = ta / ta[:3].mean() * 100, td / td[:3].mean() * 100
    fig, ax = plt.subplots(figsize=(8, 3.2))
    x = range(len(br_))
    ax.plot(x, ia, color=COR[0], lw=2, label="Afastamentos por saúde mental")
    ax.plot(x, idm, color=COR[1], lw=2, label="Demissões sem justa causa")
    ax.axhline(100, color="#898781", lw=0.8, ls=":")
    _eixo_meses(ax, br_.mes.tolist())
    ax.legend(loc="upper left", ncol=2)
    return fig_img(fig)


def graf_grupos(br_, grupos):
    fig, ax = plt.subplots(figsize=(8, 3.2))
    x = range(len(br_))
    for i, g in enumerate(grupos):
        ax.plot(x, br_[g["chave"]].values, color=COR[i], lw=1.8, label=g["nome"])
    _eixo_meses(ax, br_.mes.tolist())
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: br(v)))
    ax.legend(loc="upper left", ncol=3)
    return fig_img(fig)


def graf_dispersao(ag):
    d = pd.DataFrame(ag["ufs"])
    nomes = [g["nome"] for g in ag["grupos"]]
    fig, ax = plt.subplots(figsize=(8, 4))
    for i, n in enumerate(nomes):
        s = d[d.grupo == n]
        ax.scatter(s.taxa_demissao, s.taxa_afastamento, s=36, color=COR[i], label=n, zorder=3)
    for r in d.itertuples():
        ax.annotate(r.uf, (r.taxa_demissao, r.taxa_afastamento), xytext=(3, 3), textcoords="offset points", fontsize=7, color=TEXTO2)
    ax.set_xlabel("Demissões sem justa causa por 100 mil vínculos, por mês")
    ax.set_ylabel("Afastamentos por saúde mental\npor 100 mil vínculos, por mês")
    ax.legend(loc="best")
    return fig_img(fig)


def graf_defasagens(reg):
    d = pd.DataFrame(reg["modelos"])
    fig, ax = plt.subplots(figsize=(8, 2.8))
    lo = d.coef - d.ic95.str[0]
    hi = d.ic95.str[1] - d.coef
    cores = [COR[0] if p < 0.05 else "#c3c2b7" for p in d.p_valor]
    ax.bar(d.defasagem_meses, d.coef * 100, color=cores, width=0.6, zorder=3)
    ax.errorbar(d.defasagem_meses, d.coef * 100, yerr=[lo * 100, hi * 100], fmt="none", ecolor=TEXTO2, lw=1, capsize=3, zorder=4)
    ax.axhline(0, color=TEXTO2, lw=0.8)
    ax.set_xlabel("Defasagem (meses entre a demissão e o afastamento)")
    ax.set_ylabel("Afastamentos a mais\npor 100 demissões a mais")
    return fig_img(fig)


def graf_importancias(rf):
    d = pd.DataFrame(rf["importancias"]).sort_values("importancia")
    fig, ax = plt.subplots(figsize=(8, 0.35 * len(d) + 0.8))
    ax.barh(d.nome, d.importancia, color=COR[0], height=0.6, zorder=3)
    ax.axvline(0, color=TEXTO2, lw=0.8)
    ax.set_xlabel("Queda no R² quando a variável é embaralhada")
    ax.grid(axis="y", visible=False)
    return fig_img(fig)


def graf_previsao(pv):
    h = pd.DataFrame(pv["historico"])
    f = pd.DataFrame(pv["previsao"])
    todos = h.mes.tolist() + f.mes.tolist()
    fig, ax = plt.subplots(figsize=(8, 3.2))
    xh = np.arange(len(h))
    xf = np.arange(len(h) - 1, len(todos))
    ax.plot(xh, h.valor, color=COR[0], lw=2, label="Observado")
    ultimo = h.valor.iloc[-1]
    ax.fill_between(xf, [ultimo] + f.min80.tolist(), [ultimo] + f.max80.tolist(), color=COR[0], alpha=0.15, lw=0, label="Faixa de 80%")
    ax.plot(xf, [ultimo] + f.valor.tolist(), color=COR[0], lw=2, ls="--", label="Previsão")
    for m in pv["meses_interpolados"]:
        if m in h.mes.values:
            i = h.mes.tolist().index(m)
            ax.plot(i, h.valor[i], "o", color=COR[1], ms=4, zorder=4)
    _eixo_meses(ax, todos, passo=6)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: br(v)))
    ax.legend(loc="upper left", ncol=3)
    return fig_img(fig)


def graf_filiacao(fil, filiacoes):
    d = pd.DataFrame(fil).sort_values("mes")
    fig, ax = plt.subplots(figsize=(8, 3))
    x = range(len(d))
    for i, f in enumerate(filiacoes):
        ax.plot(x, d[f["chave"]], color=COR[i], lw=1.8, label=f["nome"])
    _eixo_meses(ax, d.mes.tolist())
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: br(v)))
    ax.legend(loc="upper left", ncol=4)
    return fig_img(fig)


# --- Documento ---------------------------------------------------------------------------------
def _rodape(c, doc):
    c.saveState()
    c.setFont("DV", 7.5)
    c.setFillColor(colors.HexColor(TEXTO2))
    c.drawString(2 * cm, 1.2 * cm, "Demissões e afastamentos por saúde mental no Brasil")
    c.drawRightString(A4[0] - 2 * cm, 1.2 * cm, str(doc.page))
    c.restoreState()


def gerar() -> Path:
    ler = lambda n: json.loads((SAIDA / n).read_text(encoding="utf-8"))  # noqa: E731
    meta, an, mem = ler("meta.json"), ler("analise.json"), ler("memoria.json")
    corr, fil = ler("correlacao.json"), ler("filiacao.json")
    serie = pd.DataFrame(ler("serie.json"))
    br_ = serie[(serie.uf == "BR")].dropna(subset=["afast_mental", "demissoes_sjc", "vinculos"]).sort_values("mes").copy()
    for c in br_.columns.difference(["uf", "mes"]):
        br_[c] = br_[c].astype(float)
    br_["ta"] = br_.afast_mental / br_.vinculos * 1e5
    br_["td"] = br_.demissoes_sjc / br_.vinculos * 1e5
    k = an["kpis"]
    ini, fim = meta["periodo"]["inicio"], meta["periodo"]["fim"]
    faltam = [m for m in pd.period_range(ini, fim, freq="M").astype(str) if m not in mem["meses_inss"]]

    h = []
    # Capa
    h += [Spacer(1, 5 * cm), P("Demissões e afastamentos do trabalho por saúde mental no Brasil", "capa_t"), Spacer(1, 0.6 * cm),
          P("Cruzamento de dados do INSS, do Novo CAGED e da RAIS, com análises estatísticas e de aprendizado de máquina", "capa_s"),
          Spacer(1, 3 * cm), P(AUTOR, "capa_s"), Spacer(1, 0.3 * cm), P("Projeto acadêmico", "capa_s"),
          Spacer(1, 0.3 * cm), P(f"Dados de {mes(ini)} a {mes(fim)}. Gerado em {pd.Timestamp(meta['gerado_em']).strftime('%d/%m/%Y')}.", "capa_s")]
    if meta["exemplo"]:
        h += [Spacer(1, 1 * cm), P("<b>Atenção: este relatório foi gerado com dados de exemplo, fictícios.</b>", "capa_s")]
    h.append(PageBreak())

    # Resumo
    h += [P("Resumo", "h1"), P(
        f"Este trabalho investiga se o aumento das demissões no mercado formal brasileiro se relaciona com o aumento dos afastamentos "
        f"do trabalho por transtornos mentais, como depressão, ansiedade, burnout e autismo. Foram cruzados, por mês e por estado, os "
        f"benefícios por incapacidade concedidos pelo INSS (com o CID da doença), as movimentações do Novo CAGED e o estoque de vínculos "
        f"da RAIS, de {mes(ini)} a {mes(fim)}. Nos 12 meses mais recentes com dados completos foram concedidos "
        f"{br(k['afast_mental_12m'])} afastamentos por saúde mental ({br(k['parte_mental_pct'], 1)}% de todos os afastamentos), "
        f"o equivalente a {br(k['taxa_afast_mes'], 1)} por 100 mil vínculos formais por mês, e houve {br(k['demissoes_12m'])} demissões "
        f"sem justa causa. Além de taxas e correlações, foram aplicados modelos de regressão com defasagem, teste de causalidade de "
        f"Granger, regressão em painel com efeitos fixos, Random Forest, agrupamento K-means, previsão Holt-Winters e detecção de "
        f"anomalias com Isolation Forest. Os resultados e suas limitações estão nas seções 5 e 7. Todo o cálculo é reproduzível pelo "
        f"código em {REPO} e os painéis interativos estão em {SITE}."),
        P("<b>Palavras-chave:</b> saúde mental; afastamento do trabalho; desemprego; INSS; CAGED; aprendizado de máquina.")]
    h.append(PageBreak())

    # 1 Introdução
    h += [P("1. Introdução e objetivo", "h1"), P(
        "Transtornos mentais estão entre as principais causas de afastamento do trabalho no Brasil. Ao mesmo tempo, o mercado formal "
        "passa por ciclos de contratação e demissão. A hipótese deste projeto é que períodos e regiões com mais demissões concentram "
        "também mais afastamentos por saúde mental, seja pela insegurança de quem permanece empregado, seja pelo adoecimento de quem é "
        "desligado e ainda mantém a qualidade de segurado do INSS."),
        P("Objetivos específicos:"), *itens([
            "medir a evolução mensal dos afastamentos por saúde mental, por grupo de doença, sexo, faixa etária e estado;",
            "medir a evolução das demissões sem justa causa e dos pedidos de demissão;",
            "testar estatisticamente se as duas séries andam juntas, no tempo e entre estados;",
            "usar modelos de aprendizado de máquina para avaliar o poder de previsão das variáveis do mercado de trabalho;",
            "documentar todo o cruzamento numa memória de cálculo verificável.",
        ])]

    # 2 Fontes
    h += [P("2. Fontes de dados", "h1"), tabela([
        ["Base", "Órgão", "O que traz", "Uso no projeto"],
        ["Benefícios concedidos", "INSS (dados abertos)", "Um registro por benefício concedido: espécie, CID-10, município de residência, sexo, nascimento, forma de filiação",
         "Numerador: afastamentos por saúde mental"],
        ["Novo CAGED (CAGEDMOV)", "MTE / PDET", "Cada admissão e desligamento de emprego formal, com o tipo de movimentação e a UF",
         "Demissões sem justa causa, pedidos e admissões"],
        ["RAIS Vínculos", "MTE / PDET", "Todos os vínculos formais do ano, com a situação em 31/12", "Denominador: vínculos ativos por UF"],
    ], [3.2, 2.6, 6.2, 4.4]), Spacer(1, 6), P(
        "As três bases são públicas e anonimizadas, e não há como ligar a mesma pessoa entre elas. Por isso o cruzamento é feito por "
        "agregados: mês × unidade da federação. A coleta, a limpeza e o cálculo são automáticos (Python e DuckDB) e rodam todo mês "
        "no GitHub Actions, que também publica o site.")]

    # 3 Metodologia
    h += [P("3. Metodologia", "h1"), P("3.1 Definições", "h2"), *itens([
        "<b>Afastamento</b>: auxílio por incapacidade temporária concedido, espécies 31 (previdenciário) e 91 (acidentário).",
        "<b>Saúde mental</b>: CID-10 do capítulo F ou Z73 (problemas relacionados à organização do modo de vida, onde entra o burnout). "
        "Grupos: " + "; ".join(f"{g['nome']} ({', '.join(g['cids'])})" for g in meta["grupos_cid"]) + ". "
        "Um CID entra no primeiro grupo cujo prefixo casar.",
        "<b>Demissão</b>: desligamento sem justa causa por iniciativa do empregador (tipo de movimentação 31 do CAGED). "
        "Pedidos de demissão (tipo 40) são tratados à parte.",
        "<b>Vínculos</b>: vínculos com situação “ativo em 31/12” na RAIS. Para cada mês usa-se a RAIS mais recente disponível até aquele ano.",
        "<b>Estado</b>: UF do município de residência do segurado, porque a coluna de UF do INSS indica a unidade que concedeu o benefício.",
    ]), P("3.2 Fórmulas", "h2"),
        P("taxa de afastamento (uf, mês) = afastamentos por saúde mental ÷ vínculos × 100.000", "formula"),
        P("taxa de demissão (uf, mês) = demissões sem justa causa ÷ vínculos × 100.000", "formula"),
        P("taxa média de 12 meses = Σ afastamentos dos 12 meses ÷ Σ vínculos dos 12 meses × 100.000", "formula"),
        P("índice base 100 = taxa do mês ÷ média da taxa nos 3 primeiros meses × 100", "formula"),
        P("3.3 Técnicas estatísticas e de aprendizado de máquina", "h2"), tabela([
            ["Técnica", "Biblioteca", "Pergunta que responde"],
            ["Correlação de Pearson", "NumPy", "As taxas sobem e descem juntas, no tempo e entre estados?"],
            ["Regressão com defasagem (erros Newey-West)", "statsmodels", "A demissão de k meses atrás explica o afastamento de hoje, descontada a tendência?"],
            ["Causalidade de Granger", "statsmodels", "O passado de uma série ajuda a prever a outra?"],
            ["Painel com efeitos fixos (erros agrupados por UF)", "statsmodels", "Dentro de um mesmo estado, meses com mais demissões têm mais afastamentos?"],
            ["Random Forest + importância por permutação", "scikit-learn", "Quanto as variáveis do mercado de trabalho melhoram a previsão da taxa de cada estado?"],
            ["K-means + silhueta", "scikit-learn", "Que grupos de estados têm perfil parecido?"],
            ["Holt-Winters", "statsmodels", "Quantos afastamentos esperar nos próximos 6 meses?"],
            ["Isolation Forest", "scikit-learn", "Que combinações estado × mês fogem do padrão?"],
        ], [5.2, 2.6, 8.6])]

    # 4 Resultados descritivos
    h += [PageBreak(), P("4. Resultados descritivos", "h1"), tabela([
        ["Indicador (Brasil, 12 meses mais recentes)", "Valor"],
        ["Afastamentos por saúde mental", br(k["afast_mental_12m"])],
        ["Variação sobre os 12 meses anteriores", (br(k["variacao_pct"], 1) + "%") if k["variacao_pct"] is not None else "–"],
        ["Parte dos afastamentos que é saúde mental", br(k["parte_mental_pct"], 1) + "%"],
        ["Afastamentos por saúde mental por 100 mil vínculos, por mês", br(k["taxa_afast_mes"], 1)],
        ["Demissões sem justa causa", br(k["demissoes_12m"])],
        ["Demissões sem justa causa por 100 mil vínculos, por mês", br(k["taxa_demissao_mes"], 1)],
    ], [11.5, 4.9]), Spacer(1, 8),
        KeepTogether([graf_indices(br_), P("Figura 1. Taxas de afastamento por saúde mental e de demissão sem justa causa no Brasil, em índice "
                                           "(média dos três primeiros meses = 100).", "legenda")]),
        KeepTogether([graf_grupos(br_, meta["grupos_cid"]), P("Figura 2. Afastamentos por saúde mental concedidos por mês, por grupo de CID.", "legenda")]),
        KeepTogether([graf_filiacao(fil, meta["filiacoes"]), P("Figura 3. Afastamentos por saúde mental por forma de filiação do segurado. "
                                                               "“Desempregado” é quem estava no período de graça após perder o emprego.", "legenda")]),
    ]
    sn = corr["serie_nacional"]
    h += [P("4.1 Correlações", "h2"), P(
        f"Entre os {corr['entre_ufs']['n_ufs']} estados, nos 12 meses mais recentes, a correlação entre a taxa de demissão e a de afastamento "
        f"por saúde mental é r = {br(corr['entre_ufs']['r'], 2)}. Na série nacional, mês a mês: "
        + "; ".join(f"{x['defasagem_meses']} meses de defasagem, r = {br(x['r'], 2)}" for x in sn if x["r"] is not None)
        + ". A correlação na série inclui a tendência das duas taxas e por isso pode exagerar a relação; as seções seguintes controlam isso.")]

    # 5 IA
    reg, gr, pn, rf, ag, pv, anom = an["regressao"], an["granger"], an["painel"], an["floresta"], an["agrupamento"], an["previsao"], an["anomalias"]
    h += [PageBreak(), P("5. Análises estatísticas e de aprendizado de máquina", "h1"), P(
        "Todas as análises foram feitas em Python com as bibliotecas scikit-learn e statsmodels, com semente aleatória fixa (42) para "
        "que os resultados sejam reproduzíveis. O código está em pipeline/analise.py.")]
    if "erro" not in reg:
        h += [P("5.1 Regressão com defasagem", "h2"), P(reg["formula"], "formula"), P(txt_regressao(reg)),
              KeepTogether([graf_defasagens(reg), P("Figura 4. Efeito estimado das demissões sobre os afastamentos para cada defasagem, com "
                                                    "intervalo de 95%. Barras azuis são significativas a 5%.", "legenda")])]
    if "erro" not in gr:
        h += [P("5.2 Causalidade de Granger", "h2"), P(txt_granger(gr))]
    if "erro" not in pn:
        h += [P("5.3 Painel de estados com efeitos fixos", "h2"),
              P("taxa_afastamento(uf, t) = b × taxa_demissao(uf, t) + efeito do estado + efeito do mês + erro", "formula"),
              tabela([["Modelo", "Afastamentos por 100 demissões", "IC 95%", "p", "R²"]] + [
                  [nome, br(pn[ch]["coef_td"] * 100, 2), f"{br(pn[ch]['ic95'][0] * 100, 2)} a {br(pn[ch]['ic95'][1] * 100, 2)}",
                   pval(pn[ch]["p_valor"]), br(pn[ch]["r2"], 2)]
                  for ch, nome in (("sem_controles", "Sem controles"), ("efeitos_fixos", "Efeitos fixos de UF e mês"),
                                   ("efeitos_fixos_com_admissoes", "Efeitos fixos + taxa de admissão"))], [5.6, 3.6, 3.4, 1.8, 1.8]),
              Spacer(1, 6), P(txt_painel(pn))]
    if "erro" not in rf:
        h += [P("5.4 Random Forest", "h2"), P(
            "Uma floresta de 400 árvores de decisão prevê a taxa de afastamento por saúde mental de cada estado em cada mês a partir de: "
            + ", ".join(i["nome"].lower() for i in rf["importancias"]) + ". A validação é temporal: o modelo só vê o passado."),
            P(txt_floresta(rf)),
            KeepTogether([graf_importancias(rf), P("Figura 5. Importância por permutação no período de teste: quanto o R² cai quando cada variável é embaralhada.", "legenda")])]
    if "erro" not in ag:
        h += [P("5.5 Agrupamento de estados (K-means)", "h2"), P(
            "Variáveis, padronizadas: taxa de afastamento, taxa de demissão, parte mental dos afastamentos e crescimento dos afastamentos "
            "sobre os 12 meses anteriores."), P(txt_agrupamento(ag)),
            KeepTogether([graf_dispersao(ag), P("Figura 6. Estados por taxa de demissão e de afastamento por saúde mental nos 12 meses mais recentes, "
                                                "coloridos pelo grupo do K-means.", "legenda")])]
    if "erro" not in pv:
        h += [P("5.6 Previsão (Holt-Winters)", "h2"), P(f"Modelo: {pv['modelo']}. " + txt_previsao(pv)),
              KeepTogether([graf_previsao(pv), P("Figura 7. Afastamentos por saúde mental por mês no Brasil, com previsão para 6 meses.", "legenda")])]
    if "erro" not in anom:
        h += [P("5.7 Meses fora do padrão (Isolation Forest)", "h2"), P(
            f"Para cada estado as taxas foram padronizadas pela média e pelo desvio do próprio estado (z). O Isolation Forest marcou "
            f"{anom['total_anomalos']} de {br(anom['n'])} combinações estado × mês como atípicas. As mais extremas:"),
            tabela([["UF", "Mês", "Afast./100 mil", "z afast.", "Demissões/100 mil", "z demissões"]] + [
                [a["uf"], mes(a["mes"]), br(a["taxa_afastamento"], 1), br(a["z_afastamento"], 1), br(a["taxa_demissao"], 0), br(a["z_demissao"], 1)]
                for a in anom["lista"][:8]], [1.4, 1.8, 3.2, 2.4, 3.6, 2.6]),
            Spacer(1, 6), P("Esses pontos merecem checagem: podem ser eventos reais (greves do INSS, mutirões de perícia, fechamento de "
                            "empresas grandes) ou problemas de registro.")]

    # 6 Memória de cálculo
    h += [PageBreak(), P("6. Memória de cálculo", "h1"), P(
        f"Esta seção refaz as contas dos indicadores com os números de cada etapa. Período: os 12 meses mais recentes com INSS e CAGED "
        f"({mes(k['meses'][0])} a {mes(k['meses'][-1])})."
        + (f" Meses sem arquivo do INSS no período coberto: {', '.join(mes(m) for m in faltam)}; eles ficam fora das somas." if faltam else "")),
        P("6.1 Etapa 1: filtro dos benefícios do INSS", "h2"),
        tabela([["Espécie", "Benefícios concedidos", "Sem UF identificada", "Com CID de saúde mental"]] + [
            [f"{e['especie']} – {ESPECIES.get(e['especie'], '')}", br(e["n"]), br(e["sem_uf"]), br(e["mental"])] for e in mem["inss_por_especie"]],
            [7.6, 3, 2.9, 2.9]),
        Spacer(1, 6), P("Dos auxílios temporários (31 e 91) com UF identificada, a distribuição por grupo de CID:"),
        tabela([["Grupo de CID", "Afastamentos"]] + [
            [next((g["nome"] for g in meta["grupos_cid"] if g["chave"] == x["grupo"]), "Outras doenças (fora da saúde mental)"), br(x["n"])]
            for x in mem["inss_grupos_afastamento"]], [11.5, 4.9]),
        P("6.2 Etapa 2: movimentações do CAGED", "h2"),
        tabela([["Tipo", "Movimentações"]] + [
            [{"sem_justa_causa": "Demissão sem justa causa (tipo 31)", "a_pedido": "Pedido de demissão (tipo 40)",
              "outros_desligamentos": "Outros desligamentos", "admissoes": "Admissões"}.get(x["tipo"], x["tipo"]), br(x["n"])]
            for x in mem["caged_movimentos"]], [11.5, 4.9]),
        P("6.3 Etapa 3: denominador (RAIS)", "h2"),
        tabela([["Ano da RAIS", "Vínculos ativos em 31/12"]] + [[str(x["ano"]), br(x["vinculos"])] for x in mem["rais_vinculos"]], [11.5, 4.9]),
        P("6.4 Etapa 4: cruzamento mês a mês (Brasil)", "h2"),
        tabela([["Mês", "Afast. saúde mental", "Afast. total", "Demissões s/ j. causa", "Vínculos", "Afast./100 mil", "Dem./100 mil"]] + [
            [mes(r["mes"]), br(r["afast_mental"]), br(r["afast_total"]), br(r["demissoes_sjc"]), br(r["vinculos"]), br(r["taxa_afast"], 1), br(r["taxa_demissao"], 0)]
            for r in k["por_mes"]], [1.6, 2.4, 2.2, 2.8, 2.8, 2.2, 2.2]),
        P("6.5 Etapa 5: indicadores", "h2"),
        P(f"afastamentos (12 meses) = Σ afastamentos por saúde mental = <b>{br(k['afast_mental_12m'])}</b>", "formula"),
        P(f"variação = {br(k['afast_mental_12m'])} ÷ {br(k['afast_mental_12m_anteriores'])} − 1 = <b>{br(k['variacao_pct'], 1)}%</b>", "formula"),
        P(f"parte mental = {br(k['afast_mental_12m'])} ÷ {br(k['afast_total_12m'])} = <b>{br(k['parte_mental_pct'], 1)}%</b>", "formula"),
        P(f"taxa de afastamento = {br(k['afast_mental_12m'])} ÷ {br(k['vinculos_soma_12m'])} × 100.000 = <b>{br(k['taxa_afast_mes'], 1)}</b> por 100 mil vínculos por mês", "formula"),
        P(f"taxa de demissão = {br(k['demissoes_12m'])} ÷ {br(k['vinculos_soma_12m'])} × 100.000 = <b>{br(k['taxa_demissao_mes'], 1)}</b> por 100 mil vínculos por mês", "formula"),
        P(f"A soma dos vínculos é a soma dos estoques mensais ({len(k['meses'])} meses × cerca de {br(k['vinculos_medio'])} vínculos), por isso o resultado já é uma média mensal."),
    ]

    # 7 Limitações e 8 Conclusão
    h += [P("7. Limitações", "h1"), *itens([
        "Correlação e associação estatística não provam causa. Ciclos econômicos, sazonalidade, filas de perícia e mudanças nas regras do INSS afetam as duas séries.",
        "Só o emprego formal entra nas contas. Trabalhadores informais e servidores de regime próprio ficam de fora.",
        "As bases não se ligam por pessoa: não é possível saber se quem se afastou foi demitido antes ou depois.",
        "O INSS quase nunca informa o setor econômico (CNAE) do segurado, então não há recorte por setor.",
        "O denominador (RAIS) é anual; as variações dentro do ano vêm só do numerador.",
        f"A série tem {len(br_)} meses, pouco para modelos de séries temporais; os testes têm baixo poder estatístico.",
        "O autismo (F84) aparece sobretudo no BPC (espécie 87), um benefício assistencial, e não como afastamento.",
    ])]
    concl = [f"Nos 12 meses mais recentes, {br(k['parte_mental_pct'], 1)}% dos afastamentos concedidos pelo INSS foram por transtornos mentais, "
             f"{br(k['taxa_afast_mes'], 1)} a cada 100 mil vínculos formais por mês."]
    if "erro" not in pn:
        b = pn["efeitos_fixos"]
        concl.append("A relação com as demissões aparece também dentro de cada estado, ao longo do tempo." if b["p_valor"] is not None and b["p_valor"] < 0.05
                     else "Entre estados, onde se demite mais há tendência de mais afastamentos, mas, controlando as diferenças permanentes entre estados e os choques comuns de cada mês, essa relação não se sustenta estatisticamente.")
    if "erro" not in rf:
        ganho = (rf["mae_sem_mercado"] - rf["mae"]) / rf["mae_sem_mercado"] * 100 if rf["mae_sem_mercado"] else 0
        concl.append("O modelo de aprendizado de máquina confirma que as variáveis de demissão ajudam a prever os afastamentos." if ganho > 3
                     else "O modelo de aprendizado de máquina indica que o nível típico de cada estado e a sazonalidade explicam mais do que as demissões.")
    concl.append("Os resultados devem ser lidos como evidência de associação, a ser aprofundada com dados individuais, que hoje não são públicos.")
    h += [P("8. Conclusão", "h1"), P(" ".join(concl))]
    h += [P("Referências", "h1"), *itens([
        "BRASIL. Instituto Nacional do Seguro Social. Benefícios concedidos – Plano de Dados Abertos. Disponível em: dadosabertos.inss.gov.br.",
        "BRASIL. Ministério do Trabalho e Emprego. Novo CAGED – microdados. Disponível em: pdet.mte.gov.br.",
        "BRASIL. Ministério do Trabalho e Emprego. RAIS – microdados de vínculos. Disponível em: pdet.mte.gov.br.",
        "ORGANIZAÇÃO MUNDIAL DA SAÚDE. CID-10: Classificação Estatística Internacional de Doenças, capítulo V (F00–F99).",
        "PEDREGOSA, F. et al. Scikit-learn: Machine Learning in Python. Journal of Machine Learning Research, v. 12, p. 2825-2830, 2011.",
        "SEABOLD, S.; PERKTOLD, J. statsmodels: Econometric and statistical modeling with Python. Proceedings of the 9th Python in Science Conference, 2010.",
        "GRANGER, C. W. J. Investigating causal relations by econometric models and cross-spectral methods. Econometrica, v. 37, n. 3, p. 424-438, 1969.",
        "BREIMAN, L. Random Forests. Machine Learning, v. 45, p. 5-32, 2001.",
        f"Código-fonte e dados do projeto: {REPO}. Painéis: {SITE}.",
    ])]

    doc = SimpleDocTemplate(str(DESTINO), pagesize=A4, leftMargin=2.3 * cm, rightMargin=2.3 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
                            title="Demissões e afastamentos por saúde mental no Brasil", author=AUTOR)
    doc.build(h, onLaterPages=_rodape)
    print(f"  {DESTINO.name}")
    return DESTINO


if __name__ == "__main__":
    gerar()
