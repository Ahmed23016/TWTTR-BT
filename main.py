import asyncio
from twikit import Client
from tabulate import tabulate

USERNAME = 'bruv911317'
EMAIL = 'oblcinar911@gmail.com'
PASSWORD = 'Wekker2001!'

client = Client('en-US')

async def main():
    await client.login(
        auth_info_1=USERNAME,
        auth_info_2=EMAIL,
        password=PASSWORD
    )


    tweets = await client.search_tweet('Hawk Tuah Scam', 'Top')

    for i in tweets:
        if i.user.name=="0xDarya💎":
            tweet = await client.get_tweet_by_id(i.id)
            replies = tweet.replies
            for reply in replies:
                print(f"{reply.user.name}: {reply.text}")
asyncio.run(main())
