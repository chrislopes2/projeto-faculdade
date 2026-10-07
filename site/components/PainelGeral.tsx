"use client";
import { useCallback, useMemo } from "react";
import type { Cores } from "@/lib/cores";
import { daUf, fmt, fmtMes, soma, taxa } from "@/lib/calc";
import type { LinhaSerie, Meta } from "@/lib/tipos";
import { base, Grafico } from "./Grafico";
import { FiltroUf, useUf } from "./FiltroUf";
import { Kpi } from "./Kpi";

export function PainelGeral({ serie, meta }: { serie: LinhaSerie[]; meta: Meta }) {
  const [uf, setUf] = useUf();
  const linhas = useMemo(
    () => daUf(serie, uf).filter((r) => r.afast_mental != null && r.demissoes_sjc != null && r.vinculos),
    [serie, uf],
  );
  const ult = linhas.slice(-12);
  const ant = linhas.slice(-24, -12);
  const afast12 = soma(ult, "afast_mental");
  const afastAnt = ant.length === 12 ? soma(ant, "afast_mental") : null;
  const dem12 = soma(ult, "demissoes_sjc");
  const vinc12 = soma(ult, "vinculos");
  const partMental = afast12 / (soma(ult, "afast_total") || 1);

  // Índice base 100 = média dos 3 primeiros meses: põe as duas taxas na mesma escala sem dois eixos.
  const indices = useMemo(() => {
    const ta = linhas.map((r) => taxa(r.afast_mental, r.vinculos)!);
    const td = linhas.map((r) => taxa(r.demissoes_sjc, r.vinculos)!);
    const b = (v: number[]) => v.slice(0, 3).reduce((s, x) => s + x, 0) / Math.min(3, v.length);
    return { ta: ta.map((v) => (v / b(ta)) * 100), td: td.map((v) => (v / b(td)) * 100) };
  }, [linhas]);

  const montar = useCallback(
    (c: Cores) => ({
      ...base(c),
      xAxis: { ...(base(c).xAxis as object), type: "category", data: linhas.map((r) => fmtMes(r.mes)) },
      yAxis: { ...(base(c).yAxis as object), type: "value", scale: true },
      series: [
        { name: "Afastamentos por saúde mental", type: "line", data: indices.ta.map((v) => +v.toFixed(1)), symbol: "none", lineStyle: { width: 2 } },
        { name: "Demissões sem justa causa", type: "line", data: indices.td.map((v) => +v.toFixed(1)), symbol: "none", lineStyle: { width: 2 } },
      ],
    }),
    [linhas, indices],
  );

  return (
    <>
      <FiltroUf uf={uf} onChange={setUf} />
      <div className="kpis">
        <Kpi
          rotulo="Afastamentos por saúde mental (12 meses)"
          valor={fmt(afast12)}
          detalhe={afastAnt ? `${afast12 >= afastAnt ? "+" : ""}${fmt(((afast12 - afastAnt) / afastAnt) * 100, 1)}% sobre os 12 meses anteriores` : undefined}
        />
        <Kpi rotulo="Por 100 mil vínculos, por mês" valor={fmt((afast12 / vinc12) * 1e5, 1)} />
        <Kpi rotulo="Parte dos afastamentos que é saúde mental" valor={`${fmt(partMental * 100, 1)}%`} />
        <Kpi rotulo="Demissões sem justa causa (12 meses)" valor={fmt(dem12)} detalhe={`${fmt((dem12 / vinc12) * 1e5, 0)} por 100 mil vínculos/mês`} />
      </div>
      <Grafico
        titulo="Afastamentos e demissões, em índice"
        descricao="Cada linha é a taxa por 100 mil vínculos, com a média dos três primeiros meses valendo 100. Assim as duas cabem na mesma escala."
        montar={montar}
        altura={360}
        tabela={{
          colunas: ["Mês", "Índice afastamentos", "Índice demissões"],
          linhas: linhas.map((r, i) => [fmtMes(r.mes), fmt(indices.ta[i], 1), fmt(indices.td[i], 1)]),
        }}
      />
      <p className="nota">Período: {fmtMes(meta.periodo.inicio)} a {fmtMes(meta.periodo.fim)}. Subir junto não prova que uma coisa causa a outra.</p>
    </>
  );
}
