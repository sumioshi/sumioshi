"""Jogo da velha do perfil: visitantes jogam abrindo issues; o bot responde via Action."""
import json
import os
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = Path(__file__).resolve().parent / "state.json"
README = ROOT / "README.md"
REPO = "sumioshi/sumioshi"

P, B, E = "P", "B", ""  # jogador (匠), bot (日), vazio
MARK = {P: "匠", B: "日"}
START = "<!--TTT:START-->"
END = "<!--TTT:END-->"


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return new_game({"score": {"voce": 0, "bot": 0, "empate": 0}})


def new_game(state):
    state["board"] = [[E] * 3 for _ in range(3)]
    state["last"] = "Tabuleiro novo — pode começar. Você é 匠."
    state["over"] = False
    return state


def lines(b):
    for i in range(3):
        yield [b[i][0], b[i][1], b[i][2]]
        yield [b[0][i], b[1][i], b[2][i]]
    yield [b[0][0], b[1][1], b[2][2]]
    yield [b[0][2], b[1][1], b[2][0]]


def winner(b):
    for line in lines(b):
        if line[0] != E and line[0] == line[1] == line[2]:
            return line[0]
    if all(c != E for row in b for c in row):
        return "draw"
    return None


def minimax(b, turn):
    w = winner(b)
    if w == B:
        return 1, None
    if w == P:
        return -1, None
    if w == "draw":
        return 0, None
    best_score, best_move = None, None
    for r in range(3):
        for c in range(3):
            if b[r][c] == E:
                b[r][c] = turn
                score, _ = minimax(b, P if turn == B else B)
                b[r][c] = E
                better = (
                    best_score is None
                    or (turn == B and score > best_score)
                    or (turn == P and score < best_score)
                )
                if better:
                    best_score, best_move = score, (r, c)
    return best_score, best_move


def bot_move(b):
    empties = [(r, c) for r in range(3) for c in range(3) if b[r][c] == E]
    if not empties:
        return None
    # 25% de chance de jogada aleatória: dá pra vencer o bot
    if random.random() < 0.25:
        return random.choice(empties)
    _, move = minimax(b, B)
    return move or random.choice(empties)


def apply_issue(state, title, user):
    user = f"@{user}" if user else "alguém"
    if title.strip() == "ttt|new":
        return new_game(state)
    m = re.fullmatch(r"ttt\|([0-2])([0-2])", title.strip())
    if not m:
        return state
    if state.get("over"):
        state["last"] = f"{user}: o jogo acabou — clica em Recomeçar."
        return state
    r, c = int(m.group(1)), int(m.group(2))
    board = state["board"]
    if board[r][c] != E:
        state["last"] = f"{user} tentou uma casa ocupada. Jogada ignorada."
        return state
    board[r][c] = P
    w = winner(board)
    if w is None:
        move = bot_move(board)
        if move:
            board[move[0]][move[1]] = B
        w = winner(board)
    if w == P:
        state["score"]["voce"] += 1
        state["over"] = True
        state["last"] = f"🏆 {user} VENCEU o Shokunin-bot! Respeito."
    elif w == B:
        state["score"]["bot"] += 1
        state["over"] = True
        state["last"] = f"⛩️ O Shokunin-bot venceu {user}. 精進 (keep training)."
    elif w == "draw":
        state["score"]["empate"] += 1
        state["over"] = True
        state["last"] = f"🤝 Empate entre {user} e o bot."
    else:
        state["last"] = f"{user} jogou ({r + 1}, {c + 1}). Sua vez de novo!"
    return state


def cell(state, r, c):
    v = state["board"][r][c]
    if v in MARK:
        return f"**{MARK[v]}**"
    if state.get("over"):
        return "·"
    body = "S%C3%B3+clicar+em+%22Create%22.+A+jogada+entra+sozinha+em+~30s+%E2%80%94+depois+volta+ao+perfil+e+d%C3%A1+refresh."
    return f"[·](https://github.com/{REPO}/issues/new?title=ttt%7C{r}{c}&body={body})"


def render(state):
    s = state["score"]
    body_new = "Bora+de+novo%21+S%C3%B3+clicar+em+%22Create%22."
    rows = [
        "| ⛩️ | A | B | C |",
        "|---|---|---|---|",
    ]
    for r in range(3):
        rows.append(
            f"| **{r + 1}** | " + " | ".join(cell(state, r, c) for c in range(3)) + " |"
        )
    board = "\n".join(rows)
    return f"""{START}
## 🎮 対戦 · Desafie o Shokunin-bot

Jogo da velha **jogável aqui no README**: você é **匠**, o bot é **日**. Clica numa casa vazia (·),
confirma a issue que abrir e em ~30 segundos o GitHub Actions processa sua jogada e a resposta do bot.

<div align="center">

{board}

**{state["last"]}**

🏆 Você (visitantes): **{s["voce"]}** · ⛩️ Shokunin-bot: **{s["bot"]}** · 🤝 Empates: **{s["empate"]}**

[🔁 Recomeçar partida](https://github.com/{REPO}/issues/new?title=ttt%7Cnew&body={body_new})

</div>
{END}"""


def main():
    state = load_state()
    title = os.environ.get("ISSUE_TITLE", "")
    user = os.environ.get("ISSUE_USER", "")
    if title:
        state = apply_issue(state, title, user)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    text = README.read_text()
    if START in text and END in text:
        pre = text.split(START)[0]
        post = text.split(END)[1]
        README.write_text(pre + render(state) + post)


if __name__ == "__main__":
    main()
