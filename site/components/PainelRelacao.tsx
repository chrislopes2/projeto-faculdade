"use client";
import { useCallback, useMemo } from "react";
import type { Cores } from "@/lib/cores";
import { fmt, fmtMes, soma, UFS } from "@/lib/calc";
import type { Correlacao, Filiacao, LinhaSerie, Meta } from "@/lib/tipos";
import { base, Grafico } from "./Grafico";

function leitura(r: number | null) {
  if (r == null) return "sem dados suficientes";
  const a = Math.abs(r);
  const forca = a < 0.2 ? "muito fraca" : a < 0.4 ? "fraca" : a < 0.6 ? "moderada" : "forte";
  return `${forca}, ${r >= 0 ? "positiva" : "negativa"}`;
}

export function PainelRelacao({ serie, correlacao, filiacao, meta }: { serie: LinhaSerie[]; correlacao: Correlacao; filiacao: Filiacao[]; meta: Meta }) {
  const pontos = useMemo(() => {
    const ult = new Set(meta.ultimos_12_meses);
    return UFS.map((u) => {
      const ls = serie.filter((r) => r.uf === u && ult.has(r.mes));
      const v = soma(ls, "vinculos") || 1;
      return { uf: u, dem: (soma(ls, "demissoes_sjc") / v) * 1e5, afast: (soma(ls, "afast_mental") / v) * 1e5 };
    });
  }, [serie, meta]);

  const dispersao = useCallback(
    (c: Cores) => ({
      ...base(c),
      legend: { show: false },
      grid: { left: 8, right: 24, top: 36, bottom: 28, containLabel: true },
      tooltip: {
        ...(base(c).tooltip as object), trigger: "item",
        formatter: (p: { data: [number, number, string] }) =>
          `<b>${p.data[2]}</b><br/>Demissões: ${fmt(p.data[0])}<br/>Afastamentos: ${fmt(p.data[1], 1)}`,
      },
      xAxis: { ...(base(c).xAxis as object), type: "value", scale: true, name: "demissões sem justa causa", nameLocation: "middle", nameGap: 24, splitLine: { lineStyle: { color: c.grade } } },
      yAxis: { ...(base(c).yAxis as object), type: "value", scale: true },
      series: [{
        type: "scatter", symbolSize: 10,
        itemStyle: { borderColor: c.superficie, borderWidth: 2 },
        label: { show: true, formatter: (p: { data: [number, number, string] }) => p.data[2], position: "right", color: c.texto2, fontSize: 10 },
        data: pontos.map((p) => [+p.dem.toFixed(0), +p.afast.toFixed(1), p.uf]),
      }],
    }),
    [pontos],
  );

  const defasagem = useCallback(
    (c: Cores) => ({
      ...base(c),
      legend: { show: false },
      tooltip: { ...(base(c).tooltip as object), axisPointer: { type: "shadow" } },
      xAxis: { ...(base(c).xAxis as object), type: "category", name: "meses depois", nameLocation: "middle", nameGap: 26,
        data: correlacao.serie_nacional.map((d) => (d.defasagem_meses === 0 ? "mesmo mês" : `${d.defasagem_meses}`)) },
      yAxis: { ...(base(c).yAxis as object), type: "value", min: -1, max: 1 },
      grid: { left: 8, right: 16, top: 36, bottom: 28, containLabel: true },
      series: [{
        name: "Correlação", type: "bar", barMaxWidth: 36,
        data: correlacao.serie_nacional.map((d) => ({
          value: d.r == null ? null : +d.r.toFixed(2),
          itemStyle: { borderRadius: (d.r ?? 0) >= 0 ? [4, 4, 0, 0] : [0, 0, 4, 4] },
        })),
      }],
    }),
    [correlacao],
  );

  const porFiliacao = useCallback(
    (c: Cores) => ({
      ...base(c),
      xAxis: { ...(base(c).xAxis as object), type: "category", data: filiacao.map((f) => fmtMes(f.mes)) },
      yAxis: { ...(base(c).yAxis as object), type: "value" },
      series: meta.filiacoes.map((f) => ({
        name: f.nome, type: "line", symbol: "none", lineStyle: { width: 2 },
        data: filiacao.map((r) => r[f.chave as keyof Filiacao] as number),
      })),
    }),
    [filiacao, meta],
  );
  const ultFil = filiacao.slice(-12);
  const totFil = ultFil.reduce((t, r) => t + r.empregado + r.desempregado + r.autonomo + r.outros, 0);
  const partDesemp = totFil ? (100 * ultFil.reduce((t, r) => t + r.desempregado, 0)) / totFil : null;

  const r = correlacao.entre_ufs.r;
  return (
    <>
      <div className="grade">
        <Grafico
          titulo="Estados: demissão × afastamento"
          descricao={`Horizontal: demissões sem justa causa; vertical: afastamentos por saúde mental. Médias mensais por 100 mil vínculos, últimos 12 meses. Correlação entre estados: r = ${fmt(r, 2)} (${leitura(r)}).`}
          montar={dispersao}
          altura={420}
          tabela={{
            colunas: ["UF", "Demissões / 100 mil", "Afastamentos / 100 mil"],
            linhas: pontos.map((p) => [p.uf, fmt(p.dem), fmt(p.afast, 1)]),
          }}
        />
        <Grafico
          titulo="As demissões antecipam os afastamentos?"
          descricao="Correlação entre a taxa de demissão de um mês e a taxa de afastamento alguns meses depois, série do Brasil. Vai de −1 a 1; perto de 0 é nenhuma relação."
          montar={defasagem}
          tabela={{
            colunas: ["Defasagem (meses)", "r", "Meses comparados"],
            linhas: correlacao.serie_nacional.map((d) => [d.defasagem_meses, fmt(d.r, 2), d.n_meses]),
          }}
        />
      </div>
      <div style={{ marginTop: 16 }}>
        <Grafico
          titulo="Quem se afasta por saúde mental: empregado ou desempregado?"
          descricao={`Número de afastamentos por mês no Brasil, pela situação do segurado no INSS. "Desempregado" é quem perdeu o emprego e ainda tem cobertura (período de graça). Nos últimos 12 meses, ${fmt(partDesemp, 1)}% dos afastamentos foram de desempregados.`}
          montar={porFiliacao}
          tabela={{
            colunas: ["Mês", ...meta.filiacoes.map((f) => f.nome)],
            linhas: filiacao.map((r) => [fmtMes(r.mes), ...meta.filiacoes.map((f) => fmt(r[f.chave as keyof Filiacao] as number))]),
          }}
        />
      </div>
    </>
  );
}
