from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

import disnake

from presentation.embeds.base import EmbedBuilder


class StatsEmbedBuilder:
    @staticmethod
    def build_server_stats(data: Dict[str, Any], period: int, guild: disnake.Guild) -> disnake.Embed:
        builder = EmbedBuilder(color=0x00FF00)
        builder.set_title(f"📈 Статистика сервера за {period} дней")

        builder.add_field("💬 Всего сообщений", str(data["total_messages"]), inline=True)
        builder.add_field("👥 Активных участников", str(data["active_users"]), inline=True)
        builder.add_field("📝 Активных каналов", str(data["active_channels"]), inline=True)
        builder.add_field("📊 Среднее в день", f"{data['avg_per_day']} сообщений", inline=True)

        if data["top_user_id"]:
            top_user = guild.get_member(data["top_user_id"])
            top_user_name = top_user.display_name if top_user else f"<@{data['top_user_id']}>"
            builder.add_field(
                "🏆 Самый активный",
                f"{top_user_name} ({data['top_user_count']} сообщений)",
                inline=True,
            )

        if data["top_channel_id"]:
            channel = guild.get_channel(data["top_channel_id"])
            channel_name = channel.mention if channel else f"<#{data['top_channel_id']}>"
            builder.add_field(
                "📝 Топ-канал",
                f"{channel_name} ({data['top_channel_count']} сообщений)",
                inline=True,
            )

        if data["top_hour"] is not None:
            builder.add_field(
                "⏰ Пик активности",
                f"{data['top_hour']}:00 ({data['top_hour_count']} сообщений)",
                inline=True,
            )

        if data["daily_stats"]:
            daily_str = " ".join([f"{d['day']}: {d['count']}" for d in data["daily_stats"]])
            builder.add_field("📅 По дням недели", daily_str, inline=False)

        builder.add_field("🎤 В голосе", f"{data['voice_users']} пользователей", inline=True)
        total_hours = round(data["total_voice_minutes"] / 60, 1)
        builder.add_field("⏱️ Часов в голосе", f"{total_hours} часов", inline=True)

        if data["top_voice"]:
            voice_str = ""
            medals = ["🥇", "🥈", "🥉"]
            for i, v in enumerate(data["top_voice"]):
                member = guild.get_member(v["user_id"])
                name = member.display_name if member else f"<@{v['user_id']}>"
                hours = round(v["voice_minutes"] / 60, 1)
                voice_str += f"{medals[i]} {name}: {hours}ч\n"
            builder.add_field("🎤 Топ-3 в голосе", voice_str, inline=False)

        builder.set_footer(text="Данные обновляются в реальном времени")
        return builder.build()

    @staticmethod
    def build_user_stats(user: disnake.User, stats: Dict[str, Any], guild: disnake.Guild) -> disnake.Embed:
        builder = EmbedBuilder(color=0x00FF00)
        builder.set_title(f"📊 {user.display_name}")
        builder.set_thumbnail(url=user.display_avatar.url)
        builder.add_field("💬 Сообщений", str(stats.get("messages_count", 0)), inline=True)
        builder.add_field("🎤 В голосе", f"{stats.get('voice_minutes', 0)} мин", inline=True)
        builder.add_field("⚠️ Предупреждений", str(stats.get("warnings_count", 0)), inline=True)

        punishments = stats.get("punishments", [])
        if punishments:
            text = ""
            for p in punishments[:5]:
                text += f"• {p['type']} ({p['reason'] or 'без причины'})\n"
            if len(punishments) > 5:
                text += f"и ещё {len(punishments)-5}..."
            builder.add_field("🔨 Активные наказания", text, inline=False)
        else:
            builder.add_field("🔨 Активные наказания", "Нет", inline=False)

        if stats.get("last_message"):
            try:
                last_msg = datetime.fromisoformat(stats["last_message"])
                builder.add_field("🕒 Последнее сообщение", disnake.utils.format_dt(last_msg, "R"), inline=False)
            except:
                pass
        return builder.build()

    @staticmethod
    def build_top_channels(top: List[Dict[str, Any]], guild: disnake.Guild) -> disnake.Embed:
        builder = EmbedBuilder(color=0xFF8C00)
        builder.set_title("🏆 Топ-5 каналов")

        desc = ""
        for i, row in enumerate(top, 1):
            channel = guild.get_channel(row["channel_id"])
            name = channel.mention if channel else f"<#{row['channel_id']}>"
            desc += f"{i}. {name} — {row['count']} сообщений\n"
        builder.set_description(desc)
        return builder.build()

    @staticmethod
    def build_activity_graph(hourly: List[Dict[str, int]]) -> disnake.Embed:
        counts = [h["count"] for h in hourly]
        max_count = max(counts) if counts else 1

        if max_count == 0:
            builder = EmbedBuilder(color=0x800080)
            builder.set_title("📊 Активность по часам (7 дней, МСК)")
            builder.set_description("📊 Нет активности за последние 7 дней.")
            return builder.build()

        bar_length = 12
        graph = ""
        for item in hourly:
            h = item["hour"]
            count = item["count"]
            bars = "🟩" * max(1, count * bar_length // max_count) if count > 0 else "⬛"
            graph += f"`{h}:00` {bars} {count}\n"

        builder = EmbedBuilder(color=0x800080)
        builder.set_title("📊 Активность по часам (7 дней, МСК)")
        builder.set_description(graph)
        builder.set_footer(text="🟩 — активность, масштаб относительный | ⬛ — нет сообщений")
        return builder.build()

    @staticmethod
    def build_leaderboard(top: List[Dict[str, Any]], guild: disnake.Guild, bot: disnake.Client) -> disnake.Embed:
        builder = EmbedBuilder(color=0xFFD700)
        builder.set_title("🏆 Топ-10 активных участников (7 дней)")

        medals = ["🥇", "🥈", "🥉"] + [f"{i}." for i in range(4, 11)]
        for i, row in enumerate(top):
            user_id = row["user_id"]
            count = row["count"]

            member = guild.get_member(user_id)
            if not member:
                try:
                    member = bot.get_user(user_id)
                except:
                    pass

            name = member.display_name if member else f"Неизвестный ({user_id})"
            medal = medals[i] if i < len(medals) else f"{i+1}."
            builder.add_field(name=f"{medal} {name}", value=f"💬 {count} сообщений", inline=False)

        return builder.build()
        