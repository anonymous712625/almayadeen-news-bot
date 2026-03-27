import logging
from telegram import Bot
from telegram.constants import ParseMode
from config.config import Config
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self):
        self.bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
        self.chat_id = Config.TELEGRAM_CHAT_ID
    
    async def send_article(self, article):
        try:
            message = self._format_article_message(article)
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=False
            )
            
            logger.info(f"Sent article: {article['headline'][:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Error sending article: {str(e)}")
            return False
    
    async def send_daily_summary(self, summary_data):
        try:
            message = self._format_daily_summary(summary_data)
            
            if len(message) > 4000:
                messages = self._split_message(message)
                for msg in messages:
                    await self.bot.send_message(
                        chat_id=self.chat_id,
                        text=msg,
                        parse_mode=ParseMode.MARKDOWN,
                        disable_web_page_preview=True
                    )
                    await asyncio.sleep(1)
            else:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
            
            logger.info("Daily summary sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error sending daily summary: {str(e)}")
            return False
    
    def _format_article_message(self, article):
        headline = self._escape_markdown(article['headline'])
        summary = self._escape_markdown(article['summary'][:300])
        
        message = f"""📰 *New Article Alert*

*{headline}*

⏰ {article['pub_time']}

📝 {summary}

🔗 [Read Full Article]({article['url']})
"""
        return message
    
    def _format_daily_summary(self, summary_data):
        date = Config.get_current_date()
        total = summary_data['total_articles']
        
        message = f"""📊 *Daily News Summary - {date}*
━━━━━━━━━━━━━━━━━━━━

📈 *Total Articles:* {total}

"""
        
        if summary_data['top_stories']:
            message += "🔥 *Top Stories:*\n\n"
            for idx, story in enumerate(summary_data['top_stories'], 1):
                story_escaped = self._escape_markdown(story)
                message += f"{idx}. {story_escaped}\n\n"
        
        if summary_data['overview']:
            overview_escaped = self._escape_markdown(summary_data['overview'])
            message += f"📋 *Overview:*\n{overview_escaped}\n\n"
        
        message += "━━━━━━━━━━━━━━━━━━━━\n\n"
        message += "📚 *All Articles:*\n\n"
        
        for idx, article in enumerate(summary_data['all_articles'][:30], 1):
            headline_escaped = self._escape_markdown(article['headline'][:80])
            message += f"{idx}. [{headline_escaped}]({article['url']})\n"
        
        message += f"\n✅ *End of Daily Summary*"
        
        return message
    
    def _escape_markdown(self, text):
        if not text:
            return ""
        
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        
        return text
    
    def _split_message(self, message, max_length=4000):
        messages = []
        current_message = ""
        
        lines = message.split('\n')
        
        for line in lines:
            if len(current_message) + len(line) + 1 > max_length:
                messages.append(current_message)
                current_message = line + '\n'
            else:
                current_message += line + '\n'
        
        if current_message:
            messages.append(current_message)
        
        return messages
    
    def send_article_sync(self, article):
        return asyncio.run(self.send_article(article))
    
    def send_daily_summary_sync(self, summary_data):
        return asyncio.run(self.send_daily_summary(summary_data))
