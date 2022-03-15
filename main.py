from zoom_client import ZoomClient


client = ZoomClient()
client.join_meeting("810 2345 8283", "12345678")
input("Enter")
client.close()
