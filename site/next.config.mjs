/**
 * Site estático: `npm run build` gera a pasta out/, que pode ir para qualquer hospedagem.
 * No GitHub Pages o site fica em /<nome-do-repositorio>/, por isso o basePath vem do ambiente.
 */
export default {
  output: "export",
  basePath: process.env.NEXT_BASE_PATH || "",
  // Para links a arquivos estáticos (o PDF), que o <Link> não prefixa.
  env: { NEXT_PUBLIC_BASE: process.env.NEXT_BASE_PATH || "" },
  images: { unoptimized: true },
  trailingSlash: true,
};
