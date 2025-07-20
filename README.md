# VoiceMaster 2.0

VoiceMaster 2.0 is a Discord bot designed to provide advanced management features for temporary voice channels. Users can create, customize, and manage their own voice channels, including setting names, user limits, and managing permissions. The bot also includes administrator commands for server setup, configuration edits, and detailed audit logging of bot activities.

If you'd like to invite the bot, you can use the following link:  
🔗 [Invite Link](https://discord.com/oauth2/authorize?client_id=1395824661207453746&permissions=8&response_type=code&redirect_uri=https%3A%2F%2Flocalhost&integration_type=0&scope=bot+applications.commands+guilds.members.read)

> ⚠️ **Note:** The bot currently requests administrator permissions.  
> If anyone besides me is interested in using it, feel free to open a pull request / Issue.  
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

- **Python**: The core programming language.
- **discord.py**: Asynchronous Python wrapper for the Discord API.
- **SQLAlchemy**: Python SQL toolkit and Object Relational Mapper for database interactions.
- **asyncpg**: PostgreSQL driver for `asyncio`.
- **Alembic**: Database migration tool for SQLAlchemy.
- **python-dotenv**: For managing environment variables.
- **PostgreSQL**: Relational database for storing guild and user configurations, and audit logs.
- **Dependency Injection**: Structured code using abstractions (interfaces) for services and repositories to improve testability and maintainability.
- **Docker**: For containerization of the bot and database services.
- **pytest**: For unit and integration testing.
- **pytest-asyncio**: Pytest plugin for testing `asyncio` code.

## Setup and Installation

### Prerequisites

- Docker and Docker Compose installed on your system.
- A Discord Bot Token from the [Discord Developer Portal](https://discord.com/developers/applications).
- Basic understanding of Discord bot setup.

### Steps

1.  **Clone the repository:**

    ```bash
    git clone <your-repository-url>
    cd VoiceMaster2.0
    ```

2.  **Create `.env` file:**
    Copy the example environment file and fill in your details:

    ```bash
    cp .env.example .env
    ```

    Open the newly created `.env` file and populate it with your Discord bot token and PostgreSQL credentials.

    ```ini
    # Your Discord Bot Token
    DISCORD_TOKEN=your_super_secret_bot_token

    # PostgreSQL Connection Details (these can be left as default if using Docker Compose locally)
    POSTGRES_USER=voicemaster
    POSTGRES_PASSWORD=your_secure_password
    POSTGRES_DB=voicemaster_db
    POSTGRES_HOST=db
    POSTGRES_PORT=5432
    ```

3.  **Build and Run with Docker Compose:**
    Navigate to the project root directory where `docker-compose.yaml` is located and run:

    ```bash
    docker-compose up --build -d
    ```

    - `--build`: Builds the Docker images before starting containers. This is important for the first run or after Dockerfile changes.
    - `-d`: Runs the services in detached mode (in the background).

    This command will:

    - Build the bot's Docker image.
    - Set up a PostgreSQL database container.
    - Run database migrations using Alembic.
    - Start the bot.

## Usage

1.  **Invite the bot to your Discord server.** Make sure your bot has the necessary permissions (e.g., `manage_channels`, `manage_roles`, `move_members`, `view_channel`, `connect`, `speak`).
2.  **Run the setup command:**
    Once the bot is online, an administrator must run the setup command in a text channel:
    ```
    .voice setup
    ```
    Follow the bot's prompts to create a voice category for temporary channels and a "Join to Create" voice channel.
3.  **Create your first channel:**
    Join the "Join to Create" voice channel. The bot will automatically create a new personal voice channel for you and move you into it.
4.  **Explore commands:**
    Use `.voice` for a list of all commands:
    ```
    .voice
    ```
    This will display an embed with available commands and their descriptions.

## Configuration

The bot's configuration, such as Discord token and database connection details, is managed via environment variables loaded from the `.env` file.

Admins can also configure the bot directly through Discord commands:

- `.voice edit rename`: To change the name of the creation channel or category.
- `.voice edit select`: To choose an existing channel or category for bot operations.
- `.voice name <new_name>`: Set your default channel name.
- `.voice limit <number>`: Set your default channel user limit.

## Running Tests

Tests are integrated into the Docker Compose setup. To run the test suite:

1.  Ensure your Docker services are built (`docker-compose build`).
2.  From the project root, execute the test service:
    ```bash
    docker-compose run --rm test
    ```
    This command will spin up the database, run pytest, and then remove the test container upon completion.

## Database Schema

VoiceMaster 2.0 uses a PostgreSQL database to store guild configurations, user-specific channel settings, active voice channels, and an audit log of bot activities.

Key tables include:

- `guilds`: Stores primary guild configurations, including owner ID, voice category ID, and creation channel ID.
- `guild_settings`: Stores default channel name and limit settings for guilds.
- `user_settings`: Stores custom channel name and limit preferences for individual users.
- `voice_channels`: Tracks active temporary voice channels and their owners.
- `audit_log_entries`: Records significant bot events and administrative actions.

Database migrations are managed using Alembic.

## License

This software is provided under a custom source-available license. You are free to use, modify, and distribute this software, but if you monetize any product or service derived from this software, you are required to share a portion of the revenue with the original author.
