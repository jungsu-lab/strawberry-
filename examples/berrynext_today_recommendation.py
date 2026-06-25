# /// script
# dependencies = []
# ///
# How to run:
#   python3 -m examples.berrynext_today_recommendation

from libsbapi.offline_demo import BerryNextOfflineDemo, build_demo, format_demo, main


__all__ = ["BerryNextOfflineDemo", "build_demo", "format_demo", "main"]


if __name__ == "__main__":
    main()
