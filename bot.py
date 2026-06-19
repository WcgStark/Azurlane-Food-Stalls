#!/usr/bin/env python3
"""
Azur Lane – Bot de memória da barraca de comida.  (v2 – matching estrutural)

Estratégia v2:
  • Fase "thinking" é detectada pela PRESENÇA DO BALÃO BRANCO (não pela cor da
    comida), eliminando a ambiguidade com a grade que já mostra comida.
  • O emparelhamento balão→grade usa recorte da comida por máscara (remove o
    fundo branco do balão e a madeira da grade), bounding-box + resize, e
    compara FORMA (template matching) + COR. Isso alinha as comidas
    espacialmente e separa itens tan parecidos (bubble tea, taiyaki, macarrão).

Requisitos:
    pip install opencv-python numpy pyautogui pywin32 mss
"""

import cv2
import numpy as np
import pyautogui
import time
import itertools
import win32gui
import mss
from pathlib import Path
from typing import List, Tuple

# ─── Configuração ─────────────────────────────────────────────────────────────

POINTS_TARGET        = 25     # para quando o "Remaining" (pontos do jogo) atinge isto
# Pontos por nº de acertos na rodada (lidos da tela de resultado: ⭕=acerto, ✗=erro)
POINTS_BY_CORRECT    = {3: 5, 2: 2, 1: 1, 0: 0}
CLICK_DELAY          = 0.18   # pausa após cada clique
SELECT_SETTLE        = 0.35   # espera a grade assentar antes de clicar (anti-animação)
MOVE_DURATION        = 0.08   # duração do movimento do mouse (clique mais confiável)
LOBBY_CREDITS_TO_ADD = 0      # 0 = vai direto no START GAME sem adicionar créditos
DEBUG_SAVE           = False  # True → salva imagens de debug (útil para diagnosticar)

WINDOW_KEYWORDS = ('Android Device', 'BlueStacks', 'NoxPlayer', 'LDPlayer', 'MuMu')

# Regiões em frações (x, y, w, h) da janela do emulador.
BUBBLE_REGION = (0.11, 0.28, 0.34, 0.19)   # balão de pensamento (3 comidas)
GRID_REGION   = (0.47, 0.27, 0.40, 0.68)   # grade 3×3 de seleção

BTN_CONTINUE  = (0.73, 0.82)
BTN_QUIT      = (0.27, 0.82)

# Detecção de fase — calibrada a partir de diag_log.txt (a grade está SEMPRE
# com comida; o que muda é o nível). Por rodada:
#   thinking   → balão_comida ~0.14-0.21, grade ~0.34
#   selection  → balão_comida ~0.05 (vazio), grade no PICO ~0.51
#   result     → botão Continue presente, grade ~0.21-0.25
VIVID_SAT    = 110     # saturação mínima para contar como "comida"
GRID_SELECT  = 0.45    # grade >= 0.45 (pico) + balão vazio → selection
BUBBLE_EMPTY = 0.12    # balão < 0.12 = vazio (na selection)
FRAC_BUBBLE  = 0.10    # balão >= 0.10 com comida → thinking

# Matching balão→grade via ORB (pontos-chave, robusto a fundo/escala) + cor.
# Validado offline em 5 rodadas reais: 14/15 slots, 4/5 rodadas perfeitas.
ORB_FEATURES = 500
ORB_RATIO    = 0.78    # teste de Lowe (razão entre 1º e 2º vizinho)
COLOR_WEIGHT = 6.0     # peso do histograma de matiz somado à contagem de matches ORB

# ──────────────────────────────────────────────────────────────────────────────

pyautogui.PAUSE    = 0.05
pyautogui.FAILSAFE = True


class MemoryBot:

    def __init__(self):
        self.sct            = mss.MSS()
        self.win            = None
        self.order_slots    = []    # [crop_slot0, crop_slot1, crop_slot2]
        self.thinking_frame = None
        self.points         = 0     # pontos acumulados (lidos da tela de resultado)
        self.mark_circle    = None  # template ⭕ (acerto)
        self.mark_x         = None  # template ✗ (erro)
        self.ref_start_game = None
        self.ref_credits    = None
        self.ref_continue   = None
        self._continue_pos  = None
        self._in_game       = False
        self._orb           = cv2.ORB_create(nfeatures=ORB_FEATURES)
        self._bf            = cv2.BFMatcher(cv2.NORM_HAMMING)

    # ── Referências e janela ──────────────────────────────────────────────────

    @staticmethod
    def _imread_unicode(path: Path):
        """cv2.imread falha com caminhos acentuados no Windows; np.fromfile não."""
        data = np.fromfile(str(path), dtype=np.uint8)
        return cv2.imdecode(data, cv2.IMREAD_COLOR)

    def load_reference_images(self):
        for fname, attr in [("start game.png",          "ref_start_game"),
                             ("creditos.png",            "ref_credits"),
                             ("botão para continuar.png", "ref_continue")]:
            p = Path(fname)
            if p.exists():
                setattr(self, attr, self._imread_unicode(p))
                print(f"Referência carregada: {fname}")
            else:
                print(f"AVISO: '{fname}' não encontrado")
        # Templates das marcas de acerto/erro (máscaras vermelhas, lidas em cinza)
        for fname, attr in [("mark_circle.png", "mark_circle"),
                            ("mark_x.png",      "mark_x")]:
            p = Path(fname)
            if p.exists():
                m = self._imread_unicode(p)
                setattr(self, attr, cv2.cvtColor(m, cv2.COLOR_BGR2GRAY))

    def find_window(self) -> bool:
        hits = []
        def cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                if any(k in win32gui.GetWindowText(hwnd) for k in WINDOW_KEYWORDS):
                    hits.append(win32gui.GetWindowRect(hwnd))
        win32gui.EnumWindows(cb, None)
        if hits:
            self.win = hits[0]
            return True
        return False

    def grab(self) -> np.ndarray:
        l, t, r, b = self.win
        raw = np.array(self.sct.grab({"left": l, "top": t, "width": r-l, "height": b-t}))
        return cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)

    def _crop(self, img: np.ndarray, region: Tuple) -> np.ndarray:
        H, W = img.shape[:2]
        x, y, w, h = region
        return img[int(y*H):int((y+h)*H), int(x*W):int((x+w)*W)].copy()

    def _abs_xy(self, xf: float, yf: float) -> Tuple[int, int]:
        l, t, r, b = self.win
        return (l + int(xf*(r-l)), t + int(yf*(b-t)))

    def _find_in_frame(self, tmpl, frame, threshold=0.70, x_frac=0.5, y_frac=0.5):
        best_val, best_loc, best_sz = 0.0, (0, 0), tmpl.shape[:2]
        for scale in np.linspace(0.75, 1.25, 6):
            nh = max(int(tmpl.shape[0]*scale), 4)
            nw = max(int(tmpl.shape[1]*scale), 4)
            if nh >= frame.shape[0] or nw >= frame.shape[1]:
                continue
            scaled = cv2.resize(tmpl, (nw, nh))
            res    = cv2.matchTemplate(frame, scaled, cv2.TM_CCOEFF_NORMED)
            _, mv, _, ml = cv2.minMaxLoc(res)
            if mv > best_val:
                best_val = mv; best_loc = ml; best_sz = (nh, nw)
        if best_val >= threshold:
            l, t, _, _ = self.win
            nh, nw = best_sz
            return (l + best_loc[0] + int(nw*x_frac),
                    t + best_loc[1] + int(nh*y_frac))
        return None

    # ── Descritores de item (ORB + cor) ───────────────────────────────────────

    def _orb_des(self, crop: np.ndarray, up: int = 200):
        """Descritores ORB do item, ampliado para tamanho fixo (robusto a escala)."""
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (up, up), interpolation=cv2.INTER_CUBIC)
        _, des = self._orb.detectAndCompute(gray, None)
        return des

    def _orb_matches(self, des_a, des_b) -> float:
        """Nº de matches bons (teste de Lowe) entre dois conjuntos de descritores."""
        if des_a is None or des_b is None or len(des_a) < 2 or len(des_b) < 2:
            return 0.0
        good = 0
        for m in self._bf.knnMatch(des_a, des_b, k=2):
            if len(m) == 2 and m[0].distance < ORB_RATIO * m[1].distance:
                good += 1
        return float(good)

    @staticmethod
    def _hue_hist(crop: np.ndarray):
        """Histograma de matiz só dos pixels coloridos (discrimina comidas vívidas)."""
        hsv = cv2.cvtColor(cv2.resize(crop, (80, 80)), cv2.COLOR_BGR2HSV)
        sat = cv2.inRange(hsv, np.array([0, 60, 40]), np.array([180, 255, 255]))
        h   = cv2.calcHist([hsv], [0], sat, [18], [0, 180])
        cv2.normalize(h, h)
        return h.flatten()

    # ── Detecção de fase ──────────────────────────────────────────────────────

    def detect_phase(self, frame: np.ndarray) -> str:
        # Lobby: só antes do jogo começar
        if not self._in_game and self.ref_start_game is not None:
            if self._find_in_frame(self.ref_start_game, frame, 0.65):
                return "lobby"

        def vivid_frac(crop) -> float:
            hsv  = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, np.array([0, VIVID_SAT, 60]),
                               np.array([180, 255, 255]))
            return mask.mean() / 255

        bubble_frac = vivid_frac(self._crop(frame, BUBBLE_REGION))
        grid_frac   = vivid_frac(self._crop(frame, GRID_REGION))
        self._bubble_frac = bubble_frac   # exposto pro loop escolher o balão mais sólido

        now = time.time()
        if now - getattr(self, "_last_meter", 0) > 0.5:
            self._last_meter = now
            print(f"\r  [fase] balão_comida={bubble_frac:.3f}  "
                  f"grade_comida={grid_frac:.3f}  "
                  f"(sel: grade>={GRID_SELECT} & balão<{BUBBLE_EMPTY})    ",
                  end="", flush=True)

        # SELECTION: grade no PICO de vivacidade e balão vazio. Checado PRIMEIRO
        # (sem custo de template) porque é a fase em que precisa agir rápido.
        if grid_frac >= GRID_SELECT and bubble_frac < BUBBLE_EMPTY:
            self._in_game = True
            return "selection"

        # RESULT: tela "Desired/Actual Order" com botão Continue central.
        # Tem comida no balão (como o thinking), então desempata pelo template.
        self._continue_pos = self._find_continue(frame)
        if self._continue_pos is not None:
            return "result"

        # THINKING: comida no balão (e grade fora do pico).
        if bubble_frac >= FRAC_BUBBLE:
            self._in_game = True
            return "thinking"

        return "idle"

    def _find_continue(self, frame):
        if self.ref_continue is None:
            return None
        return self._find_in_frame(self.ref_continue, frame, threshold=0.68)

    # ── Memorização ───────────────────────────────────────────────────────────

    def memorize_from_crop(self, bubble: np.ndarray):
        """Divide o recorte do balão (já capturado no instante mais sólido) em 3 slots."""
        W  = bubble.shape[1]
        sw = W // 3
        self.order_slots = [bubble[:, i*sw:(i+1)*sw].copy() for i in range(3)]
        print(f"  Balão memorizado (frac={getattr(self, '_best_frac', 0):.3f}): "
              f"{len(self.order_slots)} slots")
        if DEBUG_SAVE:
            self._imwrite_unicode("debug_bubble.png", bubble)
            for i, s in enumerate(self.order_slots):
                self._imwrite_unicode(f"debug_slot_{i}.png", s)

    def _save_round_sample(self, sel_frame: np.ndarray):
        """Salva amostra limpa (balão sólido + grade da selection) para desenvolver
        o matcher offline. Numerado por rodada."""
        n = getattr(self, "_sample_n", 0)
        self._sample_n = n + 1
        if self._best_bubble is not None:
            self._imwrite_unicode(f"sample_{n:02d}_bubble.png", self._best_bubble)
        self._imwrite_unicode(f"sample_{n:02d}_grid.png", self._crop(sel_frame, GRID_REGION))
        print(f"  [amostra] sample_{n:02d}_bubble.png + sample_{n:02d}_grid.png salvos")

    @staticmethod
    def _imwrite_unicode(path: str, img: np.ndarray):
        cv2.imencode(".png", img)[1].tofile(path)

    # ── Localização: balão → células da grade ─────────────────────────────────

    def find_by_direct_match(self, frame: np.ndarray) -> List[Tuple[int, int]]:
        grid = self._crop(frame, GRID_REGION)
        gH, gW = grid.shape[:2]
        cw, ch = gW // 3, gH // 3

        l, t, r, b = self.win
        ox = l + int(GRID_REGION[0] * (r-l))
        oy = t + int(GRID_REGION[1] * (b-t))

        # 9 células: centro de clique + descritores ORB + histograma de cor
        cells     = []
        cell_des  = []
        cell_hist = []
        for row in range(3):
            for col in range(3):
                cell = grid[row*ch:(row+1)*ch, col*cw:(col+1)*cw]
                cx   = ox + col*cw + cw//2
                cy   = oy + row*ch + ch//2
                cells.append((cx, cy, row, col))
                cell_des.append(self._orb_des(cell))
                cell_hist.append(self._hue_hist(cell))

        slot_des  = [self._orb_des(s)  for s in self.order_slots]
        slot_hist = [self._hue_hist(s) for s in self.order_slots]

        if DEBUG_SAVE:
            overlay = grid.copy()
            for rr in range(1, 3):
                cv2.line(overlay, (0, rr*ch), (gW, rr*ch), (0, 255, 0), 1)
                cv2.line(overlay, (rr*cw, 0), (rr*cw, gH), (0, 255, 0), 1)
            for row in range(3):
                for col in range(3):
                    cv2.circle(overlay, (col*cw+cw//2, row*ch+ch//2), 4, (0, 0, 255), -1)
            self._imwrite_unicode("debug_grid_overlay.png", overlay)
            self._imwrite_unicode("debug_selection_frame.png", frame)

        # Matriz de score 3×9: matches ORB + peso*correlação de matiz
        score = np.zeros((3, 9), dtype=np.float32)
        for i in range(3):
            for j in range(9):
                orb_n = self._orb_matches(slot_des[i], cell_des[j])
                color = float(cv2.compareHist(slot_hist[i], cell_hist[j],
                                              cv2.HISTCMP_CORREL))
                score[i, j] = orb_n + COLOR_WEIGHT * color

        # Atribuição ÓTIMA: melhor combinação de 3 células distintas (504 opções)
        best_combo, best_total = None, -1e9
        for combo in itertools.permutations(range(9), 3):
            tot = score[0, combo[0]] + score[1, combo[1]] + score[2, combo[2]]
            if tot > best_total:
                best_total, best_combo = tot, combo

        results = []
        for i in range(3):
            j = best_combo[i]
            cx, cy, row, col = cells[j]
            print(f"    Slot {i} → célula ({row},{col})  score={score[i, j]:.1f}")
            results.append((cx, cy))
        return results

    # ── Ações ─────────────────────────────────────────────────────────────────

    def click(self, x: int, y: int):
        # Mover com duração + pequena pausa antes de clicar: o emulador às vezes
        # perde cliques "teleportados" instantâneos.
        pyautogui.moveTo(x, y, duration=MOVE_DURATION)
        time.sleep(0.04)
        pyautogui.click()
        time.sleep(CLICK_DELAY)

    def settle_delay(self) -> float:
        """Tempo de espera após detectar a selection (sobrescrito no modo humano)."""
        return SELECT_SETTLE

    # ── Contagem de pontos (tela de resultado) ────────────────────────────────

    @staticmethod
    def _red_mask(bgr: np.ndarray) -> np.ndarray:
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        m1  = cv2.inRange(hsv, np.array([0,   90, 110]), np.array([12,  255, 255]))
        m2  = cv2.inRange(hsv, np.array([168, 90, 110]), np.array([180, 255, 255]))
        return cv2.bitwise_or(m1, m2)

    def count_corrects(self, frame: np.ndarray) -> int:
        """Conta acertos na tela de resultado: ⭕ (acerto) vs ✗ (erro) embaixo de
        cada uma das 3 comidas do 'Actual Order'. Validado em 6 rodadas reais."""
        if self.mark_circle is None or self.mark_x is None:
            return 3   # sem templates → assume acerto total (não trava o fluxo)

        def best(region_mask, t):
            if region_mask.shape[0] < t.shape[0] or region_mask.shape[1] < t.shape[1]:
                t = cv2.resize(t, (min(t.shape[1], region_mask.shape[1]),
                                   min(t.shape[0], region_mask.shape[0])))
            return float(cv2.matchTemplate(region_mask, t, cv2.TM_CCOEFF_NORMED).max())

        H, W = frame.shape[:2]
        thirds = np.linspace(0.52, 0.785, 4)
        correct = 0
        for i in range(3):
            reg = frame[int(0.485*H):int(0.58*H),
                        int(thirds[i]*W):int(thirds[i+1]*W)]
            m = self._red_mask(reg)
            if (m > 0).sum() < 15:
                continue
            if best(m, self.mark_circle) > best(m, self.mark_x):
                correct += 1
        return correct

    def press_continue(self):
        self.click(*self._abs_xy(*BTN_CONTINUE))

    def press_quit(self):
        self.click(*self._abs_xy(*BTN_QUIT))

    def handle_lobby(self, frame: np.ndarray):
        if LOBBY_CREDITS_TO_ADD > 0 and self.ref_credits is not None:
            plus1 = self._find_in_frame(self.ref_credits, frame,
                                        threshold=0.65, x_frac=0.91)
            if plus1 is None:
                plus1 = self._abs_xy(0.824, 0.882)
            for i in range(1, LOBBY_CREDITS_TO_ADD + 1):
                print(f"  +1 ({i}/{LOBBY_CREDITS_TO_ADD}) → {plus1}")
                self.click(*plus1)
            time.sleep(0.3)

        start_pos = self._find_in_frame(self.ref_start_game, frame, 0.65)
        if start_pos is None:
            start_pos = self._abs_xy(0.575, 0.720)
        print(f"  START GAME → {start_pos}")
        self.click(*start_pos)

    # ── Loop principal ────────────────────────────────────────────────────────

    def run(self):
        if not self.find_window():
            print("ERRO: janela do emulador não encontrada.")
            return
        self.load_reference_images()

        l, t, r, b = self.win
        print(f"Janela: ({l},{t})→({r},{b})  [{r-l}×{b-t}px]")
        print(f"Meta: {POINTS_TARGET} pontos → para\n")

        last_phase       = None
        round_click_done = False
        result_done      = False
        lobby_done       = False
        self._best_frac  = 0.0
        self._best_bubble = None

        while True:
            frame = self.grab()
            phase = self.detect_phase(frame)

            if phase != last_phase:
                print(f"\n── {phase.upper():<10}  pontos={self.points}/{POINTS_TARGET} ──")
                last_phase = phase
                if phase == "thinking":
                    round_click_done   = False
                    self._best_frac    = 0.0     # reinicia busca pelo balão mais sólido
                    self._best_bubble  = None
                if phase != "result":
                    result_done = False

            if phase == "lobby" and not lobby_done:
                time.sleep(0.4)
                self.handle_lobby(frame)
                lobby_done = True

            elif phase == "thinking":
                # Guarda o balão no instante MAIS SÓLIDO (maior vivacidade), pois as
                # comidas vão desbotando ao longo do thinking.
                if self._bubble_frac > getattr(self, "_best_frac", 0.0):
                    self._best_frac   = self._bubble_frac
                    self._best_bubble = self._crop(frame, BUBBLE_REGION)

            elif phase == "selection" and not round_click_done:
                round_click_done = True
                if self._best_bubble is not None:
                    self.memorize_from_crop(self._best_bubble)
                if self.order_slots:
                    time.sleep(self.settle_delay())   # deixa a grade parar de animar
                    frame = self.grab()               # frame fresco e estável
                    if DEBUG_SAVE:
                        self._save_round_sample(frame)
                    print("  Emparelhando slots do balão com células da grade…")
                    positions = self.find_by_direct_match(frame)
                    for pos in positions:
                        self.click(*pos)
                    print("  ✓ Clicou os 3")
                else:
                    print("  Nenhum slot memorizado, pulando")

            elif phase == "result" and not result_done:
                result_done = True
                time.sleep(0.6)
                rframe = self.grab()
                if DEBUG_SAVE:
                    rn = getattr(self, "_result_n", 0); self._result_n = rn + 1
                    self._imwrite_unicode(f"result_{rn:02d}.png", rframe)

                correct = self.count_corrects(rframe)
                gained  = POINTS_BY_CORRECT.get(correct, 0)
                self.points += gained
                print(f"  Resultado: {correct}/3 acertos → +{gained}  "
                      f"(total: {self.points}/{POINTS_TARGET})")

                if self.points >= POINTS_TARGET:
                    print(f"\n✓ Meta de {POINTS_TARGET} pontos atingida! Encerrando.")
                    return

                pos = self._continue_pos or self._find_continue(self.grab())
                if pos is not None:
                    print(f"  CONTINUE → {pos}")
                    self.click(*pos)
                else:
                    print("  CONTINUE (posição fixa, template não encontrado)")
                    self.press_continue()

            # idle: transição entre telas — apenas aguarda.

            time.sleep(0.05)


if __name__ == "__main__":
    print("=" * 54)
    print("  Azur Lane – Bot de Memória (v2)")
    print(f"  Meta: {POINTS_TARGET} pontos → para")
    print("  Parada de emergência: mouse no canto superior esquerdo")
    print("=" * 54)
    print("\nIniciando em 4s — alterne para o jogo…\n")
    time.sleep(4)
    MemoryBot().run()
