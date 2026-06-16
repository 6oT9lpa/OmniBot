import disnake

from presentation.views.roles_panel_management.helpers import COLOR_RED


class LeaveLogEmbedBuilder:
    @staticmethod
    def build(member: disnake.Member) -> disnake.Embed:
        embed = disnake.Embed(
            title="Участник покинул сервер",
            color=COLOR_RED,
        )
        embed.set_author(
            name=str(member),
            icon_url=member.display_avatar.url,
        )
        embed.add_field(name="Упоминание", value=member.mention, inline=True)
        embed.add_field(name="ID", value=str(member.id), inline=True)

        if member.joined_at:
            joined_ts = int(member.joined_at.timestamp())
            embed.add_field(
                name="Был на сервере с",
                value=f"<t:{joined_ts}:R>",
                inline=True,
            )

        role_names = [r.name for r in member.roles if not r.is_default()]
        if role_names:
            embed.add_field(
                name=f"Роли ({len(role_names)})",
                value=", ".join(role_names[:10]) + ("..." if len(role_names) > 10 else ""),
                inline=False,
            )

        member_count = member.guild.member_count
        embed.set_footer(text=f"Участников на сервере: {member_count}")
        return embed