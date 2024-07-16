import pyxel

TITLE = "ACCELERATE"
PYXRES = "game.pyxres"
TRANSPARENT_COLOR_1 = 0
TRANSPARENT_COLOR_2 = 8
COLOR_SET_1 = (11, 14, 3, 2)
COLOR_SET_2 = (7, 11, 3, 5)
COLOR_SET_3 = (15, 9, 4, 13)
COLOR_SET_4 = (7, 10, 9, 0)

SCENE_GAME = 0
SCENE_DEAD = 1
SCENE_GOAL = 2
DEAD_TIME = 60
GOAL_TIME = 60

TILE = 8
W_T = 16
H_T = 16
W = W_T * TILE
H = H_T * TILE
CAMERA_X = (W - TILE) // 2
INIT_X_T = 7
INIT_Y_T = 8
INIT_STAGE = 0

ACCX =  4 / 256
ACCL = 48 / 256
GRAV =  2 / 256
DRAG =  8 / 256

def is_left() -> bool:
    return pyxel.btn(pyxel.KEY_LEFT) \
        or pyxel.btn(pyxel.KEY_A) \
        or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_LEFT)

def is_right() -> bool:
    return pyxel.btn(pyxel.KEY_RIGHT) \
        or pyxel.btn(pyxel.KEY_D) \
        or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_RIGHT)

def draw_text(x_t: int, y_t: int, s: str) -> None:
    pyxel.text(x_t * TILE + 1, y_t * TILE + 1, s, 5)
    pyxel.text(x_t * TILE + 2, y_t * TILE + 1, s, 7)

def get_tile(x_t: int, y_t: int) -> tuple[int, int]:
    if x_t < 0 or 256 <= x_t: return (0, 0)
    return pyxel.tilemaps[(y_t // 256) % 4].pget(x_t, y_t % 256)

def is_hit(dx: int, dy: int) -> bool:
    return dx * dx + dy * dy < 48

class Enemy:
    def __init__(self, x: int, y: int, vx: float, vy: float) -> None:
        self.x = x
        self.y = y
        self.dx = 0.0
        self.dy = 0.0
        self.vx = vx
        self.vy = vy
        self.is_dead = False

    def update(self, x0: int, y0: int) -> None:
        self.dx += self.vx
        self.dy += self.vy
        fx = pyxel.floor(self.dx)
        fy = pyxel.floor(self.dy)
        self.dx -= fx
        self.dy -= fy
        self.x += fx
        self.y += fy
        if abs(self.x - x0) > W or abs(self.y - y0) > H:
            self.is_dead = True

    def draw(self) -> None:
        pyxel.blt(self.x, self.y, 0, TILE, 0, TILE, TILE, TRANSPARENT_COLOR_1)

    def is_hit(self, x0: int, y0: int) -> bool:
        return is_hit(self.x - x0, self.y - y0)

enemies = []
def update_enemies(x0: int, y0: int) -> None:
    enemies_size = len(enemies)
    for i in range(enemies_size - 1, -1, -1):
        enemies[i].update(x0, y0)
        if enemies[i].is_dead:
            enemies.pop(i)

enemy_count = 0
def reset_enemy_count() -> None:
    global enemy_count
    enemy_count = 0

def update_enemy_count() -> None:
    global enemy_count
    if enemy_count < 63:
        enemy_count += 1
    else:
        enemy_count = 0

def get_enemy_delta(phase: int) -> int:
    delta = (enemy_count + phase * TILE) % 64
    if delta < 16: return delta
    if delta < 48: return 32 - delta
    return delta - 64

def is_enemy(x0: int, y0: int) -> bool:
    for e in enemies:
        if e.is_hit(x0, y0): return True
    x0_t = x0 // TILE
    y0_t = y0 // TILE
    for y_t in (y0_t, y0_t + 1):
        for x_t in (x0_t, x0_t + 1):
            if get_tile(x_t, y_t) == (1, 0):
                dx = x0 - x_t * TILE
                dy = y0 - y_t * TILE
                if is_hit(dx, dy): return True
    y0_t -= y0_t % H_T
    for x_t in range(x0_t - 2, x0_t + 4):
        u, v = get_tile(x_t, y0_t)
        y_t = y0_t + u
        phase, _ = get_tile(x_t, y_t)
        if v == 10:
            dx = x0 - x_t * TILE - get_enemy_delta(phase)
            dy = y0 - y_t * TILE
            if is_hit(dx, dy): return True
        elif v == 11:
            dx = x0 - x_t * TILE
            dy = y0 - y_t * TILE - get_enemy_delta(phase)
            if is_hit(dx, dy): return True
    return False

def draw_enemy(x0_t: int, y0_t: int) -> None:
    for e in enemies:
        e.draw()
    for x_t in range(x0_t - 2, x0_t + W_T + 3):
        u, v = get_tile(x_t, y0_t)
        y_t = y0_t + u
        phase, _ = get_tile(x_t, y_t)
        if v == 10:
            pyxel.blt(
                x_t * TILE + get_enemy_delta(phase), y_t * TILE, 0, TILE, 0,
                TILE, TILE, TRANSPARENT_COLOR_1)
        elif v == 11:
            pyxel.blt(
                x_t * TILE, y_t * TILE + get_enemy_delta(phase), 0, TILE, 0,
                TILE, TILE, TRANSPARENT_COLOR_1)

class Player:
    def __init__(self, x_t: int, y_t: int) -> None:
        self.x = x_t * TILE
        self.y = y_t * TILE
        self.dx = 0.0
        self.dy = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.u = 0
        self.v = 8 * TILE
        self.is_mirror = False
        self.is_flipped = False
        self.is_dead = False
        self.is_goal = False
        self.is_anti_grav = False

    def update(self, x0: int, y0: int) -> None:
        x1 = x0 + W - TILE
        y1 = y0 + H - TILE
        vv = 0.0
        is_anti_grav_0 = self.is_anti_grav
        for _ in range(8):
            ax, ay = self.get_accel()
            self.vx += ax
            self.vy += ay
            self.dx += self.vx
            self.dy += self.vy
            fx = pyxel.floor(self.dx)
            fy = pyxel.floor(self.dy)
            self.dx -= fx
            self.dy -= fy
            self.x += fx
            self.y += fy
            self.adjust_pos(x0, x1, y0, y1)

            if self.y < y0 - TILE or y1 + TILE < self.y:
                self.is_dead = True
                pyxel.stop()
                pyxel.play(0, 0)
                break
            if y0 <= self.y <= y0 + H and is_enemy(self.x, self.y):
                self.is_dead = True
                pyxel.stop()
                pyxel.play(0, 0)
                break
            for dx, dy in ((2, 2), (5, 2), (2, 5), (5, 5)):
                t = get_tile((self.x + dx) // TILE, (self.y + dy) // TILE)
                if t == (5, 1):
                    self.is_goal = True
                    pyxel.stop()
                    pyxel.play(0, 1)
                    break
                elif t == (4, 3):
                    self.is_anti_grav = True
                elif t == (5, 3):
                    self.is_anti_grav = False
            if self.is_goal: break
            vv = max(vv, self.vx * self.vx + self.vy * self.vy)

        if pyxel.play_pos(0) is None and pyxel.play_pos(1) is None:
            if vv > 1.0:
                pyxel.play(1, 2)
            elif self.is_anti_grav != is_anti_grav_0:
                pyxel.play(1, 3)

        if self.vx > 0.0:
            self.is_mirror = False
        elif self.vx < 0.0:
            self.is_mirror = True
        if self.vy > 0.0:
            self.is_flipped = False
        elif self.vy < 0.0:
            self.is_flipped = True
        self.u = ((1 if self.is_mirror else 0) + (2 if self.is_flipped else 0)) * TILE

    def draw(self, t: int=-1) -> None:
        u = self.u if t < 0 else (min(t // 4 + 4, 7)) * TILE
        pyxel.blt(self.x, self.y, 0, u, self.v, TILE, TILE, TRANSPARENT_COLOR_1)

    def get_accel(self) -> tuple[float, float]:
        x_t = self.x // TILE
        y_t = self.y // TILE
        dx = self.x % TILE
        dy = self.y % TILE
        ax = -DRAG * self.vx + (-ACCX if is_left() else 0.0) + (ACCX if is_right() else 0.0)
        ay = -DRAG * self.vy + (-GRAV if self.is_anti_grav else GRAV)
        for dx_t, dy_t in ((0, 0), (1, 0), (0, 1), (1, 1)):
            ratio = (TILE - dx if dx_t == 0 else dx) \
                * (TILE - dy if dy_t == 0 else dy) / (TILE * TILE)
            t = get_tile(x_t + dx_t, y_t + dy_t)
            if   t == (0, 1): ay -= ACCL * (1.0 - 0.75 * pyxel.sgn(self.vy)) * ratio
            elif t == (1, 1): ax -= ACCL * (1.0 - 0.75 * pyxel.sgn(self.vx)) * ratio
            elif t == (2, 1): ax += ACCL * (1.0 + 0.75 * pyxel.sgn(self.vx)) * ratio
            elif t == (3, 1): ay += ACCL * (1.0 + 0.75 * pyxel.sgn(self.vy)) * ratio
        return (ax, ay)

    def adjust_pos(self, x0: int, x1: int, y0: int, y1: int) -> None:
        if self.x < x0:
            self.x = x0
            self.dx = 0.0
            self.vx = 0.0
        elif self.x > x1:
            self.x = x1
            self.dx = 0.0
            self.vx = 0.0
        if self.y < y0 and not self.is_anti_grav:
            self.y = y0
            self.dy = 0.0
            self.vy = 0.0
        elif self.y > y1 and self.is_anti_grav:
            self.y = y1
            self.dy = 0.0
            self.vy = 0.0

class App:
    def __init__(self) -> None:
        pyxel.init(W, H, title=TITLE)
        pyxel.load(PYXRES)
        self.scene = SCENE_GAME
        self.time = 0
        self.death_count = 0
        self.stage = INIT_STAGE
        self.respawn_x_t = INIT_X_T
        self.respawn_y_t = self.stage * H_T + INIT_Y_T
        self.scroll_x = 0
        self.scroll_y = self.stage * H
        self.player = Player(self.respawn_x_t, self.respawn_y_t)
        pyxel.images[0].rect(0, 9 * TILE, 16 * TILE, 3 * TILE, TRANSPARENT_COLOR_1)
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        if self.scene == SCENE_GAME:
            self.update_game()
        elif self.scene == SCENE_DEAD:
            self.update_dead()
        elif self.scene == SCENE_GOAL:
            self.update_goal()

    def update_game(self) -> None:
        update_enemy_count()
        update_enemies(self.player.x, self.player.y)
        self.player.update(self.scroll_x, self.scroll_y)
        x_t = self.player.x // TILE
        y_t = self.scroll_y // TILE + 1
        if get_tile(0, y_t) == (0, 10):
            if pyxel.frame_count % 2 == 0: self.scroll_x += 1
        else:
            self.scroll_x = self.player.x - CAMERA_X
        if get_tile(x_t, y_t) == (0, 11) and enemy_count == 0:
            ex = self.player.x + pyxel.rndi(-64, 64)
            ey = self.scroll_y + (H if self.player.is_anti_grav else -TILE)
            dx = self.player.x - ex
            dy = self.player.y - ey
            dr = pyxel.sqrt(dx * dx + dy * dy)
            if dr > 0.0:
                dx /= dr
                dy /= dr
                enemies.append(Enemy(ex, ey, dx, dy))
                enemies.append(Enemy(ex, ey, 0.8 * dx - 0.6 * dy, 0.8 * dy + 0.6 * dx))
                enemies.append(Enemy(ex, ey, 0.8 * dx + 0.6 * dy, 0.8 * dy - 0.6 * dx))
        if self.player.is_dead:
            self.death_count = min(self.death_count + 1, 9999)
            self.scene = SCENE_DEAD
            self.time = 0
        elif self.player.is_goal:
            self.scene = SCENE_GOAL
            self.time = 0

    def update_dead(self):
        self.time += 1
        if self.time > DEAD_TIME:
            self.scene = SCENE_GAME
            self.time = 0
            self.player = Player(self.respawn_x_t, self.respawn_y_t)
            self.scroll_x = self.player.x - CAMERA_X
            reset_enemy_count()

    def update_goal(self):
        self.time += 1
        if self.time > GOAL_TIME:
            self.scene = SCENE_GAME
            self.time = 0
            if get_tile(0, self.scroll_y // TILE + 1) == (8, 9):
                self.stage = 0
            else:
                self.stage += 1
            self.respawn_y_t = self.stage * H_T + INIT_Y_T
            self.scroll_y = self.stage * H
            self.player = Player(self.respawn_x_t, self.respawn_y_t)
            self.scroll_x = self.player.x - CAMERA_X
            reset_enemy_count()

    def draw(self) -> None:
        color_shift = (pyxel.frame_count // 2) % 4 - 4
        for i in range(4):
            pyxel.pal(COLOR_SET_1[i], COLOR_SET_2[color_shift])
            pyxel.pal(COLOR_SET_3[i], COLOR_SET_4[color_shift])
            color_shift += 1

        pyxel.camera()
        pyxel.bltm(0, 0, 4, (self.scroll_x // 2) % W, 0, W, H)

        text_y = 15 if self.player.is_anti_grav else 0
        draw_text(0, text_y, f"STAGE {self.stage + 1:02}")
        draw_text(8, text_y, f"DEATH {self.death_count:04}")

        pyxel.bltm(
            0, 0, (self.scroll_y // 2048) % 4,
            self.scroll_x, self.scroll_y % 2048,
            W, H, TRANSPARENT_COLOR_1)

        pyxel.camera(self.scroll_x, self.scroll_y)
        draw_enemy(self.scroll_x // TILE, self.scroll_y // TILE)
        if self.scene == SCENE_GAME:
            self.player.draw()
        else:
            self.player.draw(self.time)

        pyxel.camera()
        if self.scene == SCENE_GOAL:
            pyxel.blt(16, 56, 0, 0, 128, 96, 16, TRANSPARENT_COLOR_2)
        elif self.scene == SCENE_DEAD:
            pyxel.bltm(12, 60, 4, 0, 128, 104, 8, TRANSPARENT_COLOR_2)

App()
