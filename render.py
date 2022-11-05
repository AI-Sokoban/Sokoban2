import pygame

wall = pygame.image.load("assets/images/wall.png")
box = pygame.image.load("assets/images/box.png")
box_on_target = pygame.image.load("assets/images/box_on_target.png")
player = pygame.image.load("assets/images/player.png")
space = pygame.image.load("assets/images/space.png")
target = pygame.image.load("assets/images/target.png")


DEFAULT_RENDER_MAP = {
    '#': wall,
    ' ': space,
    'B': box,
    '.': target,
    '&': player,
    'X': box_on_target,
    '@': player,
}

DEFAULT_BOX_SIZE = wall.get_width()
DEFAULT_SCREEN_SIZE = (600, 400)


class Renderer:
    def __init__(self, board):
        pygame.init()
        self.board = board
        self.renderMap = DEFAULT_RENDER_MAP
        self.renderBoxSize = DEFAULT_BOX_SIZE
        self.screen = None
        self.setDisplaySize(DEFAULT_SCREEN_SIZE)

    def setDisplaySize(self, size: tuple[int, int]):
        self.screen = pygame.display.set_mode(size)
        return self

    def setCaption(self, name: str):
        pygame.display.set_caption(name)
        return self

    def setRenderMap(self, renderMap: dict[str, pygame.Surface]):
        self.renderMap = renderMap
        return self

    def setRenderBoxSize(self, size):
        self.renderBoxSize = size
        return self

    def fromInstance(self, board):
        self.board = board
        return self

    def clear(self):
        self.screen.fill((0, 0, 0))

    def showMessageBox(self, message: str):
        font = pygame.font.SysFont('arial', 60)
        # center
        text = font.render(message, True, (255, 255, 255))
        textRect = text.get_rect()
        textRect.centerx = self.screen.get_rect().centerx
        textRect.centery = self.screen.get_rect().centery
        self.screen.blit(text, textRect)
        pygame.display.update()

    def render(self):
        toRender = self.board.board_lst
        for i in range(len(toRender)):
            for c in range(len(toRender[i])):
                self.screen.blit(
                    self.renderMap[toRender[i][c]],
                    (c * self.renderBoxSize, i * self.renderBoxSize),
                )
        pygame.display.update()
