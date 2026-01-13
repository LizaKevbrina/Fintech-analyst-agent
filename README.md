<div align="center">

# FinTech Analyst Agent

AI-powered финансовый аналитик для автоматического анализа отчетов, извлечения KPI и распознавания графиков

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)]()
[![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen.svg)]()
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

</div>

---

🔍 Что делает этот агент

### AI-финансовый аналитик документов

**Описание**  
AI-агент анализирует финансовые отчёты компаний:
- извлекает текст, таблицы и графики  
- находит ключевые метрики (выручка, EBITDA, ROE, рост)  
- сопоставляет отчёты с архивом  
- возвращает **структурированный результат**, готовый для BI и аналитики  

**Зачем бизнесу**
- ускоряет анализ отчётов в **3–5 раз**
- снижает нагрузку на аналитиков
- минимизирует человеческие ошибки
- масштабируется под поток документов
  
##  Ключевые возможности
- ✅ Анализ финансовых отчётов (PDF, Excel)
- ✅ Извлечение KPI в структурированном виде
- ✅ Распознавание и анализ графиков (Vision API)
- ✅ Семантический поиск по архиву отчётов (RAG)
- ✅ SQL-генерация и вычисления через инструменты
- ✅ Валидация результатов (Pydantic)
- ✅ REST API для интеграции в бизнес-системы

---

##  Architecture

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │ Upload PDF/Excel
       ↓
┌─────────────────────────────┐
│   FastAPI Endpoint          │
│   - Rate Limiting           │
│   - Input Validation        │
└──────┬──────────────────────┘
       │
       ↓
┌─────────────────────────────┐
│   FinancialAnalystAgent     │
│   (SmolAgents)              │
├─────────────────────────────┤
│   Tools:                    │
│   - PDF Parser              │
│   - Excel Parser            │
│   - Vision Analyzer         │
│   - FAISS Search            │
│   - Calculator              │
│   - SQL Generator (CodeAgent)│
└──────┬──────────────────────┘
       │
       ↓
┌─────────────────────────────┐
│   Structured Output         │
│   (Pydantic Validation)     │
└─────────────────────────────┘
```

### Agent Workflow
```
1. Document Parsing
   ├── PDF: pdfplumber → extract text, tables, images
   └── Excel: openpyxl → extract sheets, formulas

2. Semantic Search (FAISS)
   └── Find similar reports in archive

3. Chart Analysis (Vision API)
   ├── Extract charts from document
   ├── Send to Claude Vision
   ├── Graceful degradation if API fails
   └── Return structured ChartAnalysis

4. KPI Extraction (ToolCallingAgent)
   ├── Build extraction prompt
   ├── Use tools: search, calculate, SQL generate
   ├── Extract metrics from text/tables
   └── Validate with Pydantic

5. Result Assembly
   └── Create AnalysisResult with all data
```

---
##  Technology Stack

| Category | Technology |
|----------|-----------|
| **AI Framework** | SmolAgents (HuggingFace) |
| **LLM** | Claude 3.5 Sonnet (Anthropic) |
| **Vector DB** | FAISS (in-memory) |
| **Embeddings** | SentenceTransformers (multilingual) |
| **Vision** | Claude Vision API |
| **API** | FastAPI + Uvicorn |
| **Validation** | Pydantic v2 |
| **Logging** | Loguru |
| **Testing** | pytest + pytest-asyncio |
| **Containerization** | Docker + docker-compose |

---

##  Installation

### Prerequisites
- Python 3.11+
- Poetry (package manager)
- Docker & Docker Compose (опционально)
- Anthropic API key

### Quick Start (Local)

```bash
# 1. Clone repository
git clone https://github.com/yourusername/fintech-analyst-agent.git
cd fintech-analyst-agent

# 2. Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# 3. Install dependencies
poetry install

# 4. Setup environment
cp .env.example .env
# Отредактируй .env и добавь ANTHROPIC_API_KEY

# 5. Run migrations (если используется DB)
poetry run alembic upgrade head

# 6. Start API server
poetry run uvicorn src.api.main:app --reload

# 7. Open Swagger docs
open http://localhost:8000/docs
```

### Quick Start (Docker)

```bash
# 1. Clone & setup .env
git clone https://github.com/yourusername/fintech-analyst-agent.git
cd fintech-analyst-agent
cp .env.example .env
# Добавь API keys в .env

# 2. Build & Run
docker-compose up --build

# 3. Access API
open http://localhost:8000/docs
```

---

##  Security

### Input Validation
- ✅ File size limits (10MB)
- ✅ File type whitelist (.pdf, .xlsx, .xls)
- ✅ Executable file detection
- ✅ SQL injection protection
- ✅ HTML/XSS sanitization

### API Security
- ✅ Rate limiting (10 requests/minute)
- ✅ CORS configuration
- ✅ Input sanitization
- ✅ Error message sanitization (no stack traces in production)

### Environment Variables
```bash
# Never commit .env file!
# Use .env.example as template
# Rotate API keys regularly
```
---

## 🐛 Troubleshooting

### Common Issues

#### 1. "FAISS index not found"
```bash
# Create embeddings directory
mkdir -p data/embeddings

# Index will be created automatically on first use
```

#### 2. "Vision API error"
```bash
# Check API key
echo $ANTHROPIC_API_KEY

# Enable fallback mode
VISION_FALLBACK_ENABLED=True

# Check logs
tail -f logs/errors.log
```

#### 3. "Rate limit exceeded"
```bash
# Increase limit in .env
RATE_LIMIT_PER_MINUTE=20

# Or wait 1 minute
```

#### 4. Docker build fails
```bash
# Clear cache
docker-compose down
docker system prune -a

# Rebuild
docker-compose up --build
```
---

##  Performance

### Benchmarks (на MacBook Pro M1, 16GB RAM)

| Task | Duration | Notes |
|------|----------|-------|
| PDF parsing (10 pages) | ~2s | pdfplumber |
| Chart analysis | ~3-5s | Claude Vision API |
| FAISS search (1000 docs) | ~50ms | In-memory |
| Full analysis | ~8-12s | End-to-end |

### Optimization Tips
- Use FAISS GPU version для больших индексов
- Кэшировать embeddings для часто используемых документов
- Batch processing для множества документов
- Использовать Redis для кэширования результатов

---

##  Лицензия

MIT License — см. [LICENSE](LICENSE)

---

<div align="center">

## 👩‍💻 Автор

**Елизавета Кевбрина**

*Prompt Engineer • AI Engineer*

[![Email](https://img.shields.io/badge/Email-elisa.kevbrina%40yandex.ru-red?style=flat-square&logo=gmail)](mailto:elisa.kevbrina@yandex.ru)
[![GitHub](https://img.shields.io/badge/GitHub-%40LizaKevbrina-black?style=flat-square&logo=github)](https://github.com/LizaKevbrina)

---

**⭐ Если проект полезен, поставьте звезду!**

*Made with ❤️ for AI engineering community*

</div>
