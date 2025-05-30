@echo off
echo 🚀 CEO Finder Pro - Setup Script
echo ===============================
echo.

echo 📦 Installing required Python packages...
pip install -r requirements.txt

echo.
echo ✅ Setup complete!
echo.
echo 📋 Next steps:
echo 1. Create a .env file with your API keys
echo 2. Run: python ceo_finder_gui.py
echo.
echo 🔑 Required API keys in .env file:
echo OPENAI_API_KEY=your_openai_key_here
echo.
echo 💡 Optional API keys for better results:
echo GEMINI_API_KEY=your_gemini_key
echo ANTHROPIC_API_KEY=your_anthropic_key
echo GOOGLE_SEARCH_API_KEY=your_google_search_key
echo GOOGLE_SEARCH_CX=your_custom_search_engine_id
echo HUNTER_API_KEY=your_hunter_key
echo APOLLO_API_KEY=your_apollo_key
echo ROCKETREACH_API_KEY=your_rocketreach_key
echo.
pause