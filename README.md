# Azurlane – Food Stalls

A computer-vision bot that automatically plays the **Food Stalls memory minigame**
in Azur Lane, running on an Android emulator on Windows.

The minigame shows a speech bubble with **3 foods in order** (the *thinking*
phase); the bubble then disappears and a **3×3 grid of 9 foods** appears (the
*selection* phase), where you must click the 3 correct ones, in order. The bot:

1. reads the emulator screen (passive capture via `mss`);
2. detects the phase from the color level of the bubble and the grid;
3. memorizes the bubble at its sharpest moment;
4. matches each bubble food to a grid cell using **ORB keypoints + color +
   optimal assignment** (robust to background, scale and focus);
5. clicks the 3 foods;
6. reads the result screen (⭕ correct / ✗ wrong) to count the points and **stops
   when it reaches the target** (default: 25 points), then clicks Quit.

## Two modes

| File               | Mode    | Clicks                                                        |
|--------------------|---------|---------------------------------------------------------------|
| `bot.py`           | Robot   | Exact center of the food, fixed timing. Fast and direct.      |
| `modo_humano.py`   | Human   | Randomized position and timing, natural mouse movement.       |

Both share all of the vision logic; the human mode only changes **how** it clicks,
to reduce the most obvious statistical signs of automation.

## Requirements

```
pip install -r requirements.txt
```

(`opencv-python`, `numpy`, `pyautogui`, `pywin32`, `mss`)

Works with emulators whose window title contains one of: `Android Device`,
`BlueStacks`, `NoxPlayer`, `LDPlayer`, `MuMu`.

## Usage

1. Open the game on the Food Stalls screen, at the **lobby with START GAME**.
2. Run one of the modes:

   ```
   python modo_humano.py    # recommended
   # or
   python bot.py
   ```

3. During the initial 4 seconds, click the emulator window.
4. **Emergency stop:** throw the mouse to the top-left corner of the screen.

To check the region framing before running:

```
python calibrate.py
```

See [TUTORIAL.md](TUTORIAL.md) for the detailed step-by-step (in Portuguese).

## Configuration

Key constants at the top of `bot.py`:

- `POINTS_TARGET` – points at which the bot quits (default 25).
- `LOBBY_CREDITS_TO_ADD` – how many times to click the credits "+1" before START
  (default 5, the per-batch maximum).
- `DEBUG_SAVE` – set `True` to dump debug images for diagnosing.

Human-mode timing/precision ranges live at the top of `modo_humano.py`.

## Disclaimer

Automation generally violates the game's Terms of Service. Use at your own risk.
Educational project about computer vision and UI automation.
