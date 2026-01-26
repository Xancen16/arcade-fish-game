import arcade
import random
import sqlite3

WID = 800
HEI = 600
TIT = "Salmon Run"
LAN = [150, 300, 450]

CON = sqlite3.connect("db3.db")
CUR = CON.cursor()
CUR.execute("CREATE TABLE IF NOT EXISTS sta (id INTEGER, hig INTEGER, mon INTEGER)")
CUR.execute("SELECT hig, mon FROM sta WHERE id = 1")
RES = CUR.fetchone()

if RES is None:
    CUR.execute("INSERT INTO sta (id, hig, mon) VALUES (1, 0, 0)")
    CON.commit()

class Salmon(arcade.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.textures = []
        self.textures.append(
            arcade.make_soft_square_texture(50, arcade.color.ORANGE, outer_alpha=255)
        )
        self.textures.append(
            arcade.make_soft_square_texture(50, arcade.color.DARK_ORANGE, outer_alpha=255)
        )
        self.textures.append(
            arcade.make_soft_square_texture(50, arcade.color.GOLD, outer_alpha=255)
        )
        self.texture = self.textures[0]
        self.current_frame = 0
        self.counter = 0
        self.animation_speed = 6
        self.center_x = x
        self.center_y = y

    def update_animation(self, delta_time: float = 1 / 60):
        self.counter += 1
        if self.counter >= self.animation_speed:
            self.current_frame = (self.current_frame + 1) % len(self.textures)
            self.texture = self.textures[self.current_frame]
            self.counter = 0

class APP(arcade.Window):
    def __init__(self):
        super().__init__(WID, HEI, TIT)
        self.ply = arcade.SpriteList()
        self.obs = arcade.SpriteList()
        self.ite = arcade.SpriteList()
        self.obj = None
        self.idx = 1
        self.target_y = LAN[self.idx]
        self.move_speed = 16
        self.cur = 0
        self.spd = -10
        CUR.execute("SELECT hig, mon FROM sta WHERE id = 1")
        DAT = CUR.fetchone()
        self.hig = DAT[0]
        self.mon = DAT[1]
        arcade.set_background_color(arcade.color.DARK_BLUE_GRAY)

    def set(self):
        self.ply = arcade.SpriteList()
        self.obs = arcade.SpriteList()
        self.ite = arcade.SpriteList()
        self.cur = 0
        self.spd = -10
        self.idx = 1
        self.obj = Salmon(120, LAN[self.idx])
        self.target_y = LAN[self.idx]
        self.ply.append(self.obj)

    def on_draw(self):
        self.clear()
        arcade.draw_text(f"{self.cur}", 10, 570, arcade.color.WHITE, 20)
        arcade.draw_text(f"{self.hig}", 10, 540, arcade.color.CYAN, 20)
        arcade.draw_text(f"{self.mon}", 10, 510, arcade.color.GOLD, 20)
        self.ply.draw()
        self.obs.draw()
        self.ite.draw()

    def on_update(self, delta_time):
        self.obs.update()
        self.ite.update()
        self.ply.update_animation()
        if self.obj.center_y < self.target_y:
            self.obj.center_y += self.move_speed
            if self.obj.center_y > self.target_y:
                self.obj.center_y = self.target_y
        elif self.obj.center_y > self.target_y:
            self.obj.center_y -= self.move_speed
            if self.obj.center_y < self.target_y:
                self.obj.center_y = self.target_y
        self.cur += 1
        if self.cur % 500 == 0:
            self.spd -= 1
        if random.randint(1, 50) == 1:
            bear = arcade.SpriteSolidColor(60, 60, arcade.color.BROWN)
            bear.center_x = WID + 60
            bear.center_y = LAN[random.randint(0, 2)]
            bear.change_x = self.spd
            self.obs.append(bear)
        if random.randint(1, 100) == 1:
            food = arcade.Sprite()
            food.texture = arcade.make_circle_texture(20, arcade.color.YELLOW)
            food.center_x = WID + 40
            food.center_y = LAN[random.randint(0, 2)]
            food.change_x = self.spd + 2
            self.ite.append(food)
        for item in self.ite:
            if arcade.check_for_collision(self.obj, item):
                self.mon += 1
                item.remove_from_sprite_lists()
        if arcade.check_for_collision_with_list(self.obj, self.obs):
            if self.cur > self.hig:
                self.hig = self.cur
            CUR.execute("UPDATE sta SET hig = ?, mon = ? WHERE id = 1", (self.hig, self.mon))
            CON.commit()
            self.set()
        for obj in self.obs:
            if obj.center_x < -100:
                obj.remove_from_sprite_lists()
        for item in self.ite:
            if item.center_x < -100:
                item.remove_from_sprite_lists()

    def on_key_press(self, key, modifiers):
        if key == arcade.key.UP and self.idx < 2:
            self.idx += 1
            self.target_y = LAN[self.idx]
        elif key == arcade.key.DOWN and self.idx > 0:
            self.idx -= 1
            self.target_y = LAN[self.idx]

game = APP()
game.set()
arcade.run()
