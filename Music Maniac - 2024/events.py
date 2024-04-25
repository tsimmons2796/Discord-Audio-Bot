import logging

def setup_events(client):
    @client.event
    async def on_ready():
        logging.info(f'{client.user} is now connected and ready.')
