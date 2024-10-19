import os
import aiohttp
import asyncio
from polygon import RESTClient


async def writeImageBytesToFile(imageBytes):
    # Save image bytes to a file
    with open('downloaded_image.jpg', 'wb') as file:
        file.write(imageBytes)
    print('Image saved successfully.')

async def getPolygonImage(session, imageUrl):
    params = {"apiKey": os.environ.get('POLYGON_API_KEY')}
    async with session.get(imageUrl, params=params) as response:
        if response.status == 200:
            # Read image bytes
            imageBytes = await response.read()
            await writeImageBytesToFile(imageBytes)
        else:
            print(f'Failed to download image. Status code: {response.status}')


async def main():
    #client = RESTClient(api_key=os.environ.get("POLYGON_API_KEY"))
    client = RESTClient() # uses POLYGON_API_KEY
    session = aiohttp.ClientSession()
    #financials = client.get_ticker_details("TSN")
    # print(financials)
    # await getPolygonImage(session, financials.branding.icon_url)
    prevClose = client.get_previous_close_agg("TSN")
    print(prevClose)

    # for i, n in enumerate(client.list_ticker_news("TSN", limit=5)):
    #     print(i, n)
    #     if i == 5:
    #         break
    await session.close()

if __name__ == "__main__":
    asyncio.run(main())