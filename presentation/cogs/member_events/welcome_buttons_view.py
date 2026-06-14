from typing import Optional

import disnake


class WelcomeButtonsView(disnake.ui.View):
    def __init__(
        self,
        rules_url: Optional[str] = None,
        roles_url: Optional[str] = None,
    ):
        super().__init__(timeout=None)

        if rules_url:
            self.add_item(
                disnake.ui.Button(
                    label="Правила сервера",
                    style=disnake.ButtonStyle.link,
                    url=rules_url,
                    emoji="📋",
                )
            )

        if roles_url:
            self.add_item(
                disnake.ui.Button(
                    label="Выбор ролей",
                    style=disnake.ButtonStyle.link,
                    url=roles_url,
                    emoji="🎭",
                )
            )