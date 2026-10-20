import re

import pytest
from django.template import Context, Template

from apps.core.templatetags import ui


def render(source: str, **context) -> str:
    return Template("{% load ui %}" + source).render(Context(context))


@pytest.mark.parametrize("state", sorted(ui.STATES))
def test_every_state_renders_a_chip_with_icon_and_label(state):
    icon_name, label = ui.STATES[state]

    html = render(f'{{% status_chip "{state}" %}}')

    assert f'data-state="{state}"' in html
    assert f"#{icon_name}" in html
    assert label in html


def test_a_chip_can_carry_its_own_label_and_class():
    html = render('{% status_chip "offline" "Temporarily offline" "extra" %}')

    assert "Temporarily offline" in html
    assert 'class="ch-chip extra"' in html


def test_the_chip_label_is_escaped():
    assert "&lt;b&gt;" in render('{% status_chip "up" label %}', label="<b>")


@pytest.mark.parametrize(
    ("tag", "state"),
    [("debug", "unknown"), ("info", "unknown"), ("success", "up"), ("warning", "degraded"), ("error", "down"), ("custom", "unknown")],
)
def test_message_levels_map_to_states(tag, state):
    assert render("{% notice_state tag %}", tag=tag) == state


def test_notice_icon_is_the_states_icon():
    assert "#x-octagon-fill" in render('{% notice_icon "down" %}')


def test_icons_are_decorative_and_come_from_the_sprite():
    html = render('{% icon "sun" "extra" %}')

    assert 'aria-hidden="true"' in html
    assert 'class="bi extra"' in html
    assert re.search(r'href="/static/vendor/bootstrap-icons/sprite\.svg#sun"', html)


def test_usage_bar_draws_the_fill_as_an_svg_attribute_not_a_style():
    html = render("{% usage_bar 46 100 %}")

    assert '<rect width="46.0" height="4"/>' in html
    assert "46% of capacity" in html
    assert "style=" not in html
    assert 'data-state="warn"' not in html


def test_usage_bar_over_capacity_is_full_width_and_warns():
    html = render('{% usage_bar 120 100 "Disk" %}')

    assert '<rect width="100.0" height="4"/>' in html
    assert 'data-state="warn"' in html
    assert "Disk 120% of capacity" in html


@pytest.mark.parametrize("used, capacity", [(None, 100), (5, None), (5, 0)])
def test_usage_bar_is_empty_without_both_numbers(used, capacity):
    assert render("{% usage_bar used capacity %}", used=used, capacity=capacity) == ""


def test_negative_usage_draws_an_empty_bar():
    assert '<rect width="0.0" height="4"/>' in render("{% usage_bar -5 100 %}")
