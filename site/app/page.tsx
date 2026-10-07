import { PainelGeral } from "@/components/PainelGeral";
import { carregar } from "@/lib/dados";

export default function Pagina() {
  const { serie, meta } = carregar();
  return (
    <>
      <h1>Demissões e afastamentos por saúde mental</h1>
      <p className="lead">
        Como evoluem, mês a mês, os afastamentos do trabalho por depressão, ansiedade, burnout e outros transtornos
        mentais, ao lado das demissões sem justa causa.
      </p>
      <PainelGeral serie={serie} meta={meta} />
    </>
  );
}
