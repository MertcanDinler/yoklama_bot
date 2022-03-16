from pydoc import cli
from zoom_client import ZoomClient
import logging


if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.DEBUG)
    logger.debug("asdas")
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.DEBUG)
    logger.debug("asdas")
    client = ZoomClient()
    client.join_meeting("810 2345 8283", "12345678")
    client.loop()
    client.close()
