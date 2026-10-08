"use client";
import { useCallback } from "react";
import type { Cores } from "@/lib/cores";
import { fmt, fmtMes } from "@/lib/calc";
import type { Analise } from "@/lib/tipos";
import { base, Grafico } from "./Grafico";

const p = (v: number | null | undefined) => (v == null ? "–" : v < 0.001 ? "< 0,001" : fmt(v, 3));

export function PainelAnalises({ a }: { a: Analise }) {
  const { regressao: reg, floresta: rf, previsao: pv, agrupamento: ag, painel: pn, granger: gr, anomalias: an, textos } = a;

  const defasagens = useCallback(
    (c: Cores) => ({
      ...base(c),
      legend: { show: false },
      tooltip: { ...(base(c).tooltip as object), axisPointer: { type: "shadow" } },
      xAxis: { ...(base(c).xAxis as object), type: "category", data: reg!.modelos.map((m) => `${m.defasagem_meses} m`) },
      yAxis: { ...(base(c).yAxis as object), type: "value" },
      series: [{
        type: "bar", name: "Afastamentos por 100 demissões", barWidth: "50%",
        data: reg!.modelos.map((m) => ({ value: +(m.coef * 100).toFixed(2), itemStyle: { color: m.p_valor < 0.05 ? c.serie[0] : c.eixo } })),
      }],
    }),
    [reg],
  );

  const importancias = useCallback(
    (c: Cores) => {
      const d = [...rf!.importancias].reverse();
      return {
        ...base(c),
        legend: { show: false },
        grid: { left: 24, right: 24, top: 8, bottom: 8, containLabel: true },
        tooltip: { ...(base(c).tooltip as object), axisPointer: { type: "shadow" } },
        xAxis: { ...(base(c).yAxis as object), type: "value", splitLine: { lineStyle: { color: c.grade } } },
        yAxis: { ...(base(c).xAxis as object), type: "category", data: d.map((x) => x.nome) },
        series: [{ type: "bar", name: "Queda no R²", data: d.map((x) => +x.importancia.toFixed(4)), barWidth: "55%" }],
      };
    },
    [rf],
  );

  const previsao = useCallback(
    (c: Cores) => {
      const h = pv!.historico, f = pv!.previsao;
      const meses = [...h.map((x) => x.mes), ...f.map((x) => x.mes)];
      const vazio = h.slice(0, -1).map(() => null);
      const ult = h[h.length - 1].valor;
      return {
        ...base(c),
        xAxis: { ...(base(c).xAxis as object), type: "category", data: meses.map(fmtMes), boundaryGap: false },
        yAxis: { ...(base(c).yAxis as object), type: "value", scale: true },
        series: [
          { name: "Observado", type: "line", data: h.map((x) => x.valor), symbol: "none", lineStyle: { width: 2 }, color: c.serie[0] },
          { name: "Previsão", type: "line", data: [...vazio, ult, ...f.map((x) => x.valor)], symbol: "none", lineStyle: { width: 2, type: "dashed" }, color: c.serie[0] },
          { name: "base", type: "line", stack: "faixa", data: [...vazio, ult, ...f.map((x) => x.min80)], symbol: "none", lineStyle: { opacity: 0 }, tooltip: { show: false } },
          { name: "Faixa de 80%", type: "line", stack: "faixa", data: [...vazio, 0, ...f.map((x) => x.max80 - x.min80)], symbol: "none", lineStyle: { opacity: 0 }, areaStyle: { color: c.serie[0], opacity: 0.15 }, color: c.serie[0] },
        ],
        legend: { ...(base(c).legend as object), data: ["Observado", "Previsão"] },
        tooltip: { ...(base(c).tooltip as object), formatter: (ps: { seriesName: string; value: number | null; axisValue: string }[]) =>
          [ps[0].axisValue, ...ps.filter((x) => x.value != null && (x.seriesName === "Observado" || x.seriesName === "Previsão")).map((x) => `${x.seriesName}: ${fmt(x.value)}`)].join("<br/>") },
      };
    },
    [pv],
  );

  const grupos = useCallback(
    (c: Cores) => ({
      ...base(c),
      grid: { left: 8, right: 24, top: 36, bottom: 28, containLabel: true },
      tooltip: { ...(base(c).tooltip as object), trigger: "item",
        formatter: (x: { data: [number, number, string] }) => `<b>${x.data[2]}</b><br/>Demissões: ${fmt(x.data[0])}<br/>Afastamentos: ${fmt(x.data[1], 1)}` },
      xAxis: { ...(base(c).xAxis as object), type: "value", scale: true, name: "demissões sem justa causa", nameLocation: "middle", nameGap: 24, splitLine: { lineStyle: { color: c.grade } } },
      yAxis: { ...(base(c).yAxis as object), type: "value", scale: true },
      series: ag!.grupos.map((g) => ({
        name: g.nome, type: "scatter", symbolSize: 10, itemStyle: { borderColor: c.superficie, borderWidth: 2 },
        label: { show: true, formatter: (x: { data: [number, number, string] }) => x.data[2], position: "right", color: c.texto2, fontSize: 10 },
        data: ag!.ufs.filter((u) => u.grupo === g.nome).map((u) => [u.taxa_demissao, u.taxa_afastamento, u.uf]),
      })),
    }),
    [ag],
  );

  return (
    <>
      {reg && (
        <section>
          <h2>1. Regressão com defasagem</h2>
          <p className="desc">{reg.formula}, com erros robustos (Newey-West). Biblioteca: statsmodels.</p>
          <p>{textos.regressao}</p>
          <Grafico
            titulo="Afastamentos a mais por 100 demissões a mais, por defasagem"
            descricao="Barras azuis são estatisticamente significativas a 5%; as cinzas não."
            montar={defasagens}
            altura={260}
            tabela={{
              colunas: ["Defasagem", "Coeficiente × 100", "IC 95%", "p", "R²", "Meses"],
              linhas: reg.modelos.map((m) => [`${m.defasagem_meses} meses`, fmt(m.coef * 100, 2), `${fmt(m.ic95[0] * 100, 2)} a ${fmt(m.ic95[1] * 100, 2)}`, p(m.p_valor), fmt(m.r2, 2), m.n]),
            }}
          />
        </section>
      )}

      {gr && (
        <section>
          <h2>2. Causalidade de Granger</h2>
          <p className="desc">O passado de uma série ajuda a prever a outra? Testado nas variações mês a mês. Biblioteca: statsmodels.</p>
          <p>{textos.granger}</p>
          <div className="cartao tabela-rolagem">
            <table>
              <thead><tr><th>Defasagem</th><th>p (demissão → afastamento)</th><th>p (afastamento → demissão)</th></tr></thead>
              <tbody>
                {(gr.testes.demissao_para_afastamento ?? []).map((t, i) => (
                  <tr key={i}><td>{t.defasagem_meses} meses</td><td>{p(t.p_valor)}</td><td>{p(gr.testes.afastamento_para_demissao?.[i]?.p_valor)}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {pn && (
        <section>
          <h2>3. Painel de estados com efeitos fixos</h2>
          <p className="desc">taxa de afastamento (uf, mês) = b × taxa de demissão (uf, mês) + efeito do estado + efeito do mês. Biblioteca: statsmodels.</p>
          <p>{textos.painel}</p>
          <div className="cartao tabela-rolagem">
            <table>
              <thead><tr><th>Modelo</th><th>Afast. por 100 demissões</th><th>IC 95%</th><th>p</th><th>R²</th></tr></thead>
              <tbody>
                {([["sem_controles", "Sem controles"], ["efeitos_fixos", "Efeitos fixos de UF e mês"], ["efeitos_fixos_com_admissoes", "Efeitos fixos + admissões"]] as const).map(([k, nome]) => (
                  <tr key={k}>
                    <td>{nome}</td><td>{fmt((pn[k].coef_td ?? 0) * 100, 2)}</td>
                    <td>{fmt((pn[k].ic95[0] ?? 0) * 100, 2)} a {fmt((pn[k].ic95[1] ?? 0) * 100, 2)}</td><td>{p(pn[k].p_valor)}</td><td>{fmt(pn[k].r2, 2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {rf && (
        <section>
          <h2>4. Random Forest</h2>
          <p className="desc">400 árvores de decisão preveem a taxa de cada estado em cada mês. Treino no passado, teste nos meses mais recentes. Biblioteca: scikit-learn.</p>
          <p>{textos.floresta}</p>
          <div className="kpis">
            <div className="kpi"><span className="kpi-rotulo">Erro médio do modelo</span><span className="kpi-valor">{fmt(rf.mae, 1)}</span><span className="kpi-detalhe">afastamentos por 100 mil vínculos</span></div>
            <div className="kpi"><span className="kpi-rotulo">Sem dados de mercado de trabalho</span><span className="kpi-valor">{fmt(rf.mae_sem_mercado, 1)}</span><span className="kpi-detalhe">erro médio</span></div>
            <div className="kpi"><span className="kpi-rotulo">Média de cada estado</span><span className="kpi-valor">{fmt(rf.mae_base, 1)}</span><span className="kpi-detalhe">erro médio da linha de base</span></div>
          </div>
          <Grafico titulo="O que mais pesa na previsão" descricao="Quanto o R² cai quando cada variável é embaralhada no período de teste." montar={importancias} altura={300} />
        </section>
      )}

      {ag && (
        <section>
          <h2>5. Grupos de estados (K-means)</h2>
          <p className="desc">Taxa de afastamento, taxa de demissão, parte mental e crescimento, padronizados. O número de grupos é o de maior silhueta. Biblioteca: scikit-learn.</p>
          <p>{textos.agrupamento}</p>
          <Grafico titulo="Estados por grupo" descricao="Por 100 mil vínculos, por mês, nos 12 meses mais recentes." montar={grupos} altura={400} />
        </section>
      )}

      {pv && (
        <section>
          <h2>6. Previsão para os próximos 6 meses</h2>
          <p className="desc">{pv.modelo}. Biblioteca: statsmodels.</p>
          <p>{textos.previsao}</p>
          <Grafico
            titulo="Afastamentos por saúde mental por mês, Brasil"
            descricao="A faixa sombreada é o intervalo de 80%."
            montar={previsao}
            tabela={{ colunas: ["Mês", "Previsão", "Mínimo (80%)", "Máximo (80%)"], linhas: pv.previsao.map((x) => [fmtMes(x.mes), fmt(x.valor), fmt(x.min80), fmt(x.max80)]) }}
          />
        </section>
      )}

      {an && (
        <section>
          <h2>7. Meses fora do padrão (Isolation Forest)</h2>
          <p className="desc">Cada taxa é comparada com a média do próprio estado (z). Biblioteca: scikit-learn.</p>
          <p>{an.total_anomalos} de {fmt(an.n)} combinações estado × mês foram marcadas como atípicas. As mais extremas:</p>
          <div className="cartao tabela-rolagem">
            <table>
              <thead><tr><th>UF</th><th>Mês</th><th>Afast./100 mil</th><th>z afast.</th><th>Dem./100 mil</th><th>z dem.</th></tr></thead>
              <tbody>
                {an.lista.map((x, i) => (
                  <tr key={i}><td>{x.uf}</td><td>{fmtMes(x.mes)}</td><td>{fmt(x.taxa_afastamento, 1)}</td><td>{fmt(x.z_afastamento, 1)}</td><td>{fmt(x.taxa_demissao)}</td><td>{fmt(x.z_demissao, 1)}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  );
}
