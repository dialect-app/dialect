# Copyright 2024 Mufeed Ali
# Copyright 2024 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later


def find_item_match(list1: list[str], list2: list[str]) -> str | None:
    """
    Get the first occurrence in two lists.

    Args:
        list1: List to iterate
        list2: List to check against
    """
    list2 = set(list2)
    return next((i for i in list1 if i in list2), None)


def first_exclude(list_: list[str], exclude: str) -> str | None:
    """
    Get the first item that is not excluded.

    Args:
        list_: List of items
        exclude: Item to ignore
    """
    return next((x for x in list_ if x != exclude), None)
