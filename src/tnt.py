import pygame
import pymunk
import math
import random
from io import BytesIO
from urllib.request import urlopen
from constants import BLOCK_SIZE
from chunk import chunks
from explosion import Explosion

class Tnt:
    avatar_cache = {}

    def __init__(
        self,
        space,
        x,
        y,
        texture_atlas,
        atlas_items,
        sound_manager,
        owner_name=None,
        velocity=0,
        rotation=0,
        mass=70,
        owner_display_name=None,
        owner_message=None,
        profile_image_url=None,
        owner_id=None,
        leaderboard=None,
    ):
        print("Spawning TNT")
        self.texture_atlas = texture_atlas
        self.atlas_items = atlas_items

        rect = atlas_items["block"]["tnt"]  
        self.texture = texture_atlas.subsurface(rect)

        width, height = self.texture.get_size()

        self.name = "tnt"

        self.velocity = velocity
        self.rotation = rotation
        self.space = space

        inertia = pymunk.moment_for_box(mass, (width, height))
        self.body = pymunk.Body(mass, inertia)
        self.body.position = (x, y)
        self.body.angle = math.radians(rotation)

        # Create a hitbox
        self.shape = pymunk.Poly.create_box(self.body, (width, height))
        self.shape.elasticity = 1  # No bounce
        self.shape.collision_type = 3 # Identifier for collisions
        self.shape.friction = 0.7
        self.shape.block_ref = self  # Reference to the block object

        self.sound_manager = sound_manager
        self.sound_manager.play_sound("tnt")

        self.space.add(self.body, self.shape)

        handler = space.add_collision_handler(3, 2)  # TNT & Block collision
        handler.post_solve = self.on_collision

        self.detonated = False
        self.spawn_time = pygame.time.get_ticks()

        # Owner info (nick from chat)
        self.owner_id = owner_id
        self.owner_display_name = owner_display_name or owner_name
        self.owner_message = owner_message
        self.profile_image_url = profile_image_url
        self.profile_image_surface = self._load_profile_image(profile_image_url)
        self.name_font = pygame.font.Font(None, 48)
        self.message_font = pygame.font.Font(None, 36)
        self.leaderboard = leaderboard

    def _load_profile_image(self, image_url):
        if not image_url:
            return None

        if image_url in Tnt.avatar_cache:
            return Tnt.avatar_cache[image_url]

        try:
            with urlopen(image_url) as response:
                data = response.read()
            image = pygame.image.load(BytesIO(data))
            image = pygame.transform.scale(image, (64, 64))
            Tnt.avatar_cache[image_url] = image
            return image
        except Exception as exc:
            print(f"Failed to load profile image {image_url}: {exc}")
            return None

    def on_collision(self, arbiter, space, data):
        # Small random rotation on collision
        self.body.angle += random.choice([0.01, -0.01])

    def explode(self, explosions):
        explosion_radius = 3 * BLOCK_SIZE  # Explosion radius in pixels
        self.detonated = True

        blocks_destroyed = 0

        for chunk in chunks:
            for row in chunks[chunk]:
                for block in row:
                    if block is None or getattr(block, "destroyed", False):
                        continue

                    dx = block.body.position.x - self.body.position.x
                    dy = block.body.position.y - self.body.position.y
                    distance = math.hypot(dx, dy)

                    if distance <= explosion_radius:
                        pre_hp = block.hp
                        damage = int(100 * (1 - (distance / explosion_radius)))
                        block.hp -= damage

                        if (
                            self.leaderboard
                            and self.owner_id is not None
                            and pre_hp > 0
                            and block.hp <= 0
                        ):
                            blocks_destroyed += 1

        if blocks_destroyed > 0 and self.leaderboard and self.owner_id is not None:
            self.leaderboard.record_blocks_broken(
                self.owner_id, self.owner_display_name or "Unknown", blocks_destroyed
            )

        explosion = Explosion(self.body.position, self.texture_atlas, self.atlas_items, particle_count=20)
        explosions.append(explosion)

    def update(self, tnt_list, explosions, camera):
        if self.detonated:
            self.space.remove(self.body, self.shape)
            if self in tnt_list:
                tnt_list.remove(self)
            return

        # Limit falling speed (terminal velocity)
        if self.body.velocity.y > 1000:
            self.body.velocity = (self.body.velocity.x, 1000)

        current_time = pygame.time.get_ticks()
        if current_time - self.spawn_time >= 4000:
            self.explode(explosions)
            camera.shake(10, 10)  # Shake camera for 10 frames with intensity 10

    def draw(self, screen, camera):
        if self.detonated:
            return

        # Draw TNT texture with rotation
        rotated_image = pygame.transform.rotate(self.texture, -math.degrees(self.body.angle))
        rect = rotated_image.get_rect(center=(self.body.position.x, self.body.position.y))
        rect.y -= camera.offset_y
        rect.x -= camera.offset_x
        screen.blit(rotated_image, rect)

        # Blinking effect: pulsating white overlay
        blink_period = 500  # 1 second cycle
        current_time = pygame.time.get_ticks() % blink_period
        brightness = (math.sin(current_time / blink_period * 2 * math.pi) + 1) / 2  # range 0-1
        alpha = int(brightness * 192)  # maximum 75% opacity

        white_overlay = pygame.Surface(self.texture.get_size(), pygame.SRCALPHA)
        white_overlay.fill((255, 255, 255, alpha))

        rotated_overlay = pygame.transform.rotate(white_overlay, -math.degrees(self.body.angle))
        overlay_rect = rotated_overlay.get_rect(center=(self.body.position.x, self.body.position.y))
        overlay_rect.y -= camera.offset_y
        overlay_rect.x -= camera.offset_x
        screen.blit(rotated_overlay, overlay_rect)

        if self.owner_display_name or self.owner_message or self.profile_image_surface:
            self._draw_chat_overlay(screen, camera)

    def _draw_chat_overlay(self, screen, camera):
        padding = 8
        avatar_width = 0
        avatar_height = 0

        if self.profile_image_surface:
            avatar_width, avatar_height = self.profile_image_surface.get_size()

        name_text = self.owner_display_name or ""
        name_surface = self.name_font.render(name_text, True, (255, 255, 255))

        message_surface = None
        if self.owner_message:
            message_surface = self.message_font.render(self.owner_message, True, (255, 255, 255))

        text_width = max(name_surface.get_width(), message_surface.get_width() if message_surface else 0)
        text_height = name_surface.get_height() + (message_surface.get_height() if message_surface else 0)

        overlay_width = padding * 3 + avatar_width + text_width
        overlay_height = padding * 2 + max(avatar_height, text_height)

        overlay_surface = pygame.Surface((overlay_width, overlay_height), pygame.SRCALPHA)
        overlay_surface.fill((0, 0, 0, 170))

        current_x = padding

        if self.profile_image_surface:
            overlay_surface.blit(self.profile_image_surface, (current_x, padding))
            current_x += avatar_width + padding
        else:
            current_x += padding

        text_y = padding
        overlay_surface.blit(name_surface, (current_x, text_y))
        if message_surface:
            overlay_surface.blit(message_surface, (current_x, text_y + name_surface.get_height()))

        overlay_rect = overlay_surface.get_rect(center=(self.body.position.x, self.body.position.y - 80))
        overlay_rect.x -= camera.offset_x
        overlay_rect.y -= camera.offset_y
        screen.blit(overlay_surface, overlay_rect)

class MegaTnt(Tnt):
    def __init__(
        self,
        space,
        x,
        y,
        texture_atlas,
        atlas_items,
        sound_manager,
        owner_name=None,
        velocity=0,
        rotation=0,
        mass=100,
        owner_display_name=None,
        owner_message=None,
        profile_image_url=None,
        owner_id=None,
        leaderboard=None,
    ):
        super().__init__(
            space,
            x,
            y,
            texture_atlas,
            atlas_items,
            sound_manager,
            owner_name,
            velocity,
            rotation,
            mass,
            owner_display_name,
            owner_message,
            profile_image_url,
            owner_id,
            leaderboard,
        )
        print("Spawning MegaTNT")
        self.name = "mega_tnt"
        self.scale_multiplier = 2

        rect = atlas_items["block"]["mega_tnt"]
        self.texture = pygame.transform.scale_by(texture_atlas.subsurface(rect), self.scale_multiplier)

        width, height = self.texture.get_size()
        self.shape.unsafe_set_vertices(pymunk.Poly.create_box(self.body, (width, height)).get_vertices())

    def explode(self, explosions):
        explosion_radius = 3 * BLOCK_SIZE * self.scale_multiplier
        self.detonated = True

        blocks_destroyed = 0

        for chunk in chunks:
            for row in chunks[chunk]:
                for block in row:
                    if block is None or getattr(block, "destroyed", False):
                        continue

                    dx = block.body.position.x - self.body.position.x
                    dy = block.body.position.y - self.body.position.y
                    distance = math.hypot(dx, dy)

                    if distance <= explosion_radius:
                        pre_hp = block.hp
                        damage = int(100 * self.scale_multiplier * (1 - (distance / explosion_radius)))
                        block.hp -= damage

                        if (
                            self.leaderboard
                            and self.owner_id is not None
                            and pre_hp > 0
                            and block.hp <= 0
                        ):
                            blocks_destroyed += 1

        if blocks_destroyed > 0 and self.leaderboard and self.owner_id is not None:
            self.leaderboard.record_blocks_broken(
                self.owner_id, self.owner_display_name or "Unknown", blocks_destroyed
            )

        explosion = Explosion(self.body.position, self.texture_atlas, self.atlas_items, particle_count=40)
        explosions.append(explosion)

    def update(self, tnt_list, explosions, camera):
        if self.detonated:
            self.space.remove(self.body, self.shape)
            if self in tnt_list:
                tnt_list.remove(self)
            return

        # Limit falling speed (terminal velocity)
        if self.body.velocity.y > 1000:
            self.body.velocity = (self.body.velocity.x, 1000)

        current_time = pygame.time.get_ticks()
        if current_time - self.spawn_time >= 4000:
            self.explode(explosions)
            camera.shake(15, 30)  # Shake camera for 15 frames with intensity 15

    def draw(self, screen, camera):
        if self.detonated:
            return

        rotated_image = pygame.transform.rotate(self.texture, -math.degrees(self.body.angle))
        rect = rotated_image.get_rect(center=(self.body.position.x, self.body.position.y))
        rect.y -= camera.offset_y
        rect.x -= camera.offset_x
        screen.blit(rotated_image, rect)

        # Blinking effect: pulsating white overlay
        blink_period = 500
        current_time = pygame.time.get_ticks() % blink_period
        brightness = (math.sin(current_time / blink_period * 2 * math.pi) + 1) / 2
        alpha = int(brightness * 192)

        white_overlay = pygame.Surface(self.texture.get_size(), pygame.SRCALPHA)
        white_overlay.fill((255, 255, 255, alpha))

        rotated_overlay = pygame.transform.rotate(white_overlay, -math.degrees(self.body.angle))
        overlay_rect = rotated_overlay.get_rect(center=(self.body.position.x, self.body.position.y))
        overlay_rect.y -= camera.offset_y
        overlay_rect.x -= camera.offset_x
        screen.blit(rotated_overlay, overlay_rect)

        # Draw owner name above MegaTNT
        if self.owner_name:
            text_surface = self.font.render(self.owner_name, True, (255, 255, 255))
            text_rect = text_surface.get_rect(center=(self.body.position.x - camera.offset_x, self.body.position.y - 55 - camera.offset_y))
            shadow = self.font.render(self.owner_name, True, (0, 0, 0))
            shadow_rect = shadow.get_rect(center=(self.body.position.x + 1 - camera.offset_x, self.body.position.y - 54 - camera.offset_y))
            screen.blit(shadow, shadow_rect)
            screen.blit(text_surface, text_rect)
