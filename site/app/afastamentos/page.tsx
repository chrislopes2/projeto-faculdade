import { PainelAfastamentos } from "@/components/PainelAfastamentos";
import { carregar } from "@/lib/dados";

export default function Pagina() {
  const { serie, perfil, bpc, meta } = carregar();
  return (
    <>
      <h1>Afastamentos</h1>
      <p className="lead">Benefícios por incapacidade concedidos pelo INSS com CID de transtorno mental, por grupo, sexo e idade.</p>
      <PainelAfastamentos serie={serie} perfil={perfil} bpc={bpc} meta={meta} />
    </>
  );
}
