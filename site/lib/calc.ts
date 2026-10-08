import type { LinhaSerie } from "./tipos";

export const BASE = process.env.NEXT_PUBLIC_BASE ?? "";
export const POR = 100_000; // taxas por 100 mil vínculos formais

export const taxa = (n: number | null, base: number | null) =>
  n == null || !base ? null : (n / base) * POR;

export const daUf = (serie: LinhaSerie[], uf: string) => serie.filter((r) => r.uf === uf);

export function soma(linhas: LinhaSerie[], campo: keyof LinhaSerie) {
  return linhas.reduce((t, r) => t + (Number(r[campo]) || 0), 0);
}

export const fmt = (v: number | null | undefined, casas = 0) =>
  v == null || Number.isNaN(v) ? "–" : v.toLocaleString("pt-BR", { maximumFractionDigits: casas, minimumFractionDigits: casas });

export const fmtMes = (m: string) => {
  const [a, mm] = m.split("-");
  return ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"][Number(mm) - 1] + "/" + a.slice(2);
};

export const UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"];
