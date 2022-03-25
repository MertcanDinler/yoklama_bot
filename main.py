from pydoc import cli
from zoom_client import ZoomClient
import logging


if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.CRITICAL)
    logger.debug("asdas")
    client = ZoomClient()
    client.join_meeting("865 9239 5184", "12345676")
    client.loop()
    client.close()
