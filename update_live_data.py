#!/usr/bin/env python3
"""Busca as taxas de juros mais recentes direto da API pública do Banco Central
(SGS -- Sistema Gerenciador de Séries Temporais, sem autenticação) e grava em
live-data.json. generate.py lê esse arquivo pra montar as páginas de "dado vivo"
(taxa do cheque especial, taxa do rotativo do cartão) com o número real e a data
real de quando o BACEN publicou -- nunca a data de hoje, que seria mentir sobre
frescor do dado (o BACEN publica com ~1-2 meses de atraso).

Séries verificadas manualmente em 2026-08-15 (valores batem com a faixa conhecida
de mercado -- cheque especial ~130-150% a.a., rotativo ~400-450% a.a.):
- 20741: Taxa média de juros das operações de crédito com recursos livres —
  Pessoas físicas — Cheque especial (% a.a.)
- 22022: Taxa média de juros das operações de crédito com recursos livres —
  Pessoas físicas — Cartão de crédito rotativo (% a.a.)

Rodar sempre que o site for reconstruído (já entra no rebuild.yml diário) --
o dado do BACEN só muda uma vez por mês, então rodar todo dia é barato e
garante que a primeira vez que o mês novo sai, o site pega no dia seguinte
em vez de esperar um cron mensal separado.

Se a API estiver fora do ar, mantém o live-data.json anterior (não derruba o
build inteiro por causa disso) e avisa no log.
"""
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_PATH = ROOT / "live-data.json"

SERIES = {
    "cheque-especial": {
        "codigo": 20741,
        "unidade": "% ao ano",
        "descricao_bacen": "Taxa média de juros das operações de crédito com recursos livres — Pessoas físicas — Cheque especial",
    },
    "rotativo-cartao": {
        "codigo": 22022,
        "unidade": "% ao ano",
        "descricao_bacen": "Taxa média de juros das operações de crédito com recursos livres — Pessoas físicas — Cartão de crédito rotativo",
    },
}

def fetch_latest(codigo: int) -> dict:
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados/ultimos/1?formato=json"
    with urllib.request.urlopen(url, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if not data:
        raise ValueError(f"série {codigo}: resposta vazia da API do BACEN")
    return data[0]  # {"data": "DD/MM/AAAA", "valor": "..."}

def main():
    existing = {}
    if OUT_PATH.exists():
        existing = json.loads(OUT_PATH.read_text(encoding="utf-8"))

    out = dict(existing)
    for key, info in SERIES.items():
        try:
            ponto = fetch_latest(info["codigo"])
            out[key] = {
                "codigo": info["codigo"],
                "valor": ponto["valor"],
                "data_referencia": ponto["data"],  # mês/ano a que o dado se refere, não hoje
                "unidade": info["unidade"],
                "descricao_bacen": info["descricao_bacen"],
            }
            print(f"{key}: {ponto['valor']} {info['unidade']} (ref. {ponto['data']})")
        except Exception as e:
            print(f"aviso: falha ao buscar série {info['codigo']} ({key}): {e} -- mantendo valor anterior, se houver")

    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Gravado em {OUT_PATH}")

if __name__ == "__main__":
    main()
