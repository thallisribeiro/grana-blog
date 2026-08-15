#!/usr/bin/env python3
"""Audita os posts existentes (content/*.md) contra a Barra de Publicacao do Blog
(pipeline/data/quality-criteria.md, spec blog-primeiro 2026-08-15, corrigida no mesmo dia).

So checa mecanicamente o que da pra checar sem julgamento humano. Itens BLOQUEANTES:
  1. Numero com fonte nomeada e data       -> campo 'sources' em publish-schedule.json
  2. Calculo mostrado (nao so citado)      -> heuristica: presenca de expressao com R$ e
                                               operador (x, *, +, =) no corpo -- heuristica
                                               imperfeita (pode dar falso positivo em
                                               palavras com 'x', ex: "taxa"), usar so como
                                               triagem, nao como veredito final
  3. Tabela ou comparacao escaneavel       -> sintaxe de tabela markdown '|---|' OU lista
  4. Assinatura + link /sobre              -> automatico pelo gerador (generate.py), sempre passa
  5. Link pilar + 2 irmaos                 -> automatico pelo gerador, sempre passa (as vezes so 1 irmao se pilar pequeno)
  6. Diferenciacao real ("nada generico")  -> NAO checavel por script, fica pendente de revisao humana

Item INFORMATIVO, NAO bloqueante (corrigido 2026-08-15 -- Google encerrou os rich
results de FAQ na busca em 7/mai/2026; o schema.org FAQPage continua valido e sem
prejuizo pra indexacao, mas nao e mais retorno de SERP, entao nao justifica bloquear
publicacao. Ver quality-criteria.md):
  - FAQ de 4 perguntas -> conta H2 terminando em '?'. So reportado, nunca conta pra
    'n_fail' nem pra decisao de passa/falha do post.

Isso NAO republica nada -- so gera um relatorio (site/audit-report.md) categorizando
cada post em PASSA / FALHA MECANICA, pra decidir o que entra na fila de reescrita antes
da data agendada chegar (ver nota final do spec: "os agendados passam pela nova barra
antes de sair; os que ja estao no ar ficam").
"""
import json
import re
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent
CONTENT_DIR = ROOT / "content"
SCHEDULE_PATH = ROOT / "publish-schedule.json"
REPORT_PATH = ROOT / "audit-report.md"

def has_table_or_list(body: str) -> bool:
    if re.search(r"^\|.+\|\s*$", body, re.MULTILINE) and re.search(r"^\|[\s:-]+\|\s*$", body, re.MULTILINE):
        return True
    # lista numerada ou de marcadores com 3+ itens (comparacao/passo a passo escaneavel)
    numbered = re.findall(r"^\d+\.\s+", body, re.MULTILINE)
    bulleted = re.findall(r"^-\s+", body, re.MULTILINE)
    return len(numbered) >= 3 or len(bulleted) >= 3

def has_shown_calculation(body: str) -> bool:
    # heuristica: linha com R$ e um operador aritmetico (x, *, +, ÷, =) na mesma frase
    for line in body.split("\n"):
        if "R$" in line and re.search(r"[×x*+÷]|=\s*R\$", line):
            return True
    return False

def count_faq_questions(body: str) -> int:
    return len(re.findall(r"^## .+\?\s*$", body, re.MULTILINE))

def parse_post(path: Path):
    raw = path.read_text(encoding="utf-8").replace("=== BLOG POST ===", "").strip()
    lines = raw.split("\n")
    titulo, body_start = "", 0
    for idx, line in enumerate(lines):
        if line.startswith("Título:"):
            titulo = line.split("Título:", 1)[1].strip()
        elif line.startswith("# "):
            body_start = idx
            break
    body = "\n".join(lines[body_start:]).strip()
    return titulo, body

def slugify(filename: str) -> str:
    stem = Path(filename).stem
    m = re.match(r"^(\d+)-(.+)$", stem)
    return m.group(2) if m else stem

def main():
    schedule = json.loads(SCHEDULE_PATH.read_text(encoding="utf-8"))
    today_iso = date.today().isoformat()
    files = sorted(CONTENT_DIR.glob("*.md"))

    results = []
    for f in files:
        slug = slugify(f.name)
        sched = schedule.get(slug, {})
        titulo, body = parse_post(f)
        sources = sched.get("sources", [])
        pub_date = sched.get("date", "")
        published = pub_date and pub_date <= today_iso

        checks = {
            "1_fonte_data": bool(sources),
            "2_calculo_mostrado": has_shown_calculation(body),
            "3_tabela_lista": has_table_or_list(body),
            "4_assinatura": True,   # automatico pelo gerador
            "5_link_pilar_irmaos": True,  # automatico pelo gerador
            "6_diferenciacao": True,  # nao checavel por script -- nunca conta contra o post aqui
        }
        n_fail = sum(1 for v in checks.values() if not v)
        results.append({
            "slug": slug, "titulo": titulo, "published": published,
            "pub_date": pub_date, "checks": checks, "n_fail": n_fail,
            "faq_count": count_faq_questions(body),  # informativo, nunca conta pra n_fail
        })

    published_fail = [r for r in results if r["published"] and r["n_fail"] > 0]
    published_pass = [r for r in results if r["published"] and r["n_fail"] == 0]
    future_fail = [r for r in results if not r["published"] and r["n_fail"] > 0]
    future_pass = [r for r in results if not r["published"] and r["n_fail"] == 0]

    lines = []
    lines.append("# Auditoria — Barra de Publicação do Blog (mecânica)")
    lines.append("")
    lines.append(f"Rodado em {today_iso}. Checa só o que dá pra checar por script, dos itens BLOQUEANTES (1, 2, 3 da Barra; itens 4 e 5 são automáticos pelo gerador, sempre passam; item 6, diferenciação real, exige leitura humana, não incluído aqui). Contagem de FAQ é só informativa — corrigido em 2026-08-15: Google encerrou os rich results de FAQ na busca em 7/mai/2026, então FAQ deixou de ser critério bloqueante (ver `quality-criteria.md`).")
    lines.append("")
    lines.append(f"**Resumo**: {len(results)} posts totais · {len(published_pass) + len(published_fail)} já publicados ({len(published_fail)} com falha mecânica) · {len(future_pass) + len(future_fail)} ainda agendados ({len(future_fail)} com falha mecânica).")
    lines.append("")

    lines.append("## Já publicados, com falha mecânica (ficam no ar — nota da spec: \"os que já estão no ar ficam\" — mas viram candidatos a reforço, não a republicação às pressas)")
    lines.append("")
    for r in published_fail:
        failed = [k for k, v in r["checks"].items() if not v]
        lines.append(f"- `{r['slug']}` ({r['pub_date']}) — falha: {', '.join(failed)} (FAQ: {r['faq_count']}/4)")
    lines.append("")

    lines.append("## Ainda agendados, com falha mecânica (candidatos reais à fila de reescrita antes de sair — nota da spec)")
    lines.append("")
    for r in future_fail:
        failed = [k for k, v in r["checks"].items() if not v]
        lines.append(f"- `{r['slug']}` ({r['pub_date']}) — falha: {', '.join(failed)} (FAQ: {r['faq_count']}/4)")
    lines.append("")

    lines.append(f"## Passam em todos os checks mecânicos ({len(published_pass) + len(future_pass)} posts)")
    lines.append("")
    lines.append(", ".join(f"`{r['slug']}`" for r in published_pass + future_pass))
    lines.append("")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Relatório salvo em {REPORT_PATH}")
    print(f"Publicados com falha: {len(published_fail)}/{len(published_pass) + len(published_fail)}")
    print(f"Agendados com falha: {len(future_fail)}/{len(future_pass) + len(future_fail)}")

if __name__ == "__main__":
    main()
