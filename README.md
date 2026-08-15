# Blog do Grana — deploy automático agendado

Site estático autocontido (2026-08-15) — não depende de mais nada fora desta pasta `site/`, pronto pra virar seu próprio repositório GitHub. 60 posts em `content/`, cada um com data de publicação, autor e fontes em `publish-schedule.json`. Todo dia às 09:00 BRT, um GitHub Action rebuilda o site e publica no Cloudflare Pages — os posts cuja data chegou entram no ar sozinhos, sem ninguém tocar em nada.

## Como funciona

1. `build_schedule.py` — dá uma data de publicação pra todo post em `content/*.md` que ainda não tem uma (nunca reatribui data de post já agendado — seguro rodar de novo sempre que um post novo for adicionado). Hoje: 5 posts publicados imediatamente, os outros 55 espalhados ao longo de ~2 meses, ~1 por dia.
2. `generate.py` — lê `publish-schedule.json`, **só escreve no `dist/` os posts cuja data já chegou** (limpa `dist/` inteiro antes de cada build, pra um post "do futuro" nunca ficar acessível por acidente por ter sobrado de um build anterior). Gera `sitemap.xml`, `robots.txt`, dado estruturado (schema.org `Article`, com `datePublished` e `author`), e a assinatura visível no rodapé de cada post ("Por Thallis Ribeiro — Administrador (UFV), MBA em Gestão Financeira (FGV) · publicado em DD.MM.AAAA · Fontes: ...").
3. `.github/workflows/rebuild.yml` — roda os dois scripts acima todo dia às 12:00 UTC (09:00 BRT) e publica o resultado no Cloudflare Pages. Também roda em qualquer `push` na branch `main` e pode ser disparado manualmente (aba Actions → "Rebuild e publicar blog" → Run workflow). **É esse workflow que "libera" os posts agendados sozinho, dia a dia** — `build_schedule.py` só atribui datas a posts que ainda não têm uma (não republica nada); quem decide o que entra no ar em cada build é o filtro de data em `generate.py`. Não existe (nem precisa existir) um mecanismo separado só pra "liberar" posts — o rebuild diário já é o mecanismo.

Rodar local, a qualquer momento (não obrigatório, só pra conferir antes de publicar):
```
python build_schedule.py
python generate.py
```

## Autor das páginas e E-E-A-T (atualizado 2026-08-15)

Autor padrão: **Thallis Ribeiro — Administrador (UFV), MBA em Gestão Financeira (FGV)**. `DEFAULT_AUTHOR` em `build_schedule.py` e os 60 registros em `publish-schedule.json` foram migrados de "Equipe Grana" pra esse nome. As credenciais reais (não inventadas) ficam em `AUTHOR_INFO` no topo de `generate.py`:

- **Schema.org `Person`** em todo post: `jobTitle`, `alumniOf` (UFV), `hasCredential` (MBA/FGV), `url` (aponta pra `/sobre.html`) e **`sameAs`** (LinkedIn + `thallisribeiro.com.br`, confirmados reais pelo usuário) — é o `sameAs` que liga o autor do artigo a uma entidade que o Google já conhece, a peça mais forte de E-E-A-T pra conteúdo YMYL (finanças). Autor não cadastrado em `AUTHOR_INFO` cai automaticamente no fallback institucional (`Organization`, sem credenciais inventadas).
- **Assinatura visível** no rodapé de cada post, com o nome linkando pra `/sobre.html`.
- **`/sobre.html`** — página-âncora com bio, formação e links pro LinkedIn/site pessoal, gerada por `SOBRE_TEMPLATE` em `generate.py`. Falta uma foto real (não gerei uma fictícia de uma pessoa real) — se quiser, é só adicionar `<img>` no template apontando pra um arquivo em `fonts/` (ou nova pasta `assets/`) depois de me passar a imagem.

## Estrutura de cluster (silo temático)

Os 60 posts são categorizados automaticamente em 3 pilares (por contagem de palavras-chave no corpo real do post, não pelo nome do arquivo — ver `categorize()` em `generate.py`): **Dívidas**, **Rotativo e juros do cartão**, **Custo de vida e orçamento**. Cada pilar tem sua própria página (`dividas.html`, `rotativo-juros.html`, `custo-de-vida.html`) listando todo post do tema; cada post linka de volta pra sua pilar + até 2 "irmãos" do mesmo tema (seção "Sobre isso, leia também"). Isso concentra autoridade nas 3 páginas-pilar em vez de deixar 60 posts soltos sem estrutura.

## Páginas de dado vivo (BACEN)

`update_live_data.py` busca, direto na API pública do Banco Central (SGS, sem chave/autenticação), a taxa média mais recente do **cheque especial** (série 20741) e do **rotativo do cartão de crédito** (série 22022) — ambas verificadas manualmente em 2026-08-15 contra a faixa real de mercado (cheque especial ~140% a.a., rotativo ~440% a.a.). Grava em `live-data.json`; `generate.py` lê esse arquivo e gera `dado-vivo-cheque-especial.html` e `dado-vivo-rotativo-cartao.html` com o número em destaque e a data real de referência do BACEN (nunca a data de hoje — o BACEN publica com 1-2 meses de atraso, e fingir que é mais recente seria mentir sobre o dado). O rebuild diário (`rebuild.yml`) já roda `update_live_data.py` antes de `generate.py`, então essas páginas se atualizam sozinhas assim que o BACEN publica um valor novo — sem precisar de cron mensal separado. Se a API do BACEN estiver fora do ar num dia, o script mantém o valor anterior em vez de quebrar o build.

## O que só você consegue fazer (nenhum destes eu executo daqui)

### 1. Configurar Git nesta máquina (nunca foi feito — não mexo em config de git)
```
git config --global user.name "Seu Nome"
git config --global user.email "seu@email.com"
```
Depois, dentro desta pasta (`site/`), o commit já está com tudo adicionado (`git add -A` já rodado) — só falta:
```
git commit -m "Blog do Grana: primeira versão"
```

### 2. Criar o repositório no GitHub e subir o código
```
gh repo create grana-blog --private --source=. --push
```
(ou crie manualmente em github.com/new e rode `git remote add origin <url> && git push -u origin master`)

### 3. Criar conta no Cloudflare e conectar (subdomínio `blog.suagrana.app` — decisão de 2026-08-15)
1. https://dash.cloudflare.com/sign-up (grátis, sem cartão)
2. Colocar `suagrana.app` atrás do Cloudflare (aponta os nameservers, se o domínio estiver noutro DNS hoje) — necessário mesmo em subdomínio, porque é o Cloudflare que vai servir `blog.suagrana.app`
3. Workers & Pages → Create → Pages → conectar ao repositório `grana-blog` que você acabou de criar — **mas o build em si já é feito pelo GitHub Action**, então no Cloudflare Pages não precisa configurar build command nenhum, só o nome do projeto: `grana-blog` (tem que bater com `projectName` em `.github/workflows/rebuild.yml`)
4. Criar 2 secrets no repositório GitHub (Settings → Secrets and variables → Actions): `CLOUDFLARE_API_TOKEN` (Cloudflare → My Profile → API Tokens → criar token com permissão "Cloudflare Pages: Edit") e `CLOUDFLARE_ACCOUNT_ID` (aparece na URL do dashboard ou na barra lateral direita de qualquer página do Cloudflare)
5. No projeto Pages `grana-blog` → Custom domains → Add a domain → `blog.suagrana.app`. Como o domínio já está no Cloudflare, o CNAME é criado automaticamente — não precisa mexer em DNS manualmente.

**Nota (reabertura da decisão de ontem):** o plano original era rota de path (`www.suagrana.app/blog/*`) por autoridade de SEO ligeiramente maior que um subdomínio. O usuário pediu explicitamente `blog.suagrana.app` em 2026-08-15 — isso já estava documentado como fallback aceitável caso a regra de rota travasse, então segui sem bloquear, só registrando aqui pra não se perder no histórico.

### 4. Search Console + GA4 (instalar no mesmo dia da publicação — cada dia sem eles é dado perdido pra sempre)
- Search Console: propriedade de **domínio** (verificação por DNS/TXT record em `suagrana.app`, não meta tag) — cobre `www.suagrana.app` (app) e `blog.suagrana.app` (blog) na mesma propriedade, sem precisar verificar cada subdomínio separado
- GA4: criar a propriedade em analytics.google.com, copiar o Measurement ID, colar em `GA4_MEASUREMENT_ID` no topo de `generate.py`, commitar e dar push (o próximo rebuild automático já publica com o snippet ativo)
- Depois de verificar: Search Console → Sitemaps → submeter `https://blog.suagrana.app/sitemap.xml`

## Consolidação de blogs

Existia um segundo blog, já publicado, em `granablog.higgsfield.app` (5 posts — confirmado real, não é achismo). Decisão: consolidar tudo aqui (60 posts, mais maduro em SEO). Depois deste site estar no ar, desativar/redirecionar o do Higgsfield pra não dividir autoridade entre dois domínios.

## Estrutura

- `content/*.md` — os 60 posts fonte (cópia de `output/BLOG/` — reexecutar `cp ../output/BLOG/*.md content/` se novos posts forem gerados lá, depois `python build_schedule.py`)
- `publish-schedule.json` — data/autor/fontes de cada post, por slug
- `live-data.json` — cache do último valor buscado do BACEN (commitado, pra o site não ficar sem dado se a API cair num dia)
- `build_schedule.py` / `update_live_data.py` / `generate.py` — os três scripts do pipeline, nessa ordem
- `.github/workflows/rebuild.yml` — automação diária
- `dist/` — saída do build (gitignored — o Action gera na hora, não precisa commitar)

Todo post linka de volta pra `https://www.suagrana.app` (CTA fixo no fim + link inline no corpo, herdado do `blog-seo-framework.md` do squad principal) — isso já está pronto, nada a fazer aqui.

**Link app → blog (pendente, fora deste repositório):** o app Grana (Higgsfield) não existe neste workspace, então não consigo editar o código dele daqui. Precisa de um link pro blog em algum lugar do app (rodapé, menu, ou tela de resultado da calculadora) — decisão e execução de quem mantém o código do app.
