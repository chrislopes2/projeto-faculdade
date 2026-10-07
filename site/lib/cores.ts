// Paleta categórica validada (ordem fixa: a cor segue a série, nunca a posição).
export type Cores = {
  serie: string[];
  texto: string;
  texto2: string;
  mudo: string;
  grade: string;
  eixo: string;
  superficie: string;
};

export const CLARO: Cores = {
  serie: ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"],
  texto: "#0b0b0b",
  texto2: "#52514e",
  mudo: "#898781",
  grade: "#e1e0d9",
  eixo: "#c3c2b7",
  superficie: "#fcfcfb",
};

export const ESCURO: Cores = {
  serie: ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"],
  texto: "#ffffff",
  texto2: "#c3c2b7",
  mudo: "#898781",
  grade: "#2c2c2a",
  eixo: "#383835",
  superficie: "#1a1a19",
};
