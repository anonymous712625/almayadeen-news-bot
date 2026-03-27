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
        self.session.headers.update({
            'User-Agent': Config.USER_AGENT,
            'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8'
        })
        
    def generate_article_id(self, url):
        return hashlib.md5(url.encode()).hexdigest()
    
    def scrape_articles(self):
        articles = []
        
        try:
            logger.info(f"Fetching articles from {Config.NEWS_URL}")
            response = self.session.get(Config.NEWS_URL, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            article_elements = soup.find_all('article', limit=Config.MAX_ARTICLES_PER_RUN)
            
            if not article_elements:
                article_elements = soup.find_all('div', class_='news-item', limit=Config.MAX_ARTICLES_PER_RUN)
            
            if not article_elements:
                article_elements = soup.select('.article, .news-article, .post, .card', limit=Config.MAX_ARTICLES_PER_RUN)
            
            logger.info(f"Found {len(article_elements)} article elements")
            
            for idx, article in enumerate(article_elements):
                try:
                    article_data = self._extract_article_data(article)
                    if article_data:
                        articles.append(article_data)
                        logger.info(f"Extracted: {article_data['headline'][:50]}...")
                    
                    if idx < len(article_elements) - 1:
                        time.sleep(1)
                        
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
            headline_elem = (
                article_element.find('h2') or 
                article_element.find('h3') or 
                article_element.find('h1') or
                article_element.find('a', class_='title') or
                article_element.find(class_='article-title') or
                article_element.find(class_='headline')
            )
            
            if not headline_elem:
                return None
            
            headline = headline_elem.get_text(strip=True)
            
            link_elem = headline_elem.find('a') if headline_elem.name != 'a' else headline_elem
            if not link_elem:
                link_elem = article_element.find('a')
            
            if not link_elem:
                return None
                
            url = urljoin(Config.BASE_URL, link_elem.get('href', ''))
            
            time_elem = (
                article_element.find('time') or 
                article_element.find(class_='date') or
                article_element.find(class_='time') or
                article_element.find(class_='timestamp')
            )
            
            pub_time = time_elem.get_text(strip=True) if time_elem else "Recently"
            
            summary_elem = (
                article_element.find('p', class_='description') or
                article_element.find('p', class_='summary') or
                article_element.find('div', class_='excerpt') or
                article_element.find('p')
            )
            
            summary = summary_elem.get_text(strip=True) if summary_elem else ""
            
            if not summary or len(summary) < 50:
                summary = self._scrape_article_summary(url)
            
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
    
    def _scrape_article_summary(self, url):
        try:
            time.sleep(Config.REQUEST_DELAY)
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            content_elem = (
                soup.find('div', class_='article-content') or
                soup.find('div', class_='content') or
                soup.find('div', class_='entry-content') or
                soup.find('article')
            )
            
            if content_elem:
                paragraphs = content_elem.find_all('p', limit=3)
                summary = ' '.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
                return summary[:500]
                
        except Exception as e:
            logger.error(f"Error scraping article summary from {url}: {str(e)}")
        
        return "Summary not available."
    
    def _limit_to_sentences(self, text, num_sentences=3):
        if not text:
            return ""
        
        sentences = re.split(r'[.!?؟。]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        limited = '. '.join(sentences[:num_sentences])
        if limited and not limited.endswith('.'):
            limited += '.'
        
        return limited
