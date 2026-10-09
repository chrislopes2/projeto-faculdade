"""Textos de interpretação montados a partir dos números (usados no relatório em PDF e no site)."""
import numpy as np

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


# --- Formatação pt-BR --------------------------------------------------------------------------
def br(x, casas=0) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "–"
    s = f"{x:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def mes(m: str) -> str:
    a, mm = m.split("-")
    return f"{MESES[int(mm) - 1]}/{a[2:]}"


def pval(p) -> str:
    return "–" if p is None else ("< 0,001" if p < 0.001 else br(p, 3))


def pp(p) -> str:
    """'p = 0,083' ou 'p < 0,001', para usar no meio do texto."""
    return "p não calculado" if p is None else ("p < 0,001" if p < 0.001 else f"p = {br(p, 3)}")


# --- Textos que dependem dos resultados --------------------------------------------------------
def txt_regressao(reg):
    m = reg.get("melhor")
    if not m:
        return "Não houve meses suficientes para estimar a regressão."
    sig = [x for x in reg["modelos"] if x["p_valor"] is not None and x["p_valor"] < 0.05]
    if not sig:
        return (f"Em nenhuma das defasagens testadas (0 a 6 meses) o coeficiente foi estatisticamente significativo a 5%. "
                f"O mais forte foi o de {m['defasagem_meses']} mês(es), com {pp(m['p_valor'])}. Depois de descontada a "
                "tendência, as oscilações mensais das demissões não acompanham as dos afastamentos no agregado nacional.")
    k = m["defasagem_meses"]
    efeito = m["coef"] * 100
    sentido = "a mais" if efeito > 0 else "a menos"
    return (f"A associação mais forte aparece com {k} mês(es) de defasagem: a cada 100 demissões sem justa causa a mais por "
            f"100 mil vínculos, há em média {br(abs(efeito), 1)} afastamentos por saúde mental {sentido} por 100 mil vínculos "
            f"({pp(m['p_valor'])}; IC 95% de {br(m['ic95'][0] * 100, 1)} a {br(m['ic95'][1] * 100, 1)}). "
            f"Em termos relativos, +1% na taxa de demissão corresponde a {br(m['elasticidade'], 2).replace('-', '−')}% na taxa de "
            f"afastamento. Defasagens significativas a 5%: {', '.join(str(x['defasagem_meses']) for x in sig)} mês(es).")


def _min_p(lista):
    if not isinstance(lista, list) or not lista:
        return None
    return min(lista, key=lambda x: x["p_valor"] if x["p_valor"] is not None else 1)


def txt_granger(g):
    t = g["testes"]
    a, b = _min_p(t.get("demissao_para_afastamento")), _min_p(t.get("afastamento_para_demissao"))
    partes = []
    if a:
        if a["p_valor"] < 0.05:
            partes.append(f"o passado das demissões ajuda a prever os afastamentos (menor {pp(a['p_valor'])}, com {a['defasagem_meses']} mês(es))")
        else:
            partes.append(f"o passado das demissões não melhora a previsão dos afastamentos de forma significativa (menor {pp(a['p_valor'])})")
    if b:
        if b["p_valor"] < 0.05:
            partes.append(f"no sentido inverso, os afastamentos ajudam a prever as demissões (menor {pp(b['p_valor'])}, com {b['defasagem_meses']} mês(es))")
        else:
            partes.append(f"no sentido inverso também não há sinal significativo (menor {pp(b['p_valor'])})")
    if not partes:
        return "O teste não pôde ser calculado com a série disponível."
    return ("Nas variações mês a mês da série nacional, " + "; ".join(partes) + ". Como são vários testes, um p isolado "
            "pouco abaixo de 0,05 deve ser lido com cautela. Causalidade de Granger mede precedência temporal, não causa no sentido comum.")


def txt_painel(pn):
    a, b = pn["sem_controles"], pn["efeitos_fixos"]
    s = (f"Comparando todos os estados e meses sem controle algum, cada 100 demissões a mais por 100 mil vínculos se associam a "
         f"{br(a['coef_td'] * 100, 2)} afastamentos por saúde mental a mais ({pp(a['p_valor'])}). ")
    if b["p_valor"] is not None and b["p_valor"] < 0.05:
        s += (f"Com efeitos fixos de estado e de mês, o efeito fica em {br(b['coef_td'] * 100, 2)} ({pp(b['p_valor'])}): "
              "mesmo dentro de um estado, nos meses em que ele demite mais do que o seu normal, há mais afastamentos.")
    else:
        s += (f"Com efeitos fixos de estado e de mês, o efeito cai para {br(b['coef_td'] * 100, 2)} e deixa de ser significativo "
              f"({pp(b['p_valor'])}). Ou seja, a relação vem de diferenças permanentes entre estados (estrutura econômica, "
              "acesso à perícia, perfil da população), e não de meses em que um estado demite mais do que o habitual.")
    return s


def txt_floresta(rf):
    if "erro" in rf:
        return f"O modelo não pôde ser treinado: {rf['erro']}."
    ganho = (rf["mae_sem_mercado"] - rf["mae"]) / rf["mae_sem_mercado"] * 100 if rf["mae_sem_mercado"] else 0
    s = (f"Treinado com {mes(rf['treino']['de'])} a {mes(rf['treino']['ate'])} e testado de {mes(rf['teste']['de'])} a "
         f"{mes(rf['teste']['ate'])}, meses que o modelo não viu, o erro médio foi de {br(rf['mae'], 1)} afastamentos por 100 mil "
         f"vínculos (a taxa média no período de teste é {br(rf['media_taxa_teste'], 1)}), com R² de {br(rf['r2'], 2)}. "
         f"O mesmo modelo sem as variáveis do mercado de trabalho erra {br(rf['mae_sem_mercado'], 1)}, e a média histórica de cada "
         f"estado erra {br(rf['mae_base'], 1)}. ")
    if ganho > 3:
        s += f"As informações de demissões, pedidos e admissões reduzem o erro em {br(ganho, 1)}%, o que indica que carregam informação útil sobre os afastamentos."
    elif ganho > -3:
        s += "As informações de demissões, pedidos e admissões praticamente não mudam o erro: o nível de cada estado e a sazonalidade explicam quase tudo o que o modelo consegue prever."
    else:
        s += "Incluir demissões, pedidos e admissões chega a piorar o erro, sinal de que, nesta janela, elas acrescentam mais ruído do que informação."
    top = rf["importancias"][0]
    s += f" A variável mais importante foi “{top['nome'].lower()}”."
    return s


def txt_agrupamento(ag):
    partes = [f"{g['nome']} ({g['descricao']}): {', '.join(g['ufs'])}" for g in ag["grupos"]]
    return (f"O K-means testou de 2 a {ag['testados'][-1]['k']} grupos e escolheu {ag['k']}, o número com maior coeficiente de silhueta "
            f"({br(ag['silhueta'], 2)}; vai de −1 a 1, e acima de 0,25 indica alguma estrutura). " + "; ".join(partes) + ".")


def txt_previsao(pv):
    f = pv["previsao"]
    s = (f"O modelo projeta entre {br(f[0]['valor'])} e {br(f[-1]['valor'])} afastamentos por saúde mental por mês até "
         f"{mes(f[-1]['mes'])}, com faixa de 80% de {br(min(x['min80'] for x in f))} a {br(max(x['max80'] for x in f))}. ")
    if pv.get("validacao"):
        s += (f"Ao esconder os últimos 6 meses e prevê-los, o erro percentual médio foi de {br(pv['validacao']['mape'], 1)}%. ")
    if pv["meses_interpolados"]:
        s += f"O mês sem dados do INSS ({', '.join(mes(m) for m in pv['meses_interpolados'])}) foi preenchido por interpolação só para este modelo."
    return s


def interpretar(an: dict) -> dict:
    """Um texto por análise; as que falharam ficam de fora."""
    fs = {"regressao": txt_regressao, "granger": txt_granger, "painel": txt_painel, "floresta": txt_floresta,
          "agrupamento": txt_agrupamento, "previsao": txt_previsao}
    return {k: f(an[k]) for k, f in fs.items() if isinstance(an.get(k), dict) and "erro" not in an[k]}
