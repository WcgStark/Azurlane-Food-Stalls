# Tutorial — Bot de Memória da Barraca de Comida (Azur Lane)

Guia completo, do zero, para entender, calibrar e rodar o bot.

---

## 1. O que é esse bot e como ele pensa

O minigame da barraca de comida funciona assim:

1. **Fase "thinking"** — aparece um **balão branco** com **3 comidas em ordem**
   (ex: tofu → bubble tea → taiyaki). Você precisa *decorar* essas 3 comidas e a ordem.
2. **Fase "selection"** — o balão some e aparece uma **grade 3×3 com 9 comidas**.
   Você precisa clicar nas 3 comidas certas, na ordem que apareceu no balão.
3. **Fase "result"** — mostra o resultado e um botão de **continuar** (acertou) ou
   você sai com **quit**.

O bot automatiza isso. Ele tira "fotos" da tela do emulador várias vezes por segundo
(isso se chama *screenshot/captura de tela*), descobre em que fase o jogo está pela
imagem, e:

- Na **thinking**, ele recorta o balão e guarda as 3 comidas na memória.
- Na **selection**, ele compara cada comida memorizada com as 9 da grade, descobre
  quais batem, e clica nelas com o mouse (de verdade — ele move e clica o seu cursor).
- Na **result**, ele clica em continuar e repete, até juntar o bônus configurado.

> **Importante:** o bot **controla o seu mouse de verdade**. Enquanto ele roda, não
> mexa no mouse nem no teclado. Para **parar de emergência**, jogue o mouse rápido
> para o **canto superior esquerdo da tela** — isso aborta o bot na hora.

---

## 2. O que você precisa ter antes

- **Um emulador Android** aberto rodando o Azur Lane (BlueStacks, LDPlayer, NoxPlayer,
  MuMu ou "Android Device"). O bot procura a janela pelo nome.
- O jogo **aberto na tela da barraca de comida** (no lobby, onde aparece o botão
  START GAME).
- **Python instalado** (já está, porque existe a pasta `.venv` no projeto).

Não precisa instalar mais nada — as bibliotecas já estão dentro do `.venv`.

---

## 3. Como abrir o PowerShell na pasta certa

Tudo é rodado por comandos numa janela preta chamada **PowerShell**. Para abrir já
na pasta do projeto:

1. Abra o **Explorador de Arquivos** e navegue até `C:\Users\willi\Downloads\Arcade`.
2. Clique na **barra de endereço** (onde mostra o caminho da pasta), apague o texto,
   digite `powershell` e aperte **Enter**.
3. Vai abrir uma janela já dentro da pasta `Arcade`. É aqui que você digita os comandos.

> Dica: para colar um comando no PowerShell, dê **clique com o botão direito** do mouse.

Para confirmar que está na pasta certa, digite e aperte Enter:

```powershell
ls
```

Você deve ver `bot.py`, `calibrate.py`, a pasta `templates`, etc.

---

## 4. Passo 1 — Calibrar (conferir o enquadramento)

O bot olha para **duas regiões fixas** da janela: onde fica o balão e onde fica a
grade. Se essas regiões estiverem tortas, ele erra tudo. O `calibrate.py` serve só
para você **ver** se as regiões estão certas — ele não joga, só desenha e tira uma foto.

**Como fazer:**

1. Deixe o jogo na **fase de seleção** (a grade 3×3 com as 9 comidas aparecendo).
2. No PowerShell, rode:

   ```powershell
   .venv\Scripts\python.exe calibrate.py
   ```

3. Vai abrir uma janelinha e também salvar um arquivo `calibrate_output.png` na pasta.
   Abra esse arquivo (dê dois cliques nele no Explorador) e confira:
   - O **retângulo verde** (BUBBLE) deve cercar **só o balão**.
   - O **retângulo laranja** (GRID) deve cercar **só a grade 3×3**, com as linhas
     dividindo certinho as 9 células.
4. No PowerShell ele também imprime algo como:

   ```
   balão_branco=0.020 (>=0.16 thinking)  grade_vívida=0.180 (>=0.06 selection)
   Fase detectada: SELECTION
   ```

   Como você está na fase de seleção, ele deve dizer `SELECTION`. 

**Se os retângulos estiverem tortos**, não mexa em nada ainda — me manda o
`calibrate_output.png` que eu ajusto os números das regiões para você.

---

## 5. Passo 2 — Rodar o bot de verdade

1. Deixe o jogo **no lobby**, mostrando o botão **START GAME**.
2. No PowerShell, rode:

   ```powershell
   .venv\Scripts\python.exe bot.py
   ```

3. Ele mostra uma contagem e diz **"Iniciando em 4s — alterne para o jogo…"**.
   Nesses 4 segundos, **clique na janela do emulador** para deixá-la na frente.
4. A partir daí o bot assume o controle. **Não toque no mouse.**

Enquanto roda, o terminal vai mostrando ao vivo em que fase ele acha que está:

```
  [fase] balão_branco=0.210/0.16  grade_vívida=0.030/0.06
── THINKING    bônus=0s ──
  Balão capturado: 3 slots (74×97px cada)
── SELECTION   bônus=0s ──
  Emparelhando slots do balão com células da grade…
    Slot 0 → célula (1,2)  score=0.78
    Slot 1 → célula (0,0)  score=0.71
    Slot 2 → célula (2,1)  score=0.69
  ✓ Clicou os 3! Bônus total: 5s
```

**Como ler isso:**
- `balão_branco` alto → ele detectou o balão → fase **thinking** (decorando).
- `grade_vívida` alto e balão baixo → fase **selection** (hora de clicar).
- `Slot X → célula (linha,coluna) score=...` → para cada comida do balão, qual célula
  da grade ele escolheu. **Score perto de 1.0 = muita confiança; perto de 0 = chute.**

O bot para sozinho quando chega no limite de bônus (configurado em `BONUS_LIMIT`, hoje 25s).

**Para parar no meio:** jogue o mouse para o **canto superior esquerdo** da tela.

---

## 6. Arquivos de debug (para me mandar se der errado)

Deixei o modo de debug ligado (`DEBUG_SAVE = True` no `bot.py`). Toda vez que ele joga,
ele salva imagens na pasta `Arcade` que ajudam a diagnosticar:

| Arquivo                      | O que mostra                                        |
|------------------------------|-----------------------------------------------------|
| `debug_bubble.png`           | o balão recortado (as 3 comidas memorizadas)        |
| `debug_slot_0/1/2.png`       | cada uma das 3 comidas separadas                    |
| `debug_grid_overlay.png`     | a grade com as linhas e os pontos de clique         |
| `debug_selection_frame.png`  | a tela inteira no momento da seleção                |
| `debug_thinking_frame.png`   | a tela inteira no momento da memorização            |

**Se algo der errado, me mande:**
1. O **texto do terminal** (pode copiar e colar).
2. Os arquivos `debug_bubble.png`, `debug_grid_overlay.png` e `debug_selection_frame.png`.

Com isso eu consigo ver exatamente o que ele errou e ajustar.

---

## 7. Problemas comuns

- **"janela do emulador não encontrada"** → o emulador não está aberto, ou tem um nome
  diferente. Me diga qual emulador você usa que eu adiciono o nome na lista.
- **Ele clica nos lugares errados** → provavelmente as regiões (Passo 4) ou os scores
  estão baixos. Me mande os arquivos de debug.
- **Ele não sai do "result" / fica travado** → me mande o texto do terminal mostrando
  em que fase ele empacou.
- **O mouse foge / o bot para sozinho** → você encostou o mouse no canto superior
  esquerdo (parada de emergência). É só rodar de novo.

---

## 8. Resumo rápido (cola)

```powershell
# 1. abrir PowerShell na pasta Arcade (digitar "powershell" na barra de endereço)

# 2. conferir as regiões (jogo na fase de seleção)
.venv\Scripts\python.exe calibrate.py

# 3. rodar o bot (jogo no lobby, com START GAME visível)
.venv\Scripts\python.exe bot.py
# -> nos 4s, clique na janela do jogo
# -> para parar: mouse no canto superior esquerdo
```
