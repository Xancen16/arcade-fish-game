import arcade
import random
import sqlite3

WID = 800
HEI = 600
TIT = "3D"
LAN = [150, 300, 450]

CON = sqlite3.connect("db3.db")
CUR = CON.cursor()
CUR.execute("CREATE TABLE IF NOT EXISTS sta (id INTEGER, hig INTEGER, mon INTEGER)")

CUR.execute("SELECT hig, mon FROM sta WHERE id = 1")
RES = CUR.fetchone()
if RES == None:
    CUR.execute("INSERT INTO sta (id, hig, mon) VALUES (1, 0, 0)")
    CON.commit()

class APP(arcade.Window):
    def __init__(self):
        super().__init__(WID, HEI, TIT)
        self.ply = arcade.SpriteList()
        self.obs = arcade.SpriteList()
        self.ite = arcade.SpriteList()
        self.obj = None
        self.idx = 1
        self.cur = 0
        CUR.execute("SELECT hig, mon FROM sta WHERE id = 1")
        DAT = CUR.fetchone()
        self.hig = DAT[0]
        self.mon = DAT[1]
        arcade.set_background_color(arcade.color.BLACK)

    def set(self):
        self.ply = arcade.SpriteList()
        self.obs = arcade.SpriteList()
        self.ite = arcade.SpriteList()
        
        # Смена цвета если монет > 10
        if self.mon > 10:
            clr = arcade.color.RED
        else:
            clr = arcade.color.GOLD
            
        self.obj = arcade.SpriteSolidColor(50, 20, clr)
        self.obj.center_x = 100
        self.obj.center_y = LAN[self.idx]
        self.ply.append(self.obj)
        self.cur = 0

    def on_draw(self):
        self.clear()
        arcade.draw_text(str(self.cur), 10, 570, arcade.color.WHITE, 20)
        arcade.draw_text(str(self.hig), 10, 540, arcade.color.BLUE, 20)
        arcade.draw_text(str(self.mon), 10, 510, arcade.color.YELLOW, 20)
        self.ply.draw()
        self.obs.draw()
        self.ite.draw()

    def on_update(self, det):
        self.obs.update()
        self.ite.update()
        self.cur = self.cur + 1
        
        if random.randint(1, 50) == 1:
            bad = arcade.SpriteSolidColor(40, 40, arcade.color.WHITE)
            bad.center_x = WID + 50
            bad.center_y = LAN[random.randint(0, 2)]
            bad.change_x = -10
            self.obs.append(bad)
            
        if random.randint(1, 100) == 1:
            get = arcade.SpriteSolidColor(20, 20, arcade.color.YELLOW)
            get.center_x = WID + 50
            get.center_y = LAN[random.randint(0, 2)]
            get.change_x = -8
            self.ite.append(get)

        for col in self.ite:
            if arcade.check_for_collision(self.obj, col):
                self.mon = self.mon + 1
                col.remove_from_sprite_lists()

        if arcade.check_for_collision_with_list(self.obj, self.obs):
            if self.cur > self.hig:
                self.hig = self.cur
            CUR.execute("UPDATE sta SET hig = ?, mon = ? WHERE id = 1", (self.hig, self.mon))
            CON.commit()
            self.set()

        for rem in self.obs:
            if rem.center_x < -50:
                rem.remove_from_sprite_lists()

    def on_key_press(self, key, mod):
        if key == arcade.key.UP and self.idx < 2:
            self.idx = self.idx + 1
        elif key == arcade.key.DOWN and self.idx > 0:
            self.idx = self.idx - 1
        self.obj.center_y = LAN[self.idx]

RUN = APP()
RUN.set()
arcade.run()
