export type LinhaSerie = {
  uf: string;
  mes: string;
  afast_total: number | null;
  afast_mental: number | null;
  afast_mental_acid: number | null;
  depressao: number | null;
  ansiedade: number | null;
  estresse_burnout: number | null;
  autismo: number | null;
  outros_mentais: number | null;
  demissoes_sjc: number | null;
  pedidos: number | null;
  desligamentos: number | null;
  admissoes: number | null;
  vinculos: number | null;
};
export type Perfil = { grupo: string; sexo: string; faixa: string; n: number };
export type Filiacao = { mes: string; empregado: number; desempregado: number; autonomo: number; outros: number };
export type Bpc = { mes: string; bpc: number; afastamento: number };
export type Correlacao = {
  serie_nacional: { defasagem_meses: number; r: number | null; n_meses: number }[];
  entre_ufs: { r: number | null; n_ufs: number; meses: string[] };
};
export type Meta = {
  gerado_em: string;
  exemplo: boolean;
  periodo: { inicio: string; fim: string };
  ultimos_12_meses: string[];
  grupos_cid: { chave: string; nome: string; cids: string[] }[];
  filiacoes: { chave: string; nome: string }[];
};

type Coef = { coef_td: number | null; p_valor: number | null; ic95: (number | null)[]; r2: number | null; n: number };
type PorMes = { mes: string; afast_mental: number; afast_total: number; demissoes_sjc: number; vinculos: number; taxa_afast: number; taxa_demissao: number };
export type Analise = {
  exemplo: boolean;
  textos: Partial<Record<"regressao" | "granger" | "painel" | "floresta" | "agrupamento" | "previsao", string>>;
  kpis: {
    meses: string[]; meses_anteriores: string[];
    afast_mental_12m: number; afast_mental_12m_anteriores: number; variacao_pct: number | null;
    afast_total_12m: number; parte_mental_pct: number; vinculos_soma_12m: number; vinculos_medio: number;
    taxa_afast_mes: number; demissoes_12m: number; taxa_demissao_mes: number; por_mes: PorMes[];
  };
  regressao?: { formula: string; modelos: { defasagem_meses: number; coef: number; p_valor: number; ic95: number[]; r2: number; n: number }[] };
  granger?: { testes: Record<string, { defasagem_meses: number; p_valor: number; f: number }[]>; n_meses: number };
  painel?: { sem_controles: Coef; efeitos_fixos: Coef; efeitos_fixos_com_admissoes: Coef; n_ufs: number; n_meses: number };
  floresta?: {
    treino: { de: string; ate: string }; teste: { de: string; ate: string };
    r2: number; mae: number; r2_sem_mercado: number; mae_sem_mercado: number; r2_base: number; mae_base: number;
    importancias: { variavel: string; nome: string; importancia: number }[];
  };
  agrupamento?: {
    k: number; silhueta: number;
    grupos: { nome: string; descricao: string; ufs: string[] }[];
    ufs: { uf: string; taxa_afastamento: number; taxa_demissao: number; parte_mental: number; crescimento: number; grupo: string }[];
  };
  previsao?: {
    modelo: string; meses_interpolados: string[];
    historico: { mes: string; valor: number }[];
    previsao: { mes: string; valor: number; min80: number; max80: number }[];
  };
  anomalias?: { total_anomalos: number; n: number; lista: { uf: string; mes: string; taxa_afastamento: number; taxa_demissao: number; z_afastamento: number; z_demissao: number }[] };
};
export type Memoria = {
  meses: string[];
  inss_por_especie: { especie: number; n: number; sem_uf: number; mental: number }[];
  inss_grupos_afastamento: { grupo: string; n: number }[];
  caged_movimentos: { tipo: string; n: number }[];
  rais_vinculos: { ano: number; vinculos: number }[];
  meses_inss: string[];
  meses_caged: string[];
};
export type Dados = {
  serie: LinhaSerie[]; perfil: Perfil[]; filiacao: Filiacao[]; bpc: Bpc[]; correlacao: Correlacao; meta: Meta;
  analise: Analise; memoria: Memoria;
};
