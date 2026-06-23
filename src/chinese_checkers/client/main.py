from textual.app import App

from chinese_checkers.ui.screens.main_menu import MainMenuScreen
from chinese_checkers.client.game_client import GameClient


class ChineseCheckersApp(App):
    AUTO_FOCUS = None

    BINDINGS = [("ctrl+c", "quit", "Quit")]

    def on_mount(self):

        self.client = GameClient()
        self.push_screen(MainMenuScreen())


def main():
    app = ChineseCheckersApp()
    app.run()


if __name__ == "__main__":
    app = ChineseCheckersApp()
    app.run()
