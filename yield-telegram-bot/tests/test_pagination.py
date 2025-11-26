"""
Тести для модуля пагінації.
"""

import pytest
from bot.utils.pagination import Paginator


def test_paginator_init():
    """Тест ініціалізації пагінатора."""
    items = list(range(100))
    paginator = Paginator(items, items_per_page=30)
    
    assert paginator.total_pages == 4
    assert paginator.items_per_page == 30
    assert len(paginator.items) == 100


def test_paginator_get_page():
    """Тест отримання сторінки."""
    items = list(range(100))
    paginator = Paginator(items, items_per_page=30)
    
    # Перша сторінка
    page1 = paginator.get_page(1)
    assert len(page1) == 30
    assert page1[0] == 0
    assert page1[-1] == 29
    
    # Друга сторінка
    page2 = paginator.get_page(2)
    assert len(page2) == 30
    assert page2[0] == 30
    assert page2[-1] == 59
    
    # Остання сторінка
    page4 = paginator.get_page(4)
    assert len(page4) == 10  # Залишок
    assert page4[0] == 90
    assert page4[-1] == 99


def test_paginator_empty_list():
    """Тест пагінатора з порожнім списком."""
    paginator = Paginator([], items_per_page=30)
    
    assert paginator.total_pages == 0
    assert paginator.get_page(1) == []


def test_paginator_invalid_page():
    """Тест неіснуючої сторінки."""
    items = list(range(100))
    paginator = Paginator(items, items_per_page=30)
    
    # Сторінка 0
    assert paginator.get_page(0) == []
    
    # Сторінка більше total_pages
    assert paginator.get_page(10) == []


def test_paginator_has_next_prev():
    """Тест перевірки наявності наступної/попередньої сторінки."""
    items = list(range(100))
    paginator = Paginator(items, items_per_page=30)
    
    # Перша сторінка
    assert not paginator.has_prev_page(1)
    assert paginator.has_next_page(1)
    
    # Друга сторінка
    assert paginator.has_prev_page(2)
    assert paginator.has_next_page(2)
    
    # Остання сторінка
    assert paginator.has_prev_page(4)
    assert not paginator.has_next_page(4)


def test_paginator_max_items_per_page():
    """Тест обмеження items_per_page до 30."""
    items = list(range(100))
    paginator = Paginator(items, items_per_page=50)
    
    # Має автоматично обмежитись до 30
    assert paginator.items_per_page == 30

