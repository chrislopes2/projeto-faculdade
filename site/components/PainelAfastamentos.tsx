"use client";
import { useCallback, useMemo, useState } from "react";
import type { Cores } from "@/lib/cores";
import { daUf, fmt, fmtMes, soma } from "@/lib/calc";
import type { Bpc, LinhaSerie, Meta, Perfil } from "@/lib/tipos";
import { base, Grafico } from "./Grafico";
import { FiltroUf, useUf } from "./FiltroUf";
import { Kpi } from "./Kpi";

const FAIXAS = ["até 24", "25 a 34", "35 a 44", "45 a 54", "55 ou mais"];

export function PainelAfastamentos({ serie, perfil, bpc, meta }: { serie: LinhaSerie[]; perfil: Perfil[]; bpc: Bpc[]; meta: Meta }) {
  const [uf, setUf] = useUf();
  const [grupo, setGrupo] = useState("todos");
  const linhas = useMemo(() => daUf(serie, uf).filter((r) => r.afast_total != null), [serie, uf]);
  const grupos = meta.grupos_cid;
  const ult = linhas.slice(-12);

  const porGrupo = useCallback(
    (c: Cores) => ({
      ...base(c),
      xAxis: { ...(base(c).xAxis as object), type: "category", data: linhas.map((r) => fmtMes(r.mes)) },
      yAxis: { ...(base(c).yAxis as object), type: "value" },
      series: grupos.map((g) => ({
        name: g.nome, type: "line", symbol: "none", lineStyle: { width: 2 },
        data: linhas.map((r) => r[g.chave as keyof LinhaSerie] as number),
      })),
    }),
    [linhas, grupos],
  );

  const participacao = useCallback(
    (c: Cores) => ({
      ...base(c),
      legend: { show: false },
      xAxis: { ...(base(c).xAxis as object), type: "category", data: linhas.map((r) => fmtMes(r.mes)) },
      yAxis: { ...(base(c).yAxis as object), type: "value", axisLabel: { color: c.mudo, formatter: "{value}%" } },
      series: [{
        name: "Saúde mental", type: "line", symbol: "none", lineStyle: { width: 2 },
        data: linhas.map((r) => +((100 * (r.afast_mental ?? 0)) / (r.afast_total || 1)).toFixed(1)),
      }],
    }),
    [linhas],
  );

  const perfilFiltrado = perfil.filter((p) => grupo === "todos" || p.grupo === grupo);
  const contar = (sexo: string) => FAIXAS.map((f) => perfilFiltrado.filter((p) => p.sexo === sexo && p.faixa === f).reduce((s, p) => s + p.n, 0));
  const perfilOpt = useCallback(
    (c: Cores) => ({
      ...base(c),
      tooltip: { ...(base(c).tooltip as object), axisPointer: { type: "shadow" } },
      xAxis: { ...(base(c).xAxis as object), type: "category", data: FAIXAS, name: "idade" },
      yAxis: { ...(base(c).yAxis as object), type: "value" },
      series: [
        { name: "Mulheres", type: "bar", data: contar("F"), barMaxWidth: 28, itemStyle: { borderRadius: [4, 4, 0, 0] } },
        { name: "Homens", type: "bar", data: contar("M"), barMaxWidth: 28, itemStyle: { borderRadius: [4, 4, 0, 0] } },
      ],
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [grupo, perfil],
  );

  const bpcOpt = useCallback(
    (c: Cores) => ({
      ...base(c),
      xAxis: { ...(base(c).xAxis as object), type: "category", data: bpc.map((r) => fmtMes(r.mes)) },
      yAxis: { ...(base(c).yAxis as object), type: "value" },
      series: [
        { name: "BPC (pessoa com deficiência)", type: "line", symbol: "none", lineStyle: { width: 2 }, data: bpc.map((r) => r.bpc) },
        { name: "Afastamento do trabalho", type: "line", symbol: "none", lineStyle: { width: 2 }, data: bpc.map((r) => r.afastamento) },
      ],
    }),
    [bpc],
  );

  return (
    <>
      <FiltroUf uf={uf} onChange={setUf} />
      <div className="kpis">
        {grupos.slice(0, 4).map((g) => (
          <Kpi key={g.chave} rotulo={`${g.nome} (12 meses)`} valor={fmt(soma(ult, g.chave as keyof LinhaSerie))} detalhe={g.cids.join(", ")} />
        ))}
        <Kpi
          rotulo="Reconhecidos como causados pelo trabalho"
          valor={`${fmt((100 * soma(ult, "afast_mental_acid")) / (soma(ult, "afast_mental") || 1), 1)}%`}
          detalhe="espécie 91 (acidentário)"
        />
      </div>
      <div className="grade">
        <Grafico
          titulo="Afastamentos por grupo de CID"
          descricao="Número de auxílios por incapacidade temporária concedidos no mês (espécies 31 e 91)."
          montar={porGrupo}
          tabela={{ colunas: ["Mês", ...grupos.map((g) => g.nome)], linhas: linhas.map((r) => [fmtMes(r.mes), ...grupos.map((g) => r[g.chave as keyof LinhaSerie] as number)]) }}
        />
        <Grafico titulo="Saúde mental no total de afastamentos" descricao="Percentual dos afastamentos concedidos no mês." montar={participacao} />
        <div>
          <div className="filtros" style={{ margin: "0 0 8px" }}>
            <label>
              Grupo{" "}
              <select value={grupo} onChange={(e) => setGrupo(e.target.value)}>
                <option value="todos">Todos os transtornos mentais</option>
                {grupos.map((g) => <option key={g.chave} value={g.chave}>{g.nome}</option>)}
              </select>
            </label>
          </div>
          <Grafico titulo="Quem se afasta: sexo e idade" descricao="Brasil, últimos 12 meses." montar={perfilOpt} />
        </div>
        <Grafico
          titulo="Autismo: BPC × afastamento"
          descricao="Número de concessões com CID F84 no Brasil, por mês. O autismo aparece muito mais no BPC do que como afastamento do trabalho."
          montar={bpcOpt}
        />
      </div>
    </>
  );
}
