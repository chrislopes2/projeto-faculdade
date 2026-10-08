"""Roda o pipeline inteiro.

    python -m pipeline.run --exemplo        # dados fictícios, sem internet
    python -m pipeline.run --rais 2023 2024 # dados reais (precisa de acesso aos sites do governo)
"""
import argparse

from pipeline import agregar, analise, relatorio, transformar


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--exemplo", action="store_true", help="usa dados fictícios gerados localmente")
    p.add_argument("--inicio", default="202306", help="primeiro mês do CAGED (AAAAMM)")
    p.add_argument("--rais", nargs="+", type=int, default=[2023, 2024], help="anos da RAIS")
    p.add_argument("--sem-coleta", action="store_true", help="pula o download e usa data/raw")
    a = p.parse_args()

    if a.exemplo:
        from pipeline import exemplo
        exemplo.gerar()
    elif not a.sem_coleta:
        from pipeline.coleta import caged, inss, rais
        inss.coletar()
        caged.coletar(a.inicio)
        for ano in a.rais:
            rais.coletar(ano)
    transformar.transformar()
    agregar.agregar(exemplo=a.exemplo)
    print("Análises")
    analise.analisar()
    print("Relatório")
    relatorio.gerar()


if __name__ == "__main__":
    main()
