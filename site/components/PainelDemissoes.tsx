"use client";
import { useCallback, useMemo } from "react";
import type { Cores } from "@/lib/cores";
import { daUf, fmt, fmtMes, soma, taxa, UFS } from "@/lib/calc";
import type { LinhaSerie, Meta } from "@/lib/tipos";
import { base, Grafico } from "./Grafico";
import { FiltroUf, useUf } from "./FiltroUf";
import { Kpi } from "./Kpi";

export function PainelDemissoes({ serie, meta }: { serie: LinhaSerie[]; meta: Meta }) {
  const [uf, setUf] = useUf();
  const linhas = useMemo(() => daUf(serie, uf).filter((r) => r.desligamentos != null && r.vinculos), [serie, uf]);
  const ult = linhas.slice(-12);

  const taxas = useCallback(
    (c: Cores) => ({
      ...base(c),
      xAxis: { ...(base(c).xAxis as object), type: "category", data: linhas.map((r) => fmtMes(r.mes)) },
      yAxis: { ...(base(c).yAxis as object), type: "value" },
      series: [
        { name: "Demissão sem justa causa", type: "line", symbol: "none", lineStyle: { width: 2 }, data: linhas.map((r) => +taxa(r.demissoes_sjc, r.vinculos)!.toFixed(0)) },
        { name: "Pedido de demissão", type: "line", symbol: "none", lineStyle: { width: 2 }, data: linhas.map((r) => +taxa(r.pedidos, r.vinculos)!.toFixed(0)) },
      ],
    }),
    [linhas],
  );

  const ranking = useMemo(() => {
    const ultimos = new Set(meta.ultimos_12_meses);
    return UFS.map((u) => {
      const ls = serie.filter((r) => r.uf === u && ultimos.has(r.mes));
      return { uf: u, t: (soma(ls, "demissoes_sjc") / (soma(ls, "vinculos") || 1)) * 1e5 };
    }).sort((a, b) => a.t - b.t);
  }, [serie, meta]);

  const rankingOpt = useCallback(
    (c: Cores) => ({
      ...base(c),
      legend: { show: false },
      grid: { left: 8, right: 24, top: 8, bottom: 8, containLabel: true },
      tooltip: { ...(base(c).tooltip as object), axisPointer: { type: "shadow" } },
      xAxis: { ...(base(c).yAxis as object), type: "value" },
      yAxis: { ...(base(c).xAxis as object), type: "category", data: ranking.map((r) => r.uf) },
      series: [{
        name: "Demissões sem justa causa por 100 mil vínculos/mês", type: "bar", barMaxWidth: 14,
        data: ranking.map((r) => ({
          value: +r.t.toFixed(0),
          itemStyle: { borderRadius: [0, 4, 4, 0], color: r.uf === uf ? c.serie[1] : c.serie[0] },
        })),
      }],
    }),
    [ranking, uf],
  );

  const vinc = soma(ult, "vinculos");
  return (
    <>
      <FiltroUf uf={uf} onChange={setUf} />
      <div className="kpis">
        <Kpi rotulo="Demissões sem justa causa (12 meses)" valor={fmt(soma(ult, "demissoes_sjc"))} />
        <Kpi rotulo="Pedidos de demissão (12 meses)" valor={fmt(soma(ult, "pedidos"))} />
        <Kpi rotulo="Rotatividade mensal" valor={`${fmt((100 * soma(ult, "desligamentos")) / (vinc || 1), 2)}%`} detalhe="desligamentos ÷ vínculos" />
      </div>
      <div className="grade">
        <Grafico
          titulo="Taxa de demissão"
          descricao="Desligamentos por 100 mil vínculos no mês, por tipo (Novo CAGED ÷ estoque da RAIS)."
          montar={taxas}
          tabela={{
            colunas: ["Mês", "Sem justa causa", "A pedido", "Vínculos"],
            linhas: linhas.map((r) => [fmtMes(r.mes), fmt(r.demissoes_sjc), fmt(r.pedidos), fmt(r.vinculos)]),
          }}
        />
        <Grafico
          titulo="Demissões sem justa causa por estado"
          descricao={`Média mensal por 100 mil vínculos, últimos 12 meses.${uf !== "BR" ? ` ${uf} em destaque.` : ""}`}
          montar={rankingOpt}
          altura={560}
        />
      </div>
    </>
  );
}
