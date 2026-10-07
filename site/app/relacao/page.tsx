import { PainelRelacao } from "@/components/PainelRelacao";
import { carregar } from "@/lib/dados";

export default function Pagina() {
  const { serie, correlacao, filiacao, meta } = carregar();
  return (
    <>
      <h1>Relação entre demissões e afastamentos</h1>
      <p className="lead">
        Onde e quando há mais demissões também há mais afastamentos por saúde mental? Correlação mostra se as duas
        coisas andam juntas, não se uma causa a outra.
      </p>
      <PainelRelacao serie={serie} correlacao={correlacao} filiacao={filiacao} meta={meta} />
    </>
  );
}
