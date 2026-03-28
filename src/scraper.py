import requests
import feedparser
import logging
from datetime import datetime
from config.config import Config
import hashlib
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AlmayadeenScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8',
        })
        
    def generate_article_id(self, url):
        return hashlib.md5(url.encode()).hexdigest()
    
    def scrape_articles(self):
        articles = []
        
        # Al-Manar RSS feeds
        rss_feeds = [
            'https://almanar.com.lb/rss',
            'https://www.almanar.com.lb/rss/news',
            'https://english.almanar.com.lb/rss',
        ]
        
        for feed_url in rss_feeds:
            try:
                logger.info(f"Fetching RSS feed from {feed_url}")
                
                response = self.session.get(feed_url, timeout=20, verify=True)
                
                logger.info(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    logger.info(f"✅ Successfully accessed {feed_url}")
                    
                    # Parse RSS feed
                    feed = feedparser.parse(response.content)
                    
                    logger.info(f"Found {len(feed.entries)} entries in feed")
                    
                    for entry in feed.entries[:Config.MAX_ARTICLES_PER_RUN]:
                        try:
                            article_data = self._extract_from_rss_entry(entry)
                            if article_data:
                                articles.append(article_data)
                                logger.info(f"Extracted: {article_data['headline'][:50]}...")
                        except Exception as e:
                            logger.error(f"Error extracting entry: {str(e)}")
                            continue
                    
                    # If we got articles, stop trying other feeds
                    if articles:
                        break
                else:
                    logger.warning(f"Status {response.status_code} for {feed_url}")
                    
            except Exception as e:
                logger.error(f"Error fetching {feed_url}: {str(e)}")
                continue
        
        # Remove duplicates
        unique_articles = []
        seen_ids = set()
        
        for article in articles:
            if article['id'] not in seen_ids:
                unique_articles.append(article)
                seen_ids.add(article['id'])
        
        logger.info(f"Successfully scraped {len(unique_articles)} unique articles")
        
        return unique_articles
    
    def _extract_from_rss_entry(self, entry):
        try:
            headline = entry.get('title', 'No title').strip()
            url = entry.get('link', '').strip()
            
            if not url or not headline:
                return None
            
            # Get publication time
            pub_time = "Recently"
            if hasattr(entry, 'published'):
                pub_time = entry.published
            elif hasattr(entry, 'updated'):
                pub_time = entry.updated
            elif hasattr(entry, 'published_parsed'):
                from time import strftime
                pub_time = strftime('%Y-%m-%d %H:%M', entry.published_parsed)
            
            # Get summary
            summary = ""
            if hasattr(entry, 'summary'):
                summary = entry.summary
            elif hasattr(entry, 'description'):
                summary = entry.description
            elif hasattr(entry, 'content'):
                summary = entry.content[0].value if entry.content else ""
            
            # Clean HTML tags from summary
            summary = re.sub(r'<[^>]+>', '', summary)
            summary = summary.strip()
            
            # Remove extra whitespace
            summary = ' '.join(summary.split())
            
            if not summary or len(summary) < 20:
                summary = f"Al-Manar News: {headline}"
            
            # Limit to 500 chars
            summary = summary[:500]
            
            # Limit to 3 sentences
            sentences = re.split(r'[.!?؟。]+', summary)
            sentences = [s.strip() for s in sentences if s.strip()]
            summary = '. '.join(sentences[:3])
            
            if summary and not summary.endswith('.'):
                summary += '.'
            
            article_id = self.generate_article_id(url)
            
            return {
                'id': article_id,
                'headline': headline,
                'url': url,
                'pub_time': pub_time,
                'summary': summary,
                'scraped_at': datetime.now(Config.TIMEZONE).isoformat(),
                'date': Config.get_current_date()
            }
            
        except Exception as e:
            logger.error(f"Error parsing RSS entry: {str(e)}")
            return None
