"""Diagnostico: as falhas do passo 1 sao de LIMIAR ou de ROTULO?

Tres falhas concretas na primeira medicao:
  - "conquistou Constantinopla apos um cerco" nao virou categoria
  - "Grande Piramide de Gize" / "2560 a.C." nao foram reconhecidos
  - "Ja em 1789" nao virou data

Cada uma tem duas explicacoes possiveis: o span foi detectado mas ficou abaixo
do limiar (0.5), ou o rotulo usado nao descreve bem o que o modelo entende.
Este script separa as duas hipoteses baixando o limiar e testando rotulos
alternativos.

Uso:
    ./.venv/bin/python calibrar.py
"""

from __future__ import annotations

from pathlib import Path

from gliner import GLiNER

from extracao.rotulos import todos_rotulos

MODELO = "urchade/gliner_multi-v2.1"
AMOSTRA = Path(__file__).parent / "amostras" / "paragrafo_teste.txt"

# Trechos que o gabarito espera e que a primeira rodada perdeu.
ALVOS_PERDIDOS = ("cerco", "conquistou", "Pirâmide", "Gizé", "2560", "1789")

# Hipotese: rotulos mais concretos / mais proximos do vocabulario do modelo
# podem pegar o que os atuais perderam.
ROTULOS_ALTERNATIVOS = [
    "local",
    "lugar",
    "monumento",
    "ano",
    "data histórica",
    "período",
    "conquista",
    "batalha",
    "cerco militar",
    "construção",
    "obra arquitetônica",
]


def testar_limiares(modelo: GLiNER, texto: str) -> None:
    print("=" * 74)
    print("A) MESMOS ROTULOS, LIMIAR DECRESCENTE")
    print("=" * 74)
    print("Se um alvo perdido aparecer so' com limiar baixo, o problema e' limiar.\n")

    rotulos = todos_rotulos()
    for limiar in (0.5, 0.4, 0.3, 0.2, 0.1):
        entidades = modelo.predict_entities(texto, rotulos, threshold=limiar)
        achados = [
            f"{e['text']!r}({e['label']},{e['score']:.2f})"
            for e in entidades
            if any(alvo.lower() in e["text"].lower() for alvo in ALVOS_PERDIDOS)
        ]
        print(f"  limiar {limiar:.1f} -> {len(entidades):>2} entidades")
        if achados:
            for a in achados:
                print(f"              ALVO RECUPERADO: {a}")


def testar_rotulos_alternativos(modelo: GLiNER, texto: str) -> None:
    print()
    print("=" * 74)
    print("B) ROTULOS ALTERNATIVOS, LIMIAR FIXO 0.4")
    print("=" * 74)
    print("Se um alvo aparecer com outro rotulo, o problema e' escolha de rotulo.\n")

    for rotulo in ROTULOS_ALTERNATIVOS:
        entidades = modelo.predict_entities(texto, [rotulo], threshold=0.4)
        if not entidades:
            print(f"  {rotulo:<22} (nada)")
            continue
        itens = ", ".join(f"{e['text']!r}({e['score']:.2f})" for e in entidades[:5])
        print(f"  {rotulo:<22} {itens}")


def main() -> None:
    texto = AMOSTRA.read_text(encoding="utf-8")
    print("Carregando modelo...\n")
    modelo = GLiNER.from_pretrained(MODELO)

    testar_limiares(modelo, texto)
    testar_rotulos_alternativos(modelo, texto)


if __name__ == "__main__":
    main()
