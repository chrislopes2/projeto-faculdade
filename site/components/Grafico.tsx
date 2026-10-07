"use client";
import * as echarts from "echarts";
import { useEffect, useRef, useState } from "react";
import { CLARO, ESCURO, type Cores } from "@/lib/cores";

export type Tabela = { colunas: string[]; linhas: (string | number | null)[][] };

function useCores(): Cores {
  const [escuro, setEscuro] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const atualizar = () => setEscuro(mq.matches);
    atualizar();
    mq.addEventListener("change", atualizar);
    return () => mq.removeEventListener("change", atualizar);
  }, []);
  return escuro ? ESCURO : CLARO;
}

/** Opções comuns: eixos discretos, grade fina, tooltip com crosshair. */
export function base(c: Cores): echarts.EChartsOption {
  const eixo = {
    axisLine: { lineStyle: { color: c.eixo } },
    axisTick: { show: false },
    axisLabel: { color: c.mudo, fontSize: 11, formatter: (v: number | string) => (typeof v === "number" ? v.toLocaleString("pt-BR") : v) },
    splitLine: { lineStyle: { color: c.grade, width: 1 } },
    nameTextStyle: { color: c.mudo, fontSize: 11 },
  };
  return {
    color: c.serie,
    backgroundColor: "transparent",
    textStyle: { fontFamily: "system-ui, -apple-system, 'Segoe UI', sans-serif", color: c.texto2 },
    grid: { left: 8, right: 16, top: 40, bottom: 8, containLabel: true },
    legend: { top: 0, left: 0, icon: "roundRect", itemWidth: 12, itemHeight: 4, textStyle: { color: c.texto2 } },
    tooltip: {
      trigger: "axis",
      backgroundColor: c.superficie,
      borderColor: c.grade,
      textStyle: { color: c.texto, fontSize: 12 },
      axisPointer: { type: "line", lineStyle: { color: c.eixo } },
    },
    xAxis: { ...eixo, splitLine: { show: false } } as echarts.XAXisComponentOption,
    yAxis: { ...eixo, axisLine: { show: false } } as echarts.YAXisComponentOption,
  };
}

export function Grafico({
  titulo,
  descricao,
  montar,
  tabela,
  altura = 320,
}: {
  titulo: string;
  descricao?: string;
  // Objeto de opções do ECharts; tipado de forma solta porque os tipos do ECharts são estritos demais para montar por partes.
  montar: (c: Cores) => object;
  tabela?: Tabela;
  altura?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const cores = useCores();

  useEffect(() => {
    if (!ref.current) return;
    const grafico = echarts.init(ref.current, undefined, { renderer: "svg" });
    grafico.setOption(montar(cores) as echarts.EChartsOption);
    const ro = new ResizeObserver(() => grafico.resize());
    ro.observe(ref.current);
    return () => {
      ro.disconnect();
      grafico.dispose();
    };
  }, [montar, cores]);

  return (
    <figure className="cartao">
      <figcaption>
        <h3>{titulo}</h3>
        {descricao && <p className="desc">{descricao}</p>}
      </figcaption>
      <div ref={ref} style={{ height: altura, width: "100%" }} role="img" aria-label={titulo} />
      {tabela && (
        <details>
          <summary>Ver tabela</summary>
          <div className="tabela-rolagem">
            <table>
              <thead>
                <tr>{tabela.colunas.map((c) => <th key={c}>{c}</th>)}</tr>
              </thead>
              <tbody>
                {tabela.linhas.map((l, i) => (
                  <tr key={i}>{l.map((v, j) => <td key={j}>{v ?? "–"}</td>)}</tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </figure>
  );
}
