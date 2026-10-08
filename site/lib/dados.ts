// Lido no build (servidor): os JSON são gerados pelo pipeline em public/data.
import fs from "node:fs";
import path from "node:path";
import type { Dados } from "./tipos";

function ler<T>(nome: string): T {
  return JSON.parse(fs.readFileSync(path.join(process.cwd(), "public", "data", nome), "utf-8"));
}

export function carregar(): Dados {
  return {
    serie: ler("serie.json"),
    perfil: ler("perfil.json"),
    filiacao: ler("filiacao.json"),
    bpc: ler("bpc_autismo.json"),
    correlacao: ler("correlacao.json"),
    meta: ler("meta.json"),
  };
}
