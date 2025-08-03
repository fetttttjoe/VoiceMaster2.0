# utils/responses.py

# General
GENERIC_ERROR = "An unexpected error occurred. Please try again later."
NOT_IN_GUILD = "This command can only be used in a server."
BOT_NOT_SETUP = "The bot has not been set up yet. Run `.voice setup` first."
NO_VOICE_CHANNEL = "Error: Could not determine your voice channel."

# Voice Commands
VOICE_HELP_TITLE = "🎧 VoiceMaster Commands"
VOICE_HELP_DESCRIPTION = (
    "Here are all the commands to manage your temporary voice channels. "
    "Commands require you to be in a voice channel you own or manage, "
    "unless otherwise specified."
)
VOICE_HELP_FOOTER = "Use {prefix}voice <command> to get started."

# Admin Commands
ADMIN_COMMANDS_TITLE = "🛠️ Admin Commands"
ADMIN_COMMANDS_VALUE = (
    "`{prefix}voice setup` - The first-time setup for the bot.\n"
    "`{prefix}voice edit rename` - Rename the creation channel or category.\n"
    "`{prefix}voice edit select` - Select a different creation channel or category.\n"
    "`{prefix}voice list` - Lists all active temporary channels.\n"
    "`{prefix}voice auditlog [count]` - Shows recent bot activity.\n"
    "`{prefix}voice config` - Opens an interactive menu for bot settings."
)

# User Commands
USER_COMMANDS_TITLE = "👤 User Commands"
USER_COMMANDS_VALUE = (
    "`{prefix}voice lock` - Locks your current temporary channel.\n"
    "`{prefix}voice unlock` - Unlocks your current temporary channel.\n"
    "`{prefix}voice permit @user` - Permits a user to join your current locked temporary channel.\n"
    "`{prefix}voice claim` - Claims an empty, ownerless channel.\n"
    "`{prefix}voice name <new_name>` - Sets your default channel name.\n"
    "`{prefix}voice limit <number>` - Sets your default channel user limit."
)

# Config Command
CONFIG_TITLE = "VoiceMaster Config for {guild_name}"
CONFIG_DESCRIPTION = "Use the buttons below to manage bot settings for this server."
CONFIG_CLEANUP_TITLE = "Automatic Channel Cleanup on Startup"
CONFIG_CLEANUP_VALUE = "{status_icon} Status: **{cleanup_status}**\nThis feature automatically deletes empty temporary channels when the bot starts."

# Setup Command
SETUP_PROMPT = "Click the button to begin the setup process."

# Edit Command
EDIT_PROMPT = "Please specify what you want to edit. Use `.voice edit rename` or `.voice edit select`."
EDIT_RENAME_PROMPT = "Press a button to start renaming:"
EDIT_SELECT_NO_CHANNELS = "No non-temporary voice channels with categories found to select from."
EDIT_SELECT_NO_CATEGORIES = "No categories found to select from."
EDIT_SELECT_PROMPT = "Use the dropdowns to select a new channel or category:"

# List Command
LIST_TITLE = "Active Temporary Channels"
LIST_NO_CHANNELS = "There are no active temporary channels managed by VoiceMaster in this guild."
LIST_OWNER_NOT_FOUND = "Owner not found (ID: {owner_id})"

# Lock/Unlock Commands
CHANNEL_LOCKED = "🔒 Channel locked."
CHANNEL_UNLOCKED = "🔓 Channel unlocked."

# Permit Command
PERMIT_SUCCESS = "✅ {member_mention} can now join your channel."

# Claim Command
CLAIM_NOT_TEMP_CHANNEL = "This channel is not a temporary channel managed by VoiceMaster."
CLAIM_OWNER_PRESENT = "The owner, {owner_mention}, is still in the channel. You cannot claim it."
CLAIM_SUCCESS = "👑 {author_mention}, you are now the owner of this channel!"

# Name Command
NAME_LENGTH_ERROR = "Please provide a name between 2 and 100 characters."
NAME_SUCCESS = "Your channel name has been set to **{new_name}**. It will apply to your current (if you own one and are in it) and all future channels."

# Limit Command
LIMIT_RANGE_ERROR = "Please provide a limit between 0 (unlimited) and 99."
LIMIT_SUCCESS = "Your channel limit has been set to **{limit_str}**. It will apply to your current (if you own one and are in it) and all future channels."

# Audit Log Command
AUDIT_LOG_COUNT_ERROR = "Please provide a count between 1 and 50."
AUDIT_LOG_NO_ENTRIES = "No audit log entries found for this guild."
AUDIT_LOG_TITLE = "Recent VoiceMaster Activity Logs ({count} entries)"
AUDIT_LOG_FOOTER = "Most recent entries first. Times are UTC."
AUDIT_LOG_USER_NOT_FOUND = "User ID: {user_id} (Not found)"
AUDIT_LOG_CHANNEL_NOT_FOUND = "Channel ID: {channel_id} (Not found)"
AUDIT_LOG_DM_CHANNEL = "DM Channel ({channel_id})"
AUDIT_LOG_UNKNOWN_CHANNEL = "Channel '{channel_name}' (ID: {channel_id})"
AUDIT_LOG_FIELD_TITLE = "Log Entry #{entry_id}"
AUDIT_LOG_FIELD_VALUE = (
    "**Type**: {event_type}\n"
    "**User**: {user_display}\n"
    "**Channel**: {channel_display}\n"
    "**Details**: {details}\n"
    "**Time**: {timestamp}"
)

# Error Responses
ERROR_PREFIX = "⚠️"
FORBIDDEN_ERROR = "🚫 I don't have the required permissions to perform this action. Please check my role and channel permissions."
MISSING_PERMISSIONS = "🚫 You don't have the required permissions (`{perms}`) to use this command."
NO_PRIVATE_MESSAGE = "This command cannot be used in private messages."
USER_INPUT_ERROR = "🤔 Invalid input: {error}. Please check your arguments."
CHECK_FAILURE = "You do not meet the requirements to run this command."
HTTP_EXCEPTION = "An error occurred while communicating with Discord. Please try again later."
UNHANDLED_EXCEPTION = "An unexpected error occurred. This has been logged for review. Please try again later."
