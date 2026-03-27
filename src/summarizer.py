import logging
from groq import Groq
from config.config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ArticleSummarizer:
    def __init__(self):
        self.client = Groq(api_key=Config.GROQ_API_KEY)
    
    def generate_daily_summary(self, articles):
        if not articles:
            return {
                'total_articles': 0,
                'top_stories': [],
                'overview': 'No articles collected today.',
                'all_articles': []
            }
        
        articles_text = self._prepare_articles_text(articles)
        
        prompt = f"""You are a news analyst. Analyze these {len(articles)} articles from Almayadeen news and provide:

1. Top 3-5 most important stories (based on significance and relevance)
2. A brief overview of main topics covered (2-3 sentences)
3. Be concise and professional

Articles:
{articles_text}

Respond in this format:
TOP STORIES:
1. [Story headline and why it's important]
2. [Story headline and why it's important]
...

OVERVIEW:
[2-3 sentence overview of main topics]
"""

        try:
            response = self.client.chat.completions.create(
                model=Config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "You are a professional news analyst specializing in Middle Eastern news."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=Config.MAX_TOKENS
            )
            
            ai_summary = response.choices[0].message.content
            parsed = self._parse_ai_summary(ai_summary)
            
            return {
                'total_articles': len(articles),
                'top_stories': parsed['top_stories'],
                'overview': parsed['overview'],
                'all_articles': articles
            }
            
        except Exception as e:
            logger.error(f"Error generating summary with Groq: {str(e)}")
            
            return {
                'total_articles': len(articles),
                'top_stories': [art['headline'] for art in articles[:5]],
                'overview': f"Collected {len(articles)} articles covering various topics.",
                'all_articles': articles
            }
    
    def _prepare_articles_text(self, articles):
        text_parts = []
        for idx, article in enumerate(articles[:20], 1):
            text_parts.append(
                f"{idx}. {article['headline']}\n   {article['summary'][:200]}\n"
            )
        return '\n'.join(text_parts)
    
    def _parse_ai_summary(self, ai_text):
        top_stories = []
        overview = ""
        
        try:
            sections = ai_text.split('OVERVIEW:')
            
            if len(sections) > 1:
                overview = sections[1].strip()
            
            top_section = sections[0].replace('TOP STORIES:', '').strip()
            lines = top_section.split('\n')
            
            for line in lines:
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-')):
                    story = line.lstrip('0123456789.-) ').strip()
                    if story:
                        top_stories.append(story)
            
        except Exception as e:
            logger.error(f"Error parsing AI summary: {str(e)}")
        
        return {
            'top_stories': top_stories,
            'overview': overview if overview else "Various news topics covered."
        }
