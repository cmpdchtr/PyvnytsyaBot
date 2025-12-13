# 🍻 PyvnytsyaBot (The Bunker)

> **Survive the Apocalypse. Betray your Friends. Trust the AI.**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![Aiogram](https://img.shields.io/badge/Aiogram-3.x-blueviolet?style=for-the-badge&logo=telegram)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15%2B-blue?style=for-the-badge&logo=postgresql)
![Gemini AI](https://img.shields.io/badge/AI-Google%20Gemini-orange?style=for-the-badge&logo=google)

**PyvnytsyaBot** is a feature-rich, AI-powered Telegram bot implementation of the popular social deduction board game **"Bunker"**. 

Players are survivors of a global catastrophe seeking refuge in a bunker with limited space. The catch? You must argue your way in based on your random characteristics (Profession, Health, Phobia, etc.). The AI acts as the Game Master, generating unique scenarios and deciding the fate of the survivors.

---

## ✨ Key Features

### 🧠 AI-Powered Gameplay
- **Dynamic Scenarios:** No two games are the same. Google Gemini generates unique disasters, bunker conditions, and survival times every match.
- **Narrative Endings:** The AI analyzes the survivors' traits to generate a dramatic (or hilarious) epilogue. Did the group survive? Or did the *Clown* with *Tuberculosis* doom everyone?

### 🎮 Deep Mechanics
- **Rich Character Cards:** Randomly generated traits including:
  - 🛠 Profession
  - ❤️ Health
  - 🎨 Hobby
  - 😱 Phobia
  - 🎒 Inventory
  - ℹ️ Random Fact
  - 🎂 Age & Bio
- **⚡ Action Cards:** Turn the tables with special abilities!
  - **Active:** `Scan`, `Heal`, `Reroll`, `Silence`, `Steal`, `Poison`, `Swap Health`, `Mask`, `Loudspeaker`.
  - **Passive:** `Defense` (survive a vote), `Revenge` (take someone with you).
- **🗳️ Interactive Voting:** Smooth inline-keyboard interface for voting players out.

### 📦 Custom Content Packs
Don't like the standard traits? Want to play in the **Metro 2033** or **S.T.A.L.K.E.R.** universe?
- **Upload JSON Packs:** Users can create and upload their own game packs.
- **Custom AI Prompts:** Define how the AI narrates the scenario and ending for your specific pack.

### 🛡️ Robust Architecture
- **GoodbyeQuota Integration:** Uses a smart key rotation system to handle Google Gemini API rate limits. Never get a `429` error again.
- **PostgreSQL Database:** Persistent storage for users, rooms, and game states.

---

## 🚀 Installation

### Prerequisites
- Python 3.10+
- PostgreSQL
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Google Gemini API Keys (get multiple for better reliability)

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/cmpdchtr/PyvnytsyaBot.git
   cd PyvnytsyaBot
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup PostgreSQL:**
   If you haven't set up the database yet, follow these steps:

   *   **Log in to PostgreSQL:**
       ```bash
       psql -U postgres
       ```
   *   **Create User and Database:**
       Run the following SQL commands:
       ```sql
       CREATE USER pyvnytsya_user WITH PASSWORD 'secure_password';
       CREATE DATABASE pyvnytsya_db OWNER pyvnytsya_user;
       GRANT ALL PRIVILEGES ON DATABASE pyvnytsya_db TO pyvnytsya_user;
       \q
       ```

5. **Configure Environment:**
   Create a `.env` file in the root directory:
   ```env
   BOT_TOKEN=your_telegram_bot_token
   # Comma-separated list of API keys for rotation
   GEMINI_API_KEY="key1,key2,key3"
   
   DB_HOST=localhost
   DB_PORT=5432
   DB_USER=pyvnytsya_user
   DB_PASS=secure_password
   DB_NAME=pyvnytsya_db
   ```

6. **Run the Bot:**
   ```bash
   python main.py
   ```

---

## 🛠️ Custom Packs Guide

You can upload a `.json` file to the bot to use custom traits and settings.

**Structure (`template.json`):**
```json
{
  "name": "Metro 2033 Pack",
  "description": "Survival in the Moscow Metro",
  "ai_prompts": {
    "scenario_prompt": "Generate a scenario based on the Metro 2033 universe...",
    "ending_prompt": "Describe the ending considering mutants and radiation..."
  },
  "data": {
    "professions": [
      {"name": "Stalker", "weight": 50},
      {"name": "Metro Guard", "weight": 30}
    ],
    "health": [
      {"name": "Radiation Sickness", "weight": 20},
      {"name": "Healthy", "weight": 50}
    ],
    "hobby": [...],
    "phobia": [...],
    "inventory": [...],
    "fact": [...],
    "bio": [...]
  }
}
```

---

## 🃏 Action Cards List

| Card | Type | Effect |
|------|------|--------|
| **🔍 Scan** | Active | Reveal one hidden trait of another player. |
| **💊 Heal** | Active | Cure your illness (become Healthy). |
| **🎲 Reroll** | Active | Get a new random profession. |
| **🤐 Silence** | Active | Prevent a player from chatting for one round. |
| **🦝 Steal** | Active | Swap inventory with another player. |
| **💉 Poison** | Active | Infect a player with a deadly illness. |
| **🔄 Swap Health** | Active | Swap health status with another player. |
| **🎭 Mask** | Active | Re-hide one of your revealed traits. |
| **📢 Loudspeaker** | Active | Your vote counts as x2 next round. |
| **🛡️ Defense** | Passive | Survive being voted out once. |
| **💣 Revenge** | Passive | If voted out, eliminate a random player with you. |

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

<div align="center">
  <sub>Built with ❤️ by <a href="https://github.com/cmpdchtr">cmpdchtr</a></sub>
</div>
