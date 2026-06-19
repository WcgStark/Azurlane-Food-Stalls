#!/usr/bin/env python3
"""
Azur Lane – Bot de Memória — MODO HUMANO.

Mesma lógica e mesmo matcher do bot.py (modo robô), mas os cliques imitam um
humano para reduzir os sinais estatísticos óbvios de automação:

  • tempo de reação variável antes de começar a clicar;
  • posição do clique com variação aleatória DENTRO da comida (não o centro exato);
  • movimento do mouse com duração e curva naturais (não teleporta);
  • intervalos irregulares entre cliques e pausas "distraídas" ocasionais.

Não te torna invisível (anti-cheat ainda pode olhar reação/consistência ao longo
do tempo), mas remove os padrões mais robóticos.

Rodar:  python modo_humano.py
Parada de emergência: jogue o mouse para o canto superior esquerdo da tela.
"""
import random
import time
import pyautogui
import bot
from bot import MemoryBot

# ─── Faixas de aleatoriedade (segundos / pixels) ──────────────────────────────
REACTION        = (0.5, 1.3)    # "ver" a grade antes de agir (também deixa assentar)
MOVE_DUR        = (0.18, 0.50)  # duração do movimento do mouse até a comida
DWELL           = (0.04, 0.14)  # pausa parado antes de pressionar
BETWEEN_CLICKS  = (0.28, 0.70)  # intervalo normal entre um clique e o próximo
JITTER_PX       = 14            # variação máxima da posição do clique (± px)
LONG_PAUSE_PROB = 0.12          # chance de uma pausa maior, como se distraísse
LONG_PAUSE      = (0.8, 2.0)
# ──────────────────────────────────────────────────────────────────────────────


class HumanBot(MemoryBot):
    """Igual ao MemoryBot, só muda COMO clica e o tempo de reação."""

    def settle_delay(self) -> float:
        # Tempo de reação humano antes de clicar (varia a cada rodada).
        return random.uniform(*REACTION)

    def click(self, x: int, y: int):
        jx = x + random.randint(-JITTER_PX, JITTER_PX)
        jy = y + random.randint(-JITTER_PX, JITTER_PX)
        pyautogui.moveTo(jx, jy, duration=random.uniform(*MOVE_DUR),
                         tween=pyautogui.easeInOutQuad)
        time.sleep(random.uniform(*DWELL))
        pyautogui.click()
        if random.random() < LONG_PAUSE_PROB:
            time.sleep(random.uniform(*LONG_PAUSE))
        else:
            time.sleep(random.uniform(*BETWEEN_CLICKS))


if __name__ == "__main__":
    print("=" * 54)
    print("  Azur Lane – Bot de Memória (MODO HUMANO)")
    print(f"  Meta: {bot.POINTS_TARGET} pontos → para")
    print("  Parada de emergência: mouse no canto superior esquerdo")
    print("=" * 54)
    print("\nIniciando em 4s — alterne para o jogo…\n")
    time.sleep(4)
    HumanBot().run()
