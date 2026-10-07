"use client";
import { useEffect, useState } from "react";
import { UFS } from "@/lib/calc";

const CHAVE = "filtro-uf";

/** Filtro de UF compartilhado entre as páginas (lembrado no navegador). */
export function useUf(): [string, (uf: string) => void] {
  const [uf, setUf] = useState("BR");
  useEffect(() => {
    try {
      const salvo = localStorage.getItem(CHAVE);
      if (salvo) setUf(salvo);
    } catch {}
  }, []);
  const mudar = (v: string) => {
    setUf(v);
    try {
      localStorage.setItem(CHAVE, v);
    } catch {}
  };
  return [uf, mudar];
}

export function FiltroUf({ uf, onChange }: { uf: string; onChange: (uf: string) => void }) {
  return (
    <div className="filtros">
      <label>
        Local{" "}
        <select value={uf} onChange={(e) => onChange(e.target.value)}>
          <option value="BR">Brasil</option>
          {UFS.map((u) => (
            <option key={u} value={u}>{u}</option>
          ))}
        </select>
      </label>
    </div>
  );
}
