from typing import Any

from activity.server.schemas.dev_blog import DevBlogPostPayload


IS_COMPONENTS_V2 = 1 << 15


def build_dev_blog_message(payload: DevBlogPostPayload) -> dict[str, Any]:
    container_components = (
        _build_inline_components(payload)
        if payload.image_render_mode == "inline_between_text"
        else _build_gallery_bottom_components(payload)
    )

    return {
        "flags": IS_COMPONENTS_V2,
        "components": [
            {
                "type": 17,
                "accent_color": payload.embeds[0].color,
                "components": container_components,
            }
        ],
        "allowed_mentions": {"parse": []},
    }


def _build_gallery_bottom_components(payload: DevBlogPostPayload) -> list[dict[str, Any]]:
    text = _build_text(payload)
    gallery_items = [_gallery_item(embed.image_url, embed.title or payload.title) for embed in payload.embeds if embed.image_url]
    components: list[dict[str, Any]] = [{"type": 10, "content": text}]
    if gallery_items:
        components.append({"type": 12, "items": gallery_items[:10]})
    return components


def _build_inline_components(payload: DevBlogPostPayload) -> list[dict[str, Any]]:
    components: list[dict[str, Any]] = [{"type": 10, "content": f"# {payload.title}"}]
    if payload.content:
        components.append({"type": 10, "content": payload.content})

    for embed in payload.embeds:
        text = _build_embed_text(embed.title, embed.description)
        if text:
            components.append({"type": 10, "content": text})
        if embed.image_url:
            components.append({"type": 12, "items": [_gallery_item(embed.image_url, embed.title or payload.title)]})
    return components[:40]


def _build_text(payload: DevBlogPostPayload) -> str:
    sections = [f"# {payload.title}"]
    if payload.content:
        sections.append(payload.content)
    for embed in payload.embeds:
        if embed.title:
            sections.append(f"## {embed.title}")
        sections.append(embed.description)
    return "\n\n".join(section.strip() for section in sections if section.strip())


def _build_embed_text(title: str | None, description: str) -> str:
    sections = []
    if title:
        sections.append(f"## {title}")
    sections.append(description)
    return "\n\n".join(section.strip() for section in sections if section.strip())


def _gallery_item(url: str, description: str) -> dict[str, Any]:
    return {
        "media": {"url": url},
        "description": description,
    }
