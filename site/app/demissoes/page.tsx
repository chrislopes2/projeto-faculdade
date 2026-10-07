import { PainelDemissoes } from "@/components/PainelDemissoes";
import { carregar } from "@/lib/dados";

export default function Pagina() {
  const { serie, meta } = carregar();
  return (
    <>
      <h1>Demissões</h1>
      <p className="lead">Desligamentos de empregos formais registrados no Novo CAGED, por tipo e por estado.</p>
      <PainelDemissoes serie={serie} meta={meta} />
    </>
  );
}
