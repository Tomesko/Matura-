# menu.py
import pygame
from settings import RESOLUTIONS, CURRENT_RESOLUTION, backgrounds_color


class Menu:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont(None, 48)  # Button font
        self.small_font = pygame.font.SysFont(None, 36)  # Smaller for settings
        self.state = "main"  # "main" or "settings"
        self.buttons = self.create_buttons()

    def create_buttons(self):
        # Define button positions and sizes (centered)
        screen_width, screen_height = self.screen.get_size()
        button_width, button_height = 200, 50
        center_x = screen_width // 2 - button_width // 2

        buttons = {
            "main": [
                {"text": "Start Game", "rect": pygame.Rect(center_x, 200, button_width, button_height),
                 "action": "start"},
                {"text": "Settings", "rect": pygame.Rect(center_x, 300, button_width, button_height),
                 "action": "settings"},
                {"text": "Quit", "rect": pygame.Rect(center_x, 400, button_width, button_height), "action": "quit"}
            ],
            "settings": [
                {"text": f"Resolution: {RESOLUTIONS[0][0]}x{RESOLUTIONS[0][1]}",
                 "rect": pygame.Rect(center_x, 150, button_width, button_height), "action": "res0"},
                {"text": f"Resolution: {RESOLUTIONS[1][0]}x{RESOLUTIONS[1][1]}",
                 "rect": pygame.Rect(center_x, 250, button_width, button_height), "action": "res1"},
                {"text": f"Resolution: {RESOLUTIONS[2][0]}x{RESOLUTIONS[2][1]}",
                 "rect": pygame.Rect(center_x, 350, button_width, button_height), "action": "res2"},
                {"text": "Back", "rect": pygame.Rect(center_x, 450, button_width, button_height), "action": "back"}
            ]
        }
        return buttons

    def draw(self):
        self.screen.fill(backgrounds_color)
        for button in self.buttons[self.state]:
            pygame.draw.rect(self.screen, (200, 200, 200), button["rect"])  # Button background
            text_surf = self.font.render(button["text"], True, (0, 0, 0))
            self.screen.blit(text_surf, (button["rect"].x + 10, button["rect"].y + 10))
        pygame.display.flip()

    def handle_click(self, pos):
        for button in self.buttons[self.state]:
            if button["rect"].collidepoint(pos):
                return button["action"]
        return None

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                if event.type == pygame.MOUSEBUTTONDOWN:
                    action = self.handle_click(event.pos)
                    if action:
                        if action == "start":
                            return "start"
                        elif action == "settings":
                            self.state = "settings"
                        elif action == "quit":
                            return "quit"
                        elif action.startswith("res"):
                            # Update resolution (you'll need to handle screen resize in main.py)
                            index = int(action[-1])
                            global CURRENT_RESOLUTION
                            CURRENT_RESOLUTION = RESOLUTIONS[index]
                            # Note: Pygame doesn't auto-resize; you'll restart or resize manually
                        elif action == "back":
                            self.state = "main"

            def wait_for_start(self):
                running = True
                while running:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            return False
                        if event.type == pygame.MOUSEBUTTONDOWN:
                            if self.button_rect.collidepoint(event.pos):
                                return True

            self.draw()