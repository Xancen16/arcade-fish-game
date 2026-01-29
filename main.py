import arcade
import random
import sqlite3
import math
import time
from PIL import Image
from dataclasses import dataclass
from typing import List, Optional

SCREEN_WIDTH = 1300
SCREEN_HEIGHT = 850
SCREEN_TITLE = "SALMON RUN: FINAL FIX"

STATE_MENU = 0
STATE_GAME = 1
STATE_SHOP = 2
STATE_GAMEOVER = 3
STATE_BOSS = 4
STATE_INVENTORY = 5

LANE_1 = 250
LANE_2 = 425
LANE_3 = 600
LANES = [LANE_1, LANE_2, LANE_3]

COLOR_WATER = (15, 30, 55)
COLOR_UI_BG = (20, 25, 40, 230)
COLOR_GOLD = (255, 215, 0)
COLOR_TEXT = (255, 255, 255)


def create_texture(width, height, color, name_uid):
    if len(color) == 3:
        c = color + (255,)
    else:
        c = color
    image = Image.new('RGBA', (width, height), c)
    return arcade.Texture(image, name=f"{name_uid}_{random.random()}")


class DataManager:
    def __init__(self):
        self.conn = sqlite3.connect("salmon_save_final.db")
        self.cursor = self.conn.cursor()
        self._check_tables()

    def _check_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_stats (
                id INTEGER PRIMARY KEY,
                high_score INTEGER DEFAULT 0,
                gold INTEGER DEFAULT 0,
                skin_level INTEGER DEFAULT 1,
                shield_level INTEGER DEFAULT 0,
                revive_tickets INTEGER DEFAULT 0,
                boss_kills INTEGER DEFAULT 0
            )
        """)
        self.cursor.execute("SELECT * FROM player_stats WHERE id=1")
        if not self.cursor.fetchone():
            self.cursor.execute("INSERT INTO player_stats VALUES (1, 0, 500, 1, 0, 0, 0)")
        self.conn.commit()

    def load(self):
        return self.cursor.execute("SELECT * FROM player_stats WHERE id=1").fetchone()

    def save(self, high_score, gold, skin, shield, revives, boss_kills):
        self.cursor.execute("""
            UPDATE player_stats 
            SET high_score=?, gold=?, skin_level=?, shield_level=?, revive_tickets=?, boss_kills=? 
            WHERE id=1
        """, (high_score, gold, skin, shield, revives, boss_kills))
        self.conn.commit()


class Particle(arcade.SpriteCircle):
    def __init__(self, x, y, color):
        super().__init__(random.randint(3, 6), color)
        self.center_x = x
        self.center_y = y
        self.change_x = random.uniform(-4, 4)
        self.change_y = random.uniform(-4, 4)
        self.fade_speed = 5

    def update(self, delta_time: float = 1 / 60):
        self.center_x += self.change_x
        self.center_y += self.change_y
        self.alpha = max(0, self.alpha - self.fade_speed)
        if self.alpha <= 0:
            self.remove_from_sprite_lists()


class Hero(arcade.Sprite):
    def __init__(self, skin_lvl):
        palette = [(255, 100, 50), (50, 200, 255), (255, 215, 0), (180, 50, 220)]
        color = palette[min(skin_lvl - 1, 3)]
        tex = create_texture(60, 40, color, "hero")
        super().__init__(tex)
        self.target_y = LANE_2
        self.center_x = 200
        self.center_y = LANE_2
        self.shield_active = False
        self.invul_timer = 0.0

    def update(self, delta_time: float = 1 / 60):
        self.center_y += (self.target_y - self.center_y) * 0.2


class Boss(arcade.Sprite):
    def __init__(self):
        tex = create_texture(220, 180, (100, 40, 20), "boss")
        super().__init__(tex)
        self.hp = 250
        self.max_hp = 250
        self.center_x = SCREEN_WIDTH + 300
        self.center_y = SCREEN_HEIGHT / 2
        self.state = "ENTER"
        self.timer = 0.0
        self.target_y = SCREEN_HEIGHT / 2


    def update_logic(self, dt):
        if self.state == "ENTER":
            if self.center_x > SCREEN_WIDTH - 250:
                self.center_x -= 150 * dt
            else:
                self.state = "IDLE"
        elif self.state == "IDLE":
            self.timer += dt
            self.center_y += math.sin(time.time() * 4) * 1.5
            if self.timer > 1.5:
                self.timer = 0
                self.target_y = random.choice(LANES)
                self.state = "MOVE"
        elif self.state == "MOVE":
            diff = self.target_y - self.center_y
            self.center_y += diff * 5 * dt
            if abs(diff) < 5:
                self.state = "IDLE"
        return self.hp <= 0


class FloatingText:
    def __init__(self, x, y, text, color):
        self.x, self.y = x, y
        self.life = 1.5
        self.text_obj = arcade.Text(text, x, y, color, 14, anchor_x="center", bold=True)

    def update(self, dt):
        self.life -= dt
        self.y += 60 * dt
        self.text_obj.y = self.y

    def draw(self):
        if self.life > 0: self.text_obj.draw()


class GameButton:
    def __init__(self, x, y, w, h, text, action_code, price=0):
        self.rect = arcade.rect.XYWH(x, y, w, h)
        self.action_code = action_code
        self.price = price
        self.is_hovered = False
        display = text + (f" ({price} G)" if price > 0 else "")
        self.text_obj = arcade.Text(display, x, y, arcade.color.WHITE, 16, anchor_x="center", anchor_y="center")

    def draw(self):
        color = (70, 80, 100) if self.is_hovered else (40, 50, 60)
        arcade.draw_rect_filled(self.rect, color)
        arcade.draw_rect_outline(self.rect, arcade.color.WHITE, 2)
        self.text_obj.draw()

    def check_hover(self, mx, my):
        self.is_hovered = self.rect.point_in_rect((mx, my))
        return self.is_hovered


class GameWindow(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, antialiasing=True)
        self.db = DataManager()

        self.s_hero = arcade.SpriteList()
        self.s_enemies = arcade.SpriteList()
        self.s_coins = arcade.SpriteList()
        self.s_particles = arcade.SpriteList()
        self.s_boss = arcade.SpriteList()
        self.floating_texts = []

        self.state = STATE_MENU
        self.score = 0.0
        self.speed = -7.0
        self.session_gold = 0
        self.mouse_x, self.mouse_y = 0, 0

        self.load_profile()
        self.create_ui()

    def load_profile(self):
        data = self.db.load()
        self.p_hi = data[1];
        self.p_gold = data[2];
        self.p_skin = data[3]
        self.p_shield = data[4];
        self.p_revs = data[5];
        self.p_boss_kills = data[6]

    def save_profile(self):
        self.db.save(self.p_hi, self.p_gold, self.p_skin, self.p_shield, self.p_revs, self.p_boss_kills)

    def create_ui(self):
        self.btns_menu = [
            GameButton(SCREEN_WIDTH / 2, 500, 300, 60, "START RUN", STATE_GAME),
            GameButton(SCREEN_WIDTH / 2, 420, 300, 60, "SHOP", STATE_SHOP),
            GameButton(SCREEN_WIDTH / 2, 340, 300, 60, "STATS", STATE_INVENTORY),
            GameButton(SCREEN_WIDTH / 2, 260, 300, 60, "EXIT", -1)
        ]
        self.btns_shop = [
            GameButton(SCREEN_WIDTH / 2, 550, 400, 60, "SKIN UPGRADE", 101, 500),
            GameButton(SCREEN_WIDTH / 2, 470, 400, 60, "SHIELD UPGRADE", 102, 300),
            GameButton(SCREEN_WIDTH / 2, 390, 400, 60, "BUY LIFE", 103, 1000),
            GameButton(SCREEN_WIDTH / 2, 100, 200, 50, "BACK", STATE_MENU)
        ]
        self.btn_back = GameButton(SCREEN_WIDTH / 2, 100, 200, 50, "BACK", STATE_MENU)
        self.txt_title = arcade.Text(SCREEN_TITLE, SCREEN_WIDTH / 2, 700, arcade.color.AQUA, 60, anchor_x="center",
                                     bold=True)

    def start_game(self):
        self.state = STATE_GAME
        self.score = 0;
        self.session_gold = 0;
        self.speed = -8.0
        self.s_enemies.clear();
        self.s_coins.clear();
        self.s_particles.clear()
        self.s_boss.clear();
        self.s_hero.clear();
        self.floating_texts.clear()
        self.hero = Hero(self.p_skin)
        self.s_hero.append(self.hero)

    def spawn_particles(self, x, y, color):
        for _ in range(8): self.s_particles.append(Particle(x, y, color))

    def on_draw(self):
        self.clear()
        arcade.draw_rect_filled(arcade.rect.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
                                COLOR_WATER)
        for y in LANES: arcade.draw_line(0, y, SCREEN_WIDTH, y, (255, 255, 255, 30), 4)

        if self.state == STATE_MENU:
            self.txt_title.draw()
            for b in self.btns_menu: b.draw()
        elif self.state in [STATE_GAME, STATE_BOSS]:
            self.s_particles.draw();
            self.s_coins.draw();
            self.s_enemies.draw()
            self.s_boss.draw();
            self.s_hero.draw()
            arcade.draw_rect_filled(arcade.rect.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT - 40, SCREEN_WIDTH, 80),
                                    COLOR_UI_BG)
            arcade.Text(f"DIST: {int(self.score)}m", 50, SCREEN_HEIGHT - 50, arcade.color.WHITE, 20).draw()
            arcade.Text(f"GOLD: {self.session_gold}", 250, SCREEN_HEIGHT - 50, COLOR_GOLD, 20).draw()
            if self.hero.shield_active: arcade.draw_circle_outline(self.hero.center_x, self.hero.center_y, 50,
                                                                   arcade.color.CYAN, 3)
            if self.state == STATE_BOSS and self.s_boss:
                b = self.s_boss[0]
                w = (b.hp / b.max_hp) * 500
                arcade.draw_rect_filled(arcade.rect.XYWH(SCREEN_WIDTH / 2, 40, 500, 20), (50, 0, 0))
                arcade.draw_rect_filled(arcade.rect.XYWH(SCREEN_WIDTH / 2 - (500 - w) / 2, 40, w, 20), arcade.color.RED)
            for ft in self.floating_texts: ft.draw()
        elif self.state == STATE_SHOP:
            arcade.Text("SHOP", SCREEN_WIDTH / 2, 750, COLOR_GOLD, 50, anchor_x="center").draw()
            arcade.Text(f"GOLD: {self.p_gold}", SCREEN_WIDTH / 2, 680, arcade.color.GREEN, 30, anchor_x="center").draw()
            for b in self.btns_shop: b.draw()
        elif self.state == STATE_INVENTORY:
            arcade.Text("STATS", SCREEN_WIDTH / 2, 750, arcade.color.PURPLE, 50, anchor_x="center").draw()
            stats = [f"Best: {self.p_hi}m", f"Revives: {self.p_revs}", f"Boss Kills: {self.p_boss_kills}"]
            for i, s in enumerate(stats): arcade.Text(s, SCREEN_WIDTH / 2, 550 - i * 60, arcade.color.WHITE, 24,
                                                      anchor_x="center").draw()
            self.btn_back.draw()
        elif self.state == STATE_GAMEOVER:
            arcade.draw_rect_filled(arcade.rect.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
                                    (0, 0, 0, 220))
            arcade.Text("GAME OVER", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 50, arcade.color.RED, 60, anchor_x="center",
                        bold=True).draw()
            arcade.Text("Press SPACE", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 50, arcade.color.WHITE, 20,
                        anchor_x="center").draw()

    def on_update(self, dt):
        for ft in self.floating_texts[:]:
            ft.update(dt)
            if ft.life <= 0: self.floating_texts.remove(ft)

        if self.state == STATE_MENU:
            for b in self.btns_menu: b.check_hover(self.mouse_x, self.mouse_y)
        elif self.state == STATE_SHOP:
            for b in self.btns_shop: b.check_hover(self.mouse_x, self.mouse_y)
        elif self.state == STATE_INVENTORY:
            self.btn_back.check_hover(self.mouse_x, self.mouse_y)

        if self.state in [STATE_GAME, STATE_BOSS]:
            self.score += dt * 25
            self.speed -= dt * 0.05

            self.s_hero.update()
            self.s_enemies.update()
            self.s_coins.update()
            self.s_particles.update()

            if self.hero.invul_timer > 0: self.hero.invul_timer -= dt

            if self.state == STATE_GAME:
                if random.random() < 0.025:
                    t = create_texture(70, 70, (100, 50, 20), "obs")
                    o = arcade.Sprite(t);
                    o.center_x = SCREEN_WIDTH + 100;
                    o.center_y = random.choice(LANES);
                    o.change_x = self.speed
                    self.s_enemies.append(o)
                if random.random() < 0.02:
                    c = arcade.SpriteCircle(14, COLOR_GOLD);
                    c.center_x = SCREEN_WIDTH + 50;
                    c.center_y = random.choice(LANES);
                    c.change_x = self.speed
                    self.s_coins.append(c)

            if int(self.score) > 0 and int(self.score) % 3000 == 0 and self.state != STATE_BOSS:
                self.state = STATE_BOSS
                self.s_enemies.clear();
                self.s_boss.append(Boss())
                self.floating_texts.append(FloatingText(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, "BOSS!", arcade.color.RED))

            if self.state == STATE_BOSS:
                b = self.s_boss[0]
                if b.update_logic(dt):
                    self.s_boss.clear();
                    self.state = STATE_GAME
                    self.session_gold += 500;
                    self.p_gold += 500;
                    self.p_boss_kills += 1
                    self.spawn_particles(b.center_x, b.center_y, COLOR_GOLD)

            self.check_collisions()

    def check_collisions(self):
        for c in arcade.check_for_collision_with_list(self.hero, self.s_coins):
            c.remove_from_sprite_lists();
            self.session_gold += 1;
            self.p_gold += 1
            self.spawn_particles(c.center_x, c.center_y, COLOR_GOLD)
            self.floating_texts.append(FloatingText(c.center_x, c.center_y, "+1", COLOR_GOLD))

        hits = arcade.check_for_collision_with_list(self.hero, self.s_enemies) + arcade.check_for_collision_with_list(
            self.hero, self.s_boss)
        if hits and self.hero.invul_timer <= 0:
            if self.hero.shield_active:
                self.hero.shield_active = False;
                self.hero.invul_timer = 2.0
                self.spawn_particles(self.hero.center_x, self.hero.center_y, arcade.color.CYAN)
                self.floating_texts.append(
                    FloatingText(self.hero.center_x, self.hero.center_y, "SHIELD BROKEN", arcade.color.CYAN))
            else:
                self.die()

    def die(self):
        if self.p_revs > 0:
            self.p_revs -= 1;
            self.hero.invul_timer = 3.0;
            self.s_enemies.clear()
            self.floating_texts.append(
                FloatingText(self.hero.center_x, self.hero.center_y, "REVIVED!", arcade.color.GREEN))
        else:
            if int(self.score) > self.p_hi: self.p_hi = int(self.score)
            self.save_profile();
            self.state = STATE_GAMEOVER

    def on_mouse_motion(self, x, y, dx, dy):
        self.mouse_x, self.mouse_y = x, y

    def on_mouse_press(self, x, y, b, m):
        if self.state == STATE_MENU:
            for btn in self.btns_menu:
                if btn.check_hover(x, y):
                    if btn.action_code == -1:
                        arcade.exit()
                    elif btn.action_code == STATE_GAME:
                        self.start_game()
                    else:
                        self.state = btn.action_code
        elif self.state == STATE_SHOP:
            if self.btn_back.check_hover(x, y): self.state = STATE_MENU
            for btn in self.btns_shop:
                if btn.check_hover(x, y):
                    if btn.action_code == 101 and self.p_gold >= 500:
                        self.p_gold -= 500; self.p_skin += 1
                    elif btn.action_code == 102 and self.p_gold >= 300:
                        self.p_gold -= 300; self.p_shield += 1
                    elif btn.action_code == 103 and self.p_gold >= 1000:
                        self.p_gold -= 1000; self.p_revs += 1
                    self.save_profile()
        elif self.state == STATE_INVENTORY and self.btn_back.check_hover(x, y):
            self.state = STATE_MENU

    def on_key_press(self, key, mod):
        if self.state in [STATE_GAME, STATE_BOSS]:
            curr = LANES.index(self.hero.target_y)
            if key == arcade.key.UP and curr < 2: self.hero.target_y = LANES[curr + 1]
            if key == arcade.key.DOWN and curr > 0: self.hero.target_y = LANES[curr - 1]
            if key == arcade.key.SPACE and self.p_shield > 0 and not self.hero.shield_active: self.hero.shield_active = True
        elif self.state == STATE_GAMEOVER and key == arcade.key.SPACE:
            self.state = STATE_MENU


if __name__ == "__main__":
    GameWindow()
    arcade.run()
