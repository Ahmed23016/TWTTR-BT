import asyncio
import os
import json
import logging
from twikit import Client
from httpx import Timeout
from dotenv import load_dotenv

logging.basicConfig(
    filename='twitter_bot.log', 
    filemode='a',                
    format='%(asctime)s - %(levelname)s - %(message)s',  
    level=logging.INFO           
)

load_dotenv()

USERNAME = os.getenv("TWITTER_USERNAME")
EMAIL = os.getenv("TWITTER_EMAIL")
PASSWORD = os.getenv("TWITTER_PASSWORD")
SEARCH_QUERY = 'Suicide Drive Thru'
THREAD_EMOJI = '🧵'
COOKIES_FILE = "cookies.json"  

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
        self.threads = []  
        self.processed_ids = set()
        self.lock = asyncio.Lock()

    async def get_replies(self, tweet_id):
        try:
            tweet = await client.get_tweet_by_id(tweet_id)
            return tweet.replies
        except Exception as e:
            logging.error(f"Error fetching replies for {tweet_id}: {e}")
            return []

    async def process_thread(self, tweet_id, original_text):
        if tweet_id in self.processed_ids:
            return
        self.processed_ids.add(tweet_id)

        try:
            async with self.lock:
                if not self.threads or original_text not in self.threads[-1]:
                    self.threads.append([original_text])

            replies = await self.get_replies(tweet_id)
            parent_tweet = await client.get_tweet_by_id(tweet_id)
            
            tasks = []
            for reply in replies[:15]:
                if reply.user.id == parent_tweet.user.id:
                    async with self.lock:
                        if reply.text not in self.threads[-1]:
                            self.threads[-1].append(reply.text)
                    tasks.append(self.process_thread(reply.id, reply.text))
            
            if tasks:
                await asyncio.gather(*tasks)
            
        except Exception as e:
            logging.error(f"Error processing {tweet_id}: {e}")

async def load_cookies(file_path):
  
    if not os.path.exists(file_path):
        logging.info(f"No cookies file found at {file_path}.")
        return False
    try:
        with open(file_path, 'r') as f:
            cookies = json.load(f)
            client.set_cookies(cookies)
        user = await client.user()
        logging.info(f"Loaded cookies successfully. Logged in as {user.name} (@{user.screen_name}).")
        print(f"✅ Logged in as {user.name} (@{user.screen_name})")
        return True
    except Exception as e:
        logging.warning(f"Failed to load cookies from {file_path}: {e}")
        print(f"Failed to load cookies: {e}")
        return False

async def save_cookies(file_path):
    try:
        cookies = client.get_cookies()
        with open(file_path, 'w') as f:
            json.dump(cookies, f)
        logging.info(f"Cookies saved successfully to {file_path}.")
    except Exception as e:
        logging.error(f"Failed to save cookies to {file_path}: {e}")

async def main():
    processor = TweetProcessor()
    
    try:
        login_success = await load_cookies(COOKIES_FILE)
        
        if not login_success:
            logging.info("Attempting to log in...")
            print("🔑 Logging in to Twitter...")
            await client.login(
                auth_info_1=USERNAME,
                auth_info_2=EMAIL,
                password=PASSWORD
            )
            await save_cookies(COOKIES_FILE)
            logging.info("Login successful and cookies saved.")
            print("✅ Login successful and cookies saved.")
        else:
            print("✅ Loaded existing session from cookies.")

        print("🚀 Starting search for thread emoji tweets...")
        logging.info("Starting search for thread emoji tweets...")
        tweets = await client.search_tweet(SEARCH_QUERY, 'Top')
        print(f"🔍 Found {len(tweets)} potential tweets")
        logging.info(f"🔍 Found {len(tweets)} potential tweets")

        thread_starts = [tweet for tweet in tweets if THREAD_EMOJI in tweet.text]
        
        if not thread_starts:
            print("\n❌ No threads found. Showing top 3 tweets:")
            logging.info("No threads found. Displaying top 3 tweets.")
            top_tweets = tweets[:3]  
            for idx, tweet in enumerate(top_tweets, 1):
                print(f"\n📌 Top Tweet #{idx}")
                print(f"🆔 ID: {tweet.id}")
                print(f"👤 User: {tweet.user.name} (@{tweet.user.screen_name})")
                print(f"📝 Content:\n{tweet.text}")
                print("-" * 80)
                logging.info(f"Top Tweet #{idx} - ID: {tweet.id}, User: {tweet.user.name}, Content: {tweet.text}")
            return

        print(f"📌 Found {len(thread_starts)} tweets with thread emoji")
        logging.info(f"📌 Found {len(thread_starts)} tweets with thread emoji")

        tasks = []
        for tweet in thread_starts:
            print(f"\n🧵 Found thread starter: {tweet.id}")
            logging.info(f"🧵 Found thread starter: {tweet.id}")
            print(f"📝 Content: {tweet.text[:60]}...")
            logging.info(f"📝 Content: {tweet.text[:60]}...")
            self_thread = []  
            processor.threads.append(self_thread)
            tasks.append(processor.process_thread(tweet.id, tweet.text))
        
        await asyncio.gather(*tasks)

        print("\n📚 Collected Threads:")
        logging.info("📚 Collected Threads:")
        for idx, thread in enumerate(processor.threads, 1):
            print(f"\n📖 Thread #{idx} (Length: {len(thread)} tweets)")
            logging.info(f"📖 Thread #{idx} (Length: {len(thread)} tweets)")
            for tweet_idx, text in enumerate(thread, 1):
                print(f"{tweet_idx}. {text}")
                print("-" * 80)
                logging.info(f"{tweet_idx}. {text}")

    except Exception as e:
        print(f"🔥 Critical error: {str(e)}")
        logging.critical(f"Critical error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
