import Link from "next/link";
import { BASE, fmt, fmtMes } from "@/lib/calc";
import { carregar } from "@/lib/dados";

const ESPECIES: Record<number, string> = {
  31: "Auxílio por incapacidade temporária (comum)",
  91: "Auxílio por incapacidade temporária (acidentário)",
  32: "Aposentadoria por incapacidade permanente (comum)",
  92: "Aposentadoria por incapacidade permanente (acidentária)",
  87: "BPC – pessoa com deficiência",
};
const MOVIMENTOS: Record<string, string> = {
  sem_justa_causa: "Demissão sem justa causa (tipo 31)",
  a_pedido: "Pedido de demissão (tipo 40)",
  outros_desligamentos: "Outros desligamentos",
  admissoes: "Admissões",
};

function T({ colunas, linhas }: { colunas: string[]; linhas: (string | number)[][] }) {
  return (
    <div className="tabela-rolagem sem-limite">
      <table>
        <thead><tr>{colunas.map((c) => <th key={c}>{c}</th>)}</tr></thead>
        <tbody>{linhas.map((l, i) => <tr key={i}>{l.map((v, j) => <td key={j}>{v}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}

export default function Pagina() {
  const { memoria: m, analise, meta } = carregar();
  const k = analise.kpis;
  const nomeGrupo = (g: string) => meta.grupos_cid.find((x) => x.chave === g)?.nome ?? "Outras doenças (fora da saúde mental)";
  const todos: string[] = [];
  for (let d = new Date(meta.periodo.inicio + "-01T12:00"); d <= new Date(meta.periodo.fim + "-01T12:00"); d.setMonth(d.getMonth() + 1)) {
    todos.push(d.toISOString().slice(0, 7));
  }
  const faltam = todos.filter((x) => !m.meses_inss.includes(x));

  return (
    <div className="texto">
      <h1>Memória de cálculo</h1>
      <p className="lead">
        O caminho de cada número: o que foi filtrado em cada base, como as bases foram cruzadas e a conta dos indicadores, com os
        valores dos {k.meses.length} meses mais recentes ({fmtMes(k.meses[0])} a {fmtMes(k.meses[k.meses.length - 1])}).
      </p>

      <h2>O racional</h2>
      <ol>
        <li>O INSS diz <b>quantas pessoas foram afastadas</b> e por qual doença (CID), mas não diz se foram demitidas.</li>
        <li>O CAGED diz <b>quantas pessoas foram demitidas</b>, mas não diz se adoeceram.</li>
        <li>As bases são anônimas e não se ligam por pessoa. Então elas são cruzadas pelo que têm em comum: <b>o mês e o estado</b>.</li>
        <li>Estados grandes têm mais de tudo. Para comparar, as contagens viram <b>taxas por 100 mil vínculos formais</b>, usando a RAIS como denominador.</li>
        <li>Com as duas taxas lado a lado, mede-se se andam juntas (correlação) e testa-se se a relação resiste a controles (regressões e modelos de IA, na aba <Link href="/analises/">Análises</Link>).</li>
      </ol>

      <h2>Etapa 1: benefícios do INSS</h2>
      <p>Todos os benefícios concedidos nas espécies de interesse, nos meses do período. A UF vem do município de residência.</p>
      <T
        colunas={["Espécie", "Concedidos", "Sem UF", "Com CID de saúde mental"]}
        linhas={m.inss_por_especie.map((e) => [`${e.especie} – ${ESPECIES[e.especie] ?? ""}`, fmt(e.n), fmt(e.sem_uf), fmt(e.mental)])}
      />
      <p>
        Entram como <b>afastamento</b> só as espécies 31 e 91. Entre elas, com UF identificada, por grupo de CID (capítulo F e Z73
        contam como saúde mental; o primeiro prefixo que casar define o grupo):
      </p>
      <T colunas={["Grupo de CID", "Afastamentos"]} linhas={m.inss_grupos_afastamento.map((g) => [nomeGrupo(g.grupo), fmt(g.n)])} />
      {faltam.length > 0 && (
        <p className="nota">Meses do período sem arquivo do INSS: {faltam.map(fmtMes).join(", ")}. Eles ficam fora das somas e das taxas.</p>
      )}

      <h2>Etapa 2: movimentações do CAGED</h2>
      <T colunas={["Tipo", "Movimentações"]} linhas={m.caged_movimentos.map((c) => [MOVIMENTOS[c.tipo] ?? c.tipo, fmt(c.n)])} />
      <p>O site usa as demissões sem justa causa, que são decisão do empregador. Pedidos de demissão aparecem à parte.</p>

      <h2>Etapa 3: denominador (RAIS)</h2>
      <T colunas={["Ano", "Vínculos ativos em 31/12"]} linhas={m.rais_vinculos.map((r) => [r.ano, fmt(r.vinculos)])} />
      <p>Cada mês usa a RAIS mais recente disponível até o seu ano.</p>

      <h2>Etapa 4: cruzamento por mês (Brasil)</h2>
      <p>A mesma tabela existe para cada estado; o Brasil é a soma dos estados.</p>
      <T
        colunas={["Mês", "Afast. saúde mental", "Afast. total", "Demissões s/ justa causa", "Vínculos", "Afast./100 mil", "Dem./100 mil"]}
        linhas={k.por_mes.map((r) => [fmtMes(r.mes), fmt(r.afast_mental), fmt(r.afast_total), fmt(r.demissoes_sjc), fmt(r.vinculos), fmt(r.taxa_afast, 1), fmt(r.taxa_demissao, 0)])}
      />

      <h2>Etapa 5: os indicadores da página inicial</h2>
      <div className="formula">afastamentos em 12 meses = Σ afastamentos por saúde mental = <b>{fmt(k.afast_mental_12m)}</b></div>
      {k.variacao_pct != null && (
        <div className="formula">variação = {fmt(k.afast_mental_12m)} ÷ {fmt(k.afast_mental_12m_anteriores)} − 1 = <b>{fmt(k.variacao_pct, 1)}%</b></div>
      )}
      <div className="formula">parte mental = {fmt(k.afast_mental_12m)} ÷ {fmt(k.afast_total_12m)} = <b>{fmt(k.parte_mental_pct, 1)}%</b></div>
      <div className="formula">taxa de afastamento = {fmt(k.afast_mental_12m)} ÷ {fmt(k.vinculos_soma_12m)} × 100.000 = <b>{fmt(k.taxa_afast_mes, 1)}</b> por 100 mil vínculos por mês</div>
      <div className="formula">taxa de demissão = {fmt(k.demissoes_12m)} ÷ {fmt(k.vinculos_soma_12m)} × 100.000 = <b>{fmt(k.taxa_demissao_mes, 1)}</b> por 100 mil vínculos por mês</div>
      <p>
        A soma dos vínculos é a soma dos estoques mensais ({k.meses.length} meses × cerca de {fmt(k.vinculos_medio)}), por isso o
        resultado já sai como média por mês.
      </p>

      <h2>Etapa 6: índice e correlações</h2>
      <div className="formula">índice = taxa do mês ÷ média da taxa nos 3 primeiros meses × 100</div>
      <div className="formula">r de Pearson = cov(taxa de demissão, taxa de afastamento) ÷ (desvio da demissão × desvio do afastamento)</div>
      <p>
        Entre estados usa-se a taxa de cada UF nos últimos 12 meses (27 pontos). Na série nacional, a taxa de demissão do mês t é
        comparada com a de afastamento do mês t + k, para k = 0, 3, 6 e 12.
      </p>
      <p className="nota">
        O código de cada etapa está em pipeline/agregar.py e pipeline/analise.py. O <a href={`${BASE}/relatorio.pdf`}>relatório em PDF</a> traz esta
        memória e as análises completas.
      </p>
    </div>
  );
}
