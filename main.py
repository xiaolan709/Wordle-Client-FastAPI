
import os
import random
import uuid
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Wordle API Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

WORD_BANK = [
    "APPLE", "TRAIN", "HOUSE", "PLANT", "SMART",
    "WORLD", "LIGHT", "BRAIN", "CLOUD", "WATER"
]

games_db: Dict[str, dict] = {}

stats = {
    "total_games": 0,
    "wins": 0
}


class GuessRequest(BaseModel):
    game_id: str
    guess: str


class NewGameRequest(BaseModel):
    hard_mode: bool = False


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/api/new-game")
def start_new_game(req: NewGameRequest):
    game_id = str(uuid.uuid4())
    target_word = random.choice(WORD_BANK)

    games_db[game_id] = {
        "target": target_word,
        "status": "PLAYING",
        "attempts": 0,
        "hard_mode": req.hard_mode,
        "hints": {}
    }

    stats["total_games"] += 1

    return {
        "game_id": game_id,
        "message": "New game started!",
        "hard_mode": req.hard_mode
    }


@app.post("/api/guess")
def process_guess(req: GuessRequest):

    game_id = req.game_id
    guess = req.guess.upper()

    if game_id not in games_db:
        raise HTTPException(
            status_code=404,
            detail="Game session not found."
        )

    game = games_db[game_id]

    if game["status"] != "PLAYING":
        raise HTTPException(
            status_code=400,
            detail="Game is already over. Please restart."
        )

    if len(guess) != 5:
        raise HTTPException(
            status_code=400,
            detail="Word must be 5 letters."
        )

    if not guess.isascii() or not guess.isalpha():
        raise HTTPException(
            status_code=400,
            detail="Guess must contain only English letters."
        )

    if guess not in WORD_BANK:
        raise HTTPException(
            status_code=400,
            detail="Not in word list!"
        )

    # Hard Mode 防呆：必須保留之前的綠色字母
    if game["hard_mode"]:
        for position, letter in game["hints"].items():
            if guess[position] != letter:
                raise HTTPException(
                    status_code=400,
                    detail="Hard Mode: Must use revealed hint at green position."
                )

    target = game["target"]
    feedback = ["absent"] * 5
    target_letter_counts = {}

    game["attempts"] += 1
    attempts = game["attempts"]
    attempts_left = 6 - attempts

    # 計算答案中字母數量
    for char in target:
        target_letter_counts[char] = (
            target_letter_counts.get(char, 0) + 1
        )

    # 第一輪：標記綠色
    for i in range(5):
        if guess[i] == target[i]:
            feedback[i] = "correct"
            target_letter_counts[guess[i]] -= 1

            # 記錄綠色字母的位置
            game["hints"][i] = guess[i]

    # 第二輪：標記黃色
    for i in range(5):
        if feedback[i] != "correct":
            if target_letter_counts.get(guess[i], 0) > 0:
                feedback[i] = "present"
                target_letter_counts[guess[i]] -= 1

    is_correct = (guess == target)

    if is_correct:
        game["status"] = "WON"
        stats["wins"] += 1

    elif attempts >= 6:
        game["status"] = "LOST"

    return {
        "guess": guess,
        "feedback": feedback,
        "is_correct": is_correct,
        "attempts_left": attempts_left,
        "target_word": target if is_correct or attempts >= 6 else None
    }


@app.get("/api/stats")
def get_stats():

    total = stats["total_games"]
    wins = stats["wins"]

    win_rate = 0

    if total > 0:
        win_rate = round((wins / total) * 100, 2)

    return {
        "total_games": total,
        "wins": wins,
        "win_rate": win_rate
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
