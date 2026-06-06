"""ThingHound desktop UI app entrypoint."""


import argparse
from pathlib import Path

from thinghound.ui.bridge import Bridge


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run ThingHound desktop shell")
    parser.add_argument("--mock", action="store_true", help="Run bridge in mock-data mode")
    return parser


def main() -> int:
    """Start the desktop shell with a bound bridge."""
    args = _build_parser().parse_args()

    import webview

    bridge = Bridge(mock=args.mock)
    entrypoint = (Path(__file__).resolve().parents[3] / "ui" / "dist" / "index.html").as_uri()
    window = webview.create_window("ThingHound", url=entrypoint, js_api=bridge)
    webview.start(debug=args.mock)
    return 0 if window is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
