#!/usr/bin/env python3
"""Preenche cover-manifest.json com um prompt estruturado pra todo post de content/*.md
que ainda nao tem entrada -- mesmo template validado nas 7 capas ja publicadas (sujeito
unico, fundo preto puro, luz de borda, lente/abertura, "sem texto/logo/pessoas/marca").

Nunca sobrescreve entrada existente. Roda em toda build (atualidade.yml e rebuild.yml),
antes de generate_cover_pollinations.py -- so mexe em slug novo.

CORRIGIDO 2026-08-21 (achado real, feedback direto do usuario: "todas imagens do blog
tao NADA a ver... ficou tudo desconexo do tema"): a primeira versao escolhia o sujeito
por HASH da slug, so pra variar visualmente -- nao tinha nenhuma relacao com o assunto
do post. Reescrito pra escolher por PALAVRA-CHAVE no titulo/slug, igual ao criterio
humano usado nos 7 originais (vidro transbordando = "cheque especial no teto", vela =
"custo de sobrevivencia", cartao em pe = "rotativo", bola de neve = "metodo bola de
neve"). Cada regra abaixo é uma escolha deliberada de metafora visual pro tema, nao um
sorteio -- ver o mapeamento comentado em THEME_RULES.

Piscina de sujeitos restrita a objetos sem "superficie rotulavel" natural -- licao real
do FLUX-schnell local (2026-08-16): moeda de ouro virou logo de Bitcoin, relogio de
bolso ganhou nome de marca falso no mostrador. Evitar qualquer coisa com mostrador,
selo, rotulo ou face que convide o modelo a "preencher" um texto.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT_DIR = ROOT / "content"
MANIFEST_PATH = ROOT / "cover-manifest.json"

WRAPPER = (
    "product photography of {subject}, centered in frame, sitting on a dark "
    "reflective black surface, deep pure black background, single soft {color} "
    "rim light from upper right edge, studio lighting from the left, {lens}, "
    "sharp focus, high contrast, minimalist, no text, no numbers, no logos, "
    "no people, no brand markings"
)

LENS_DEFAULT = "85mm lens, f/2.8"
LENS_MACRO = "100mm macro lens, f/4"

# Ordem importa -- primeira regra cujo keyword bate no titulo+slug (minusculo, sem
# acento) vence. Cada (keywords, sujeito, lente) e' uma metafora visual escolhida a
# dedo pro tema, nao um sorteio.
THEME_RULES = [
    (["reserva de emerg", "reserva-emerg", "reserva-genero", "reserva-52",
      "reserva-nao-basta", "reserva-passo", "reserva-renda", "regra-6-salarios"],
     "a single closed black umbrella standing upright", LENS_DEFAULT),

    (["bola de neve", "bola-de-neve", "efeito bola"],
     "a single small white snowball resting on a dark icy surface", LENS_MACRO),

    # "cartao"/credit-card-shaped objects viraram alucinacao real via Pollinations
    # (achado 2026-08-21: texto/logo falso apareceu em 3 de 6 imagens com objeto
    # plano tipo cartao/tela -- mesma licao do FLUX local, superficie que parece
    # "pedir" texto). Anel/argola sem face plana, e ainda encaixa melhor no tema:
    # "rotativo" e' literalmente girar em circulo.
    (["rotativo", "cartao", "parcelamento", "pagamento minimo", "fatura"],
     "a single dark ring or torus shape, plain and unmarked", LENS_DEFAULT),

    (["custo de sobrevivencia", "custo-sobrevivencia"],
     "a single lit candle with an unusually tall flickering flame", LENS_DEFAULT),

    (["ordem certa", "ordem das", "ordem-certa", "ordem-das", "prioridades"],
     "a small pyramid of plain wooden blocks stacked in order", LENS_DEFAULT),

    (["endivida", "negativad", "vermelho", "8,5 milhoes", "cet do credito",
      "credito para negativado", "credito-negativado"],
     "a plain blank smooth metal sphere balanced perfectly split in half, "
     "one half in shadow one half lit", LENS_MACRO),

    (["raio-x", "raiox", "quanto sobra", "proximo passo", "proximo-passo",
      "antes de parcelar", "1 minuto", "controle financeiro em 1 minuto"],
     "a brass magnifying glass with a plain handle", LENS_DEFAULT),

    (["habito", "planilha"],
     "a short wooden ladder seen close on two rungs", LENS_DEFAULT),

    (["consultor de bolso", "consultor-de-bolso"],
     "a single warm glowing lightbulb with visible filament", LENS_MACRO),

    (["conta misturada", "mei-conta-misturada"],
     "two water droplets merging into one, suspended in mid-air", LENS_MACRO),

    (["desiste de controlar", "lancamento-1-minuto"],
     "a small wilting plant sprout in dry soil", LENS_DEFAULT),

    (["redirecionar", "redirecionar-divida"],
     "a plain brass compass, closed", LENS_MACRO),

    (["consignado"],
     "a closed brass padlock", LENS_MACRO),

    (["financiamento de carro", "financiamento-veiculo"],
     "a metal coil spring stretched far beyond its natural length", LENS_DEFAULT),

    (["selic", "focus"],
     "a plain brass compass, closed", LENS_MACRO),

    (["casas bahia", "recuperacao judicial", "carne-casas-bahia"],
     "a single piece of dark folded fabric", LENS_DEFAULT),

    (["pix", "med", "golpe"],
     "a single brass key", LENS_MACRO),

    (["liquidacao", "consorcio", "bc decreta"],
     "a heavy brass bank vault door slightly ajar", "50mm lens, f/4"),

    (["fgts"],
     "a single ripple frozen on a still dark water surface", LENS_MACRO),

    (["renda variavel", "renda-variavel"],
     "a simple metal balance scale with two empty pans, perfectly level", LENS_DEFAULT),
]

FALLBACK_SUBJECT = ("a plain glass marble", LENS_MACRO)

RED_HINTS = (
    "divida", "rotativo", "cheque", "cartao", "parcelamento", "negativad",
    "consignado", "atraso", "vermelho", "escondid", "armadilha", "golpe",
    "credito-tarde", "credito-negativado", "financiamento",
)


def strip_accents(s: str) -> str:
    table = str.maketrans("áàâãéêíóôõúüç", "aaaaeeiooouuc")
    return s.translate(table)


def slugify(filename: str) -> str:
    stem = Path(filename).stem
    m = re.match(r"^(\d+)-(.+)$", stem)
    return m.group(2) if m else stem


def extract_titulo(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    m = re.search(r"T[ií]tulo:\s*(.+)", raw)
    return m.group(1).strip() if m else ""


def pick_color(slug: str) -> str:
    return "red" if any(h in slug for h in RED_HINTS) else "green"


def pick_subject(slug: str, titulo: str):
    haystack = strip_accents((slug + " " + titulo).lower())
    for keywords, subject, lens in THEME_RULES:
        if any(strip_accents(k) in haystack for k in keywords):
            return subject, lens
    return FALLBACK_SUBJECT


def main():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    existing = {m["slug"] for m in manifest}

    files = sorted(CONTENT_DIR.glob("*.md"))
    added = []
    for f in files:
        slug = slugify(f.name)
        if slug in existing:
            continue
        titulo = extract_titulo(f)
        subject, lens = pick_subject(slug, titulo)
        color = pick_color(slug)
        prompt = WRAPPER.format(subject=subject, color=color, lens=lens)
        manifest.append({"slug": slug, "prompt": prompt})
        added.append((slug, subject))

    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Adicionadas {len(added)} entradas novas em cover-manifest.json:")
    for s, subj in added:
        print(f" - {s} -> {subj}")


if __name__ == "__main__":
    main()
