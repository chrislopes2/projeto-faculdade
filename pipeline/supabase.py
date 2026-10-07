"""Envia os resultados do pipeline (site/public/data/*.json) para o Supabase.

Precisa das variáveis de ambiente SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY
(no GitHub, guardadas como secrets). As tabelas são criadas por supabase/schema.sql.
"""
import json
import os

import requests

from pipeline.config import SAIDA

LOTE = 1000


def _enviar(url: str, chave: str, tabela: str, linhas: list[dict], conflito: str) -> None:
    cab = {
        "apikey": chave,
        "Authorization": f"Bearer {chave}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    for i in range(0, len(linhas), LOTE):
        r = requests.post(f"{url}/rest/v1/{tabela}?on_conflict={conflito}", headers=cab,
                          data=json.dumps(linhas[i:i + LOTE]), timeout=120)
        if r.status_code >= 300:
            raise SystemExit(f"Supabase recusou {tabela}: {r.status_code} {r.text[:300]}")
    print(f"  {tabela}: {len(linhas)} linhas")


def enviar() -> None:
    url = os.environ["SUPABASE_URL"].rstrip("/")
    chave = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    ler = lambda n: json.loads((SAIDA / n).read_text(encoding="utf-8"))  # noqa: E731

    if ler("meta.json").get("exemplo"):
        raise SystemExit("Dados de exemplo: nada foi enviado ao Supabase.")

    corr = ler("correlacao.json")
    correlacoes = [{"tipo": "serie_nacional", "defasagem_meses": d["defasagem_meses"], "r": d["r"], "n": d["n_meses"]}
                   for d in corr["serie_nacional"]]
    correlacoes.append({"tipo": "entre_ufs", "defasagem_meses": 0, "r": corr["entre_ufs"]["r"], "n": corr["entre_ufs"]["n_ufs"]})

    print("Enviando ao Supabase")
    _enviar(url, chave, "serie_mensal", ler("serie.json"), "uf,mes")
    _enviar(url, chave, "perfil_afastamentos", ler("perfil.json"), "grupo,sexo,faixa")
    _enviar(url, chave, "setores", ler("setores.json"), "setor")
    _enviar(url, chave, "bpc_autismo", ler("bpc_autismo.json"), "mes")
    _enviar(url, chave, "correlacoes", correlacoes, "tipo,defasagem_meses")


if __name__ == "__main__":
    enviar()
