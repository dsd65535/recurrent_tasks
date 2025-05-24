"""This script is the start of the recurrent tasks functionality"""

import argparse
import json
from datetime import datetime
from datetime import timezone
from pathlib import Path

import requests


def create_cards(
    cards: list[tuple[str, datetime]],
    list_id: str,
    api_key: str,
    token: str,
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
            "due": card_due.astimezone(timezone.utc).isoformat(),
            "key": api_key,
            "token": token,
        }
        response = requests.post(url, params=query, timeout=timeout)
        if response.status_code != 200:
            raise RuntimeError(f"Couldn't create card {card_name}")


def parse_args() -> argparse.Namespace:
    """Parse CLI Arguments"""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "cards_filepath", type=Path, help="Path to a JSON file containing desired cards"
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

    with args.cards_filepath.open(encoding="UTF-8") as cards_file:
        cards = [
            (card_name, datetime.fromisoformat(card_due))
            for card_name, card_due in json.load(cards_file)
        ]
    list_id = args.list_id
    with args.secrets_filepath.open(encoding="UTF-8") as secrets_file:
        secrets = json.load(secrets_file)
        api_key = secrets["api_key"]
        token = secrets["token"]

    create_cards(cards, list_id, api_key, token)


if __name__ == "__main__":
    main()
