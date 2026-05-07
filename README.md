# Product Search LLM

An AI-powered product parsing and search system that transforms messy e-commerce queries into structured product intelligence using Large Language Models (LLMs), semantic matching, and intelligent normalization.

Built for real-world e-commerce search scenarios where users type incomplete, noisy, multilingual, or highly compressed product queries such as:

```text
16 pro max 256 desert
s24 ultra black 512
airpods pro type c
```

The system intelligently extracts product attributes, normalizes them into structured JSON, and prepares them for downstream search, matching, ranking, or recommendation pipelines.

---

## 🚀 Features

- ✅ LLM-based product understanding
- ✅ Structured JSON extraction
- ✅ Handles incomplete and noisy queries
- ✅ Product attribute normalization
- ✅ E-commerce focused parsing pipeline
- ✅ Semantic product interpretation
- ✅ Supports compressed/mobile-style queries
- ✅ Multi-stage parsing architecture
- ✅ Designed for scalable search systems
- ✅ Easy API deployment with Docker
- ✅ Production-ready API deployment

---

## 🚀 Production Ready API

The API is currently deployed and actively serving production traffic with support for approximately **100 requests per minute**.

Designed with scalability in mind for real-world e-commerce search and product parsing workloads.

---

## 🧠 Example

### Input

```text
iphone 16 pro 512 desert
```

### Parsed Output

```json
{
  "brand": "Apple",
  "product_line": "iPhone 16 Pro",
  "storage": "512GB",
  "color": "Desert Titanium"
}
```

---

## 🏗️ Architecture

The system is designed around a multi-stage intelligent parsing pipeline:

```text
Raw Query
   ↓
LLM Parsing
   ↓
Attribute Extraction
   ↓
Normalization Layer
   ↓
Structured Product JSON
   ↓
Search / Matching / Ranking
```

The pipeline focuses on maximizing parsing accuracy while ensuring that no important user input is lost during extraction.

---

## 💡 Key Challenges Solved

### Messy User Queries

Users rarely search using clean product names.

Examples:

```text
15pm 256 nat
s25u blk
buds 3 pro white
```

This project handles:

- shorthand queries
- abbreviations
- compressed naming formats
- missing product words
- inconsistent ordering
- noisy search text
- typo-tolerant parsing

---

### Attribute Ambiguity

The parser intelligently differentiates between:

- storage
- RAM
- colors
- model variants
- product generations
- editions
- regional naming differences

---

### Missing Information Detection

The pipeline is designed to ensure the parsed output fully covers the original text input and can detect missing segments during parsing iterations.

This significantly reduces silent parsing failures in production search systems.

---

## ⚙️ Tech Stack

- Python
- FastAPI
- Docker
- LLM APIs
- JSON Schema Validation
- Semantic Parsing Pipelines

---

## 📦 Installation

Clone the repository:

```bash
git clone https://github.com/MuradAladdinzade/product-search-llm.git
cd product-search-llm
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run locally:

```bash
uvicorn app.main:app --reload
```

---

## 🐳 Docker

Build the container:

```bash
docker build -t product-search-llm .
```

Run the container:

```bash
docker run -p 8000:8000 --name product-search-llm product-search-llm
```

---

## 🔌 API Example

### Request

```json
{
  "query": "iphone 16 pro max 256 desert"
}
```

### Response

```json
{
  "brand": "Apple",
  "series": "iPhone 16",
  "model": "Pro Max",
  "storage": "256GB",
  "color": "Desert Titanium"
}
```

---

## 🎯 Use Cases

- E-commerce search engines
- Marketplace platforms
- Product matching systems
- AI shopping assistants
- Product recommendation systems
- Inventory normalization
- Query understanding pipelines
- Semantic search systems

---

## 📈 Future Improvements

- Hybrid vector + keyword retrieval
- Product catalog RAG integration
- Multi-language support
- Real-time ranking models
- Fine-tuned domain-specific LLMs
- User behavior-aware search ranking
- Catalog deduplication pipelines

---

## 👨‍💻 Author

**Murad Aladdinzade**

MS in Data Science @ Vanderbilt University  
AI Engineer | Data Scientist | Product-Oriented Builder

GitHub: https://github.com/MuradAladdinzade

---

## ⭐ Repository

If you found this project useful, consider starring the repository:

https://github.com/MuradAladdinzade/product-search-llm
