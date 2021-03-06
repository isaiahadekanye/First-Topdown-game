'''
@author: Ned Austin Datiles
'''
import pygame as pg
from os import path
from settings import WIDTH, HEIGHT, TITLE, TILESIZE, CLIP_IMG, CROSSHAIRS, \
    ITEM_IMAGES, WEAPONS, RIFLE_BULLET_IMG, HANDGUN_BULLET_IMG, SHOTGUN_BULLET_IMG, \
    MUZZLE_FLASHES, ENEMY_IMGS, HANDGUN_ANIMATIONS, KNIFE_ANIMATIONS, RIFLE_ANIMATIONS, \
    SHOTGUN_ANIMATIONS, FPS, LIGHTGREY, WHITE, DARKGREY, RED, PLAYER_HEALTH, PLAYER_STAMINA, \
    BAR_LENGTH, BAR_HEIGHT, GOLD, LIMEGREEN, DODGERBLUE, GREEN, DEEPSKYBLUE, BLOOD_SHADES, \
    ENEMY_KNOCKBACK, vec, PLAYER_HIT_SOUNDS, ZOMBIE_MOAN_SOUNDS, ENEMY_HIT_SOUNDS, \
    PLAYER_FOOTSTEPS, NIGHT_COLOR, LIGHT_MASK, LIGHT_RADIUS, PLAYER_SWING_NOISES, BG_MUSIC, \
    GAME_OVER_MUSIC, MAIN_MENU_MUSIC
from random import choice, randrange, random
from player import Player
from mobs import Mob
from tilemap import Map, Camera
from sprites import Obstacle, WeaponPickup, MiscPickup
from core_functions import collide_hit_rect
from pathfinding import Pathfinder, WeightedGraph


class Game:
    """
    Blueprint for game objects
    """

    def __init__(self):
        # initialize game window, etc
        pg.init()
        pg.mixer.pre_init(44100, -16, 1, 1024)
        pg.mouse.set_visible(False)
        self.screen = pg.display.set_mode((WIDTH, HEIGHT))
        self.screen.set_alpha(None)
        self.screen_width = WIDTH
        self.screen_height = HEIGHT
        pg.display.set_caption(TITLE)
        self.clock = pg.time.Clock()

        # Resource folders
        self.game_folder = path.dirname(__file__)
        self.img_folder = path.join(self.game_folder, 'img')
        self.snd_folder = path.join(self.game_folder, 'snd')
        self.music_folder = path.join(self.snd_folder, 'Music')
        self.crosshair_folder = path.join(self.img_folder, 'Crosshairs')
        self.item_folder = path.join(self.img_folder, 'Items')
        # Loads game assets
        self.load_data()
        self.running = True
        # Debugging flags
        self.debug = False
        self.hardcore_mode = False

    def load_data(self):
        """
        Loads the necessary assets for the game. 
        :return: None
        """
        # Game map
        self.map = Map(path.join(self.game_folder, 'map3.txt'))

        self.pause_screen_effect = pg.Surface(self.screen.get_size()).convert()
        self.pause_screen_effect.fill((0, 0, 0, 225))

        # Fog of war
        self.fog = pg.Surface(self.screen.get_size()).convert()
        self.fog.fill(NIGHT_COLOR)

        # Light on the player
        self.light_mask = pg.image.load(path.join(self.img_folder, LIGHT_MASK)).convert_alpha()
        self.light_mask = pg.transform.smoothscale(self.light_mask, (LIGHT_RADIUS, LIGHT_RADIUS))
        self.light_rect = self.light_mask.get_rect()

        # HUD Elements
        self.mag_img = pg.transform.smoothscale(pg.image.load(path.join(self.img_folder, CLIP_IMG)),
                                                (40, 40)).convert_alpha()
        # Crosshairs
        self.crosshairs = [
            pg.transform.smoothscale(pg.image.load(path.join(self.crosshair_folder, crosshair)),
                                     (32, 32)).convert_alpha()
            for crosshair in CROSSHAIRS]
        # todo - have a menu decide the player's crosshair
        self.crosshair = choice(self.crosshairs)

        # Item pickups
        self.pickup_items = {}
        for item in ITEM_IMAGES:
            self.pickup_items[item] = []
            self.pickup_items[item] = pg.image.load(path.join(self.item_folder, ITEM_IMAGES[item])).convert_alpha()

        # Fonts
        self.hud_font = path.join(self.img_folder, 'Fonts\Impacted2.0.ttf')

        # Sound loading
        self.music_tracks = {"main menu": MAIN_MENU_MUSIC, 'Game over': GAME_OVER_MUSIC, 'background music': BG_MUSIC}
        pg.mixer.music.load(path.join(self.music_folder, self.music_tracks['background music']))
        pg.mixer.music.set_volume(.5)

        self.swing_noises = {}
        for weapon in PLAYER_SWING_NOISES:
            noise = pg.mixer.Sound(path.join(self.snd_folder, PLAYER_SWING_NOISES[weapon]))
            noise.set_volume(.25)
            self.swing_noises[weapon] = noise

        self.player_hit_sounds = []
        for snd in PLAYER_HIT_SOUNDS:
            self.player_hit_sounds.append(pg.mixer.Sound(path.join(self.snd_folder, snd)))

        self.weapon_sounds = {}
        for weapon in WEAPONS['sound']:
            self.weapon_sounds[weapon] = {}
            sound_list = {}
            for snd in WEAPONS['sound'][weapon]:
                noise = pg.mixer.Sound(path.join(self.snd_folder, WEAPONS['sound'][weapon][snd]))
                noise.set_volume(.9)
                sound_list[snd] = noise
            self.weapon_sounds[weapon] = sound_list

        self.zombie_moan_sounds = []
        for snd in ZOMBIE_MOAN_SOUNDS:
            noise = pg.mixer.Sound(path.join(self.snd_folder, snd))
            noise.set_volume(.25)
            self.zombie_moan_sounds.append(noise)

        self.zombie_hit_sounds = {}
        for type in ENEMY_HIT_SOUNDS:
            self.zombie_hit_sounds[type] = []
            for snd in ENEMY_HIT_SOUNDS[type]:
                snd = pg.mixer.Sound(path.join(self.snd_folder, snd))
                snd.set_volume(.75)
                self.zombie_hit_sounds[type].append(snd)

        self.player_foot_steps = {}
        for terrain in PLAYER_FOOTSTEPS:
            self.player_foot_steps[terrain] = []
            for snd in PLAYER_FOOTSTEPS[terrain]:
                snd = pg.mixer.Sound(path.join(self.snd_folder, snd))
                snd.set_volume(.5)
                self.player_foot_steps[terrain].append(snd)

        # Bullets
        self.bullet_images = {}
        self.bullet_images['lg'] = pg.transform.smoothscale(pg.image.load(path.join(self.img_folder, RIFLE_BULLET_IMG)),
                                                            (10, 3)).convert_alpha()
        self.bullet_images['med'] = pg.transform.smoothscale(
            pg.image.load(path.join(self.img_folder, HANDGUN_BULLET_IMG)), (5, 3)).convert_alpha()
        self.bullet_images['sm'] = pg.transform.smoothscale(pg.image.load(
            path.join(self.img_folder, SHOTGUN_BULLET_IMG)).convert_alpha(), (7, 7))

        # Effects
        self.gun_flashes = [pg.image.load(path.join(self.img_folder, flash)).convert_alpha() for flash in
                            MUZZLE_FLASHES]

        # Load enemy animations
        self.enemy_imgs = [pg.transform.smoothscale(pg.image.load(path.join(self.game_folder, name)),
                                                    (96, 96)).convert_alpha() for name in
                           ENEMY_IMGS]
        # Load player animations
        self.default_player_weapon = 'knife'
        self.default_player_action = 'idle'
        self.player_animations = {'handgun': {}, 'knife': {}, 'rifle': {}, 'shotgun': {}}

        # Create all hand gun animations
        self.player_animations['handgun']['idle'] = [pg.image.load(path.join(self.game_folder, name)).convert_alpha()
                                                     for name in HANDGUN_ANIMATIONS['idle']]
        self.player_animations['handgun']['melee'] = [pg.image.load(path.join(self.game_folder, name)).convert_alpha()
                                                      for name in HANDGUN_ANIMATIONS['melee']]
        self.player_animations['handgun']['move'] = [pg.image.load(path.join(self.game_folder, name)).convert_alpha()
                                                     for name in HANDGUN_ANIMATIONS['move']]
        self.player_animations['handgun']['reload'] = [pg.image.load(path.join(self.game_folder, name)).convert_alpha()
                                                       for name in HANDGUN_ANIMATIONS['reload']]
        self.player_animations['handgun']['shoot'] = [pg.image.load(path.join(self.game_folder, name)).convert_alpha()
                                                      for name in HANDGUN_ANIMATIONS['shoot']]

        # Create all knife animations
        self.player_animations['knife']['idle'] = [pg.image.load(path.join(self.game_folder, name)).convert_alpha() for
                                                   name in KNIFE_ANIMATIONS['idle']]
        self.player_animations['knife']['melee'] = [pg.image.load(path.join(self.game_folder, name)).convert_alpha() for
                                                    name in KNIFE_ANIMATIONS['melee']]
        self.player_animations['knife']['move'] = [pg.image.load(path.join(self.game_folder, name)).convert_alpha() for
                                                   name in KNIFE_ANIMATIONS['move']]

        # Create all rifle animations
        self.player_animations['rifle']['idle'] = [pg.image.load(path.join(self.game_folder, name)).convert_alpha() for
                                                   name in RIFLE_ANIMATIONS['idle']]
        self.player_animations['rifle']['melee'] = [pg.image.load(path.join(self.game_folder, name)).convert_alpha() for
                                                    name in RIFLE_ANIMATIONS['melee']]
        self.player_animations['rifle']['move'] = [pg.image.load(path.join(self.game_folder, name)).convert_alpha() for
                                                   name in RIFLE_ANIMATIONS['move']]
        self.player_animations['rifle']['reload'] = [pg.image.load(path.join(self.game_folder, name)).convert_alpha()
                                                     for name in RIFLE_ANIMATIONS['reload']]
        self.player_animations['rifle']['shoot'] = [pg.image.load(path.join(self.game_folder, name)).convert_alpha() for
                                                    name in RIFLE_ANIMATIONS['shoot']]

        # Create all shotgun animations
        self.player_animations['shotgun']['idle'] = [pg.image.load(path.join(self.game_folder, name)).convert_alpha()
                                                     for name in SHOTGUN_ANIMATIONS['idle']]
        self.player_animations['shotgun']['melee'] = [pg.image.load(path.join(self.game_folder, name)).convert_alpha()
                                                      for name in SHOTGUN_ANIMATIONS['melee']]
        self.player_animations['shotgun']['move'] = [pg.image.load(path.join(self.game_folder, name)).convert_alpha()
                                                     for name in SHOTGUN_ANIMATIONS['move']]
        self.player_animations['shotgun']['reload'] = [pg.image.load(path.join(self.game_folder, name)).convert_alpha()
                                                       for name in SHOTGUN_ANIMATIONS['reload']]
        self.player_animations['shotgun']['shoot'] = [pg.image.load(path.join(self.game_folder, name)).convert_alpha()
                                                      for name in SHOTGUN_ANIMATIONS['shoot']]

    def new(self):
        """
        Creates a new game
        :return: None
        """
        self.all_sprites = pg.sprite.LayeredUpdates()
        self.walls = pg.sprite.Group()
        self.bullets = pg.sprite.Group()
        self.mobs = pg.sprite.Group()
        self.items = pg.sprite.Group()
        self.swingAreas = pg.sprite.Group()
        self.camera = Camera(self.map.width, self.map.height)
        self.paused = False
        self.running = True
        self.pathfinder = Pathfinder()
        self.game_graph = WeightedGraph()
        mob_positions = []
        wall_positions = []

        for row, tiles in enumerate(self.map.data):
            for col, tile in enumerate(tiles):
                if tile == '1':
                    wall_positions.append((col * TILESIZE, row * TILESIZE))
                if tile == 'P':
                    self.player = Player(self, col * TILESIZE, row * TILESIZE)
                if tile == 'E':
                    mob_positions.append((col * TILESIZE, row * TILESIZE))
                if tile == 'W':
                    WeaponPickup(self, (col * TILESIZE, row * TILESIZE))

        for position in wall_positions:
            Obstacle(self, position[0], position[1])

        for position in mob_positions:
            Mob(self, position[0], position[1])

        self.game_graph.walls = [(int(wall[0] // TILESIZE), int(wall[1] // TILESIZE)) for wall in wall_positions]
        self.mob_idx = 0
        self.last_queue_update = 0
        g.run()

    def find_path(self, predator, prey):
        """
        Finds a path for the predator to reach its prey
        :param predator: The entity who seeks
        :param prey: The unknowning target
        :return: A list of Vector2 objects to guide the predator
        """
        return self.pathfinder.a_star_search(self.game_graph,
                                             vec(predator.pos.x // TILESIZE, predator.pos.y // TILESIZE),
                                             vec(prey.pos.x // TILESIZE, prey.pos.y // TILESIZE))

    def run(self):
        """
        Runs the game
        :return: None
        """
        self.playing = True
        pg.mixer.music.play(loops=-1)
        while self.playing:
            pg.display.set_caption("{:.1f}".format(self.clock.get_fps()))
            self.dt = self.clock.tick(FPS) / 1000
            self.events()
            if not self.paused:
                self.update()
            self.draw()

    def update(self):
        """
        Updates game state
        :return: None
        """
        self.impact_positions = []
        for sprite in self.all_sprites:
            if sprite == self.player:
                sprite.update(pg.key.get_pressed())
            else:
                sprite.update()
        self.camera.update(self.player)
        self.swingAreas.update()
        self.update_pathfinding_queue()

        # Player hits mobs
        hit_melee_box = pg.sprite.groupcollide(self.mobs, self.swingAreas, False, True, collide_hit_rect)
        for hit in hit_melee_box:
            choice(self.zombie_hit_sounds['bash']).play()
            hit.health -= hit.health
            self.impact_positions.append(hit.rect.center)

        # Enemy hits player
        hits = pg.sprite.spritecollide(self.player, self.mobs, False, collide_hit_rect)
        for hit in hits:
            if random() < .7:
                choice(self.player_hit_sounds).play()
            if hit.can_attack:
                self.impact_positions.append(self.player.rect.center)
                self.player.health -= hit.damage
                hit.vel.normalize()
                hit.pause()
                if self.player.health <= 0:
                    self.playing = False
        if hits:
            self.player.pos += vec(ENEMY_KNOCKBACK, 0).rotate(-hits[0].rot)

        # Bullet collisions
        hits = pg.sprite.groupcollide(self.mobs, self.bullets, False, False, collide_hit_rect)
        for mob in hits:
            for bullet in hits[mob]:
                self.impact_positions.append(bullet.rect.center)
                mob.health -= bullet.damage
                mob.pos += vec(WEAPONS[self.player.weapon]['damage'] // 10, 0).rotate(-self.player.rot)
            # Drowns out blood gushing noises the further the collision is from the player
            dist = self.player.pos.distance_to(mob.pos)
            ratio = 1
            if dist > 0:
                ratio = round(200 / dist, 2)
                if ratio > 1:
                    ratio = 1
            snd = choice(self.zombie_hit_sounds['bullet'])
            snd.set_volume(ratio)
            if snd.get_num_channels() > 2:
                snd.stop()
            snd.play()

        # Item collisions
        hits = pg.sprite.spritecollide(self.player, self.items, True, collide_hit_rect)
        for hit in hits:
            self.player.pickup_item(hit)
            if isinstance(hit, WeaponPickup):
                snd = self.weapon_sounds[hit.type]['pickup']
                snd.play()
            else:
                pass

    def events(self):
        """
        Game loop event handling
        :return: None
        """
        for event in pg.event.get():
            if event.type == pg.QUIT:
                if self.playing:
                    self.playing = False
                self.running = False
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_b:
                    self.debug = not self.debug
                if event.key == pg.K_p:
                    self.paused = not self.paused
                if event.key == pg.K_h:
                    self.hardcore_mode = not self.hardcore_mode

    def draw_grid(self):
        """
        Used for debugging
        :return: None
        """
        for x in range(0, WIDTH, TILESIZE):
            pg.draw.line(self.screen, LIGHTGREY, (x, 0), (x, HEIGHT))
        for y in range(0, HEIGHT, TILESIZE):
            pg.draw.line(self.screen, LIGHTGREY, (0, y), (WIDTH, y))

    def render_fog(self):
        self.fog.fill(NIGHT_COLOR)
        self.light_rect.center = self.camera.apply_rect(self.player.hit_rect.copy()).center
        self.fog.blit(self.light_mask, self.light_rect)
        self.screen.blit(self.fog, (0, 0), special_flags=pg.BLEND_RGBA_MULT)

    def draw(self):
        """
        Draws the updated game state onto the screen
        :return: None
        """
        self.screen.fill(DARKGREY)
        if self.debug:
            self.draw_grid()
        self.draw_blood_splatters()
        # Draw all sprites to the screen
        for sprite in self.all_sprites:
            # if isinstance(sprite, Mob):
            #     sprite.draw_health()
            self.screen.blit(sprite.image, self.camera.apply(sprite))
            if self.debug:
                pg.draw.rect(self.screen, (0, 255, 255), self.camera.apply_rect(sprite.hit_rect), 1)
        self.render_fog()
        x, y = pg.mouse.get_pos()
        self.screen.blit(self.crosshair, (x - self.crosshair.get_rect().width // 2,
                                          y - self.crosshair.get_rect().height // 2))
        # draw hud information
        if not self.hardcore_mode:
            self.update_hud()
        if self.paused:
            self.screen.blit(self.pause_screen_effect, (0, 0))
            self.draw_text('Paused', self.hud_font, 105, RED, WIDTH / 2, HEIGHT / 2, align='center')
        pg.display.flip()

    def update_hud(self):
        """
        Updates the HUD information for the player to see
        :return: None
        """
        self.draw_player_stats()
        if self.player.weapon != 'knife':
            self.draw_current_clip(self.screen, 10, 70, self.player.arsenal[self.player.weapon]['clip'], 3, 15)

    def draw_player_stats(self):
        """
        Gives the player visual indication of their health & stamina
        :return: None
        """
        self.draw_player_health(self.screen, 10, 10, self.player.health // PLAYER_HEALTH)
        self.draw_text(str(self.player.health) + "%", self.hud_font, 15, (119, 136, 153),
                       BAR_LENGTH // 2 - 5, 10)
        self.draw_player_stamina(self.screen, 10, 40, self.player.stamina / PLAYER_STAMINA)
        self.draw_text("{0:.0f}".format(self.player.stamina) + "%", self.hud_font, 15, (119, 136, 153),
                       BAR_LENGTH // 2 - 5, 40)

    def draw_current_clip(self, surface, x, y, bullets, bullet_length, bullet_height):
        """
        Used to give the player visual indication of how much ammunition they have at 
        the moment in their weapon
        :param surface: The location in which to draw this information
        :param x: The x location to draw
        :param y: The y location to draw
        :param bullets: How many bullets to draw
        :param bullet_length: How wide the bullet figure will be
        :param bullet_height: How tall the bullet figure will be
        :return: None
        """
        if self.player.weapon != 'knife':
            temp = x
            # Draws how many bullets are in the player's magazine in GOLD with the difference between
            # maximum mag capacity - current bullet count is in LIGHTGREY
            for j in range(0, WEAPONS[self.player.weapon]['clip size']):
                bullet_outline = pg.Surface((bullet_length, bullet_height)).convert()
                if j < bullets:
                    bullet_outline.fill(GOLD)
                else:
                    bullet_outline.fill(LIGHTGREY)
                surface.blit(bullet_outline, (temp, y))
                temp += 2 * bullet_length
            surface.blit(self.mag_img, (temp, y - 10))
            self.draw_text('x', self.hud_font, 15, WHITE,
                           temp + 32, y)
            self.draw_text(str(self.player.arsenal[self.player.weapon]['reloads']), self.hud_font, 20, WHITE,
                           temp + 40, y - 5)

    @staticmethod
    def draw_player_health(surface, x, y, pct):
        """
        Draws the player's health bar
        :param surface: The surface on which to draw the health bar
        :param x: x location
        :param y: y location
        :param pct: How much health is left in %
        :return: None
        """
        if pct < 0:
            pct = 0
        fill = pct * BAR_LENGTH
        static = BAR_LENGTH

        outline_rect = pg.Rect(x, y, BAR_LENGTH, BAR_HEIGHT)
        filled_rect = pg.Rect(x, y, fill, BAR_HEIGHT)
        static_rect = pg.Rect(x, y, static, BAR_HEIGHT)

        pg.draw.rect(surface, LIMEGREEN, static_rect)
        pg.draw.rect(surface, GREEN, filled_rect)
        pg.draw.rect(surface, WHITE, outline_rect, 2)

    @staticmethod
    def draw_player_stamina(surface, x, y, pct):
        """
        Draws the player's stamina bar
        :param surface: The surface to draw on
        :param x: x location
        :param y: y location
        :param pct: How much stamina is left in %
        :return: None
        """
        if pct < 0:
            pct = 0

        fill = pct * BAR_LENGTH
        static = BAR_LENGTH
        outline_rect = pg.Rect(x, y, BAR_LENGTH, BAR_HEIGHT)
        filled_rect = pg.Rect(x, y, fill, BAR_HEIGHT)
        static_rect = pg.Rect(x, y, static, BAR_HEIGHT)

        pg.draw.rect(surface, DODGERBLUE, static_rect)
        pg.draw.rect(surface, DEEPSKYBLUE, filled_rect)
        pg.draw.rect(surface, WHITE, outline_rect, 2)

    def draw_text(self, text, font_name, size, color, x, y, align='nw'):
        """
        Draws informative text.
        :param text: The text to draw.
        :param font_name: The font to use.
        :param size: The size of the font.
        :param color: The colour of the font.
        :param x: The x-coordinate of the location
        :param y: The y-coordinate of the location 
        :param align: Compass location
        :return: None
        """
        font = pg.font.Font(font_name, size)
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect()
        if align == "nw":
            text_rect.topleft = (x, y)
        if align == "ne":
            text_rect.topright = (x, y)
        if align == "sw":
            text_rect.bottomleft = (x, y)
        if align == "se":
            text_rect.bottomright = (x, y)
        if align == "n":
            text_rect.midtop = (x, y)
        if align == "s":
            text_rect.midbottom = (x, y)
        if align == "e":
            text_rect.midright = (x, y)
        if align == "w":
            text_rect.midleft = (x, y)
        if align == "center":
            text_rect.center = (x, y)

        self.screen.blit(text_surface, text_rect)

    def draw_blood_splatters(self):
        if self.impact_positions:
            for pos in self.impact_positions:
                impact = True
                while impact:
                    self.events()
                    for magnitude in range(1, randrange(35, 65)):
                        exploding_bit_x = pos[0] + randrange(-1 * magnitude, magnitude) + self.camera.camera.x
                        exploding_bit_y = pos[1] + randrange(-1 * magnitude, magnitude) + self.camera.camera.y
                        pg.draw.circle(self.screen, choice(BLOOD_SHADES), (exploding_bit_x, exploding_bit_y),
                                       randrange(1, 5))
                    impact = False
            self.impact_positions.clear()

    def update_pathfinding_queue(self):
        """
        Gives each mob on the level the opportunity to find a path
        to its prey (the player). Each mob will be given this
        opportunity in order according to their list position into
        the mobs group.
        :return: None
        """
        now = pg.time.get_ticks()
        if now - self.last_queue_update > 5000:
            self.last_queue_update = now
            if self.mob_idx == len(self.mobs):
                self.mob_idx = 0
            count = 0
            for mob in self.mobs:
                mob.can_find_path = False
                if count == self.mob_idx:
                    mob.can_find_path = True
                count += 1
            self.mob_idx += 1

    def show_start_screen(self):
        """
        Displays the start screen for the game
        :return: None
        """
        pass

    def show_gameover_screen(self):
        """
        Displays the gameover screen for the game
        :return: None
        """
        pass

    def show_pause_screen(self):
        """
        Displays the pause screen for the game
        :return: None
        """
        pass


if __name__ == '__main__':
    g = Game()
    g.show_start_screen()
    while g.running:
        g.new()
        g.show_gameover_screen()

    pg.quit()
