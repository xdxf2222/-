import pygame
import sys
import random
import os

# 初始化Pygame
pygame.init()
pygame.mixer.init()

# 窗口固定尺寸
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
PANEL_HEIGHT = 80
FPS = 60

# 颜色定义
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)

# 难度配置（横向网格）
DIFFICULTY_CONFIG = {
    1: {"name": "初级", "rows": 6, "cols": 12, "type_range": (8, 18)},
    2: {"name": "容易", "rows": 7, "cols": 14, "type_range": (10, 22)},
    3: {"name": "中等", "rows": 8, "cols": 14, "type_range": (14, 28)},
    4: {"name": "高难", "rows": 10, "cols": 16, "type_range": (22, 36)}
}

font_small = None
font_medium = None
font_large = None


class LinkGame:
    def __init__(self):
        global font_small, font_medium, font_large
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("连连看游戏")

        font_small = pygame.font.SysFont("simhei", 20)
        font_medium = pygame.font.SysFont("simhei", 28)
        font_large = pygame.font.SysFont("simhei", 36)

        # 加载背景图片
        self.background = self.load_background()

        # 加载图片
        self.raw_images = self.load_raw_images()
        self.scaled_images = {}

        # 加载音效
        self.sounds = self.load_sounds()

        # 游戏状态
        self.state = "MENU"
        self.difficulty = 1
        self.rows = 6
        self.cols = 12
        self.grid = []
        self.selected = None
        self.score = 0
        self.pairs_eliminated = 0
        self.total_pairs = 0
        self.start_time = 0
        self.remaining_time = 180
        self.hint_timer = 0
        self.hint_positions = []

        # 消息提示
        self.message = ""
        self.message_timer = 0

        # 动态格子尺寸和偏移
        self.grid_size = 0
        self.grid_offset_x = 0
        self.grid_offset_y = 0

        # 动画相关
        self.animation_path_points = []
        self.animation_timer = 0
        self.pending_eliminate = None

        # 自动消除相关
        self.auto_eliminate_active = False
        self.auto_eliminate_shuffle_count = 0
        self.auto_eliminate_max_shuffle = 3

        # 生成初始网格（用于菜单）
        self.generate_layout()
        self.update_grid_size_and_offset()

    def load_background(self):
        """加载背景图片，随机选择一张有效图片，默认使用天空.jpg"""
        bg_dir = os.path.join(os.path.dirname(__file__), "bg")
        if not os.path.exists(bg_dir):
            bg_dir = "bg"

        # 候选背景文件列表
        candidates = ["卡通.jpg", "天使.jpg", "天空.jpg", "海洋.jpg", "苹果.gif"]
        # 随机打乱顺序
        random.shuffle(candidates)
        # 尝试加载，优先用随机顺序，但确保天空.jpg作为最后保底
        for name in candidates:
            path = os.path.join(bg_dir, name)
            try:
                img = pygame.image.load(path).convert()
                # 缩放至窗口大小
                img = pygame.transform.scale(img, (WINDOW_WIDTH, WINDOW_HEIGHT))
                print(f"加载背景图片: {name}")
                return img
            except Exception as e:
                print(f"无法加载背景 {path}: {e}")

        # 如果所有图片都加载失败，尝试强制加载天空.jpg（若存在）
        default_path = os.path.join(bg_dir, "天空.jpg")
        try:
            img = pygame.image.load(default_path).convert()
            img = pygame.transform.scale(img, (WINDOW_WIDTH, WINDOW_HEIGHT))
            return img
        except:
            pass

        print("无法加载任何背景图片，使用纯色背景")
        return None

    def load_sounds(self):
        """加载音效文件"""
        sounds = {}
        wav_dir = os.path.join(os.path.dirname(__file__), "wav")
        if not os.path.exists(wav_dir):
            wav_dir = "wav"

        sound_files = [
            "选中.wav", "连对.wav", "连错.wav", "打乱.wav",
            "提示.wav", "空击.wav", "取消.wav", "叮.wav", "撤销.wav"
        ]
        for name in sound_files:
            path = os.path.join(wav_dir, name)
            try:
                sounds[name] = pygame.mixer.Sound(path)
                sounds[name].set_volume(0.7)
            except Exception as e:
                print(f"无法加载音效 {path}: {e}")
                sounds[name] = None
        return sounds

    def play_sound(self, name):
        if name in self.sounds and self.sounds[name] is not None:
            self.sounds[name].play()

    def load_raw_images(self):
        images = {}
        img_dir = os.path.join(os.path.dirname(__file__), "cat")
        if not os.path.exists(img_dir):
            img_dir = "cat"
        for i in range(36):
            filename = f"block_{i}.jpg"
            path = os.path.join(img_dir, filename)
            try:
                img = pygame.image.load(path).convert_alpha()
                images[i] = img
            except Exception:
                surf = pygame.Surface((100, 100))
                surf.fill((random.randint(100, 255), random.randint(100, 255), random.randint(100, 255)))
                images[i] = surf
        return images

    def update_grid_size_and_offset(self):
        available_height = WINDOW_HEIGHT - PANEL_HEIGHT
        self.grid_size = min(WINDOW_WIDTH // self.cols, available_height // self.rows)
        self.grid_offset_x = (WINDOW_WIDTH - self.cols * self.grid_size) // 2
        self.grid_offset_y = PANEL_HEIGHT + (available_height - self.rows * self.grid_size) // 2
        self.scaled_images = {}
        for img_id, img in self.raw_images.items():
            self.scaled_images[img_id] = pygame.transform.scale(img, (self.grid_size, self.grid_size))

    def generate_layout(self):
        rows, cols = self.rows, self.cols
        total_cells = rows * cols
        type_min, type_max = DIFFICULTY_CONFIG[self.difficulty]["type_range"]
        min_by_capacity = (total_cells + 5) // 6
        max_by_capacity = total_cells // 2
        type_min = max(type_min, min_by_capacity)
        type_max = min(type_max, max_by_capacity)
        if type_min > type_max:
            type_min = type_max = max(1, type_min)

        num_types = random.randint(type_min, type_max)
        available_ids = list(range(36))
        random.shuffle(available_ids)
        used_ids = available_ids[:num_types]

        counts = [2] * num_types
        current_sum = 2 * num_types
        diff = total_cells - current_sum
        indices = list(range(num_types))
        while diff > 0:
            random.shuffle(indices)
            added = False
            for idx in indices:
                if counts[idx] < 6:
                    counts[idx] += 2
                    diff -= 2
                    added = True
                    if diff <= 0:
                        break
            if not added:
                return self.generate_layout()

        image_pool = []
        for i, img_id in enumerate(used_ids):
            image_pool.extend([img_id] * counts[i])
        random.shuffle(image_pool)

        grid = [[None for _ in range(cols)] for _ in range(rows)]
        idx = 0
        for r in range(rows):
            for c in range(cols):
                grid[r][c] = image_pool[idx]
                idx += 1
        self.grid = grid
        self.total_pairs = total_cells // 2

    def reset_game(self, difficulty):
        self.difficulty = difficulty
        self.rows = DIFFICULTY_CONFIG[difficulty]["rows"]
        self.cols = DIFFICULTY_CONFIG[difficulty]["cols"]
        self.generate_layout()
        self.update_grid_size_and_offset()

        self.selected = None
        self.score = 0
        self.pairs_eliminated = 0
        self.start_time = pygame.time.get_ticks()
        self.remaining_time = 180
        self.state = "PLAYING"
        self.hint_positions = []
        self.hint_timer = 0
        self.animation_path_points = []
        self.animation_timer = 0
        self.pending_eliminate = None
        self.message = ""
        self.message_timer = 0
        self.auto_eliminate_active = False
        self.auto_eliminate_shuffle_count = 0

    def shuffle_grid(self):
        images_list = []
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] is not None:
                    images_list.append(self.grid[r][c])
        random.shuffle(images_list)
        idx = 0
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] is not None:
                    self.grid[r][c] = images_list[idx]
                    idx += 1
        self.selected = None
        self.hint_positions = []
        self.hint_timer = 0
        self.play_sound("打乱.wav")

    def is_valid_pos(self, r, c):
        return 0 <= r < self.rows and 0 <= c < self.cols

    def is_empty(self, r, c):
        if r < 0 or r >= self.rows or c < 0 or c >= self.cols:
            return True
        return self.grid[r][c] is None

    def find_path(self, r1, c1, r2, c2):
        if not (self.is_valid_pos(r1, c1) and self.is_valid_pos(r2, c2)):
            return []
        if r1 == r2 and c1 == c2:
            return []
        if self.grid[r1][c1] is None or self.grid[r2][c2] is None:
            return []
        if self.grid[r1][c1] != self.grid[r2][c2]:
            return []

        def check_horizontal(r, ca, cb):
            step = 1 if cb > ca else -1
            for c in range(ca + step, cb, step):
                if not self.is_empty(r, c):
                    return False
            return True

        def check_vertical(c, ra, rb):
            step = 1 if rb > ra else -1
            for r in range(ra + step, rb, step):
                if not self.is_empty(r, c):
                    return False
            return True

        # 同行直接连接
        if r1 == r2 and check_horizontal(r1, c1, c2):
            points = [(r1, c1)]
            step = 1 if c2 > c1 else -1
            for c in range(c1 + step, c2, step):
                points.append((r1, c))
            points.append((r2, c2))
            return points

        # 同列直接连接
        if c1 == c2 and check_vertical(c1, r1, r2):
            points = [(r1, c1)]
            step = 1 if r2 > r1 else -1
            for r in range(r1 + step, r2, step):
                points.append((r, c1))
            points.append((r2, c2))
            return points

        # 一个拐点 (r1, c2)
        if self.is_empty(r1, c2) and check_horizontal(r1, c1, c2) and check_vertical(c2, r1, r2):
            points = [(r1, c1)]
            step = 1 if c2 > c1 else -1
            for c in range(c1 + step, c2, step):
                points.append((r1, c))
            points.append((r1, c2))
            step = 1 if r2 > r1 else -1
            for r in range(r1 + step, r2, step):
                points.append((r, c2))
            points.append((r2, c2))
            return points

        # 一个拐点 (r2, c1)
        if self.is_empty(r2, c1) and check_horizontal(r2, c1, c2) and check_vertical(c1, r1, r2):
            points = [(r1, c1)]
            step = 1 if r2 > r1 else -1
            for r in range(r1 + step, r2, step):
                points.append((r, c1))
            points.append((r2, c1))
            step = 1 if c2 > c1 else -1
            for c in range(c1 + step, c2, step):
                points.append((r2, c))
            points.append((r2, c2))
            return points

        # 两个拐点：扫描列
        for col in range(-1, self.cols + 1):
            if col == c1 or col == c2:
                continue
            if self.is_empty(r1, col) and self.is_empty(r2, col):
                if (check_horizontal(r1, c1, col) and
                    check_vertical(col, r1, r2) and
                    check_horizontal(r2, col, c2)):
                    points = [(r1, c1)]
                    step = 1 if col > c1 else -1
                    for c in range(c1 + step, col, step):
                        points.append((r1, c))
                    points.append((r1, col))
                    step = 1 if r2 > r1 else -1
                    for r in range(r1 + step, r2, step):
                        points.append((r, col))
                    points.append((r2, col))
                    step = 1 if c2 > col else -1
                    for c in range(col + step, c2, step):
                        points.append((r2, c))
                    points.append((r2, c2))
                    return points

        # 两个拐点：扫描行
        for row in range(-1, self.rows + 1):
            if row == r1 or row == r2:
                continue
            if self.is_empty(row, c1) and self.is_empty(row, c2):
                if (check_vertical(c1, r1, row) and
                    check_horizontal(row, c1, c2) and
                    check_vertical(c2, row, r2)):
                    points = [(r1, c1)]
                    step = 1 if row > r1 else -1
                    for r in range(r1 + step, row, step):
                        points.append((r, c1))
                    points.append((row, c1))
                    step = 1 if c2 > c1 else -1
                    for c in range(c1 + step, c2, step):
                        points.append((row, c))
                    points.append((row, c2))
                    step = 1 if r2 > row else -1
                    for r in range(row + step, r2, step):
                        points.append((r, c2))
                    points.append((r2, c2))
                    return points

        return []

    def can_connect(self, r1, c1, r2, c2):
        return len(self.find_path(r1, c1, r2, c2)) > 0

    def has_any_connectable(self):
        for r1 in range(self.rows):
            for c1 in range(self.cols):
                if self.grid[r1][c1] is not None:
                    for r2 in range(self.rows):
                        for c2 in range(self.cols):
                            if (r1 == r2 and c1 == c2):
                                continue
                            if self.grid[r2][c2] is not None and self.grid[r1][c1] == self.grid[r2][c2]:
                                if self.can_connect(r1, c1, r2, c2):
                                    return True
        return False

    def eliminate(self, r1, c1, r2, c2):
        path = self.find_path(r1, c1, r2, c2)
        if not path:
            self.play_sound("连错.wav")
            return False

        self.play_sound("连对.wav")

        pixel_points = []
        for r, c in path:
            x = self.grid_offset_x + c * self.grid_size + self.grid_size // 2
            y = self.grid_offset_y + r * self.grid_size + self.grid_size // 2
            pixel_points.append((x, y))

        self.animation_path_points = []
        for i in range(len(pixel_points) - 1):
            self.animation_path_points.append((pixel_points[i], pixel_points[i + 1]))
        self.animation_timer = 10
        self.pending_eliminate = (r1, c1, r2, c2)

        self.hint_positions = []
        self.hint_timer = 0
        return True

    def finish_eliminate(self, r1, c1, r2, c2):
        self.grid[r1][c1] = None
        self.grid[r2][c2] = None
        self.pairs_eliminated += 1
        time_bonus = max(0, int(self.remaining_time) * 10)
        self.score = self.pairs_eliminated * 100 + time_bonus
        self.selected = None
        self.animation_path_points = []
        self.animation_timer = 0
        self.pending_eliminate = None

        if not self.has_any_connectable():
            self.shuffle_grid()

    def find_hint(self):
        for r1 in range(self.rows):
            for c1 in range(self.cols):
                if self.grid[r1][c1] is not None:
                    for r2 in range(self.rows):
                        for c2 in range(self.cols):
                            if (r1 == r2 and c1 == c2):
                                continue
                            if self.grid[r2][c2] is not None and self.grid[r1][c1] == self.grid[r2][c2]:
                                if self.can_connect(r1, c1, r2, c2):
                                    return ((r1, c1), (r2, c2))
        return None

    def check_win(self):
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] is not None:
                    return False
        return True

    def update_timer(self):
        if self.state == "PLAYING":
            elapsed = (pygame.time.get_ticks() - self.start_time) / 1000
            self.remaining_time = max(0, 180 - elapsed)
            time_bonus = max(0, int(self.remaining_time) * 10)
            self.score = self.pairs_eliminated * 100 + time_bonus
            if self.remaining_time <= 0:
                self.state = "GAMEOVER"
                self.auto_eliminate_active = False
                self.play_sound("叮.wav")

    def draw_background(self):
        """绘制背景图片（如果存在）"""
        if self.background is not None:
            self.screen.blit(self.background, (0, 0))
        else:
            self.screen.fill(BLACK)

    def draw_grid(self):
        for r in range(self.rows):
            for c in range(self.cols):
                x = self.grid_offset_x + c * self.grid_size
                y = self.grid_offset_y + r * self.grid_size
                rect = pygame.Rect(x, y, self.grid_size, self.grid_size)
                pygame.draw.rect(self.screen, BLACK, rect, 1)

                img_id = self.grid[r][c]
                if img_id is not None and img_id in self.scaled_images:
                    self.screen.blit(self.scaled_images[img_id], (x, y))
                # 空格子不做填充，直接显示背景

                if self.selected == (r, c):
                    pygame.draw.rect(self.screen, RED, rect, 3)
                if (r, c) in self.hint_positions and self.hint_timer > 0:
                    pygame.draw.rect(self.screen, GREEN, rect, 3)

        if self.animation_timer > 0 and self.animation_path_points:
            for start, end in self.animation_path_points:
                pygame.draw.line(self.screen, BLUE, start, end, 4)

    def draw_panel(self):
        panel_rect = pygame.Rect(0, 0, WINDOW_WIDTH, PANEL_HEIGHT)
        # 面板半透明效果
        s = pygame.Surface((WINDOW_WIDTH, PANEL_HEIGHT), pygame.SRCALPHA)
        s.fill((128, 128, 128, 200))  # 半透明灰色
        self.screen.blit(s, (0, 0))
        pygame.draw.line(self.screen, BLACK, (0, PANEL_HEIGHT), (WINDOW_WIDTH, PANEL_HEIGHT), 2)

        score_text = font_medium.render(f"得分: {self.score}", True, WHITE)
        self.screen.blit(score_text, (10, 10))

        minutes = int(self.remaining_time) // 60
        seconds = int(self.remaining_time) % 60
        time_str = f"{minutes:02d}:{seconds:02d}"
        time_text = font_medium.render(f"时间: {time_str}", True, WHITE)
        self.screen.blit(time_text, (10, 45))

        diff_name = DIFFICULTY_CONFIG[self.difficulty]["name"] if self.difficulty in DIFFICULTY_CONFIG else "未知"
        if self.state == "PLAYING":
            status = "游戏中"
        elif self.state == "GAMEOVER":
            status = "游戏结束"
        else:
            status = "菜单"
        info_text = font_small.render(f"{diff_name} | {status}", True, WHITE)
        self.screen.blit(info_text, (WINDOW_WIDTH - 150, 15))

        hint_text = font_small.render("H:提示  R:洗牌  A:自动消除  1-4:难度", True, YELLOW)
        self.screen.blit(hint_text, (WINDOW_WIDTH // 2 - 180, 55))

        if self.message_timer > 0:
            msg_surf = font_small.render(self.message, True, YELLOW)
            msg_rect = msg_surf.get_rect(center=(WINDOW_WIDTH // 2, PANEL_HEIGHT - 20))
            self.screen.blit(msg_surf, msg_rect)
            self.message_timer -= 1

        if self.state == "GAMEOVER":
            over_text = font_large.render("游戏结束!", True, RED)
            over_rect = over_text.get_rect(center=(WINDOW_WIDTH // 2, PANEL_HEIGHT // 2))
            self.screen.blit(over_text, over_rect)

    def draw_menu(self):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        title = font_large.render("连连看", True, WHITE)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 100))
        self.screen.blit(title, title_rect)

        y = 180
        for key in [1, 2, 3, 4]:
            name = DIFFICULTY_CONFIG[key]["name"]
            text = font_medium.render(f"按 {key}: {name}", True, YELLOW)
            rect = text.get_rect(center=(WINDOW_WIDTH // 2, y))
            self.screen.blit(text, rect)
            y += 50

        prompt = font_small.render("请按数字键 1-4 开始游戏", True, WHITE)
        prompt_rect = prompt.get_rect(center=(WINDOW_WIDTH // 2, y + 50))
        self.screen.blit(prompt, prompt_rect)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if self.state == "MENU":
                    if event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4]:
                        diff = event.key - pygame.K_0
                        self.reset_game(diff)
                        self.state = "PLAYING"
                elif self.state == "PLAYING":
                    if event.key == pygame.K_r:
                        self.shuffle_grid()
                        self.hint_positions = []
                        self.hint_timer = 0
                        self.message = "已洗牌"
                        self.message_timer = 60
                    elif event.key == pygame.K_h:
                        self.play_sound("提示.wav")
                        hint = self.find_hint()
                        if hint:
                            self.hint_positions = hint
                            self.hint_timer = 60
                            self.message = ""
                            self.message_timer = 0
                        else:
                            self.shuffle_grid()
                            hint2 = self.find_hint()
                            if hint2:
                                self.hint_positions = hint2
                                self.hint_timer = 60
                                self.message = "已洗牌，找到可消除对"
                                self.message_timer = 60
                            else:
                                self.hint_positions = []
                                self.hint_timer = 0
                                self.message = "无解，请手动洗牌"
                                self.message_timer = 60
                    elif event.key == pygame.K_a:
                        if not self.auto_eliminate_active:
                            self.auto_eliminate_active = True
                            self.auto_eliminate_shuffle_count = 0
                            self.message = "自动消除开始"
                            self.message_timer = 60
                    elif event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4]:
                        diff = event.key - pygame.K_0
                        self.reset_game(diff)
                        self.state = "PLAYING"
                elif self.state == "GAMEOVER":
                    if event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4]:
                        diff = event.key - pygame.K_0
                        self.reset_game(diff)
                        self.state = "PLAYING"
            elif event.type == pygame.MOUSEBUTTONDOWN and self.state == "PLAYING" and self.animation_timer == 0:
                if self.auto_eliminate_active:
                    continue
                mx, my = pygame.mouse.get_pos()
                if (self.grid_offset_x <= mx < self.grid_offset_x + self.cols * self.grid_size and
                    self.grid_offset_y <= my < self.grid_offset_y + self.rows * self.grid_size):
                    col = (mx - self.grid_offset_x) // self.grid_size
                    row = (my - self.grid_offset_y) // self.grid_size
                    if 0 <= row < self.rows and 0 <= col < self.cols:
                        if self.grid[row][col] is not None:
                            if self.selected is None:
                                self.selected = (row, col)
                                self.play_sound("选中.wav")
                            else:
                                r1, c1 = self.selected
                                if self.eliminate(r1, c1, row, col):
                                    self.selected = None
                                else:
                                    self.selected = None
                                    self.play_sound("取消.wav")
                        else:
                            self.play_sound("空击.wav")
                            self.selected = None
                    else:
                        if self.selected is not None:
                            self.selected = None
                            self.play_sound("取消.wav")
                else:
                    if self.selected is not None:
                        self.selected = None
                        self.play_sound("取消.wav")
        return True

    def run(self):
        clock = pygame.time.Clock()
        running = True
        while running:
            running = self.handle_events()
            if not running:
                break

            if self.state == "PLAYING":
                self.update_timer()
                if self.remaining_time <= 0:
                    self.state = "GAMEOVER"
                    self.auto_eliminate_active = False
                if self.hint_timer > 0:
                    self.hint_timer -= 1
                else:
                    self.hint_positions = []

                # 自动消除逻辑
                if self.auto_eliminate_active and self.animation_timer == 0:
                    if self.check_win():
                        self.auto_eliminate_active = False
                        self.message = "自动消除完成！"
                        self.message_timer = 60
                        self.play_sound("叮.wav")
                    else:
                        hint = self.find_hint()
                        if hint:
                            r1, c1 = hint[0]
                            r2, c2 = hint[1]
                            self.eliminate(r1, c1, r2, c2)
                            self.hint_positions = []
                            self.hint_timer = 0
                        else:
                            if self.auto_eliminate_shuffle_count < self.auto_eliminate_max_shuffle:
                                self.shuffle_grid()
                                self.auto_eliminate_shuffle_count += 1
                                self.message = f"自动洗牌 {self.auto_eliminate_shuffle_count}/{self.auto_eliminate_max_shuffle}"
                                self.message_timer = 60
                            else:
                                self.auto_eliminate_active = False
                                self.message = "自动消除停止：多次洗牌后无解"
                                self.message_timer = 60
                                self.play_sound("取消.wav")

                if self.animation_timer > 0:
                    self.animation_timer -= 1
                    if self.animation_timer == 0 and self.pending_eliminate is not None:
                        r1, c1, r2, c2 = self.pending_eliminate
                        self.finish_eliminate(r1, c1, r2, c2)
                        if self.check_win():
                            self.state = "GAMEOVER"
                            self.auto_eliminate_active = False
                            self.play_sound("叮.wav")

            # 绘制
            self.draw_background()      # 先绘制背景
            self.draw_grid()            # 再绘制网格（图片、选中框等）
            self.draw_panel()           # 最后绘制面板（半透明覆盖）
            if self.state == "MENU":
                self.draw_menu()
            elif self.state == "GAMEOVER":
                if not self.check_win():
                    fail_text = font_medium.render("时间到！按1-4重开", True, RED)
                else:
                    fail_text = font_medium.render("恭喜通关！按1-4继续", True, GREEN)
                fail_rect = fail_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
                self.screen.blit(fail_text, fail_rect)

            pygame.display.flip()
            clock.tick(FPS)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = LinkGame()
    game.run()