# Welcome Messages

This directory contains welcome messages that are shown to first-time users before they execute the `/main` command.

## Structure

```
welcome/
├── en/
│   └── welcome.txt    # English welcome message
├── ua/
│   └── welcome.txt    # Ukrainian welcome message
├── ru/
│   └── welcome.txt    # Russian welcome message
└── __init__.py        # Message loader function
```

## Purpose

The welcome message serves as a **first contact point** for new users. It is automatically sent by the `FirstContactMiddleware` when:

1. A user sends their **first message** to the bot
2. The user is **not yet registered** in the database
3. The message is **not a `/start` command**

## Message Content Guidelines

Each welcome message should include:

1. **Greeting** - Friendly welcome to the bot
2. **Purpose** - Brief explanation of what the bot does
3. **Menu Instructions** - How to enable the command menu in Telegram:
   - Tap the menu icon (☰) at the bottom left
   - Select "Menu" to see available commands
4. **Available Commands** - List of main commands:
   - `/main` - Show main menu
   - `/help` - Detailed help
   - `/recommendations` - Personalized strategies
   - `/exchanges` - Browse by exchange
5. **Quick Start** - Simple call-to-action (type `/main`)
6. **Support** - How to get help (type `/help`)

## Formatting

- Use **HTML formatting** (supported by Telegram)
- Use `<b>` for bold text
- Use `<code>` for commands
- Use emojis for visual appeal (📱, 🎯, 💡, etc.)
- Keep text concise and scannable

## Language Detection

The middleware automatically detects the user's language from their Telegram `language_code`:

- `uk` → Ukrainian (`ua`)
- `ru` → Russian (`ru`)
- `en` → English (`en`)
- Other → Default to English

## How to Edit

To modify a welcome message:

1. Navigate to the appropriate language folder (`en/`, `ua/`, or `ru/`)
2. Edit the `welcome.txt` file
3. Save the file
4. Restart the bot to apply changes

## Adding New Languages

To add a new language:

1. Create a new folder with the language code (e.g., `de/` for German)
2. Create a `welcome.txt` file in that folder
3. Create an `__init__.py` file with docstring
4. Update the `get_welcome_message()` function in `__init__.py` to support the new language
5. Update the `FirstContactMiddleware` to detect the new language code

## Technical Implementation

The welcome message is loaded using the `get_welcome_message(language)` function from `bot.content.welcome`.

Example:

```python
from bot.content.welcome import get_welcome_message

# Load English message
message = get_welcome_message("en")

# Load Ukrainian message
message = get_welcome_message("ua")
```

## Testing

Tests are located in `tests/test_first_contact_middleware.py`:

- Content loading for all languages
- Fallback to English for invalid languages
- Middleware behavior for new vs. existing users
- Language detection from Telegram

Run tests:

```bash
pytest tests/test_first_contact_middleware.py -v
```
