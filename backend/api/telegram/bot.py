"""Telegram bot implementation."""

import asyncio
from typing import Optional

from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes

from api.config import get_settings

settings = get_settings()


class JiraFeedbackBot:
    """Telegram bot for Jira Feedback notifications and commands."""

    def __init__(self):
        self.token = settings.telegram_bot_token
        self.webhook_url = settings.telegram_webhook_url
        self.bot: Optional[Bot] = None
        self.application: Optional[Application] = None

        if self.token:
            self.bot = Bot(token=self.token)
            self.application = Application.builder().token(self.token).build()
            self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Set up command handlers."""
        if not self.application:
            return

        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("link", self.cmd_link))
        self.application.add_handler(CommandHandler("unlink", self.cmd_unlink))
        self.application.add_handler(CommandHandler("status", self.cmd_status))
        self.application.add_handler(CommandHandler("analyze", self.cmd_analyze))
        self.application.add_handler(CommandHandler("stats", self.cmd_stats))
        self.application.add_handler(CommandHandler("settings", self.cmd_settings))

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        welcome_message = (
            "Welcome to *Jira Feedback Bot*\\! 🎯\n\n"
            "I help you analyze Jira issues and get instant feedback on issue quality\\.\n\n"
            "*Getting Started:*\n"
            "1\\. Get your verification code from the web dashboard\n"
            "2\\. Link your account with `/link <code>`\n\n"
            "*Available Commands:*\n"
            "/link `<code>` \\- Link your account\n"
            "/unlink \\- Unlink your account\n"
            "/status \\- Check link status\n"
            "/analyze `<issue\\-key>` \\- Analyze an issue\n"
            "/stats \\- View your statistics\n"
            "/settings \\- Notification settings\n"
            "/help \\- Show this help message"
        )
        await update.message.reply_text(welcome_message, parse_mode="MarkdownV2")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        await self.cmd_start(update, context)

    async def cmd_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /link <code> command to link Telegram account."""
        if not context.args:
            await update.message.reply_text(
                "Please provide the verification code\\.\n"
                "Usage: `/link YOUR_CODE`\n\n"
                "Get your code from the web dashboard under Settings \\> Telegram\\.",
                parse_mode="MarkdownV2",
            )
            return

        code = context.args[0].upper()
        chat_id = str(update.effective_chat.id)
        username = update.effective_user.username

        from api.telegram.service import verify_telegram_link

        result = await verify_telegram_link(code, chat_id, username)

        if result["success"]:
            await update.message.reply_text(
                f"✅ *Account linked successfully\\!*\n\n"
                f"Connected to: `{result['email']}`\n\n"
                "You will now receive feedback notifications here\\.\n"
                "Use /settings to manage notification preferences\\.",
                parse_mode="MarkdownV2",
            )
        else:
            await update.message.reply_text(
                f"❌ *Link failed*\n\n{result['error']}\n\n"
                "Please check your code and try again\\.",
                parse_mode="MarkdownV2",
            )

    async def cmd_unlink(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /unlink command."""
        chat_id = str(update.effective_chat.id)

        from api.telegram.service import unlink_telegram

        result = await unlink_telegram(chat_id)

        if result["success"]:
            await update.message.reply_text(
                "✅ Account unlinked\\. You will no longer receive notifications\\.",
                parse_mode="MarkdownV2",
            )
        else:
            await update.message.reply_text(
                "No linked account found\\. Use /link to connect your account\\.",
                parse_mode="MarkdownV2",
            )

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        chat_id = str(update.effective_chat.id)

        from api.telegram.service import get_telegram_status

        status = await get_telegram_status(chat_id)

        if status["is_linked"]:
            await update.message.reply_text(
                f"✅ *Account Status: Linked*\n\n"
                f"Email: `{status['email']}`\n"
                f"Notifications: {'Enabled' if status['notifications_enabled'] else 'Disabled'}\n"
                f"Recent analyses: {status['recent_count']}",
                parse_mode="MarkdownV2",
            )
        else:
            await update.message.reply_text(
                "❌ *Account Status: Not Linked*\n\n"
                "Use /link `<code>` to connect your account\\.",
                parse_mode="MarkdownV2",
            )

    async def cmd_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /analyze <issue-key> command."""
        chat_id = str(update.effective_chat.id)

        if not context.args:
            await update.message.reply_text(
                "Please provide an issue key\\.\n"
                "Usage: `/analyze PROJ\\-123`",
                parse_mode="MarkdownV2",
            )
            return

        issue_key = context.args[0].upper()

        from api.telegram.service import analyze_issue_for_telegram

        # Send "analyzing" message
        analyzing_msg = await update.message.reply_text(
            f"🔄 Analyzing `{issue_key}`\\.\\.\\.",
            parse_mode="MarkdownV2",
        )

        result = await analyze_issue_for_telegram(chat_id, issue_key)

        if result["success"]:
            feedback = result["feedback"]
            message = (
                f"*{feedback['emoji']} Feedback for {issue_key}*\n\n"
                f"*Score:* {feedback['score']}/100\n\n"
                f"*Assessment:*\n{self._escape_markdown(feedback['assessment'][:300])}\n\n"
                f"*Strengths:*\n"
            )
            for s in feedback["strengths"][:3]:
                message += f"• {self._escape_markdown(s)}\n"

            message += f"\n*Improvements:*\n"
            for i in feedback["improvements"][:3]:
                message += f"• {self._escape_markdown(i)}\n"

            await analyzing_msg.edit_text(message, parse_mode="MarkdownV2")
        else:
            await analyzing_msg.edit_text(
                f"❌ *Analysis failed*\n\n{self._escape_markdown(result['error'])}",
                parse_mode="MarkdownV2",
            )

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stats command."""
        chat_id = str(update.effective_chat.id)

        from api.telegram.service import get_user_stats

        stats = await get_user_stats(chat_id)

        if stats["success"]:
            await update.message.reply_text(
                f"📊 *Your Statistics*\n\n"
                f"Total analyzed: {stats['total_analyzed']}\n"
                f"Average score: {stats['average_score']:.1f}\n"
                f"This week: {stats['this_week']}\n"
                f"Issues below 70: {stats['below_70']}",
                parse_mode="MarkdownV2",
            )
        else:
            await update.message.reply_text(
                "❌ Could not fetch statistics\\. Make sure your account is linked\\.",
                parse_mode="MarkdownV2",
            )

    async def cmd_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /settings command."""
        chat_id = str(update.effective_chat.id)

        # Check if toggling notifications
        if context.args and context.args[0].lower() in ["on", "off"]:
            enabled = context.args[0].lower() == "on"
            from api.telegram.service import update_telegram_settings

            result = await update_telegram_settings(chat_id, enabled)
            if result["success"]:
                status = "enabled" if enabled else "disabled"
                await update.message.reply_text(
                    f"✅ Notifications {status}\\.",
                    parse_mode="MarkdownV2",
                )
            else:
                await update.message.reply_text(
                    "❌ Failed to update settings\\.",
                    parse_mode="MarkdownV2",
                )
            return

        # Show current settings
        from api.telegram.service import get_telegram_status

        status = await get_telegram_status(chat_id)

        if status["is_linked"]:
            notif_status = "✅ Enabled" if status["notifications_enabled"] else "❌ Disabled"
            await update.message.reply_text(
                f"⚙️ *Notification Settings*\n\n"
                f"Status: {notif_status}\n\n"
                f"To change: `/settings on` or `/settings off`",
                parse_mode="MarkdownV2",
            )
        else:
            await update.message.reply_text(
                "❌ Account not linked\\. Use /link first\\.",
                parse_mode="MarkdownV2",
            )

    def _escape_markdown(self, text: str) -> str:
        """Escape special characters for MarkdownV2."""
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text

    async def send_notification(
        self,
        chat_id: str,
        message: str,
        parse_mode: str = "MarkdownV2",
    ) -> bool:
        """Send a notification to a user."""
        if not self.bot:
            return False

        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=parse_mode,
            )
            return True
        except Exception as e:
            print(f"Failed to send Telegram message: {e}")
            return False

    async def process_update(self, update_data: dict) -> None:
        """Process an incoming webhook update."""
        if not self.application:
            return

        update = Update.de_json(update_data, self.bot)
        await self.application.process_update(update)


# Global bot instance
bot_instance: Optional[JiraFeedbackBot] = None


def get_bot() -> JiraFeedbackBot:
    """Get or create the bot instance."""
    global bot_instance
    if bot_instance is None:
        bot_instance = JiraFeedbackBot()
    return bot_instance


async def setup_webhook() -> bool:
    """Set up the Telegram webhook."""
    bot = get_bot()
    if not bot.bot or not bot.webhook_url:
        return False

    try:
        await bot.bot.set_webhook(url=f"{bot.webhook_url}")
        return True
    except Exception as e:
        print(f"Failed to set webhook: {e}")
        return False
