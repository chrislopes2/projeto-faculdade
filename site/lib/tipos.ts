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
export type Setor = { setor: string; nome: string; afast_mental: number; demissoes_sjc: number; vinculos_medio: number | null };
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
};
export type Dados = { serie: LinhaSerie[]; perfil: Perfil[]; setores: Setor[]; bpc: Bpc[]; correlacao: Correlacao; meta: Meta };
