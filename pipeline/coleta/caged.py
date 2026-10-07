"""Baixa os microdados de movimentações do Novo CAGED (um arquivo por mês)."""
import argparse
import datetime as dt

from pipeline.config import CAGED_URL, RAW
from pipeline.util import baixar, extrair_7z


def meses(inicio: str, fim: str):
    a, m = int(inicio[:4]), int(inicio[4:])
    while f"{a}{m:02d}" <= fim:
        yield a, m
        m += 1
        if m == 13:
            a, m = a + 1, 1


def coletar(inicio: str = "202306", fim: str | None = None) -> None:
    hoje = dt.date.today()
    fim = fim or f"{hoje.year}{hoje.month:02d}"
    pasta = RAW / "caged"
    for ano, mes in meses(inicio, fim):
        txt = pasta / f"CAGEDMOV{ano}{mes:02d}.txt"
        if txt.exists():
            continue
        try:
            arq = baixar(CAGED_URL.format(ano=ano, mes=mes), pasta / f"CAGEDMOV{ano}{mes:02d}.7z")
        except Exception as erro:  # mês ainda não publicado
            print(f"  {ano}{mes:02d} indisponível: {erro}")
            continue
        extrair_7z(arq, pasta)
        arq.unlink()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--inicio", default="202306")
    p.add_argument("--fim")
    a = p.parse_args()
    coletar(a.inicio, a.fim)
