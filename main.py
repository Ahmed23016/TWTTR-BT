import asyncio
from twikit import Client
from httpx import Timeout
from dotenv import main
import os
from functools import lru_cache

load_dotenv()

USERNAME = os.getenv("TWITTER_USERNAME")
EMAIL = os.getenv("TWITTER_EMAIL")
PASSWORD = os.getenv("TWITTER_PASSWORD")
SEARCH_QUERY = 'Hawk Tuah Scam'
TARGET_USER = "0xDarya💎"

client = Client('en-US')
client.http = client.http.__class__(
    headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Content-Type': 'application/json',
        'Origin': 'https://x.com',
        'Referer': 'https://x.com/',
        'DNT': '1'
    },
    timeout=Timeout(45.0)
)

class TweetProcessor:
    def __init__(self):
        self.thread = []
        self.lock = asyncio.Lock()
        self.processed_ids = set()

    async def get_replies(self, tweet_id):
        try:
            tweet = await client.get_tweet_by_id(tweet_id)
            return tweet.replies
        except Exception as e:
            print(f"Error fetching replies for {tweet_id}: {str(e)}")
            return []

    async def process_replies(self, tweet_id):
        if tweet_id in self.processed_ids:
            return
        self.processed_ids.add(tweet_id)

        try:
            replies = await self.get_replies(tweet_id)
            parent_tweet = await client.get_tweet_by_id(tweet_id)
            
            tasks = []
            for reply in replies[:10]: 
                if reply.user.id == parent_tweet.user.id:
                    async with self.lock:
                        if reply.text not in self.thread:
                            self.thread.append(reply.text)
                    tasks.append(self.process_replies(reply.id))
            
            await asyncio.gather(*tasks)
            
        except Exception as e:
            print(f"Error processing {tweet_id}: {str(e)}")

async def main():
    processor = TweetProcessor()
    
    try:
        await client.login(
            auth_info_1=USERNAME,
            auth_info_2=EMAIL,
            password=PASSWORD
        )

        print("🚀 Starting search...")
        tweets = await client.search_tweet(SEARCH_QUERY, 'Top')
        print(f"🔍 Found {len(tweets)} potential tweets")

        tasks = []
        for tweet in tweets:
            if tweet.user.name == TARGET_USER:
                print(f"🎯 Found target tweet: {tweet.id}")
                processor.thread.append(tweet.text)
                tasks.append(processor.process_replies(tweet.id))
        
        await asyncio.gather(*tasks)

        print("\n📜 Final Thread:")
        for idx, text in enumerate(processor.thread, 1):
            print(f"{idx}. {text}")
            print("-" * 80)

    except Exception as e:
        print(f"🔥 Critical error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())