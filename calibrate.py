#!/usr/bin/env python3
"""
Ferramenta de calibração visual para bot.py.

Mostra as regiões detectadas sobrepostas na captura da tela do jogo.
Use para verificar se BUBBLE_REGION e GRID_REGION estão corretos
antes de rodar o bot principal.

Uso:
    python calibrate.py
"""

import cv2
import numpy as np
import win32gui
import mss
import time

WINDOW_KEYWORDS = ('Android Device', 'BlueStacks', 'NoxPlayer', 'LDPlayer', 'MuMu')

# Deve bater com as constantes em bot.py
BUBBLE_REGION = (0.11, 0.28, 0.34, 0.19)
GRID_REGION   = (0.47, 0.27, 0.40, 0.68)
BTN_CONTINUE  = (0.73, 0.82)
BTN_QUIT      = (0.27, 0.82)


def find_window():
    hits = []
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if any(k in title for k in WINDOW_KEYWORDS):
                hits.append((hwnd, win32gui.GetWindowRect(hwnd), title))
    win32gui.EnumWindows(cb, None)
    return hits


def draw_region(img, region, color, label):
    H, W = img.shape[:2]
    x, y, w, h = region
    x1, y1 = int(x*W), int(y*H)
    x2, y2 = int((x+w)*W), int((y+h)*H)
    cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
    cv2.putText(img, label, (x1+4, y1+18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)


def draw_point(img, pt, color, label):
    H, W = img.shape[:2]
    cx, cy = int(pt[0]*W), int(pt[1]*H)
    cv2.circle(img, (cx, cy), 10, color, -1)
    cv2.putText(img, label, (cx+14, cy+6),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)


def main():
    windows = find_window()
    if not windows:
        print("Nenhuma janela de emulador encontrada.")
        print("Janelas visíveis:")
        def list_cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                t = win32gui.GetWindowText(hwnd)
                if t:
                    print(f"  '{t}'")
        win32gui.EnumWindows(list_cb, None)
        return

    hwnd, rect, title = windows[0]
    l, t, r, b = rect
    print(f"Usando janela: '{title}'")
    print(f"Posição: ({l},{t}) → ({r},{b})  [{r-l}×{b-t}px]")
    print("\nMostrando regiões calibradas. Pressione qualquer tecla na janela para fechar.")

    sct = mss.mss()
    raw = np.array(sct.grab({"left": l, "top": t, "width": r-l, "height": b-t}))
    frame = cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)

    # Desenhando regiões
    draw_region(frame, BUBBLE_REGION,  (0, 255,   0), "BUBBLE (thinking)")
    draw_region(frame, GRID_REGION,    (0, 128, 255), "GRID (selection)")
    draw_point (frame, BTN_CONTINUE,   (255, 200,  0), "CONTINUE")
    draw_point (frame, BTN_QUIT,       (0,   80, 255), "QUIT")

    # Mostrar divisões do balão (3 slots)
    H, W = frame.shape[:2]
    bx, by, bw, bh = BUBBLE_REGION
    for i in range(1, 3):
        sx = int((bx + bw * i/3) * W)
        sy1, sy2 = int(by*H), int((by+bh)*H)
        cv2.line(frame, (sx, sy1), (sx, sy2), (0, 255, 100), 1)

    # Mostrar divisões da grade (3×3)
    gx, gy, gw, gh = GRID_REGION
    for i in range(1, 3):
        # colunas
        sx = int((gx + gw * i/3) * W)
        cv2.line(frame, (sx, int(gy*H)), (sx, int((gy+gh)*H)), (100, 180, 255), 1)
        # linhas
        sy = int((gy + gh * i/3) * H)
        cv2.line(frame, (int(gx*W), sy), (int((gx+gw)*W), sy), (100, 180, 255), 1)

    # Detecção de fase (mesma lógica do bot.py v2)
    def detect_phase(img):
        bx_, by_, bw_, bh_ = BUBBLE_REGION
        gx_, gy_, gw_, gh_ = GRID_REGION
        bubble = img[int(by_*H):int((by_+bh_)*H), int(bx_*W):int((bx_+bw_)*W)]
        grid   = img[int(gy_*H):int((gy_+gh_)*H), int(gx_*W):int((gx_+gw_)*W)]
        bubble_v = cv2.inRange(cv2.cvtColor(bubble, cv2.COLOR_BGR2HSV),
                               np.array([0, 110, 60]), np.array([180, 255, 255])).mean()/255
        grid_v   = cv2.inRange(cv2.cvtColor(grid, cv2.COLOR_BGR2HSV),
                               np.array([0, 110, 60]), np.array([180, 255, 255])).mean()/255
        print(f"  balão_comida={bubble_v:.3f} (>=0.05 thinking)  grade_comida={grid_v:.3f} (>=0.06 selection)")
        if bubble_v >= 0.05: return "thinking"
        if grid_v   >= 0.06: return "selection"
        return "result"

    phase = detect_phase(frame)
    cv2.putText(frame, f"Fase detectada: {phase.upper()}", (10, H-12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

    cv2.imwrite("calibrate_output.png", frame)
    print("Imagem salva em: calibrate_output.png")

    cv2.imshow("Calibração – pressione qualquer tecla para fechar", frame)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
