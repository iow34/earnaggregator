import pytest
from bot.utils.pagination import Paginator


def test_paginator_init():
    items = list(range(100))
    paginator = Paginator(items, items_per_page=30)

    assert paginator.total_pages == 4
    assert paginator.items_per_page == 30
    assert len(paginator.items) == 100


def test_paginator_get_page():
    items = list(range(100))
    paginator = Paginator(items, items_per_page=30)

    page1 = paginator.get_page(1)
    assert len(page1) == 30
    assert page1[0] == 0
    assert page1[-1] == 29

    page2 = paginator.get_page(2)
    assert len(page2) == 30
    assert page2[0] == 30
    assert page2[-1] == 59

    page4 = paginator.get_page(4)
    assert len(page4) == 10
    assert page4[0] == 90
    assert page4[-1] == 99


def test_paginator_empty_list():
    paginator = Paginator([], items_per_page=30)

    assert paginator.total_pages == 0
    assert paginator.get_page(1) == []


def test_paginator_invalid_page():
    items = list(range(100))
    paginator = Paginator(items, items_per_page=30)

    assert paginator.get_page(0) == []

    assert paginator.get_page(10) == []


def test_paginator_has_next_prev():
    items = list(range(100))
    paginator = Paginator(items, items_per_page=30)

    assert not paginator.has_prev_page(1)
    assert paginator.has_next_page(1)

    assert paginator.has_prev_page(2)
    assert paginator.has_next_page(2)

    assert paginator.has_prev_page(4)
    assert not paginator.has_next_page(4)


def test_paginator_max_items_per_page():
    items = list(range(100))
    paginator = Paginator(items, items_per_page=100)

    assert paginator.items_per_page == 60
