"""This script creates Trello cards based on definitions"""

import argparse
import json
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from datetime import timezone
from pathlib import Path

import requests


@dataclass
class Rule:
    """A rule for creating a recurrent task"""

    card_name: str
    list_id: str
    year: int | None
    month: int | None
    day: int | None
    weekday: int | None
    due_in: int | None


@dataclass
class Card:
    """A Trello Card"""

    name: str
    list_id: str
    due: datetime | None = None


def get_cards(
    rules: list[Rule], evaluation_date: date, *, due_time: time = time(9, 0, 0)
) -> list[Card]:
    """Get cards from rules at an evaluation date"""

    cards: list[Card] = []
    for rule in rules:
        if rule.year is not None and rule.year != evaluation_date.year:
            continue
        if rule.month is not None and rule.month != evaluation_date.month:
            continue
        if rule.day is not None and rule.day != evaluation_date.day:
            continue
        if rule.weekday is not None and rule.weekday != evaluation_date.weekday():
            continue

        card_due = (
            None
            if rule.due_in is None
            else datetime.combine(
                evaluation_date + timedelta(days=rule.due_in), due_time
            )
        )

        cards.append(Card(rule.card_name, rule.list_id, card_due))

    return cards


def create_cards(
    cards: list[Card],
    api_key: str,
    token: str,
    *,
    timeout: int = 60,
) -> None:
    """Create cards from a list if they don't already exist"""

    current_card_names = {}
    for list_id in set(card.list_id for card in cards):
        url = f"https://api.trello.com/1/lists/{list_id}/cards"
        query = {"key": api_key, "token": token}
        response = requests.get(url, params=query, timeout=timeout)
        if response.status_code != 200:
            raise RuntimeError(f"Couldn't get card lista for {list_id}")
        current_card_names[list_id] = [card["name"] for card in response.json()]

    url = "https://api.trello.com/1/cards"
    for card in cards:
        if card.name in current_card_names:
            continue
        query = {
            "idList": card.list_id,
            "name": card.name,
            "key": api_key,
            "token": token,
        }
        if card.due is not None:
            query["due"] = card.due.astimezone(timezone.utc).isoformat()
        response = requests.post(url, params=query, timeout=timeout)
        if response.status_code != 200:
            raise RuntimeError(f"Couldn't create card {card}")


def parse_args() -> argparse.Namespace:
    """Parse CLI Arguments"""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "rules_filepath", type=Path, help="Path to a JSON file containing rules"
    )
    parser.add_argument(
        "secrets_filepath",
        type=Path,
        help="Path to a JSON file containing an API key and a token",
    )

    return parser.parse_args()


def main() -> None:
    """CLI Entry Point"""

    args = parse_args()

    with args.rules_filepath.open(encoding="UTF-8") as rules_file:
        rules = [Rule(**rule) for rule in json.load(rules_file)]
    with args.secrets_filepath.open(encoding="UTF-8") as secrets_file:
        secrets = json.load(secrets_file)
        api_key = secrets["api_key"]
        token = secrets["token"]

    cards = get_cards(rules, date.today())
    create_cards(cards, api_key, token)


if __name__ == "__main__":
    main()
