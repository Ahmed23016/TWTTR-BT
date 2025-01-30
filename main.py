import asyncio
import os
import json
import logging
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from twikit import Client
from httpx import Timeout
from dotenv import load_dotenv
import sys

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
MAX_LOGIN_RETRIES = 3         


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
        logging.warning(f"Failed to load or validate cookies from {file_path}: {e}")
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

async def perform_login_with_retries(username, email, password, max_retries=MAX_LOGIN_RETRIES):

    for attempt in range(1, max_retries + 1):
        try:
            logging.info(f"Login attempt {attempt}...")
            print(f"🔑 Logging in to Twitter (Attempt {attempt})...")
            await client.login(
                auth_info_1=username,
                auth_info_2=email,
                password=password
            )
            await save_cookies(COOKIES_FILE)
            logging.info("Login successful and cookies saved.")
            print("✅ Login successful and cookies saved.")
            return True
        except Exception as e:
            logging.error(f"Login attempt {attempt} failed: {e}")
            print(f"⚠️ Login attempt {attempt} failed: {e}")
            if attempt < max_retries:
                wait_time = 2 ** attempt 
                print(f"⏳ Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                print("🔥 All login attempts failed. Exiting.")
    return False


app = FastAPI(
    title="Twitter Thread Search API",
    description="API to search Twitter threads based on a topic.",
    version="1.0.0"
)


class ThreadModel(BaseModel):
    thread_id: int
    tweets: List[str]

class SearchResponse(BaseModel):
    topic: str
    threads: List[ThreadModel]
    top_tweets: Optional[List[ThreadModel]] = None  


tweet_processor = TweetProcessor()

@app.on_event("startup")
async def startup_event():
    logging.info("Starting up the Twitter Backend API...")
    print("🚀 Starting up the Twitter Backend API...")
    login_success = await load_cookies(COOKIES_FILE)
    
    if not login_success:
        login_success = await perform_login_with_retries(USERNAME, EMAIL, PASSWORD)
        if not login_success:
            logging.critical("Failed to log in after multiple attempts.")
            print("🔥 Critical error: Failed to log in after multiple attempts.")
            sys.exit(1)

@app.post("/search", response_model=SearchResponse)
async def search_tweets(topic: str = Query(..., description="The topic to search for tweets.")):
  
    SEARCH_QUERY = topic  
    THREAD_EMOJI = '🧵'     

    logging.info(f"Received search request for topic: {topic}")
    print(f"🔍 Searching for tweets with topic: {topic}")

    try:
        tweets = await client.search_tweet(SEARCH_QUERY, 'Top')
        logging.info(f"🔍 Found {len(tweets)} potential tweets for topic: {topic}")
        print(f"🔍 Found {len(tweets)} potential tweets for topic: {topic}")
    except Exception as e:
        logging.error(f"Error during tweet search for topic '{topic}': {e}")
        raise HTTPException(status_code=500, detail=f"Error during tweet search: {e}")

    thread_starts = [tweet for tweet in tweets if THREAD_EMOJI in tweet.text]
    
    response_threads = []
    response_top_tweets = []

    if not thread_starts:
        logging.info(f"No threads found for topic '{topic}'.")
        print(f"❌ No threads found for topic '{topic}'.")
        top_tweets = tweets[:3]
        for idx, tweet in enumerate(top_tweets, 1):
            response_top_tweets.append(ThreadModel(thread_id=idx, tweets=[tweet.text]))
            logging.info(f"Top Tweet #{idx} - ID: {tweet.id}, User: {tweet.user.name}, Content: {tweet.text}")
        return SearchResponse(topic=topic, threads=[], top_tweets=response_top_tweets)

    logging.info(f"📌 Found {len(thread_starts)} tweets with thread emoji for topic '{topic}'.")
    print(f"📌 Found {len(thread_starts)} tweets with thread emoji for topic '{topic}'.")

    tasks = []
    for idx, tweet in enumerate(thread_starts, 1):
        logging.info(f"🧵 Found thread starter: {tweet.id}")
        print(f"🧵 Found thread starter: {tweet.id}")
        print(f"📝 Content: {tweet.text[:60]}...")
        logging.info(f"📝 Content: {tweet.text[:60]}...")
        self_thread = []
        tweet_processor.threads.append(self_thread)
        tasks.append(tweet_processor.process_thread(tweet.id, tweet.text))
    
    await asyncio.gather(*tasks)

    for idx, thread in enumerate(tweet_processor.threads[-len(thread_starts):], 1):
        response_threads.append(ThreadModel(thread_id=idx, tweets=thread))
    
    logging.info(f"📚 Collected {len(response_threads)} threads for topic '{topic}'.")
    print(f"📚 Collected {len(response_threads)} threads for topic '{topic}'.")

    return SearchResponse(topic=topic, threads=response_threads, top_tweets=None)
