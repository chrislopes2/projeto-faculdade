import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { carregar } from "@/lib/dados";

export const metadata: Metadata = {
  title: "Demissões e saúde mental",
  description: "Dashboards que relacionam demissões e afastamentos do trabalho por transtornos mentais no Brasil.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  const { meta } = carregar();
  return (
    <html lang="pt-BR">
      <body>
        <header className="topo">
          <div className="topo-dentro">
            <Link href="/" className="marca">Demissões e saúde mental</Link>
            <nav>
              <Link href="/">Visão geral</Link>
              <Link href="/afastamentos/">Afastamentos</Link>
              <Link href="/demissoes/">Demissões</Link>
              <Link href="/relacao/">Relação</Link>
              <Link href="/metodologia/">Metodologia</Link>
            </nav>
          </div>
        </header>
        {meta.exemplo && (
          <div className="aviso" role="note">
            <p>Dados de exemplo, fictícios. Rode o pipeline com as fontes reais antes de publicar.</p>
          </div>
        )}
        <main>{children}</main>
        <footer>
          Fontes: INSS (benefícios concedidos), MTE (Novo CAGED e RAIS). Atualizado em{" "}
          {new Date(meta.gerado_em).toLocaleDateString("pt-BR")}.
        </footer>
      </body>
    </html>
  );
}
