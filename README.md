# Demissões e saúde mental

Site com dashboards que relacionam as demissões no Brasil com os afastamentos do trabalho
por transtornos mentais (depressão, ansiedade, burnout, autismo e outros).

- **Afastamentos:** INSS, benefícios concedidos por mês com CID (espécies 31 e 91; BPC 87 para autismo).
- **Demissões:** Novo CAGED, microdados de movimentações.
- **Denominador:** RAIS, vínculos formais ativos por UF e setor.

## Estrutura

```
pipeline/
  config.py        CIDs, espécies, códigos do CAGED, URLs
  coleta/          download de cada fonte (inss.py, caged.py, rais.py)
  transformar.py   brutos -> data/clean/*.parquet
  agregar.py       cruza as fontes e gera site/public/data/*.json
  exemplo.py       gera dados FICTÍCIOS no formato real, para testes
  run.py           roda tudo
site/              Next.js + Apache ECharts, exportado como site estático
.github/workflows/ atualização mensal e publicação no GitHub Pages
```

## Rodando

```bash
pip install -r requirements.txt

# Com dados fictícios (não precisa de internet)
python -m pipeline.run --exemplo

# Com dados reais (baixa INSS, CAGED desde jun/2023 e RAIS 2023-2024; a RAIS tem vários GB)
python -m pipeline.run

cd site
npm install
npm run dev      # http://localhost:3000
npm run build    # gera site/out
```

O site mostra uma faixa amarela de "dados de exemplo" enquanto os JSON vierem do modo `--exemplo`.

## Publicação

No GitHub, em Settings > Pages, escolha "GitHub Actions" como fonte. O workflow roda todo dia 20 e quando
disparado à mão em Actions (lá dá para escolher dados de exemplo, útil para a primeira publicação).

## Pontos a conferir na primeira carga real

- **INSS:** os nomes de coluna mudam entre meses. `transformar.py` procura cada campo por palavra-chave
  e avisa no log quando não acha espécie, CID ou UF. Se aparecer esse aviso, ajuste as chaves em `limpar_inss`.
- **CAGED:** os códigos de `tipomovimentação` (31 = sem justa causa, 40 = a pedido) estão em `config.py`;
  confira no dicionário do layout do Novo CAGED no PDET.
- **Setores:** o INSS informa "ramo de atividade", não CNAE. A correspondência em `config.SETORES` é aproximada.
