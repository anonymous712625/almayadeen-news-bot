import os
from datetime import datetime
import pytz

class Config:
    TELEGRAM_BOT_TOKEN = "8784262536:AAFFCFumI7m5hnlmj2uajqyRC76C4OhonQ8"
    TELEGRAM_CHAT_ID = "7574027479"
    GROQ_API_KEY = "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"
    
    BASE_URL = "https://www.almayadeen.net"
    NEWS_URL = "https://www.almayadeen.net/news"
    
    REQUEST_DELAY = 3
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    MAX_ARTICLES_PER_RUN = 20
    
    TIMEZONE = pytz.timezone('Asia/Beirut')
    SUMMARY_TIME = "23:55"
    SCRAPE_INTERVAL = 30
    
    ARTICLES_DB = "data/articles.json"
    LOG_FILE = "logs/bot.log"
    
    GROQ_MODEL = "llama-3.1-70b-versatile"
    MAX_TOKENS = 500
    
    @staticmethod
    def get_current_date():
        return datetime.now(Config.TIMEZONE).strftime("%Y-%m-%d")
