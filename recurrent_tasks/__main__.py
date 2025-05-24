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
    year: int | None
    month: int | None
    day: int | None
    weekday: int | None
    due_in: int | None


def get_cards(
    rules: list[Rule], evaluation_date: date, *, due_time: time = time(9, 0, 0)
) -> list[tuple[str, datetime | None]]:
    """Get cards from rules at an evaluation date"""

    cards: list[tuple[str, datetime | None]] = []
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

        cards.append((rule.card_name, card_due))

    return cards


def create_cards(
    cards: list[tuple[str, datetime | None]],
    list_id: str,
    api_key: str,
    token: str,
    *,
    timeout: int = 60,
) -> None:
    """Create cards from a list if they don't already exist"""

    url = f"https://api.trello.com/1/lists/{list_id}/cards"
    query = {"key": api_key, "token": token}
    response = requests.get(url, params=query, timeout=timeout)
    if response.status_code != 200:
        raise RuntimeError("Couldn't get card list")
    current_card_names = [card["name"] for card in response.json()]

    url = "https://api.trello.com/1/cards"
    for card_name, card_due in cards:
        if card_name in current_card_names:
            continue
        query = {
            "idList": list_id,
            "name": card_name,
            "key": api_key,
            "token": token,
        }
        if card_due is not None:
            query["due"] = card_due.astimezone(timezone.utc).isoformat()
        response = requests.post(url, params=query, timeout=timeout)
        if response.status_code != 200:
            raise RuntimeError(f"Couldn't create card {card_name}")


def parse_args() -> argparse.Namespace:
    """Parse CLI Arguments"""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "rules_filepath", type=Path, help="Path to a JSON file containing rules"
    )
    parser.add_argument("list_id", type=str, help="ID of target list")
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
    list_id = args.list_id
    with args.secrets_filepath.open(encoding="UTF-8") as secrets_file:
        secrets = json.load(secrets_file)
        api_key = secrets["api_key"]
        token = secrets["token"]

    cards = get_cards(rules, date.today())
    create_cards(cards, list_id, api_key, token)


if __name__ == "__main__":
    main()
