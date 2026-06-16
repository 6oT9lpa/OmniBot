import pytest
from datetime import datetime, timezone

from presentation.embeds.logging_embed import (
    VoiceLogEmbedBuilder,
    MessageLogEmbedBuilder,
)


class MockMember:
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name
        self._str = name

    def __str__(self):
        return self._str


class MockUser:
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name
        self._str = name

    def __str__(self):
        return self._str


def test_voice_log_embed_build_join():
    member = MockMember(123456789, "TestUser")
    embed = VoiceLogEmbedBuilder.build_join(member, "General Voice")
    
    assert embed.title == "TestUser (123456789)"
    assert embed.color.value == 0x57F287
    
    field_names = [f.name for f in embed.fields]
    assert "Channel:" in field_names


def test_voice_log_embed_build_leave():
    member = MockMember(123456789, "TestUser")
    embed = VoiceLogEmbedBuilder.build_leave(member, "General Voice")
    
    assert embed.title == "TestUser (123456789)"
    assert embed.color.value == 0xED4245
    
    field_names = [f.name for f in embed.fields]
    assert "Channel:" in field_names


def test_voice_log_embed_build_move():
    member = MockMember(123456789, "TestUser")
    embed = VoiceLogEmbedBuilder.build_move(member, "Voice 1", "Voice 2")
    
    assert embed.title == "TestUser (123456789)"
    assert embed.color.value == 0x5865F2
    
    field_names = [f.name for f in embed.fields]
    assert "Before Channel:" in field_names
    assert "After Channel:" in field_names


def test_message_log_embed_build_delete():
    author = MockUser(123456789, "TestUser")
    embed = MessageLogEmbedBuilder.build_delete(author)
    
    assert embed.title == "TestUser (123456789)"
    assert embed.color.value == 0xED4245


def test_message_log_embed_build_edit():
    author = MockUser(123456789, "TestUser")
    embed = MessageLogEmbedBuilder.build_edit(author)
    
    assert embed.title == "TestUser (123456789)"
    assert embed.color.value == 0xFEE75C