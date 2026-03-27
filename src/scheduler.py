import json
import os
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from config.config import Config
from src.scraper import AlmayadeenScraper
from src.summarizer import ArticleSummarizer
from src.telegram_bot import TelegramNotifier

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NewsScheduler:
    def __init__(self):
        self.scraper = AlmayadeenScraper()
        self.summarizer = ArticleSummarizer()
        self.notifier = TelegramNotifier()
        self.scheduler = BackgroundScheduler(timezone=Config.TIMEZONE)
        self.articles_db = self._load_articles_db()
        
    def _load_articles_db(self):
        os.makedirs('data', exist_ok=True)
        
        if os.path.exists(Config.ARTICLES_DB):
            try:
                with open(Config.ARTICLES_DB, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading articles DB: {str(e)}")
                return {}
        return {}
    
    def _save_articles_db(self):
        try:
            with open(Config.ARTICLES_DB, 'w', encoding='utf-8') as f:
                json.dump(self.articles_db, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving articles DB: {str(e)}")
    
    def scrape_and_notify(self):
        logger.info("Starting scheduled scraping...")
        
        try:
            articles = self.scraper.scrape_articles()
            
            current_date = Config.get_current_date()
            
            if current_date not in self.articles_db:
                self.articles_db[current_date] = []
            
            existing_ids = {art['id'] for art in self.articles_db[current_date]}
            
            new_articles = []
            
            for article in articles:
                if article['id'] not in existing_ids:
                    self.articles_db[current_date].append(article)
                    new_articles.append(article)
                    existing_ids.add(article['id'])
            
            logger.info(f"Found {len(new_articles)} new articles")
            
            for article in new_articles:
                try:
                    self.notifier.send_article_sync(article)
                except Exception as e:
                    logger.error(f"Error sending notification: {str(e)}")
            
            self._save_articles_db()
            self._cleanup_old_articles()
            
        except Exception as e:
            logger.error(f"Error in scrape_and_notify: {str(e)}")
    
    def send_daily_summary(self):
        logger.info("Generating daily summary...")
        
        try:
            current_date = Config.get_current_date()
            today_articles = self.articles_db.get(current_date, [])
            
            if not today_articles:
                logger.warning("No articles found for today")
                return
            
            summary_data = self.summarizer.generate_daily_summary(today_articles)
            self.notifier.send_daily_summary_sync(summary_data)
            
            logger.info(f"Daily summary sent: {summary_data['total_articles']} articles")
            
        except Exception as e:
            logger.error(f"Error in send_daily_summary: {str(e)}")
    
    def _cleanup_old_articles(self):
        try:
            cutoff_date = (datetime.now(Config.TIMEZONE) - timedelta(days=7)).strftime("%Y-%m-%d")
            
            dates_to_remove = [date for date in self.articles_db.keys() if date < cutoff_date]
            
            for date in dates_to_remove:
                del self.articles_db[date]
                logger.info(f"Removed old articles from {date}")
            
            if dates_to_remove:
                self._save_articles_db()
                
        except Exception as e:
            logger.error(f"Error cleaning up old articles: {str(e)}")
    
    def start(self):
        logger.info("Starting News Scheduler...")
        
        self.scheduler.add_job(
            self.scrape_and_notify,
            trigger=IntervalTrigger(minutes=Config.SCRAPE_INTERVAL),
            id='scrape_job',
            name='Scrape Almayadeen News',
            replace_existing=True
        )
        
        hour, minute = Config.SUMMARY_TIME.split(':')
        self.scheduler.add_job(
            self.send_daily_summary,
            trigger=CronTrigger(hour=int(hour), minute=int(minute)),
            id='summary_job',
            name='Send Daily Summary',
            replace_existing=True
        )
        
        self.scrape_and_notify()
        self.scheduler.start()
        logger.info("Scheduler started successfully")
        
        return self.scheduler
