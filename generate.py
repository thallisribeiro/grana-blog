#!/usr/bin/env python3
"""Gera o site estático do blog do Grana a partir de output/BLOG/*.md.
Sem build step nenhum: roda `python generate.py` e o site final fica pronto em site/dist/.
Reexecutar sempre que novos posts forem gerados em output/BLOG/ — idempotente, sobrescreve tudo.
"""
import os
import re
import html
import json
import urllib.parse
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# site/content/ (não output/BLOG/ fora da pasta) -- desde 2026-08-15, site/ é autocontido
# de propósito: vira o repositório GitHub próprio (ver README), não pode depender de nada
# fora desta pasta. output/BLOG/*.md continua sendo a fonte canônica de produção do squad;
# copiar pra cá (cp output/BLOG/*.md site/content/) sempre que novos posts forem gerados lá.
BLOG_DIR = ROOT / "content"
DIST_DIR = ROOT / "dist"
POSTS_DIR = DIST_DIR / "posts"
SCHEDULE_PATH = ROOT / "publish-schedule.json"

# Trocado 2026-08-15 (decisão do usuário) para subdomínio -- reabre a recomendação de
# 2026-08-14 de usar path (www.suagrana.app/blog) em vez de subdomínio, que era sobre
# autoridade de SEO ficar represada no subdomínio em vez de fortalecer o domínio raiz.
# Aquela recomendação já previa isso como fallback aceitável ("publicado imperfeito vale
# mais que perfeito parado") se a regra de rota do Cloudflare travasse -- mantendo o
# registro aqui pra não se perder: SEO de um site novo em blog.suagrana.app cresce
# separado de suagrana.app, não fortalece o domínio principal. Decisão em vigor mesmo assim.
SITE_URL = "https://blog.suagrana.app"

# Google Analytics 4 — preencher assim que o usuário criar a propriedade GA4 (grátis,
# analytics.google.com) e regerar o site. Vazio = nenhum snippet é inserido (não quebra nada).
GA4_MEASUREMENT_ID = "G-GTR0Q0BCPF"

BRAND_BG = "#0D0F0E"
BRAND_GREEN_DARK = "#1E5E45"
BRAND_GREEN = "#4CAF7D"

def build_css(font_prefix: str = "") -> str:
    """font_prefix: caminho relativo até a pasta fonts/ a partir da página atual --
    "" para dist/index.html (fonts/ está no mesmo nível), "../" para dist/posts/*.html
    (fonts/ está um nível acima). Nunca path absoluto: a forma exata como o Cloudflare
    vai rotear /blog/* é incerta (pode ou não preservar o prefixo no path repassado pro
    Pages), path relativo funciona igual não importa qual mecanismo for usado."""
    return f"""
@font-face {{ font-family: 'Anton'; src: url('{font_prefix}fonts/Anton.ttf') format('truetype'); font-display: swap; }}
@font-face {{ font-family: 'Inter'; src: url('{font_prefix}fonts/Inter.ttf') format('truetype'); font-display: swap; font-weight: 100 900; }}

:root {{
  --bg: {BRAND_BG};
  --green-dark: {BRAND_GREEN_DARK};
  --green: {BRAND_GREEN};
  --text: #F2F4F3;
  --text-dim: #8D968F;
  --line: #1C211D;
}}
* {{ box-sizing: border-box; }}
html {{ background: var(--bg); }}
body {{
  background:
    radial-gradient(ellipse 900px 500px at 50% -10%, rgba(76,175,125,0.10), transparent 60%),
    var(--bg);
  color: var(--text);
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  margin: 0;
  padding: 0;
  line-height: 1.45;
  font-size: 17px;
  -webkit-font-smoothing: antialiased;
}}
.wrap {{
  max-width: 680px;
  margin: 0 auto;
  padding: 28px 22px 90px;
}}
/* Home usa coluna mais larga -- o texto de post continua em 680px (linha
   confortável de leitura), mas a listagem de cards não é texto corrido,
   e travada em 680px sobrava espaço vazio enorme dos dois lados em tela
   larga, fazendo a home parecer pobre/desorganizada no desktop. */
.wrap-wide {{ max-width: 1100px; }}
.card-grid {{ display: grid; grid-template-columns: 1fr; gap: 14px; margin-bottom: 12px; }}
.card-grid .card {{ margin-bottom: 0; }}
@media (min-width: 720px) {{
  .card-grid {{ grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); }}
}}
header.site {{
  border-bottom: 1px solid var(--line);
  padding: 22px 0;
  margin-bottom: 40px;
}}
header.site .wrap {{ padding-top: 0; padding-bottom: 0; display: flex; align-items: center; justify-content: space-between; }}
header.site a.brand {{
  color: var(--text);
  text-decoration: none;
  font-family: 'Anton';
  font-weight: 400;
  font-size: 1.4rem;
  letter-spacing: 0.01em;
}}
header.site a.brand span {{ color: var(--green); }}
header.site a.back {{
  color: var(--text-dim);
  text-decoration: none;
  font-size: 0.9rem;
}}
header.site a.back:hover {{ color: var(--green); }}
h1 {{
  font-family: 'Anton';
  font-weight: 400;
  font-size: 2.4rem;
  line-height: 1.12;
  letter-spacing: 0.002em;
  margin: 0.1em 0 0.5em;
  color: var(--text);
}}
h2 {{
  font-family: 'Anton';
  font-weight: 400;
  font-size: 1.5rem;
  line-height: 1.25;
  color: var(--green);
  margin-top: 1.9em;
  margin-bottom: 0.5em;
}}
h3 {{ font-size: 1.1rem; font-weight: 700; color: var(--text); margin-top: 1.4em; }}
p {{ margin: 1.1em 0; color: var(--text); }}
strong {{ color: var(--text); font-weight: 700; }}
a {{ color: var(--green); text-underline-offset: 2px; }}
ul, ol {{ padding-left: 1.3em; }}
li {{ margin: 0.5em 0; }}
table {{ width: 100%; border-collapse: collapse; margin: 1.4em 0; font-size: 0.92rem; }}
th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--line); }}
th {{ color: var(--green); font-weight: 700; }}
blockquote {{
  margin: 1.8em 0;
  padding: 4px 0 4px 20px;
  border-left: 3px solid var(--green);
  color: var(--text-dim);
  font-style: italic;
}}
.meta {{ color: var(--text-dim); font-size: 0.95rem; margin-bottom: 0; }}
/* "o número é a imagem" (mesma linguagem visual dos carrosséis) — resposta direta da
   meta description em destaque, logo abaixo do título, reforça o Critério de SEO
   "resposta liftable nas primeiras frases" e dá impacto visual sem precisar de imagem */
.hero-stat {{
  background: linear-gradient(180deg, rgba(76,175,125,0.10), rgba(76,175,125,0.02));
  border: 1px solid rgba(76,175,125,0.28);
  border-left: 4px solid var(--green);
  border-radius: 4px 12px 12px 4px;
  padding: 18px 22px;
  margin: 1.6em 0 2em;
  font-size: 1.08rem;
  line-height: 1.55;
  color: var(--text);
}}
.hero-stat strong {{ color: var(--green); }}
.card {{
  display: block;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 20px 22px;
  margin-bottom: 12px;
  text-decoration: none;
  transition: border-color 0.15s, transform 0.15s;
}}
.card:hover {{ border-color: var(--green); transform: translateX(2px); }}
.card .date {{ color: var(--green); font-size: 0.78rem; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; }}
.card h2 {{ margin: 6px 0 6px; color: var(--text); font-size: 1.15rem; font-family: 'Inter'; font-weight: 800; }}
.card p {{ margin: 0; color: var(--text-dim); font-size: 0.92rem; line-height: 1.5; }}
.card.featured {{
  border: 1px solid rgba(76,175,125,0.35);
  border-left: 4px solid var(--green);
  border-radius: 4px 12px 12px 4px;
  background: linear-gradient(180deg, rgba(76,175,125,0.10), rgba(76,175,125,0.02));
  padding: 28px 30px;
  margin-bottom: 26px;
}}
.card.featured h2 {{ font-size: 1.8rem; font-family: 'Anton'; font-weight: 400; line-height: 1.15; }}
.card.featured .date {{ color: var(--green); }}
.card.featured p {{ font-size: 1rem; margin-top: 8px; }}
.section-label {{ color: var(--text-dim); font-size: 0.78rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; margin: 2em 0 12px; }}
.cta {{
  display: block;
  background: var(--green-dark);
  color: #fff !important;
  text-align: center;
  padding: 18px;
  border-radius: 12px;
  text-decoration: none;
  font-weight: 700;
  font-size: 1.02rem;
  margin: 2.4em 0 0.6em;
  transition: background 0.15s;
}}
.cta:hover {{ background: var(--green); }}
.byline {{ color: var(--text-dim); font-size: 0.85rem; margin-top: 2.4em; padding-top: 1.2em; border-top: 1px solid var(--line); }}
.share {{
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin: 2em 0 0;
  padding-top: 1.4em;
  border-top: 1px solid var(--line);
}}
.share span {{ color: var(--text-dim); font-size: 0.85rem; margin-right: 2px; }}
.share button, .share a {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: transparent;
  border: 1px solid var(--line);
  color: var(--text);
  font-family: inherit;
  font-size: 0.85rem;
  padding: 8px 14px;
  border-radius: 20px;
  text-decoration: none;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}}
.share button:hover, .share a:hover {{ border-color: var(--green); color: var(--green); }}
.byline a {{ color: var(--text-dim); text-decoration: underline; }}
footer {{ color: var(--text-dim); font-size: 0.85rem; text-align: center; margin-top: 3em; }}
.cluster {{ margin-top: 2.6em; padding-top: 1.2em; border-top: 1px solid var(--line); }}
.cluster-pillar {{ display: block; color: var(--green); font-weight: 700; text-decoration: none; margin-bottom: 0.8em; }}
.cluster-sibling {{ display: block; color: var(--text-dim); text-decoration: none; font-size: 0.95rem; margin: 0.4em 0; }}
.cluster-sibling:hover {{ color: var(--green); }}
.avatar-circle {{
  width: 64px; height: 64px; border-radius: 50%;
  background: linear-gradient(160deg, var(--green), var(--green-dark));
  color: #fff; font-family: 'Anton'; font-size: 1.3rem;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 0.8em;
}}
.hero-stat-big {{ font-family: 'Anton'; font-size: 2.6rem; color: var(--green); display: flex; align-items: baseline; gap: 10px; }}
.hero-stat-big .unidade {{ font-family: 'Inter'; font-size: 1rem; font-weight: 700; color: var(--text-dim); }}
.cover {{ width: 100%; height: auto; border-radius: 12px; margin: 0.4em 0 1.2em; display: block; border: 1px solid var(--line); }}
"""

def ga4_snippet() -> str:
    if not GA4_MEASUREMENT_ID:
        return ""
    # GA4_MEASUREMENT_ID (G-GTR0Q0BCPF) é o MESMO stream que o app (www.suagrana.app) deve
    # usar -- suagrana.app e blog.suagrana.app são o mesmo domínio registrável, então GA4
    # já mantém sessão contínua entre os dois nativamente, sem precisar de cross-domain nem
    # de um segundo stream (isso quebraria o relatório de jornada blog->calculadora, que é
    # o ponto inteiro de medir isso). Corrigido 2026-08-15 depois de eu ter orientado errado
    # pro usuário criar um stream separado -- não criar.
    #
    # Evento "click_cta_app" em todo clique no CTA fixo (link pro app): é sinal ANTECEDENTE
    # (intenção), não de resultado -- nunca tratar como métrica de sucesso sozinha, ou a
    # tentação vira otimizar o botão (cor/texto/posição) quando o gargalo real pode estar
    # depois, na calculadora do app. Enquanto os 2 eventos reais do app (conclusão da
    # calculadora, captura de e-mail) não existirem, usar isso só como diagnóstico de
    # conteúdo (qual post empurra mais gente pro app), nunca como KPI isolado.
    return (
        f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA4_MEASUREMENT_ID}"></script>\n'
        f"<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}"
        f"gtag('js',new Date());gtag('config','{GA4_MEASUREMENT_ID}');"
        f"document.addEventListener('click',function(e){{"
        f"var a=e.target.closest('.cta');"
        f"if(a){{gtag('event','click_cta_app',{{destination:a.href,page_path:location.pathname}});}}"
        f"}});</script>"
    )

def slugify(filename: str) -> str:
    stem = Path(filename).stem
    # NN-slug-de-titulo -> slug-de-titulo (mantém o número pra ordenação de leitura, mas gera slug limpo pra URL)
    m = re.match(r"^(\d+)-(.+)$", stem)
    return m.group(2) if m else stem

def md_inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)
    return text

def md_to_html(body: str) -> str:
    lines = body.split("\n")
    out = []
    i = 0
    list_buffer = []
    list_type = None
    para_buffer = []

    def flush_list():
        nonlocal list_buffer, list_type
        if list_buffer:
            tag = "ol" if list_type == "ol" else "ul"
            out.append(f"<{tag}>")
            for item in list_buffer:
                out.append(f"<li>{md_inline(item)}</li>")
            out.append(f"</{tag}>")
            list_buffer = []
            list_type = None

    def flush_para():
        # Um `\n` isolado dentro do markdown-fonte é só quebra de linha suave (o autor
        # deu Enter no meio da frase pra não passar de N colunas no editor) -- markdown
        # de verdade trata isso como espaço, não como parágrafo novo. Bug real achado
        # 2026-08-21: cada linha virava um <p> próprio, e cada <p> tem margin -- o
        # "espaçamento gigante" que o usuário reportou era isso, não line-height.
        nonlocal para_buffer
        if para_buffer:
            out.append(f"<p>{md_inline(' '.join(para_buffer))}</p>")
            para_buffer = []

    while i < len(lines):
        line = lines[i].strip()
        if not line:
            flush_list()
            flush_para()
            i += 1
            continue
        if line.startswith("### "):
            flush_list()
            flush_para()
            out.append(f"<h3>{md_inline(line[4:])}</h3>")
        elif line.startswith("## "):
            flush_list()
            flush_para()
            out.append(f"<h2>{md_inline(line[3:])}</h2>")
        elif line.startswith("# "):
            flush_list()
            flush_para()
            # H1 já vira o <h1> do template, pula linha do corpo pra não duplicar
        elif re.match(r"^\d+\.\s+", line):
            flush_para()
            if list_type != "ol":
                flush_list()
                list_type = "ol"
            list_buffer.append(re.sub(r"^\d+\.\s+", "", line))
        elif line.startswith("- "):
            flush_para()
            if list_type != "ul":
                flush_list()
                list_type = "ul"
            list_buffer.append(line[2:])
        elif line.startswith("> "):
            flush_list()
            flush_para()
            out.append(f"<blockquote>{md_inline(line[2:])}</blockquote>")
        else:
            flush_list()
            para_buffer.append(line)
        i += 1
    flush_list()
    flush_para()
    return "\n".join(out)

def strip_md(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1", text)
    return text.strip()

def extract_faq(body: str):
    """Heurística: H2 (formato real usado pelos posts, ver blog-seo-framework.md secao 2)
    terminando em '?' = pergunta; parágrafos seguintes até a próxima heading/lista = resposta.
    Checado em 2026-08-14 contra os 60 posts reais: headings são sempre H2, nunca H3 — e só
    ~1 em 60 usa formato de pergunta, então FAQPage só aparece quando o post realmente tiver
    2+ perguntas de verdade (nunca inventado). Usado só pra gerar FAQPage schema — não afeta
    o HTML visível, que já vem de md_to_html separadamente."""
    lines = body.split("\n")
    faqs = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("## ") and line.rstrip().endswith("?"):
            question = strip_md(line[3:])
            answer_parts = []
            j = i + 1
            while j < len(lines):
                l = lines[j].strip()
                if not l:
                    j += 1
                    continue
                if l.startswith("#") or l.startswith("- ") or re.match(r"^\d+\.\s+", l):
                    break
                answer_parts.append(strip_md(l))
                j += 1
            if answer_parts:
                faqs.append((question, " ".join(answer_parts)))
            i = j
        else:
            i += 1
    return faqs

# Credenciais reais por autor (2026-08-15) -- E-E-A-T de verdade exige credencial real,
# nunca inventada. Autor não listado aqui cai no fallback institucional (Organization).
AUTHOR_INFO = {
    "Thallis Ribeiro": {
        "jobTitle": "Administrador, MBA em Gestão Financeira (FGV)",
        "alumniOf": ["Universidade Federal de Viçosa"],
        "hasCredential": "MBA em Gestão Financeira (Fundação Getulio Vargas)",
        "url": f"{SITE_URL}/sobre.html",
        # Confirmados reais pelo usuário em 2026-08-15 -- sameAs é o que liga o autor do
        # artigo a uma entidade que o Google já conhece (peça central de E-E-A-T pra YMYL).
        "sameAs": [
            "https://www.linkedin.com/in/thallisribeiro",
            "https://www.thallisribeiro.com.br",
        ],
    },
}

def author_byline_html(author: str) -> str:
    info = AUTHOR_INFO.get(author)
    name = html.escape(author)
    if not info:
        return name
    name_html = f'<a href="../sobre.html">{name}</a>' if info.get("url") else name
    return f"{name_html} — {html.escape(info['jobTitle'])}"

def build_author_schema(author: str) -> dict:
    info = AUTHOR_INFO.get(author)
    if not info:
        return {"@type": "Organization", "name": author}
    schema = {"@type": "Person", "name": author, "jobTitle": info["jobTitle"]}
    if info.get("url"):
        schema["url"] = info["url"]
    if info.get("sameAs"):
        schema["sameAs"] = info["sameAs"]
    if info.get("alumniOf"):
        schema["alumniOf"] = [{"@type": "CollegeOrUniversity", "name": n} for n in info["alumniOf"]]
    if info.get("hasCredential"):
        schema["hasCredential"] = {"@type": "EducationalOccupationalCredential", "credentialCategory": info["hasCredential"]}
    return schema

def build_structured_data(titulo: str, meta: str, url: str, faqs, pub_date: str, author: str) -> str:
    graphs = [{
        "@type": "Article",
        "headline": titulo,
        "description": meta,
        "url": url,
        "datePublished": pub_date,
        "author": build_author_schema(author),
        "publisher": {"@type": "Organization", "name": "Grana", "url": "https://www.suagrana.app"},
    }]
    if len(faqs) >= 2:
        graphs.append({
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": q,
                    "acceptedAnswer": {"@type": "Answer", "text": a},
                }
                for q, a in faqs
            ],
        })
    data = {"@context": "https://schema.org", "@graph": graphs}
    return json.dumps(data, ensure_ascii=False)

# Estrutura de cluster (2026-08-15, pedido do usuário): 3 páginas-pilar por tema,
# cada post linka de volta pra pilar + 2 "irmãos" do mesmo tema. Categorização por
# contagem de palavras-chave no corpo real do post (não pelo nome do arquivo, que
# nem sempre é temático) -- checado manualmente contra os 60 posts reais em
# 2026-08-15: distribuição 31/17/12, sem post órfão (todo post bate pelo menos
# uma palavra-chave de algum pilar).
PILLARS = {
    "dividas": {
        "titulo": "Dívidas: como sair e não voltar",
        "intro": "Dívida vencida, negativação, cobrança, cartão consignado sem autorização, ou a estratégia certa pra sumir com o rombo sem quebrar de novo no mês seguinte.",
        "keywords": ["divida", "negativad", "spc", "serasa", "cobranca", "bola de neve", "endividad", "consignado"],
    },
    "rotativo-juros": {
        "titulo": "Rotativo e juros do cartão",
        "intro": "Por que o rotativo do cartão e o cheque especial são as portas de entrada mais caras pra uma dívida, e como sair delas sem perder o controle da fatura.",
        "keywords": ["rotativo", "cheque especial", "juros", "cartao", "fatura", "parcelamento", "parcelar", "financiamento", "minimo da fatura"],
    },
    "custo-de-vida": {
        "titulo": "Custo de vida e orçamento",
        "intro": "Quanto custa sua vida de verdade, por mês: custo de sobrevivência, reserva de emergência, orçamento sem planilha complicada, e o número que mostra se sobra ou falta antes de faltar de verdade.",
        "keywords": ["custo de sobrevivencia", "reserva de emergencia", "orcamento", "planilha", "quanto sobra", "raio-x", "raio x", "renda variavel", "salario"],
    },
}

def _strip_accents(s: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

def categorize(titulo: str, body: str) -> str:
    text = _strip_accents((titulo + " " + body).lower())
    scores = {k: sum(text.count(kw) for kw in p["keywords"]) for k, p in PILLARS.items()}
    return max(scores, key=scores.get)

def parse_post(path: Path):
    raw = path.read_text(encoding="utf-8")
    raw = raw.replace("=== BLOG POST ===", "").strip()
    lines = raw.split("\n")
    titulo, meta = "", ""
    body_start = 0
    for idx, line in enumerate(lines):
        if line.startswith("Título:"):
            titulo = line.split("Título:", 1)[1].strip()
        elif line.startswith("Meta description:"):
            meta = line.split("Meta description:", 1)[1].strip()
            if meta.startswith('"') and meta.endswith('"'):
                meta = meta[1:-1]
        elif line.startswith("# "):
            body_start = idx
            break
    body = "\n".join(lines[body_start + 1:]).strip()
    return titulo, meta, body

POST_TEMPLATE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo} — Grana</title>
<meta name="description" content="{meta}">
<meta property="article:published_time" content="{pub_date}">
<link rel="canonical" href="{url}">
{og_image_tags}
<script type="application/ld+json">{schema}</script>
{ga4}
<style>{css}</style>
</head>
<body>
<header class="site"><div class="wrap">
  <a class="brand" href="../index.html">gr<span>a</span>na</a>
  <a class="back" href="../index.html">← Blog</a>
</div></header>
<div class="wrap">
<h1>{titulo}</h1>
{cover_html}
<div class="hero-stat">{meta}</div>
{body_html}
{cluster_html}
<p class="byline">Por {author} · publicado em {pub_date_br}{sources_html}</p>
{share_html}
<a class="cta" href="https://www.suagrana.app">Calcular meu custo de sobrevivência →</a>
</div>
<footer>Grana · suagrana.app</footer>
</body>
</html>
"""

SHARE_TEMPLATE = """<div class="share">
<span>Compartilhar:</span>
<a href="https://twitter.com/intent/tweet?text={text_enc}&url={url_enc}" target="_blank" rel="noopener">X</a>
<a href="https://wa.me/?text={text_enc}%20{url_enc}" target="_blank" rel="noopener">WhatsApp</a>
<button type="button" onclick="grNativeShare(this,'{url_js}','{title_js}')">Mais opções</button>
<button type="button" onclick="grCopyLink(this,'{url_js}')">Copiar link</button>
</div>
<script>
function grNativeShare(btn,url,title){{
  if(navigator.share){{navigator.share({{title:title,url:url}}).catch(function(){{}});}}
  else{{grCopyLink(btn,url);}}
}}
function grCopyLink(btn,url){{
  navigator.clipboard.writeText(url).then(function(){{
    var orig=btn.textContent;btn.textContent='Copiado!';
    setTimeout(function(){{btn.textContent=orig;}},1500);
  }});
}}
</script>"""

CLUSTER_TEMPLATE = """<div class="cluster">
<div class="section-label">Sobre isso, leia também</div>
<a class="cluster-pillar" href="../{pillar_slug}.html">{pillar_titulo} →</a>
{siblings_html}
</div>"""

SOBRE_TEMPLATE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sobre Thallis Ribeiro — Grana</title>
<meta name="description" content="Thallis Ribeiro, Administrador (UFV) com MBA em Gestão Financeira (FGV), fundador do Grana e autor do blog.">
<link rel="canonical" href="{url}">
<script type="application/ld+json">{schema}</script>
{ga4}
<style>{css}</style>
</head>
<body>
<header class="site"><div class="wrap">
  <a class="brand" href="index.html">gr<span>a</span>na</a>
  <a class="back" href="index.html">← Blog</a>
</div></header>
<div class="wrap">
<div class="avatar-circle">TR</div>
<h1>Thallis Ribeiro</h1>
<p class="meta">Administrador, MBA em Gestão Financeira (FGV)</p>
<p>Formado em Administração pela Universidade Federal de Viçosa (UFV), com MBA em Gestão Financeira pela Fundação Getulio Vargas (FGV). Fundador do <a href="https://www.suagrana.app">Grana</a>, app de finanças pessoais, e autor deste blog.</p>
<p>Escrevo sobre dívida, rotativo do cartão, reserva de emergência e custo de vida com número e fonte oficial (Banco Central, IBGE, Receita Federal) na mesa — sem economês e sem fórmula mágica.</p>
<p><a href="https://www.linkedin.com/in/thallisribeiro">LinkedIn →</a> · <a href="https://www.thallisribeiro.com.br">thallisribeiro.com.br →</a></p>
<a class="cta" href="https://www.suagrana.app">Calcular meu custo de sobrevivência →</a>
</div>
<footer>Grana · suagrana.app</footer>
</body>
</html>
"""

PILLAR_TEMPLATE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo} — Blog do Grana</title>
<meta name="description" content="{intro}">
<link rel="canonical" href="{url}">
{ga4}
<style>{css}</style>
</head>
<body>
<header class="site"><div class="wrap">
  <a class="brand" href="index.html">gr<span>a</span>na</a>
  <a class="back" href="index.html">← Blog</a>
</div></header>
<div class="wrap">
<h1>{titulo}</h1>
<p class="meta">{intro}</p>
<div class="section-label">Todos os posts</div>
{cards}
<a class="cta" href="https://www.suagrana.app">Calcular meu custo de sobrevivência →</a>
</div>
<footer>Grana · suagrana.app</footer>
</body>
</html>
"""

DADO_VIVO_TEMPLATE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo} — Grana</title>
<meta name="description" content="{meta}">
<link rel="canonical" href="{url}">
<script type="application/ld+json">{schema}</script>
{ga4}
<style>{css}</style>
</head>
<body>
<header class="site"><div class="wrap">
  <a class="brand" href="index.html">gr<span>a</span>na</a>
  <a class="back" href="index.html">← Blog</a>
</div></header>
<div class="wrap">
<h1>{titulo}</h1>
<div class="hero-stat hero-stat-big">{valor}<span class="unidade">{unidade}</span></div>
<p class="meta">Dado de referência: {data_referencia} · Fonte: Banco Central do Brasil (série SGS {codigo}) · atualizado automaticamente todo dia com o último valor publicado pelo BACEN.</p>
<p>{explicacao}</p>
<p>Esse número é a <strong>taxa média de mercado</strong> — o que os bancos cobram na média do país. O que sai da sua fatura pode ser maior ou menor, dependendo do seu banco e do seu limite. Pra saber quanto sobra ou falta de verdade no seu mês (e decidir se vale a pena recorrer a essa linha de crédito), use o cálculo de custo de sobrevivência do Grana.</p>
<p><a href="{pillar_href}">Ver todos os posts sobre {pillar_titulo_lower} →</a></p>
<p class="byline">Fonte primária: <a href="https://www3.bcb.gov.br/sgspub/consultarvalores/consultarValoresSeries.do?method=consultarValores">Banco Central — SGS série {codigo}</a></p>
<a class="cta" href="https://www.suagrana.app">Calcular meu custo de sobrevivência →</a>
</div>
<footer>Grana · suagrana.app</footer>
</body>
</html>
"""

INDEX_TEMPLATE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Blog do Grana — educação financeira sem enrolação</title>
<meta name="description" content="Artigos sobre custo de sobrevivência, dívida, reserva de emergência e finanças pessoais no mundo real, do app Grana.">
{ga4}
<style>{css}</style>
</head>
<body>
<header class="site"><div class="wrap wrap-wide">
  <a class="brand" href="index.html">gr<span>a</span>na</a>
  <a class="back" href="sobre.html">Sobre o autor</a>
</div></header>
<div class="wrap wrap-wide">
<h1>Blog do Grana</h1>
<p class="meta">Finanças pessoais sem economês, sem culpa, com número na mesa.</p>
<div class="section-label">Mais recente</div>
{featured_card}
<div class="section-label">Dados ao vivo</div>
<div class="card-grid">{dado_vivo_cards}</div>
<div class="section-label">Temas</div>
<div class="card-grid">{pillar_cards}</div>
<div class="section-label">Todos os posts</div>
<div class="card-grid">{cards}</div>
<a class="cta" href="https://www.suagrana.app">Calcular meu custo de sobrevivência →</a>
</div>
<footer>Grana · suagrana.app</footer>
</body>
</html>
"""

def build_sobre_schema(url: str) -> str:
    graphs = [{
        "@context": "https://schema.org",
        "@type": "ProfilePage",
        "url": url,
        "mainEntity": build_author_schema("Thallis Ribeiro"),
    }]
    return json.dumps(graphs[0], ensure_ascii=False)

LIVE_DATA_PAGES = {
    "cheque-especial": {
        "titulo": "Qual é a taxa do cheque especial hoje? Direto do Banco Central",
        "meta_prefix": "A taxa média do cheque especial no Brasil hoje é",
        "explicacao": "Essa é a taxa média de juros que os bancos cobram no cheque especial no Brasil, segundo o Banco Central — a linha de crédito mais cara e mais fácil de cair sem perceber, porque ela é usada automaticamente quando a conta fica negativa.",
        "pillar": "rotativo-juros",
    },
    "rotativo-cartao": {
        "titulo": "Qual é a taxa do rotativo do cartão hoje? Direto do Banco Central",
        "meta_prefix": "A taxa média do rotativo do cartão de crédito no Brasil hoje é",
        "explicacao": "Essa é a taxa média de juros do rotativo do cartão de crédito no Brasil, segundo o Banco Central — o que acontece quando você paga só o mínimo da fatura e o resto vira dívida cara automaticamente.",
        "pillar": "rotativo-juros",
    },
}

def main():
    # Limpa dist/ inteiro antes de gerar -- essencial pro date-gating funcionar de verdade:
    # sem isso, um post cuja data ainda não chegou podia continuar publicamente acessível
    # só porque sobrou de um build anterior (achado real, 2026-08-15: rodar de novo sem
    # limpar deixou os 55 posts "futuros" de uma versão anterior ainda no dist/).
    import shutil
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    fonts_dist = DIST_DIR / "fonts"
    fonts_dist.mkdir(exist_ok=True)
    for font_file in (ROOT / "fonts").glob("*.ttf"):
        shutil.copy(font_file, fonts_dist / font_file.name)

    # Capas geradas localmente (ComfyUI/FLUX, ver generate_cover_images.py) -- opcional
    # por post, pulado sem quebrar nada quando não existir (achado 2026-08-16: geração
    # de imagem só roda com PC ligado, então nem todo post vai ter capa o tempo todo).
    covers_src = ROOT / "images" / "covers"
    covers_dist = DIST_DIR / "images" / "covers"
    covers_dist.mkdir(parents=True, exist_ok=True)
    cover_slugs = set()
    if covers_src.exists():
        for cover_file in covers_src.glob("*.jpg"):
            shutil.copy(cover_file, covers_dist / cover_file.name)
            cover_slugs.add(cover_file.stem)

    schedule = {}
    if SCHEDULE_PATH.exists():
        schedule = json.loads(SCHEDULE_PATH.read_text(encoding="utf-8"))
    today_iso = date.today().isoformat()

    files = sorted(BLOG_DIR.glob("*.md"))
    files = [f for f in files if not f.stem.startswith("_")]

    ga4 = ga4_snippet()
    urls = [f"{SITE_URL}/"]
    skipped_future = 0

    # Passo 1: parseia e categoriza todo post JÁ publicado (data <= hoje) antes de
    # renderizar qualquer HTML -- precisa da lista inteira pronta pra montar os links
    # de cluster (pilar + irmãos), que dependem de quem mais está publicado agora.
    posts = []
    for f in files:
        titulo, meta, body = parse_post(f)
        if not titulo:
            continue
        slug = slugify(f.name)
        sched = schedule.get(slug)
        if not sched:
            print(f"aviso: '{slug}' sem entrada em publish-schedule.json -- rodar build_schedule.py antes. Pulando por ora.")
            continue
        pub_date = sched["date"]
        if pub_date > today_iso:
            skipped_future += 1
            continue
        posts.append({
            "slug": slug, "titulo": titulo, "meta": meta, "body": body,
            "pub_date": pub_date, "author": sched.get("author", "Equipe Grana"),
            "sources": sched.get("sources", []),
            "pillar": categorize(titulo, body),
        })

    # Passo 2: renderiza cada post com link pra pilar + até 2 irmãos do mesmo pilar
    # (ordem determinística: os próximos da lista, com wraparound -- sem aleatoriedade,
    # pra o build ser reprodutível e o link não pular de post a cada rebuild).
    cards = []
    pillar_posts = {k: [] for k in PILLARS}
    for post in posts:
        pillar_posts[post["pillar"]].append(post)

    for post in posts:
        slug, titulo, meta, body = post["slug"], post["titulo"], post["meta"], post["body"]
        pub_date, author, sources = post["pub_date"], post["author"], post["sources"]
        pillar_key = post["pillar"]
        pub_date_br = ".".join(reversed(pub_date.split("-")))
        sources_html = f" · Fontes: {html.escape(', '.join(sources))}" if sources else ""

        siblings = [p for p in pillar_posts[pillar_key] if p["slug"] != slug][:2]
        siblings_html = "\n".join(
            f'<a class="cluster-sibling" href="{s["slug"]}.html">{html.escape(s["titulo"])}</a>'
            for s in siblings
        )
        cluster_html = CLUSTER_TEMPLATE.format(
            pillar_slug=pillar_key, pillar_titulo=html.escape(PILLARS[pillar_key]["titulo"]),
            siblings_html=siblings_html,
        ) if siblings_html else ""

        url = f"{SITE_URL}/posts/{slug}.html"
        body_html = md_to_html(body)
        faqs = extract_faq(body)
        schema = build_structured_data(titulo, meta, url, faqs, pub_date, author)

        title_js = html.escape(titulo).replace("\\", "\\\\").replace("'", "\\'")
        share_html = SHARE_TEMPLATE.format(
            text_enc=urllib.parse.quote(titulo), url_enc=urllib.parse.quote(url, safe=""),
            url_js=url, title_js=title_js,
        )

        if slug in cover_slugs:
            cover_url = f"{SITE_URL}/images/covers/{slug}.jpg"
            og_image_tags = (
                f'<meta property="og:image" content="{cover_url}">\n'
                f'<meta name="twitter:card" content="summary_large_image">\n'
                f'<meta name="twitter:image" content="{cover_url}">'
            )
            cover_html = f'<img class="cover" src="../images/covers/{slug}.jpg" alt="{html.escape(titulo)}" width="1280" height="720" loading="eager">'
        else:
            og_image_tags = ""
            cover_html = ""

        html_out = POST_TEMPLATE.format(
            titulo=html.escape(titulo), meta=html.escape(meta), css=build_css("../"),
            body_html=body_html, cluster_html=cluster_html, url=url, schema=schema, ga4=ga4,
            pub_date=pub_date, pub_date_br=pub_date_br, author=author_byline_html(author),
            sources_html=sources_html, og_image_tags=og_image_tags, cover_html=cover_html,
            share_html=share_html,
        )
        (POSTS_DIR / f"{slug}.html").write_text(html_out, encoding="utf-8")
        cards.append((
            pub_date,
            f'<a class="card" href="posts/{slug}.html"><div class="date">{pub_date_br}</div>'
            f'<h2>{html.escape(titulo)}</h2><p>{html.escape(meta)}</p></a>'
        ))
        urls.append(url)
    count = len(posts)

    # Páginas-pilar (cluster): uma por tema, listando todo post publicado daquele tema.
    pillar_cards_html = []
    for key, info in PILLARS.items():
        plist = pillar_posts[key]
        post_cards = "\n".join(
            f'<a class="card" href="posts/{p["slug"]}.html"><h2>{html.escape(p["titulo"])}</h2><p>{html.escape(p["meta"])}</p></a>'
            for p in plist
        )
        pillar_url = f"{SITE_URL}/{key}.html"
        pillar_html = PILLAR_TEMPLATE.format(
            titulo=html.escape(info["titulo"]), intro=html.escape(info["intro"]),
            css=build_css(""), ga4=ga4, url=pillar_url, cards=post_cards or "<p>Em breve.</p>",
        )
        (DIST_DIR / f"{key}.html").write_text(pillar_html, encoding="utf-8")
        urls.append(pillar_url)
        pillar_cards_html.append(
            f'<a class="card" href="{key}.html"><h2>{html.escape(info["titulo"])}</h2><p>{html.escape(info["intro"])}</p></a>'
        )

    # Página /sobre -- âncora de autoridade (E-E-A-T) pra onde todo post e o schema.org apontam.
    sobre_url = f"{SITE_URL}/sobre.html"
    sobre_html = SOBRE_TEMPLATE.format(
        css=build_css(""), ga4=ga4, url=sobre_url, schema=build_sobre_schema(sobre_url),
    )
    (DIST_DIR / "sobre.html").write_text(sobre_html, encoding="utf-8")
    urls.append(sobre_url)

    # Páginas de "dado vivo" -- taxa do cheque especial e do rotativo, direto da API
    # pública do Banco Central (ver update_live_data.py). Só gera se live-data.json
    # existir (rodar update_live_data.py antes) -- sem dado real, não inventa página.
    live_data_path = ROOT / "live-data.json"
    dado_vivo_cards_html = []
    if live_data_path.exists():
        live_data = json.loads(live_data_path.read_text(encoding="utf-8"))
        for key, page_info in LIVE_DATA_PAGES.items():
            d = live_data.get(key)
            if not d:
                continue
            pillar_key = page_info["pillar"]
            valor_fmt = d["valor"].replace(".", ",")
            meta_desc = f'{page_info["meta_prefix"]} {valor_fmt}{" " if not d["unidade"].startswith("%") else ""}{d["unidade"]}, segundo o Banco Central (ref. {d["data_referencia"]}).'
            page_url = f"{SITE_URL}/dado-vivo-{key}.html"
            schema = json.dumps({
                "@context": "https://schema.org", "@type": "Article",
                "headline": page_info["titulo"], "description": meta_desc, "url": page_url,
                "dateModified": d["data_referencia"],
                "author": build_author_schema("Thallis Ribeiro"),
                "publisher": {"@type": "Organization", "name": "Grana", "url": "https://www.suagrana.app"},
            }, ensure_ascii=False)
            page_html = DADO_VIVO_TEMPLATE.format(
                titulo=html.escape(page_info["titulo"]), meta=html.escape(meta_desc),
                css=build_css(""), ga4=ga4, url=page_url, schema=schema,
                valor=html.escape(valor_fmt), unidade=html.escape(d["unidade"]),
                data_referencia=html.escape(d["data_referencia"]), codigo=d["codigo"],
                explicacao=html.escape(page_info["explicacao"]),
                pillar_href=f"{pillar_key}.html", pillar_titulo_lower=html.escape(PILLARS[pillar_key]["titulo"].lower()),
            )
            (DIST_DIR / f"dado-vivo-{key}.html").write_text(page_html, encoding="utf-8")
            urls.append(page_url)
            dado_vivo_cards_html.append(
                f'<a class="card" href="dado-vivo-{key}.html"><div class="date">{d["data_referencia"]}</div>'
                f'<h2>{html.escape(page_info["titulo"])}</h2><p>{html.escape(meta_desc)}</p></a>'
            )
    else:
        print("aviso: live-data.json não existe -- rodar update_live_data.py antes pra gerar as páginas de dado vivo. Pulando por ora.")

    # Card em destaque = post mais recente (maior pub_date); resto em ordem cronológica
    # decrescente (mais novo primeiro) -- lista fica sempre com o que há de mais fresco no topo.
    cards.sort(key=lambda c: c[0], reverse=True)
    featured_card = ""
    rest_cards = cards
    if cards:
        pub_date, card_html = cards[0]
        featured_card = card_html.replace('<a class="card"', '<a class="card featured"', 1)
        rest_cards = cards[1:]

    index_html = INDEX_TEMPLATE.format(
        css=build_css(""), ga4=ga4, featured_card=featured_card,
        cards="\n".join(c for _, c in rest_cards),
        pillar_cards="\n".join(pillar_cards_html),
        dado_vivo_cards="\n".join(dado_vivo_cards_html) or "<p class=\"meta\">Em breve.</p>",
    )
    (DIST_DIR / "index.html").write_text(index_html, encoding="utf-8")

    sitemap_entries = "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
    sitemap_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{sitemap_entries}\n"
        "</urlset>\n"
    )
    (DIST_DIR / "sitemap.xml").write_text(sitemap_xml, encoding="utf-8")

    robots_txt = f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n"
    (DIST_DIR / "robots.txt").write_text(robots_txt, encoding="utf-8")

    print(f"Gerados {count} posts em {POSTS_DIR} ({skipped_future} ainda não chegaram na data agendada, ficaram de fora)")
    print(f"{len(PILLARS)} páginas-pilar, /sobre, {len(dado_vivo_cards_html)} páginas de dado vivo")
    print(f"Index em {DIST_DIR / 'index.html'}")
    print(f"sitemap.xml e robots.txt gerados (SITE_URL={SITE_URL})")
    if not GA4_MEASUREMENT_ID:
        print("aviso: GA4_MEASUREMENT_ID vazio -- nenhum snippet de analytics foi inserido, preencher e regerar depois de criar a propriedade GA4")

if __name__ == "__main__":
    main()
