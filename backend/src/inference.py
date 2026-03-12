from __future__ import annotations

import argparse
import json

from prediction_service import predict_single_player


def main() -> None:
    parser = argparse.ArgumentParser(description="CLI prediction for a single NBA player prop context")
    parser.add_argument("player")
    parser.add_argument("--opponent")
    parser.add_argument("--is-home", type=int, choices=[0, 1])
    parser.add_argument("--rest-days", type=int)
    parser.add_argument("--season")
    args = parser.parse_args()

    payload = predict_single_player(
        player_name=args.player,
        opponent=args.opponent,
        is_home=args.is_home,
        rest_days=args.rest_days,
        season=args.season,
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
