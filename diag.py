#!/usr/bin/env python3
"""
Diagnóstico de fases — grava os medidores ao longo de uma rodada inteira.

Como usar:
  1. Deixe o jogo no LOBBY (com START GAME), OU já entrando numa rodada.
  2. Rode:  python diag.py
  3. Você tem 4s para alternar para o jogo. NÃO mexa no mouse — ele só observa,
     não clica em nada.
  4. Jogue/observe UMA rodada inteira (memorizar → selecionar → resultado).
  5. Ao terminar (30s), ele salva:
       - diag_log.txt          → tabela com os números a cada instante
       - diag_phase_*.png      → uma foto de cada vez que a fase muda
  6. Me mande o diag_log.txt e as imagens diag_phase_*.png.
"""

import cv2
import numpy as np
import time
import win32gui
import mss
from pathlib import Path

WINDOW_KEYWORDS = ('Android Device', 'BlueStacks', 'NoxPlayer', 'LDPlayer', 'MuMu')
BUBBLE_REGION   = (0.11, 0.28, 0.34, 0.19)
GRID_REGION     = (0.47, 0.27, 0.40, 0.68)
VIVID_SAT       = 110
DURATION        = 30.0     # segundos observando
FPS             = 5


def find_window():
    hits = []
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            if any(k in win32gui.GetWindowText(hwnd) for k in WINDOW_KEYWORDS):
                hits.append(win32gui.GetWindowRect(hwnd))
    win32gui.EnumWindows(cb, None)
    return hits[0] if hits else None


def crop(img, region):
    H, W = img.shape[:2]
    x, y, w, h = region
    return img[int(y*H):int((y+h)*H), int(x*W):int((x+w)*W)]


def vivid_frac(c):
    hsv  = cv2.cvtColor(c, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([0, VIVID_SAT, 60]), np.array([180, 255, 255]))
    return mask.mean() / 255


def main():
    win = find_window()
    if not win:
        print("ERRO: janela do emulador não encontrada.")
        return
    l, t, r, b = win
    print(f"Janela: ({l},{t})→({r},{b})  [{r-l}×{b-t}px]")
    print("Observando por 30s — alterne para o jogo e jogue uma rodada. NÃO mexa no mouse.")
    print("Iniciando em 4s…")
    time.sleep(4)

    sct = mss.mss()
    lines = ["tempo  balão_comida  grade_comida  fase_estimada"]
    last_label = None
    snap_i = 0
    t0 = time.time()

    while time.time() - t0 < DURATION:
        raw = np.array(sct.grab({"left": l, "top": t, "width": r-l, "height": b-t}))
        frame = cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)

        bf = vivid_frac(crop(frame, BUBBLE_REGION))
        gf = vivid_frac(crop(frame, GRID_REGION))

        if   bf >= 0.05 and gf >= 0.06: label = "BALÃO+GRADE"
        elif bf >= 0.05:                label = "só_BALÃO"
        elif gf >= 0.06:                label = "só_GRADE"
        else:                           label = "vazio"

        el = time.time() - t0
        line = f"{el:5.1f}  {bf:11.3f}  {gf:12.3f}  {label}"
        lines.append(line)
        print("  " + line)

        if label != last_label:
            last_label = label
            fname = f"diag_phase_{snap_i:02d}_{label}.png"
            data = cv2.imencode(".png", frame)[1]
            data.tofile(fname)        # salva com caminho/nome unicode-safe
            print(f"    → snapshot: {fname}")
            snap_i += 1

        time.sleep(1.0 / FPS)

    Path("diag_log.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\nPronto! Gerados: diag_log.txt e diag_phase_*.png")
    print("Me mande esses arquivos.")


if __name__ == "__main__":
    main()
