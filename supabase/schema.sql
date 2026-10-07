-- Tabelas do projeto "Demissões e saúde mental".
-- Rode uma vez no SQL Editor do Supabase. O pipeline (pipeline/supabase.py) preenche
-- as tabelas a cada execução do GitHub Actions, sempre com upsert.

create table if not exists serie_mensal (
  uf                 text    not null,          -- sigla da UF ou 'BR'
  mes                text    not null,          -- 'AAAA-MM'
  afast_total        integer,                   -- auxílios por incapacidade temporária (espécies 31 e 91)
  afast_mental       integer,                   -- idem, com CID do capítulo F ou Z73
  afast_mental_acid  integer,                   -- idem, só espécie 91 (acidentário)
  depressao          integer,
  ansiedade          integer,
  estresse_burnout   integer,
  autismo            integer,
  outros_mentais     integer,
  demissoes_sjc      integer,                   -- Novo CAGED, demissão sem justa causa
  pedidos            integer,                   -- Novo CAGED, a pedido
  desligamentos      integer,
  admissoes          integer,
  vinculos           integer,                   -- RAIS, vínculos ativos (denominador)
  atualizado_em      timestamptz not null default now(),
  primary key (uf, mes)
);

create table if not exists perfil_afastamentos (
  grupo         text    not null,
  sexo          text    not null,
  faixa         text    not null,
  n             integer not null,
  atualizado_em timestamptz not null default now(),
  primary key (grupo, sexo, faixa)
);

create table if not exists setores (
  setor          text primary key,
  nome           text    not null,
  afast_mental   integer not null,
  demissoes_sjc  integer not null,
  vinculos_medio integer,
  atualizado_em  timestamptz not null default now()
);

create table if not exists bpc_autismo (
  mes           text primary key,
  bpc           integer not null,
  afastamento   integer not null,
  atualizado_em timestamptz not null default now()
);

create table if not exists correlacoes (
  tipo             text    not null,            -- 'serie_nacional' ou 'entre_ufs'
  defasagem_meses  integer not null,
  r                double precision,
  n                integer not null,            -- meses ou UFs comparados
  atualizado_em    timestamptz not null default now(),
  primary key (tipo, defasagem_meses)
);

-- Leitura pública (para o site ou outros painéis); escrita só com a service_role, que ignora RLS.
do $$
declare t text;
begin
  foreach t in array array['serie_mensal','perfil_afastamentos','setores','bpc_autismo','correlacoes'] loop
    execute format('alter table %I enable row level security', t);
    if not exists (select 1 from pg_policies where tablename = t and policyname = 'leitura_publica') then
      execute format('create policy leitura_publica on %I for select using (true)', t);
    end if;
  end loop;
end $$;
