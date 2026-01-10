"""Telegram bot implementation with inline keyboard menus."""

from typing import Optional

from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from api.config import get_settings

settings = get_settings()

# Callback data constants
MENU_MAIN = "menu_main"
MENU_ANALYZE = "menu_analyze"
MENU_STATS = "menu_stats"
MENU_STATUS = "menu_status"
MENU_SETTINGS = "menu_settings"
MENU_LINK = "menu_link"
MENU_UNLINK = "menu_unlink"
MENU_HELP = "menu_help"
NOTIF_ON = "notif_on"
NOTIF_OFF = "notif_off"
CONFIRM_UNLINK = "confirm_unlink"
CANCEL_UNLINK = "cancel_unlink"


class JiraFeedbackBot:
    """Telegram bot for Jira Feedback notifications with menu interface."""

    def __init__(self):
        self.token = settings.telegram_bot_token
        self.webhook_url = settings.telegram_webhook_url
        self.bot: Optional[Bot] = None
        self.application: Optional[Application] = None
        # Track users waiting for input
        self.waiting_for_code: set[str] = set()
        self.waiting_for_issue: set[str] = set()

        if self.token:
            self.bot = Bot(token=self.token)
            self.application = Application.builder().token(self.token).build()
            self._setup_handlers()

    async def initialize(self) -> None:
        """Initialize the Telegram bot application for webhook mode."""
        if self.bot:
            await self.bot.initialize()
        if self.application and not self.application.running:
            await self.application.initialize()

    def _setup_handlers(self) -> None:
        """Set up command and callback handlers."""
        if not self.application:
            return

        # Command handlers
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("menu", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))

        # Keep legacy command support
        self.application.add_handler(CommandHandler("link", self.cmd_link))
        self.application.add_handler(CommandHandler("analyze", self.cmd_analyze))

        # Callback query handler for inline buttons
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))

        # Message handler for text input (link codes, issue keys)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_input)
        )

    def _get_main_menu_keyboard(self, is_linked: bool = False) -> InlineKeyboardMarkup:
        """Get the main menu keyboard."""
        if is_linked:
            keyboard = [
                [
                    InlineKeyboardButton("🔍 Analyze Issue", callback_data=MENU_ANALYZE),
                    InlineKeyboardButton("📊 My Stats", callback_data=MENU_STATS),
                ],
                [
                    InlineKeyboardButton("👤 Account Status", callback_data=MENU_STATUS),
                    InlineKeyboardButton("⚙️ Settings", callback_data=MENU_SETTINGS),
                ],
                [
                    InlineKeyboardButton("❓ Help", callback_data=MENU_HELP),
                ],
            ]
        else:
            keyboard = [
                [
                    InlineKeyboardButton("🔗 Link Account", callback_data=MENU_LINK),
                ],
                [
                    InlineKeyboardButton("❓ Help", callback_data=MENU_HELP),
                ],
            ]
        return InlineKeyboardMarkup(keyboard)

    def _get_back_button(self) -> InlineKeyboardMarkup:
        """Get a back to menu button."""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("« Back to Menu", callback_data=MENU_MAIN)]
        ])

    def _get_settings_keyboard(self, notifications_enabled: bool) -> InlineKeyboardMarkup:
        """Get settings keyboard."""
        if notifications_enabled:
            notif_btn = InlineKeyboardButton("🔕 Turn Off Notifications", callback_data=NOTIF_OFF)
        else:
            notif_btn = InlineKeyboardButton("🔔 Turn On Notifications", callback_data=NOTIF_ON)

        keyboard = [
            [notif_btn],
            [InlineKeyboardButton("🔓 Unlink Account", callback_data=MENU_UNLINK)],
            [InlineKeyboardButton("« Back to Menu", callback_data=MENU_MAIN)],
        ]
        return InlineKeyboardMarkup(keyboard)

    def _get_unlink_confirm_keyboard(self) -> InlineKeyboardMarkup:
        """Get unlink confirmation keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, Unlink", callback_data=CONFIRM_UNLINK),
                InlineKeyboardButton("❌ Cancel", callback_data=CANCEL_UNLINK),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    async def _check_linked(self, chat_id: str) -> dict:
        """Check if user is linked and return status."""
        from api.telegram.service import get_telegram_status
        return await get_telegram_status(chat_id)

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command - show main menu."""
        chat_id = str(update.effective_chat.id)
        status = await self._check_linked(chat_id)

        if status["is_linked"]:
            welcome = (
                "🎯 *Jira Feedback Bot*\n\n"
                f"Welcome back\\! Connected as `{self._escape_markdown(status['email'])}`\n\n"
                "What would you like to do?"
            )
        else:
            welcome = (
                "🎯 *Jira Feedback Bot*\n\n"
                "Welcome\\! I help you analyze Jira issues and get instant feedback\\.\n\n"
                "To get started, link your account using a code from the web dashboard\\."
            )

        await update.message.reply_text(
            welcome,
            parse_mode="MarkdownV2",
            reply_markup=self._get_main_menu_keyboard(status["is_linked"]),
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        help_text = (
            "❓ *Help*\n\n"
            "*How to use this bot:*\n\n"
            "1️⃣ *Link your account*\n"
            "Get a verification code from the web dashboard \\(Settings \\> Telegram\\) "
            "and use it to link your account\\.\n\n"
            "2️⃣ *Analyze issues*\n"
            "Enter a Jira issue key \\(like `PROJ\\-123`\\) to get instant feedback on issue quality\\.\n\n"
            "3️⃣ *View statistics*\n"
            "Check your analysis history and average scores\\.\n\n"
            "4️⃣ *Get notifications*\n"
            "Receive alerts when batch analyses complete\\.\n\n"
            "*Commands:*\n"
            "/start or /menu \\- Open main menu\n"
            "/help \\- Show this help\n"
            "/link `<code>` \\- Link with code\n"
            "/analyze `<issue>` \\- Analyze issue"
        )
        await update.message.reply_text(
            help_text,
            parse_mode="MarkdownV2",
            reply_markup=self._get_back_button(),
        )

    async def cmd_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /link <code> command (legacy support)."""
        if not context.args:
            await update.message.reply_text(
                "Please provide the verification code\\.\n"
                "Usage: `/link YOUR_CODE`",
                parse_mode="MarkdownV2",
            )
            return
        await self._process_link_code(update, context.args[0])

    async def cmd_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /analyze <issue-key> command (legacy support)."""
        if not context.args:
            await update.message.reply_text(
                "Please provide an issue key\\.\n"
                "Usage: `/analyze PROJ\\-123`",
                parse_mode="MarkdownV2",
            )
            return
        await self._process_analyze(update, context.args[0])

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle inline button callbacks."""
        query = update.callback_query
        await query.answer()

        chat_id = str(update.effective_chat.id)
        data = query.data

        if data == MENU_MAIN:
            status = await self._check_linked(chat_id)
            if status["is_linked"]:
                text = (
                    "🎯 *Jira Feedback Bot*\n\n"
                    f"Connected as `{self._escape_markdown(status['email'])}`\n\n"
                    "What would you like to do?"
                )
            else:
                text = (
                    "🎯 *Jira Feedback Bot*\n\n"
                    "Link your account to get started\\."
                )
            await query.edit_message_text(
                text,
                parse_mode="MarkdownV2",
                reply_markup=self._get_main_menu_keyboard(status["is_linked"]),
            )

        elif data == MENU_LINK:
            self.waiting_for_code.add(chat_id)
            self.waiting_for_issue.discard(chat_id)
            await query.edit_message_text(
                "🔗 *Link Account*\n\n"
                "Please enter your verification code from the web dashboard\\.\n\n"
                "Go to *Settings \\> Telegram* to generate a code\\.",
                parse_mode="MarkdownV2",
                reply_markup=self._get_back_button(),
            )

        elif data == MENU_ANALYZE:
            status = await self._check_linked(chat_id)
            if not status["is_linked"]:
                await query.edit_message_text(
                    "❌ *Not Linked*\n\nPlease link your account first\\.",
                    parse_mode="MarkdownV2",
                    reply_markup=self._get_main_menu_keyboard(False),
                )
                return

            self.waiting_for_issue.add(chat_id)
            self.waiting_for_code.discard(chat_id)
            await query.edit_message_text(
                "🔍 *Analyze Issue*\n\n"
                "Enter the Jira issue key \\(e\\.g\\. `PROJ\\-123`\\):",
                parse_mode="MarkdownV2",
                reply_markup=self._get_back_button(),
            )

        elif data == MENU_STATS:
            await self._show_stats(query, chat_id)

        elif data == MENU_STATUS:
            await self._show_status(query, chat_id)

        elif data == MENU_SETTINGS:
            await self._show_settings(query, chat_id)

        elif data == MENU_HELP:
            help_text = (
                "❓ *Help*\n\n"
                "*How to use this bot:*\n\n"
                "1️⃣ *Link your account* \\- Get a code from the web dashboard\n"
                "2️⃣ *Analyze issues* \\- Enter issue keys like `PROJ\\-123`\n"
                "3️⃣ *View statistics* \\- Check your analysis history\n"
                "4️⃣ *Get notifications* \\- Alerts for batch analyses"
            )
            await query.edit_message_text(
                help_text,
                parse_mode="MarkdownV2",
                reply_markup=self._get_back_button(),
            )

        elif data == NOTIF_ON:
            from api.telegram.service import update_telegram_settings
            await update_telegram_settings(chat_id, True)
            await query.edit_message_text(
                "✅ *Notifications Enabled*\n\n"
                "You will receive notifications when analyses complete\\.",
                parse_mode="MarkdownV2",
                reply_markup=self._get_settings_keyboard(True),
            )

        elif data == NOTIF_OFF:
            from api.telegram.service import update_telegram_settings
            await update_telegram_settings(chat_id, False)
            await query.edit_message_text(
                "🔕 *Notifications Disabled*\n\n"
                "You will no longer receive notifications\\.",
                parse_mode="MarkdownV2",
                reply_markup=self._get_settings_keyboard(False),
            )

        elif data == MENU_UNLINK:
            await query.edit_message_text(
                "⚠️ *Unlink Account*\n\n"
                "Are you sure you want to unlink your Telegram account?\n\n"
                "You will stop receiving notifications and need to re\\-link to use the bot\\.",
                parse_mode="MarkdownV2",
                reply_markup=self._get_unlink_confirm_keyboard(),
            )

        elif data == CONFIRM_UNLINK:
            from api.telegram.service import unlink_telegram
            result = await unlink_telegram(chat_id)
            if result["success"]:
                await query.edit_message_text(
                    "✅ *Account Unlinked*\n\n"
                    "Your Telegram account has been disconnected\\.",
                    parse_mode="MarkdownV2",
                    reply_markup=self._get_main_menu_keyboard(False),
                )
            else:
                await query.edit_message_text(
                    "❌ *Error*\n\nFailed to unlink account\\.",
                    parse_mode="MarkdownV2",
                    reply_markup=self._get_back_button(),
                )

        elif data == CANCEL_UNLINK:
            await self._show_settings(query, chat_id)

    async def handle_text_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text input (codes or issue keys)."""
        chat_id = str(update.effective_chat.id)
        text = update.message.text.strip()

        if chat_id in self.waiting_for_code:
            self.waiting_for_code.discard(chat_id)
            await self._process_link_code(update, text)
        elif chat_id in self.waiting_for_issue:
            self.waiting_for_issue.discard(chat_id)
            await self._process_analyze(update, text)
        else:
            # Check if it looks like an issue key (e.g., PROJ-123)
            if "-" in text and text.replace("-", "").replace(" ", "").isalnum():
                status = await self._check_linked(chat_id)
                if status["is_linked"]:
                    await self._process_analyze(update, text)
                    return

            # Show menu for unrecognized input
            status = await self._check_linked(chat_id)
            await update.message.reply_text(
                "Use the menu below or type an issue key \\(e\\.g\\. `PROJ\\-123`\\)\\.",
                parse_mode="MarkdownV2",
                reply_markup=self._get_main_menu_keyboard(status["is_linked"]),
            )

    async def _process_link_code(self, update: Update, code: str) -> None:
        """Process a link verification code."""
        chat_id = str(update.effective_chat.id)
        username = update.effective_user.username
        code = code.upper().strip()

        from api.telegram.service import verify_telegram_link

        result = await verify_telegram_link(code, chat_id, username)

        if result["success"]:
            await update.message.reply_text(
                f"✅ *Account Linked\\!*\n\n"
                f"Connected to: `{self._escape_markdown(result['email'])}`\n\n"
                "You can now analyze issues and receive notifications\\.",
                parse_mode="MarkdownV2",
                reply_markup=self._get_main_menu_keyboard(True),
            )
        else:
            await update.message.reply_text(
                f"❌ *Link Failed*\n\n{self._escape_markdown(result['error'])}\n\n"
                "Please check your code and try again\\.",
                parse_mode="MarkdownV2",
                reply_markup=self._get_main_menu_keyboard(False),
            )

    async def _process_analyze(self, update: Update, issue_key: str) -> None:
        """Process an issue analysis request."""
        chat_id = str(update.effective_chat.id)
        issue_key = issue_key.upper().strip()

        from api.telegram.service import analyze_issue_for_telegram

        # Send "analyzing" message
        analyzing_msg = await update.message.reply_text(
            f"🔄 Analyzing `{self._escape_markdown(issue_key)}`\\.\\.\\.",
            parse_mode="MarkdownV2",
        )

        result = await analyze_issue_for_telegram(chat_id, issue_key)

        if result["success"]:
            feedback = result["feedback"]
            message = (
                f"*{feedback['emoji']} Feedback for {self._escape_markdown(issue_key)}*\n\n"
                f"*Score:* {feedback['score']}/100\n\n"
                f"*Assessment:*\n{self._escape_markdown(feedback['assessment'][:300])}\n\n"
                f"*Strengths:*\n"
            )
            for s in feedback["strengths"][:3]:
                message += f"• {self._escape_markdown(s)}\n"

            message += f"\n*Improvements:*\n"
            for i in feedback["improvements"][:3]:
                message += f"• {self._escape_markdown(i)}\n"

            await analyzing_msg.edit_text(
                message,
                parse_mode="MarkdownV2",
                reply_markup=self._get_back_button(),
            )
        else:
            await analyzing_msg.edit_text(
                f"❌ *Analysis Failed*\n\n{self._escape_markdown(result['error'])}",
                parse_mode="MarkdownV2",
                reply_markup=self._get_back_button(),
            )

    async def _show_stats(self, query, chat_id: str) -> None:
        """Show user statistics."""
        from api.telegram.service import get_user_stats

        stats = await get_user_stats(chat_id)

        if stats["success"]:
            text = (
                f"📊 *Your Statistics*\n\n"
                f"📝 Total analyzed: *{stats['total_analyzed']}*\n"
                f"⭐ Average score: *{stats['average_score']:.1f}*\n"
                f"📅 This week: *{stats['this_week']}*\n"
                f"⚠️ Below 70: *{stats['below_70']}*"
            )
        else:
            text = "❌ Could not fetch statistics\\."

        await query.edit_message_text(
            text,
            parse_mode="MarkdownV2",
            reply_markup=self._get_back_button(),
        )

    async def _show_status(self, query, chat_id: str) -> None:
        """Show account status."""
        status = await self._check_linked(chat_id)

        if status["is_linked"]:
            notif = "✅ On" if status["notifications_enabled"] else "❌ Off"
            text = (
                f"👤 *Account Status*\n\n"
                f"✅ *Linked*\n\n"
                f"📧 Email: `{self._escape_markdown(status['email'])}`\n"
                f"🔔 Notifications: {notif}\n"
                f"📊 Recent analyses: {status['recent_count']}"
            )
        else:
            text = "👤 *Account Status*\n\n❌ *Not Linked*"

        await query.edit_message_text(
            text,
            parse_mode="MarkdownV2",
            reply_markup=self._get_back_button(),
        )

    async def _show_settings(self, query, chat_id: str) -> None:
        """Show settings menu."""
        status = await self._check_linked(chat_id)

        if not status["is_linked"]:
            await query.edit_message_text(
                "❌ *Not Linked*\n\nPlease link your account first\\.",
                parse_mode="MarkdownV2",
                reply_markup=self._get_main_menu_keyboard(False),
            )
            return

        notif = "✅ Enabled" if status["notifications_enabled"] else "❌ Disabled"
        text = (
            f"⚙️ *Settings*\n\n"
            f"🔔 Notifications: {notif}\n"
            f"📧 Account: `{self._escape_markdown(status['email'])}`"
        )
        await query.edit_message_text(
            text,
            parse_mode="MarkdownV2",
            reply_markup=self._get_settings_keyboard(status["notifications_enabled"]),
        )

    def _escape_markdown(self, text: str) -> str:
        """Escape special characters for MarkdownV2."""
        if not text:
            return ""
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
