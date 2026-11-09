import sys
import pygame
import requests

# Server 網址
# API_BASE_URL = "http://127.0.0.1:8000"

# Render 部署時改成：
API_BASE_URL = "https://wordle-client-fastapi.onrender.com"

# 顏色定義
COLOR_BG = (18, 18, 19)
COLOR_TEXT = (255, 255, 255)
COLOR_EMPTY = (58, 58, 60)
COLOR_CORRECT = (83, 141, 78)
COLOR_PRESENT = (181, 159, 59)
COLOR_ABSENT = (58, 58, 60)

pygame.init()

WIDTH, HEIGHT = 500, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Wordle + FastAPI Client")

font = pygame.font.SysFont("Arial", 36, bold=True)
small_font = pygame.font.SysFont("Arial", 18)


class WordleGame:

    def __init__(self):

        self.game_id = None
        self.hard_mode = False

        self.stats = {
            "total_games": 0,
            "wins": 0,
            "win_rate": 0
        }

        self.grid = [["" for _ in range(5)] for _ in range(6)]

        self.colors = [
            [COLOR_EMPTY for _ in range(5)]
            for _ in range(6)
        ]

        self.row = 0
        self.col = 0
        self.game_over = False

        self.message = "Enter: Submit | R: Restart"

        self.start_new_game()

    # 建立新遊戲
    def start_new_game(self):

        try:

            res = requests.post(
                f"{API_BASE_URL}/api/new-game",
                json={"hard_mode": self.hard_mode},
                timeout=60
            )

            if res.status_code == 200:

                self.game_id = res.json()["game_id"]

                self.grid = [
                    ["" for _ in range(5)]
                    for _ in range(6)
                ]

                self.colors = [
                    [COLOR_EMPTY for _ in range(5)]
                    for _ in range(6)
                ]

                self.row = 0
                self.col = 0
                self.game_over = False

                self.message = "New game started!"

                self.update_stats()

            else:

                self.message = "Server error!"

        except requests.exceptions.RequestException:

            self.message = "Cannot connect to server!"

    # 更新統計資料
    def update_stats(self):

        try:

            res = requests.get(
                f"{API_BASE_URL}/api/stats",
                timeout=10
            )

            if res.status_code == 200:
                self.stats = res.json()

        except requests.exceptions.RequestException:

            pass

    # 提交猜測
    def submit_guess(self):

        if self.game_over:
            return

        if self.col != 5:

            self.message = "Not enough letters!"
            return

        guess_word = "".join(self.grid[self.row])

        try:

            payload = {
                "game_id": self.game_id,
                "guess": guess_word
            }

            res = requests.post(
                f"{API_BASE_URL}/api/guess",
                json=payload,
                timeout=60
            )

            # 猜測成功
            if res.status_code == 200:

                data = res.json()
                feedback = data["feedback"]

                # 更新字母顏色
                for i in range(5):

                    if feedback[i] == "correct":

                        self.colors[self.row][i] = COLOR_CORRECT

                    elif feedback[i] == "present":

                        self.colors[self.row][i] = COLOR_PRESENT

                    else:

                        self.colors[self.row][i] = COLOR_ABSENT

                # 猜對答案
                if data["is_correct"]:

                    self.message = "You won! Press R to restart."
                    self.game_over = True
                    self.update_stats()

                else:

                    attempts_left = data["attempts_left"]

                    # 六次猜測結束
                    if attempts_left == 0:

                        target_word = data["target_word"]

                        self.message = (
                            f"Game Over! Answer: {target_word}"
                        )

                        self.game_over = True
                        self.update_stats()

                    else:

                        # 移動到下一行
                        self.row += 1
                        self.col = 0

                        self.message = (
                            f"Keep guessing! "
                            f"({attempts_left} tries left)"
                        )

            else:

                # 顯示 Server 回傳的錯誤
                detail = res.json().get(
                    "detail",
                    "Error processing guess"
                )

                self.message = detail

        except requests.exceptions.RequestException:

            self.message = "Network error during guess!"

    # 鍵盤操作
    def handle_keydown(self, event):

        # Shift + H：切換 Hard Mode
        if (
            event.key == pygame.K_h
            and event.mod & pygame.KMOD_SHIFT
            and not self.game_over
        ):

            self.hard_mode = not self.hard_mode
            self.start_new_game()
            return

        # R：只有遊戲結束後才能重新開始
        if event.key == pygame.K_r and self.game_over:

            self.start_new_game()
            return

        if self.game_over:
            return

        # Backspace：刪除字母
        if event.key == pygame.K_BACKSPACE:

            if self.col > 0:

                self.col -= 1
                self.grid[self.row][self.col] = ""

        # Enter：提交答案
        elif event.key == pygame.K_RETURN:

            self.submit_guess()

        # 輸入英文字母
        elif event.unicode.isalpha() and len(event.unicode) == 1:

            if self.col < 5:

                self.grid[self.row][self.col] = event.unicode.upper()
                self.col += 1

    # 繪製畫面
    def draw(self, surface):

        surface.fill(COLOR_BG)

        # 顯示遊戲模式
        mode_text = (
            "Mode: HARD" if self.hard_mode
            else "Mode: Normal"
        )

        mode_surface = small_font.render(
            mode_text,
            True,
            COLOR_TEXT
        )

        surface.blit(
            mode_surface,
            (WIDTH - mode_surface.get_width() - 15, 15)
        )

        # 操作提示
        help_text = small_font.render(
            "Shift+H: Mode | R: Restart after game",
            True,
            COLOR_TEXT
        )

        surface.blit(help_text, (20, 55))

        # 繪製 6x5 網格
        margin_x = 20
        margin_y = 110
        box_size = 45
        gap = 7

        for r in range(6):

            for c in range(5):

                x = margin_x + c * (box_size + gap)
                y = margin_y + r * (box_size + gap)

                rect = pygame.Rect(
                    x, y, box_size, box_size
                )

                pygame.draw.rect(
                    surface,
                    self.colors[r][c],
                    rect,
                    border_radius=4
                )

                if self.colors[r][c] == COLOR_EMPTY:

                    pygame.draw.rect(
                        surface,
                        (80, 80, 80),
                        rect,
                        width=2,
                        border_radius=4
                    )

                char = self.grid[r][c]

                if char:

                    text_surface = font.render(
                        char,
                        True,
                        COLOR_TEXT
                    )

                    text_rect = text_surface.get_rect(
                        center=rect.center
                    )

                    surface.blit(text_surface, text_rect)

        # 底部提示訊息
        msg_surface = small_font.render(
            self.message[:55],
            True,
            COLOR_TEXT
        )

        msg_rect = msg_surface.get_rect(
            center=(WIDTH // 2, HEIGHT - 40)
        )

        surface.blit(msg_surface, msg_rect)

        # 統計面板
        panel_x = 305
        panel_y = 180

        title = small_font.render(
            "STATISTICS",
            True,
            COLOR_TEXT
        )

        surface.blit(title, (panel_x, panel_y))

        total_text = small_font.render(
            f"Total: {self.stats['total_games']}",
            True,
            COLOR_TEXT
        )

        surface.blit(total_text, (panel_x, panel_y + 45))

        wins_text = small_font.render(
            f"Wins: {self.stats['wins']}",
            True,
            COLOR_TEXT
        )

        surface.blit(wins_text, (panel_x, panel_y + 85))

        rate_text = small_font.render(
            f"Win Rate: {self.stats['win_rate']}%",
            True,
            COLOR_TEXT
        )

        surface.blit(rate_text, (panel_x, panel_y + 125))


# 主程式
def main():

    clock = pygame.time.Clock()
    game = WordleGame()

    while True:

        for event in pygame.event.get():

            if event.type == pygame.QUIT:

                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN:

                game.handle_keydown(event)

        game.draw(screen)

        pygame.display.flip()

        clock.tick(30)


if __name__ == "__main__":

    main()
