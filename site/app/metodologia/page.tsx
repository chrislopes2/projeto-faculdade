import { carregar } from "@/lib/dados";

export default function Pagina() {
  const { meta } = carregar();
  return (
    <div className="texto">
      <h1>Metodologia</h1>
      <p className="lead">De onde vêm os números, como foram calculados e o que eles não dizem.</p>

      <h2>Fontes</h2>
      <ul>
        <li>
          <a href="https://dadosabertos.inss.gov.br/dataset/beneficios-concedidos-plano-de-dados-abertos-jun-2023-a-jun-2025">INSS – Benefícios concedidos</a>:
          um registro por benefício, com espécie, CID-10, UF, sexo e data de nascimento. Mensal, desde jun/2023.
        </li>
        <li>
          <a href="https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/estatisticas-trabalho/novo-caged">Novo CAGED (MTE)</a>:
          admissões e desligamentos de empregos formais, com o tipo de desligamento.
        </li>
        <li>
          <a href="https://pdet.mte.gov.br/">RAIS (MTE)</a>: estoque de vínculos ativos em 31/12, usado como denominador das taxas.
        </li>
      </ul>

      <h2>O que conta como afastamento por saúde mental</h2>
      <p>
        Auxílios por incapacidade temporária concedidos (espécies 31, comum, e 91, acidentário) com CID do capítulo F
        ou Z73 (burnout). Os grupos usados no site:
      </p>
      <ul>
        {meta.grupos_cid.map((g) => (
          <li key={g.chave}>{g.nome}: {g.cids.join(", ")}{g.chave === "outros_mentais" ? " (demais códigos do capítulo F)" : ""}</li>
        ))}
      </ul>

      <h2>Cálculos</h2>
      <ul>
        <li>Taxa de afastamento = afastamentos no mês ÷ vínculos formais × 100 mil.</li>
        <li>Taxa de demissão = demissões sem justa causa no mês ÷ vínculos formais × 100 mil.</li>
        <li>Para cada mês usa-se a RAIS mais recente disponível até aquele ano.</li>
        <li>Correlação de Pearson, entre estados (últimos 12 meses) e na série nacional com 0, 3, 6 e 12 meses de defasagem.</li>
      </ul>

      <h2>Limitações</h2>
      <ul>
        <li>Correlação não é causalidade. Crises econômicas, sazonalidade e mudanças nas regras do INSS afetam as duas taxas.</li>
        <li>Só o trabalho formal entra nas contas. Informais e servidores de regime próprio ficam de fora.</li>
        <li>As bases são anonimizadas e não se ligam por pessoa: o cruzamento é por mês e estado.</li>
        <li>O INSS quase nunca informa o setor (CNAE) do segurado, por isso não há recorte por setor. A UF é a de residência.</li>
        <li>O autismo (F84) aparece sobretudo no BPC (espécie 87), não como afastamento, e é mostrado à parte.</li>
        <li>Burnout costuma ser registrado também como F43 (reação ao estresse), por isso os dois ficam no mesmo grupo.</li>
      </ul>
      <p className="nota">Período coberto: {meta.periodo.inicio} a {meta.periodo.fim}. Gerado em {new Date(meta.gerado_em).toLocaleString("pt-BR")}.</p>
    </div>
  );
}
