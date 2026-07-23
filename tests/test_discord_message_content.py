from types import SimpleNamespace

from application.services.discord_message_content import DiscordMessageContentNormalizer


def _message(content="", attachment_url="", edited_at=None):
    attachments = [SimpleNamespace(url=attachment_url, filename="file.gif", content_type="image/gif")] if attachment_url else []
    return SimpleNamespace(content=content, attachments=attachments, embeds=[], stickers=[], edited_at=edited_at)


def test_same_gif_with_only_metadata_change_is_not_a_content_change() -> None:
    normalizer = DiscordMessageContentNormalizer()
    assert not normalizer.changed(_message(attachment_url="https://cdn.example/a.gif", edited_at=1), _message(attachment_url="https://cdn.example/a.gif", edited_at=2))


def test_changed_link_or_attachment_is_a_content_change() -> None:
    normalizer = DiscordMessageContentNormalizer()
    assert normalizer.changed(_message("https://example.com/a"), _message("https://example.com/b"))
    assert normalizer.changed(_message(attachment_url="https://cdn.example/a.gif"), _message(attachment_url="https://cdn.example/b.gif"))


def test_changed_text_is_a_content_change() -> None:
    assert DiscordMessageContentNormalizer().changed(_message("before"), _message("after"))
