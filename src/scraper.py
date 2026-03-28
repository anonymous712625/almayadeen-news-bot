import requests
from bs4 import BeautifulSoup
import time
import logging
from datetime import datetime
from config.config import Config
from urllib.parse import urljoin
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
        # Better headers to look like real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.google.com/'
        })
        
    def generate_article_id(self, url):
        return hashlib.md5(url.encode()).hexdigest()
    
    def scrape_articles(self):
        articles = []
        
        try:
            logger.info(f"Fetching articles from {Config.NEWS_URL}")
            
            # Add delay before request
            time.sleep(2)
            
            response = self.session.get(
                Config.NEWS_URL, 
                timeout=20,
                allow_redirects=True
            )
            
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 403:
                logger.error("403 Forbidden - Website is blocking us")
                # Try alternative URL
                alt_url = "https://www.almayadeen.net/news/politics"
                logger.info(f"Trying alternative URL: {alt_url}")
                time.sleep(3)
                response = self.session.get(alt_url, timeout=20)
            
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Multiple selectors
            article_elements = soup.find_all('article', limit=Config.MAX_ARTICLES_PER_RUN)
            
            if not article_elements:
                article_elements = soup.find_all('div', class_='article-card', limit=Config.MAX_ARTICLES_PER_RUN)
            
            if not article_elements:
                article_elements = soup.find_all('div', class_='news-item', limit=Config.MAX_ARTICLES_PER_RUN)
            
            if not article_elements:
                # Try finding any links with article pattern
                article_elements = soup.find_all('a', href=re.compile(r'/news/'), limit=Config.MAX_ARTICLES_PER_RUN)
            
            logger.info(f"Found {len(article_elements)} article elements")
            
            for idx, article in enumerate(article_elements):
                try:
                    article_data = self._extract_article_data(article)
                    if article_data:
                        articles.append(article_data)
                        logger.info(f"Extracted: {article_data['headline'][:50]}...")
                    
                    if idx < len(article_elements) - 1:
                        time.sleep(2)
                        
                except Exception as e:
                    logger.error(f"Error extracting article {idx}: {str(e)}")
                    continue
            
            logger.info(f"Successfully scraped {len(articles)} articles")
            
        except requests.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Scraping error: {str(e)}")
        
        return articles
    
    def _extract_article_data(self, article_element):
        try:
            # Find headline
            headline_elem = (
                article_element.find('h2') or 
                article_element.find('h3') or 
                article_element.find('h1') or
                article_element.find('a', class_='title') or
                article_element.find(class_='article-title') or
                article_element.find(class_='headline')
            )
            
            # If element IS an 'a' tag
            if article_element.name == 'a':
                headline = article_element.get_text(strip=True)
                link_elem = article_element
            elif not headline_elem:
                return None
            else:
                headline = headline_elem.get_text(strip=True)
                link_elem = headline_elem.find('a') if headline_elem.name != 'a' else headline_elem
            
            if not headline:
                return None
            
            if not link_elem:
                link_elem = article_element.find('a')
            
            if not link_elem:
                return None
                
            url = urljoin(Config.BASE_URL, link_elem.get('href', ''))
            
            # Skip if not a valid article URL
            if '/news/' not in url:
                return None
            
            # Find time
            time_elem = (
                article_element.find('time') or 
                article_element.find(class_='date') or
                article_element.find(class_='time') or
                article_element.find(class_='timestamp')
            )
            
            pub_time = time_elem.get_text(strip=True) if time_elem else "Recently"
            
            # Find summary
            summary_elem = (
                article_element.find('p', class_='description') or
                article_element.find('p', class_='summary') or
                article_element.find('div', class_='excerpt') or
                article_element.find('p')
            )
            
            summary = summary_elem.get_text(strip=True) if summary_elem else ""
            
            if not summary or len(summary) < 30:
                summary = f"News article from Almayadeen: {headline}"
            
            summary = self._limit_to_sentences(summary, 3)
            
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
            logger.error(f"Error extracting article data: {str(e)}")
            return None
    
    def _limit_to_sentences(self, text, num_sentences=3):
        if not text:
            return ""
        
        sentences = re.split(r'[.!?؟。]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        limited = '. '.join(sentences[:num_sentences])
        if limited and not limited.endswith('.'):
            limited += '.'
        
        return limited
