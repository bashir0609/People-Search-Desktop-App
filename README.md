# 🚀 CEO Finder Pro

An advanced AI-powered tool to find CEO information for companies from CSV files.

## ⚡ Quick Start (3 Steps)

### 1. 📦 Install Requirements

**Windows:**
```bash
setup.bat
```

**Mac/Linux:**
```bash
chmod +x setup.sh
./setup.sh
```

**Manual Installation:**
```bash
pip install -r requirements.txt
```

### 2. 🔑 Setup API Keys

Create a `.env` file in the same folder with your API keys:

```env
# Required (minimum to run)
OPENAI_API_KEY=your_openai_key_here

# Optional (for better results)
GEMINI_API_KEY=your_gemini_key
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_SEARCH_API_KEY=your_google_search_key
GOOGLE_SEARCH_CX=your_custom_search_engine_id
HUNTER_API_KEY=your_hunter_key
APOLLO_API_KEY=your_apollo_key
ROCKETREACH_API_KEY=your_rocketreach_key
```

### 3. 🚀 Run the App

**Desktop App (Recommended):**
```bash
python ceo_finder_gui.py
```

**Command Line:**
```bash
python people.py
```

## 🎯 Features

- ✅ **Smart CEO Finding** - Uses multiple AI models and databases
- ✅ **Targeted Processing** - Only process companies missing CEO data
- ✅ **Progress Tracking** - Real-time progress with pause/resume
- ✅ **LinkedIn Search** - Automatically finds CEO LinkedIn profiles
- ✅ **Results Analysis** - Detailed statistics and success rates
- ✅ **Error Recovery** - Handles connection issues gracefully

## 📊 Usage

1. **Select CSV File** - Must have a company name column
2. **Choose Processing Mode:**
   - 🎯 **Process ONLY missing CEOs** (recommended for re-runs)
   - ➡️ **Continue from where left off**
   - 🔄 **Process all companies**
3. **Click Start** - Watch real-time progress
4. **View Results** - Analyze success rates and export data

## 🔑 API Keys (Where to Get Them)

| API | Purpose | Get Key From |
|-----|---------|--------------|
| **OpenAI** ⭐ | Required - Main AI processing | [platform.openai.com](https://platform.openai.com) |
| Gemini | Optional - Alternative AI | [ai.google.dev](https://ai.google.dev) |
| Anthropic | Optional - Claude AI | [console.anthropic.com](https://console.anthropic.com) |
| Google Search | Optional - Better search results | [console.cloud.google.com](https://console.cloud.google.com) |
| Hunter.io | Optional - Email/contact data | [hunter.io](https://hunter.io) |
| Apollo.io | Optional - B2B database | [apollo.io](https://apollo.io) |
| RocketReach | Optional - Contact database | [rocketreach.co](https://rocketreach.co) |

⭐ = Required (minimum to run)

## 📁 File Structure

```
CEO Finder Pro/
├── ceo_finder_gui.py    # Desktop app (main interface)
├── people.py            # Core CEO finding engine
├── requirements.txt     # Python dependencies
├── setup.bat           # Windows setup script
├── setup.sh            # Mac/Linux setup script
├── .env                # Your API keys (create this)
└── README.md           # This file
```

## 🆘 Troubleshooting

**"No module named 'X'" error:**
```bash
pip install -r requirements.txt
```

**"API key not found" error:**
- Check your `.env` file exists
- Ensure `OPENAI_API_KEY` is set
- No spaces around the `=` sign

**GUI won't start:**
- Try: `python3 ceo_finder_gui.py` (on Mac/Linux)
- Ensure tkinter is installed (usually built-in)

**SSL/Connection errors:**
- Tool automatically handles SSL issues
- Check your internet connection

## 📈 Expected Results

- **70-90% success rate** for finding CEOs
- **Better results** with more API keys
- **LinkedIn profiles** found for 60-80% of CEOs
- **Processing speed:** 1-3 companies per minute

## 💡 Tips for Best Results

1. **Use multiple API keys** for higher success rates
2. **Include website URLs** in your CSV for better accuracy
3. **Use "Process ONLY missing CEOs"** mode for re-runs
4. **Process in batches** for very large datasets

## 📞 Support

For issues or questions:
1. Check the **Live Log** in the app for error details
2. Review the **Results Analysis** for processing insights
3. Ensure all **API keys** are valid and have sufficient credits

---
Made with ❤️ for efficient CEO research
