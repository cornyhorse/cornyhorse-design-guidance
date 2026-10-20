"""Template helpers for the design language: icons, status chips, notices and usage bars.

Everything here renders markup that is safe under the strict Content-Security-Policy (no `style=""`
attributes, no inline script) and that needs nothing from outside this server.
"""

from __future__ import annotations

from django import template
from django.templatetags.static import static
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()

#: The inline-SVG sprite, built from the vendored Bootstrap Icons by scripts/build_icon_sprite.py.
SPRITE = "vendor/bootstrap-icons/sprite.svg"

#: The one place that says which icon and default label each state wears. `data-state` on the
#: element picks the colours (static/css/components.css); the label and icon are always shown with
#: it, so a state is never colour alone. Do not add a state without adding its colours there.
STATES: dict[str, tuple[str, str]] = {
    "up": ("check-circle-fill", "Up"),
    "degraded": ("exclamation-triangle-fill", "Degraded"),
    "down": ("x-octagon-fill", "Down"),
    "stale": ("hourglass-split", "Stale"),
    "offline": ("pause-circle", "Expected offline"),
    "unreach": ("wifi-off", "Site unreachable"),
    "unknown": ("question-circle", "Unknown"),
    "warn": ("pie-chart-fill", "Overcommitted"),
}

#: Django message level tags to a state, for the notices at the top of a page.
MESSAGE_STATES = {
    "debug": "unknown",
    "info": "unknown",
    "success": "up",
    "warning": "degraded",
    "error": "down",
}


def icon_html(name: str, extra_class: str = ""):
    classes = f"bi {extra_class}".strip()
    return format_html(
        '<svg class="{}" aria-hidden="true" focusable="false"><use href="{}#{}"/></svg>',
        classes,
        static(SPRITE),
        name,
    )


@register.simple_tag
def icon(name: str, extra_class: str = ""):
    """`{% icon "sun" %}`: a decorative icon from the sprite, coloured by the text around it."""
    return icon_html(name, extra_class)


@register.simple_tag
def status_chip(state: str, label: str = "", extra_class: str = ""):
    """`{% status_chip "offline" "Temporarily offline" %}`: an annunciator chip, icon plus label.

    The label defaults to the state's name. The text stays in sentence case in the HTML; the
    stylesheet sets it in mono caps.
    """
    icon_name, default_label = STATES[state]
    return format_html(
        '<span class="ch-chip{}" data-state="{}">{}{}</span>',
        f" {extra_class}" if extra_class else "",
        state,
        icon_html(icon_name),
        label or default_label,
    )


@register.simple_tag
def notice_state(level_tag: str) -> str:
    """The state a Django message with this level tag is shown in."""
    return MESSAGE_STATES.get(level_tag, "unknown")


@register.simple_tag
def notice_icon(state: str):
    return icon_html(STATES[state][0])


@register.simple_tag
def usage_bar(used, capacity, label: str = "Used"):
    """`{% usage_bar item.used item.capacity %}`: a thin meter of used / capacity.

    Drawn as an inline SVG whose `<rect width>` is an attribute rather than a `style=""`
    attribute, so it works under a strict Content-Security-Policy. Empty when either number is
    missing; amber and full width when usage is over capacity.
    """
    if used is None or not capacity:
        return ""
    percent = used / capacity * 100
    width = max(0.0, min(percent, 100.0))
    state = mark_safe(' data-state="warn"') if percent > 100 else ""
    return format_html(
        '<svg class="ch-meter"{} viewBox="0 0 100 4" preserveAspectRatio="none" role="img" '
        'aria-label="{} {}% of capacity"><rect width="{}" height="4"/></svg>',
        state,
        label,
        f"{percent:.0f}",
        f"{width:.1f}",
    )
