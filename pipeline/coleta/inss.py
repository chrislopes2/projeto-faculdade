"""Baixa os arquivos mensais de benefícios concedidos do portal de dados abertos do INSS."""
import json
import re
import urllib.request

from pipeline.config import INSS_CKAN, INSS_PACOTE, RAW
from pipeline.util import baixar

MESES = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
         "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}


def competencia_do_recurso(nome: str, url: str) -> str | None:
    """Tenta descobrir AAAAMM pelo nome ou URL do recurso."""
    texto = f"{nome} {url}".lower()
    m = re.search(r"(20\d{2})[-_]?(0[1-9]|1[0-2])", texto)
    if m:
        return m.group(1) + m.group(2)
    m = re.search(r"(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\w*[\s/_-]*(20\d{2})", texto)
    if m:
        return f"{m.group(2)}{MESES[m.group(1)]:02d}"
    return None


def coletar() -> None:
    destino = RAW / "inss"
    url = f"{INSS_CKAN}?id={INSS_PACOTE}"
    print(f"INSS: lendo a lista de arquivos em {url}")
    with urllib.request.urlopen(url, timeout=120) as resp:
        pacote = json.load(resp)["result"]
    for rec in pacote["resources"]:
        link = rec.get("url", "")
        ext = link.rsplit(".", 1)[-1].lower()
        if ext not in ("csv", "xlsx", "xls", "zip"):
            continue
        comp = competencia_do_recurso(rec.get("name", ""), link)
        if not comp:
            print(f"  ignorado (sem competência no nome): {rec.get('name')}")
            continue
        baixar(link, destino / f"concedidos_{comp}.{ext}")


if __name__ == "__main__":
    coletar()
