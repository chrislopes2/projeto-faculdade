import { PainelAnalises } from "@/components/PainelAnalises";
import { BASE } from "@/lib/calc";
import { carregar } from "@/lib/dados";

export default function Pagina() {
  const { analise } = carregar();
  return (
    <div className="analises">
      <h1>Análises com estatística e IA</h1>
      <p className="lead">
        Modelos de statsmodels e scikit-learn testam se a relação entre demissões e afastamentos resiste a controles, se as
        demissões ajudam a prever os afastamentos e que estados se parecem. Os textos se atualizam a cada carga de dados.
      </p>
      <p><a className="botao" href={`${BASE}/relatorio.pdf`}>Baixar o relatório completo (PDF)</a></p>
      <PainelAnalises a={analise} />
      <p className="nota">Código em pipeline/analise.py. Semente aleatória fixa (42), então os resultados são reproduzíveis.</p>
    </div>
  );
}
