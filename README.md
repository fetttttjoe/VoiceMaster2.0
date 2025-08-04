# VoiceMaster 2.0

VoiceMaster 2.0 is a Discord bot designed to provide advanced management features for temporary voice channels. Users can create, customize, and manage their own voice channels, including setting names, user limits, and managing permissions. The bot also includes administrator commands for server setup, configuration edits, and detailed audit logging of bot activities.

If you'd like to invite the bot, you can use the following link:  
🔗 [Invite Link](https://discord.com/oauth2/authorize?client_id=1395824661207453746&permissions=8&response_type=code&redirect_uri=https%3A%2F%2Flocalhost&integration_type=0&scope=bot+applications.commands+guilds.members.read)

> ⚠️ **Note:** The bot currently requests administrator permissions.  
> If anyone besides me is interested in using it, feel free to open a pull request or issue.  
> I'll then look into defining the minimal set of permissions the bot actually needs.

## Features

- **Dynamic Channel Creation**: Users can join a designated "Join to Create" channel to automatically generate a new temporary voice channel.
- **Personalized Voice Channels**:
  - **Custom Naming**: Set a personalized name for your temporary channel (e.g., `.voice name My Awesome Squad`).
  - **User Limits**: Configure the maximum number of users who can join your channel (e.g., `.voice limit 5` or `0` for no limit).
- **Channel Management**:
  - **Lock/Unlock**: Restrict or allow access to your channel (`.voice lock`, `.voice unlock`).
  - **Permit Users**: Grant specific users access to your locked channel (`.voice permit @user`).
  - **Claim Ownership**: Take ownership of an abandoned temporary channel (`.voice claim`).
- **Admin Tools**:
  - **First-time Setup**: Easy initial setup of the voice channel creation category and channel (`.voice setup`).
  - **Configuration Editing**: Rename or re-select the creation channel and category (`.voice edit rename`, `.voice edit select`).
  - **List Channels**: View all active temporary channels on the server (`.voice list`).
  - **Audit Log**: Track recent bot activities and administrative actions (`.voice auditlog [count]`).

## Technologies Used

- **Python**
- **discord.py**
- **SQLAlchemy**
- **asyncpg**
- **Alembic**
- **python-dotenv**
- **PostgreSQL**
- **Dependency Injection** (interfaces, container)
- **Docker**
- **pytest** & **pytest-asyncio**

## Setup and Installation

### Prerequisites

- Docker & Docker Compose
- A Discord Bot Token ([Discord Developer Portal](https://discord.com/developers/applications))
- Basic familiarity with Discord bots

### Steps

1. **Clone the repo**

2. **Create your `.env` file**

   ```bash
   cp .env.example .env
   ```

   Then open `.env` and fill in:

   ```ini
   DISCORD_TOKEN=your_super_secret_bot_token
   POSTGRES_USER=voicemaster
   POSTGRES_PASSWORD=your_secure_password
   POSTGRES_DB=voicemaster_db
   POSTGRES_HOST=db
   POSTGRES_PORT=5432
   ```

3. **Build & run with Docker Compose**

   ```bash
   docker-compose up --build -d
   ```

   - `--build`: rebuilds the images (useful after changes)
   - `-d`: runs in detached mode

4. **Local installation (optional)**  
   For development without Docker:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: `.venv\ScriptsActivate`
   pip install --upgrade pip
   pip install -e .[dev]
   ```
   Then:
   ```bash
   alembic upgrade head
   python main.py
   ```

## Usage

1. Invite your bot (ensure it has `manage_channels`, `manage_roles`, `move_members`, `view_channel`, `connect`, `speak`).
2. Run setup:
   ```
   .voice setup
   ```
3. Join “Join to Create” to spawn your personal voice channel.
4. Type `.voice` to see all commands.

## Configuration

Environment variables (in `.env`):

- **Required**  
  `DISCORD_TOKEN`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`

- **Optional**
  - `DB_ECHO` (bool, default `False`): echo SQL queries for debugging
  - `MAX_LOCKS` (int, default `1000`): max channel locks per user
  - `VIEW_TIMEOUT` (int, default `100`): seconds before interactive menus time out
  - `DATABASE_URL` (str): full asyncpg DSN (`postgresql+asyncpg://user:pass@host:port/db`) to override individual POSTGRES\_\*

## Architecture

VoiceMaster 2.0 uses a **repository/service** pattern:

- **Repositories** encapsulate all SQLAlchemy operations for each domain (guilds, channels, audit logs).
- **Services** implement higher-level logic by calling into repositories.
- **Container** in `container.py` wires repositories → services, then attaches them to the `VoiceMasterBot` in `bot_instance.py`.
- Cogs access these via `ctx.bot.guild_service`, `ctx.bot.voice_channel_service`, etc.

This promotes testability (mockable services), separation of concerns, and clean dependency injection.

## Running Tests

In Docker Compose:

```bash
docker-compose run --rm test
```

```bash
docker-compose run --rm lint
```

## Database Schema

Key tables:

- `guilds`
- `guild_settings`
- `user_settings`
- `voice_channels`
- `audit_log_entries`

Migrations are managed by Alembic.

## License

This project is under a custom source-available license; modifications and non-open commercial use require revenue sharing with the original author.
