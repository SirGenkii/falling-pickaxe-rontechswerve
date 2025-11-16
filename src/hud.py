import pygame
from constants import BLOCK_SIZE, CHUNK_HEIGHT

def render_text_with_outline(text, font, text_color, outline_color, outline_width=2):
    # Render the text in the main color.
    text_surface = font.render(text, True, text_color)
    # Create a new surface larger than the text surface to hold the outline.
    w, h = text_surface.get_size()
    outline_surface = pygame.Surface((w + 2*outline_width, h + 2*outline_width), pygame.SRCALPHA)
    
    # Blit the text multiple times in the outline color, offset by outline_width in every direction.
    for dx in range(-outline_width, outline_width+1):
        for dy in range(-outline_width, outline_width+1):
            # Only draw outline if offset is non-zero (avoids overdraw, though it's not a big deal)
            if dx != 0 or dy != 0:
                pos = (dx + outline_width, dy + outline_width)
                outline_surface.blit(font.render(text, True, outline_color), pos)
    
    # Blit the main text in the center.
    outline_surface.blit(text_surface, (outline_width, outline_width))
    return outline_surface

class Hud:
    def __init__(self, texture_atlas, atlas_items, position=(32, 32)):
        """
        :param texture_atlas: The atlas surface containing the item icons.
        :param atlas_items: A dict with keys under "item" for each ore.
        :param position: Top-left position where the HUD will be drawn.
        """
        self.texture_atlas = texture_atlas
        self.atlas_items = atlas_items

        # Initialize ore amounts to 0.
        self.amounts = {
            "coal": 0,
            "iron_ingot": 0,
            "copper_ingot": 0,
            "gold_ingot": 0,
            "redstone": 0,
            "lapis_lazuli": 0,
            "diamond": 0,
            "emerald": 0,
        }

        self.position = position
        self.icon_size = (64, 64)  # Size to draw each icon
        self.spacing = 15  # Space between items

        self.pickaxe_name = ""
        self.pickaxe_font = pygame.font.Font(None, 72)

        self.command_font = pygame.font.Font(None, 56)
        self.leaderboard_font = pygame.font.Font(None, 48)

        self.command_definitions = [
            {"key": "tnt", "label": "TNT"},
            {"key": "megatnt", "label": "MegaTNT"},
            {"key": "diamond", "label": "Diamond"},
            {"key": "netherite", "label": "Netherite"},
            {"key": "gold", "label": "Gold"},
            {"key": "iron", "label": "Iron"},
            {"key": "stone", "label": "Stone"},
            {"key": "wood", "label": "Wood"},
            {"key": "big", "label": "Big"},
            {"key": "fast", "label": "Fast"},
            {"key": "slow", "label": "Slow"},
        ]
        self.command_state = {cmd["key"]: {"last_triggered": None} for cmd in self.command_definitions}
        self.command_highlight_duration = 1500

        self.leaderboard_entries = {}

        # Initialize a font (using the default font and size 24)
        self.font = pygame.font.Font(None, 64)

    def update_amounts(self, new_amounts):
        """
        Update the ore amounts.
        :param new_amounts: Dict with ore names as keys and integer amounts as values.
        """
        self.amounts.update(new_amounts)

    def set_pickaxe_name(self, pickaxe_name):
        self.pickaxe_name = pickaxe_name

    def mark_command_trigger(self, command_key):
        if command_key in self.command_state:
            self.command_state[command_key]["last_triggered"] = pygame.time.get_ticks()

    def record_blocks_broken(self, author_id, display_name, count=1):
        if author_id is None:
            return

        existing = self.leaderboard_entries.get(author_id, {"display_name": display_name or "Unknown", "blocks": 0})
        existing["display_name"] = display_name or existing["display_name"]
        existing["blocks"] += count
        self.leaderboard_entries[author_id] = existing

    def draw(self, screen, pickaxe_y, fast_slow_active, fast_slow):
        """
        Draws the HUD: each ore icon with its amount and other indicators.
        """
        now = pygame.time.get_ticks()
        pickaxe_label_bottom = self._draw_command_legend(screen, now)
        pickaxe_label_bottom = self._draw_pickaxe_label(screen, pickaxe_label_bottom)

        x, y = self.position

        for ore, amount in self.amounts.items():
            # Retrieve the icon rect from atlas_items["item"][ore]
            if ore in self.atlas_items["item"]:
                icon_rect = pygame.Rect(self.atlas_items["item"][ore])
                icon = self.texture_atlas.subsurface(icon_rect)
                # Scale the icon to desired icon size
                icon = pygame.transform.scale(icon, self.icon_size)
                # Blit the icon
                screen.blit(icon, (x, y))
            else:
                # In case the ore key is missing, skip drawing the icon
                continue

            # Render the amount text with a black outline.
            text = str(amount)
            # You can tweak outline_width, text color, and outline color as needed.
            text_surface = render_text_with_outline(text, self.font, (255, 255, 255), (0, 0, 0), outline_width=2)
            
            # Position text to the right of the icon
            text_x = x + self.icon_size[0] + self.spacing
            text_y = y + (self.icon_size[1] - text_surface.get_height()) // 2 + 3
            screen.blit(text_surface, (text_x, text_y))

            # Move to the next line
            y += self.icon_size[1] + self.spacing

        # Draw the pickaxe position indicator with outlined text
        pickaxe_indicator_text = f"Y: {-int(pickaxe_y // BLOCK_SIZE)}"
        pickaxe_indicator_surface = render_text_with_outline(pickaxe_indicator_text, self.font, (255, 255, 255), (0, 0, 0), outline_width=2)
        pickaxe_indicator_x = x + self.spacing
        pickaxe_indicator_y = y + self.spacing
        screen.blit(pickaxe_indicator_surface, (pickaxe_indicator_x, pickaxe_indicator_y))

        # Draw the fast/slow indicator with outlined text
        if fast_slow_active:
            fast_slow_text = f"{fast_slow}"
        else:
            fast_slow_text = "Normal"
        fast_slow_surface = render_text_with_outline(fast_slow_text, self.font, (255, 255, 255), (0, 0, 0), outline_width=2)
        fast_slow_x = x + self.spacing
        fast_slow_y = y + 2 * self.spacing + fast_slow_surface.get_height()
        screen.blit(fast_slow_surface, (fast_slow_x, fast_slow_y))

        self._draw_leaderboard(screen)


    def _draw_pickaxe_label(self, screen, start_y):
        pickaxe_label = self.pickaxe_name or ""
        pickaxe_surface = render_text_with_outline(
            f"Pickaxe: {pickaxe_label}",
            self.pickaxe_font,
            (255, 255, 255),
            (0, 0, 0),
            outline_width=2,
        )
        pickaxe_x = (screen.get_width() - pickaxe_surface.get_width()) // 2
        screen.blit(pickaxe_surface, (pickaxe_x, start_y))
        return start_y + pickaxe_surface.get_height() + self.spacing // 2

    def _draw_command_legend(self, screen, now):
        command_spacing = 18
        commands_per_row = 6

        command_surfaces = []
        for cmd in self.command_definitions:
            last_triggered = self.command_state[cmd["key"]]["last_triggered"]
            recently_triggered = last_triggered is not None and now - last_triggered <= self.command_highlight_duration
            if recently_triggered:
                text_color = (255, 215, 0)
                outline_color = (255, 140, 0)
            else:
                text_color = (255, 255, 255)
                outline_color = (40, 40, 40)

            surface = render_text_with_outline(
                cmd["label"],
                self.command_font,
                text_color,
                outline_color,
                outline_width=3,
            )
            command_surfaces.append(surface)

        y = self.spacing // 2

        def draw_row(row_surfaces, y_offset):
            if not row_surfaces:
                return y_offset

            row_width = sum(s.get_width() for s in row_surfaces) + command_spacing * (len(row_surfaces) - 1)
            start_x = (screen.get_width() - row_width) // 2
            max_height = 0
            for surface in row_surfaces:
                screen.blit(surface, (start_x, y_offset))
                start_x += surface.get_width() + command_spacing
                max_height = max(max_height, surface.get_height())
            return y_offset + max_height + self.spacing // 3

        y = draw_row(command_surfaces[:commands_per_row], y)
        y = draw_row(command_surfaces[commands_per_row:], y)
        return y + self.spacing // 2

    def _draw_leaderboard(self, screen):
        if not self.leaderboard_entries:
            return

        title_surface = render_text_with_outline(
            "Top TNT Miners",
            self.leaderboard_font,
            (255, 255, 255),
            (0, 0, 0),
            outline_width=2,
        )

        base_x = screen.get_width() - title_surface.get_width() - self.spacing
        y = self.spacing
        screen.blit(title_surface, (base_x, y))
        y += title_surface.get_height() + self.spacing // 2

        top_entries = sorted(
            self.leaderboard_entries.values(), key=lambda e: (-e["blocks"], e["display_name"])
        )[:5]

        for idx, entry in enumerate(top_entries, start=1):
            line = f"{idx}. {entry['display_name']}: {entry['blocks']}"
            line_surface = render_text_with_outline(
                line,
                self.leaderboard_font,
                (240, 240, 240),
                (0, 0, 0),
                outline_width=2,
            )
            line_x = screen.get_width() - line_surface.get_width() - self.spacing
            screen.blit(line_surface, (line_x, y))
            y += line_surface.get_height() + self.spacing // 3

            

