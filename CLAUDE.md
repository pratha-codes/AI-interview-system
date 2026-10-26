# AI Interview System - Project Guide

## 🎯 What This Project Does

Yeh ek **AI Interview System** hai jo automatically job interviews conduct karta hai. Ek candidate apna resume aur job description deta hai, aur AI samjhe hue questions puchta hai. Candidate apne answers voice se record karta hai, aur AI automatically:
- Answer transcribe karta hai (speech-to-text)
- Answer ko analyze karta hai
- Score aur feedback deta hai

---

## 🚀 How to Run It (Simple Steps)

### Step 1: Setup Karo
```bash
# 1. Virtual environment banao
python -m venv .venv

# 2. Virtual environment activate karo
.venv\Scripts\activate  # Windows

# 3. Dependencies install karo
pip install -r requirements.txt
```

### Step 2: API Keys Add Karo
`.env` file create karo (`.env.example` se copy kar sakte ho):
```
MISTRAL_API_KEY="your-api-key-here"
LLM_MODEL="mistral/mistral-large-latest"
SPEECHMATICS_API_KEY="your-api-key-here"
```

**API Keys कहाँ से मिलेंगे:**
- **Mistral AI**: https://mistral.ai/ (free trial available)
- **Speechmatics**: https://www.speechmatics.com/ (speech-to-text ke liye)

### Step 3: App Run Karo
```bash
streamlit run app.py
```
Browser khud-ba-khud `http://localhost:8501` par khul jayega.

---

## 📁 Project Structure

```
.
├── app.py              # Main Streamlit UI
├── main.py             # Backend logic (LLM calls, interviews)
├── requirements.txt    # Python dependencies
├── .env.example        # API key template
├── utils/              # Helper functions
└── Dockerfile          # Docker config
```

---

## 🔄 How It Works (Flow)

1. **User Upload**: Resume (PDF) + Job Description
2. **Processing**: System resume aur job desc analyze karta hai
3. **Questions**: AI relevant questions generate karta hai
4. **Recording**: User apne answers voice se record karta hai
5. **Analysis**: System answers transcribe aur score deta hai
6. **Results**: Final report with scores aur feedback

---

## 🐳 Docker Ke Saath Run Karo (Optional)

```bash
# Build karo
make build

# Run karo
make run

# Rebuild aur run dono
make rebuild
```

---

## ⚠️ Important Notes

- **Browser**: Chrome use karo (audio recording ke liye)
- **Microphone**: Microphone access allow karna padega
- **Internet**: API calls ke liye internet zaroori hai
- **Async Mode**: LLM calls async hain (fast responses ke liye)

---

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| API key error | `.env` file check karo, keys sahi hain ka? |
| Mic not working | Chrome use karo, permission allow karo |
| Module not found | `pip install -r requirements.txt` phir se run karo |
| Port already in use | Port change karo: `streamlit run app.py --server.port 8502` |

---

## 📚 Key Technologies

- **Streamlit**: Web UI framework
- **LiteLLM**: Multi-LLM support (Mistral, OpenAI, etc.)
- **Speechmatics**: Speech-to-text
- **PyPDF**: Resume parsing

---

## 🎓 Next Steps

1. API keys generate karo
2. `.env` file setup karo
3. `streamlit run app.py` chalao
4. Resume upload karo aur interview lelo!
