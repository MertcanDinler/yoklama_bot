from os import path

SCRIPTH_PATH: str = path.join(path.dirname(
    path.abspath(__file__)))
DRIVER_CACHE_PATH: str = path.join(SCRIPTH_PATH, "drivers")
