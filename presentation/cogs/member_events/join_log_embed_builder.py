import disnake

from presentation.views.roles_panel_management.helpers import COLOR_GREEN


class JoinLogEmbedBuilder:
    @staticmethod
    def build(member: disnake.Member) -> disnake.Embed:
        embed = disnake.Embed(
            title="Участник присоединился",
            color=COLOR_GREEN,
        )
        embed.set_author(
            name=str(member),
            icon_url=member.display_avatar.url,
        )
        embed.add_field(name="Упоминание", value=member.mention, inline=True)
        embed.add_field(name="ID", value=str(member.id), inline=True)

        created_ts = int(member.created_at.timestamp())
        embed.add_field(
            name="Аккаунт создан",
            value=f"<t:{created_ts}:R>",
            inline=True,
        )

        member_count = member.guild.member_count
        embed.set_footer(text=f"Участников на сервере: {member_count}")
        return embed