"""This script creates Trello cards based on definitions"""

import argparse
import json
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from datetime import timezone
from pathlib import Path

import requests


def get_cards(
    defs: list[tuple[str, int | None, int | None, int | None, int | None, int | None]],
    target_date: date,
) -> list[tuple[str, date | None]]:
    """Get cards from definitions"""

    cards: list[tuple[str, date | None]] = []
    for name, year, month, day, weekday, due in defs:
        if year is not None and year != target_date.year:
            continue
        if month is not None and month != target_date.month:
            continue
        if day is not None and day != target_date.day:
            continue
        if weekday is not None and weekday != target_date.weekday():
            continue
        if due is None:
            cards.append((name, None))
        else:
            cards.append((name, target_date + timedelta(days=due)))

    return cards


def create_cards(
    cards: list[tuple[str, date | None]],
    list_id: str,
    api_key: str,
    token: str,
    *,
    timeout: int = 60,
    due_time: time = time(9, 0, 0),
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
            query["due"] = (
                datetime.combine(card_due, due_time)
                .astimezone(timezone.utc)
                .isoformat()
            )
        response = requests.post(url, params=query, timeout=timeout)
        if response.status_code != 200:
            raise RuntimeError(f"Couldn't create card {card_name}")


def parse_args() -> argparse.Namespace:
    """Parse CLI Arguments"""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "defs_filepath", type=Path, help="Path to a JSON file containing desired defs"
    )
    parser.add_argument("list_id", type=str, help="ID for target list")
    parser.add_argument(
        "secrets_filepath",
        type=Path,
        help="Path to a JSON file containing an API key aand a token",
    )

    return parser.parse_args()


def main() -> None:
    """CLI Entry Point"""

    args = parse_args()

    with args.defs_filepath.open(encoding="UTF-8") as defs_file:
        defs = json.load(defs_file)
    list_id = args.list_id
    with args.secrets_filepath.open(encoding="UTF-8") as secrets_file:
        secrets = json.load(secrets_file)
        api_key = secrets["api_key"]
        token = secrets["token"]

    cards = get_cards(defs, date.today())
    create_cards(cards, list_id, api_key, token)


if __name__ == "__main__":
    main()
