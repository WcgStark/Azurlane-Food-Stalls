# Azurlane – Food Stalls

Bot de visão computacional que joga automaticamente o **minigame de memória da
barraca de comida** (Food Stalls) do Azur Lane, rodando em emulador Android no
Windows.

O minigame mostra um balão com **3 comidas em ordem** (fase *thinking*); em
seguida some o balão e aparece uma **grade 3×3 com 9 comidas** (fase *selection*),
onde você precisa clicar nas 3 certas, na ordem. O bot:

1. lê a tela do emulador (captura passiva via `mss`);
2. detecta a fase pelo nível de cor do balão e da grade;
3. memoriza o balão no instante mais nítido;
4. casa cada comida do balão com a célula da grade usando **pontos-chave ORB +
   cor + atribuição ótima** (robusto a fundo, escala e foco);
5. clica nas 3 comidas;
6. lê a tela de resultado (⭕ acerto / ✗ erro) para contar os pontos e **para ao
   atingir a meta** (padrão: 25 pontos).

## Dois modos

| Arquivo            | Modo    | Cliques                                                        |
|--------------------|---------|---------------------------------------------------------------|
| `bot.py`           | Robô    | Centro exato da comida, tempos fixos. Rápido e direto.        |
| `modo_humano.py`   | Humano  | Posição e tempos aleatórios, movimento natural do mouse.      |

Os dois compartilham toda a lógica de visão; o modo humano só muda **como** clica,
para reduzir os padrões estatísticos óbvios de automação.

## Requisitos

```
pip install -r requirements.txt
```

(`opencv-python`, `numpy`, `pyautogui`, `pywin32`, `mss`)

Funciona com emuladores cuja janela contenha um dos nomes: `Android Device`,
`BlueStacks`, `NoxPlayer`, `LDPlayer`, `MuMu`.

## Como usar

1. Abra o jogo na tela da barraca de comida, no **lobby com START GAME**.
2. Rode um dos modos:

   ```
   python modo_humano.py    # recomendado
   # ou
   python bot.py
   ```

3. Nos 4 segundos iniciais, clique na janela do emulador.
4. **Parada de emergência:** jogue o mouse para o canto superior esquerdo da tela.

Para conferir o enquadramento das regiões antes de rodar:

```
python calibrate.py
```

Veja o [TUTORIAL.md](TUTORIAL.md) para o passo a passo detalhado.

## Aviso

Automação geralmente viola os Termos de Serviço do jogo. Use por sua conta e
risco. Projeto educacional sobre visão computacional e automação de UI.
