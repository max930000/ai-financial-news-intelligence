# AI Financial News Intelligence Platform

An AI-assisted financial news intelligence platform that automatically collects financial news, analyzes its sentiment and topic, generates concise summaries, and presents the results through a FastAPI-powered dashboard.

The project is designed as an end-to-end AI pipeline rather than a standalone machine learning demo:

**News Collection → Data Storage → AI Processing → API → Dashboard → Event Intelligence**

---

## Project Motivation

Financial news arrives continuously from many different sources, making it difficult to quickly understand:

* What is happening?
* Which topics are receiving attention?
* Is the overall tone positive, neutral, or negative?
* Which articles are actually discussing the same event?

Instead of manually reading every article, this project explores how NLP models can transform raw financial news into structured information.

The current system automatically performs three AI tasks:

1. **Sentiment Analysis**
2. **Topic Classification**
3. **News Summarization**

The next stage of the project will extend this pipeline with **Event Clustering**, allowing multiple articles about the same financial event to be grouped together.

---

# Current Project Status

| Sprint     | Feature                         | Status         |
| ---------- | ------------------------------- | -------------- |
| Sprint 1   | News Data Collection            | ✅ Completed    |
| Sprint 2   | AI Processing                   | ✅ Completed    |
| Sprint 2.5 | Dashboard AI Result Integration | 🚧 In Progress |
| Sprint 3   | Event Clustering                | 🔜 Next        |

The current local database contains approximately **50+ collected financial news records**, with AI analysis results gradually being backfilled into existing rows.

---

# System Architecture

```text
                     Financial News Sources
                              │
                              ▼
                        RSS Collector
                              │
                              ▼
                      Data Normalization
                              │
                              ▼
                     SQLite / SQLAlchemy
                         News Database
                              │
              ┌───────────────┼────────────────┐
              │               │                │
              ▼               ▼                ▼
           FinBERT       BART-MNLI        DistilBART
         Sentiment        Topic            Summary
          Analysis     Classification      Generation
              │               │                │
              └───────────────┼────────────────┘
                              │
                              ▼
                       Enriched News Data
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
                FastAPI API         Dashboard
                    │
                    ▼
             Event Clustering
               (Next Stage)
```

---

# Data Pipeline

## 1. News Collection

Financial news is collected from RSS feeds and normalized into a consistent internal structure.

Each article contains fields such as:

```text
title
url
source
author
published_at
description
content
```

The collection module is intentionally separated from database and AI logic.

This keeps each component responsible for only one stage of the pipeline.

```text
RSS Feed
   │
   ▼
RSSCollector
   │
   ▼
Normalized NewsItem
   │
   ▼
SQLite Database
```

---

## 2. Database Layer

The project currently uses:

* **SQLite**
* **SQLAlchemy ORM**

The main database is stored locally as:

```text
data/news.db
```

The `News` model stores both the original article data and the generated AI results.

Conceptually, each record contains:

```text
News
├── id
├── title
├── url
├── source
├── author
├── published_at
├── description
├── content
│
├── sentiment
├── sentiment_score
├── category
├── summary
├── ai_model
└── analyzed_at
```

This structure allows the AI pipeline to enrich the original news records without creating a separate dataset.

---

# AI Processing Pipeline

The AI processing layer currently performs three independent NLP tasks.

## Sentiment Analysis — FinBERT

Model:

```text
FinBERT
```

FinBERT is used to classify the financial sentiment of each news article.

Output:

```json
{
  "label": "positive",
  "score": 0.9287
}
```

Supported labels:

```text
positive
neutral
negative
```

The result is stored as:

```text
News.sentiment
News.sentiment_score
```

---

## Topic Classification — BART-MNLI

Model:

```text
facebook/bart-large-mnli
```

The project uses **zero-shot classification** to categorize financial news without requiring a custom labeled training dataset.

Example categories include:

```text
Economy
Markets
Companies
Technology
Finance
Politics
```

Example:

```text
"Nvidia reports stronger-than-expected AI chip revenue"

        ↓

Technology
```

The result is stored in:

```text
News.category
```

Using predefined categories also prevents inconsistent labels such as:

```text
Tech
Technology
AI Technology
Technology News
```

which would make later analytics and clustering more difficult.

---

## News Summarization — DistilBART

Model:

```text
sshleifer/distilbart-cnn-12-6
```

The summarization module generates a shorter representation of the RSS article description.

Rather than blindly summarizing every article, the pipeline includes a small data-quality guard.

Before generating a summary, the system checks whether the article title and description appear to refer to the same story.

If they are inconsistent:

```text
Title:
Company A reports record earnings

Description:
A completely unrelated story about Country B...
```

the summarizer skips the record instead of creating a confident but misleading summary.

Example log:

```text
[SKIP-SUMMARY] title/description mismatch, summary left empty
```

This decision was introduced after observing mismatched RSS title/description pairs in real collected data.

---

# AI Orchestration

The AI models are intentionally separated from the orchestration logic.

The analysis runner performs the following process:

```text
Fetch News with Missing AI Fields
              │
              ▼
      Build Article Text
              │
       ┌──────┼───────┐
       ▼      ▼       ▼
 Sentiment  Topic   Summary
       │      │       │
       └──────┼───────┘
              ▼
       Update News Row
              │
              ▼
           Commit
```

The pipeline also supports **per-field backfilling**.

For example, if an existing article already contains:

```text
sentiment = positive
category  = Technology
summary   = NULL
```

the pipeline only generates the missing `summary`.

It does not rerun the sentiment and topic models unnecessarily.

This makes the processing pipeline:

* repeatable
* incremental
* safer for previously analyzed data

A failure on one article is also isolated so that it does not abort the entire batch.

---

# AI Models

The current AI pipeline uses:

| Task                 | Model           |
| -------------------- | --------------- |
| Financial Sentiment  | FinBERT         |
| Topic Classification | BART Large MNLI |
| News Summarization   | DistilBART CNN  |
| Event Clustering     | Planned         |

The database records the model pipeline using an identifier similar to:

```text
finbert+bart-large-mnli+distilbart-cnn-12-6
```

This helps track how each article was analyzed.

---

# FastAPI Backend

The application exposes a lightweight read-only API built with **FastAPI**.

Current endpoints:

```text
GET /news
GET /news/{news_id}
GET /analytics/sentiment
GET /dashboard
```

---

## `GET /news`

Returns the collected news articles ordered from newest to oldest.

Example fields:

```json
{
  "id": 52,
  "title": "Example Financial News",
  "source": "BBC",
  "published_at": "2026-09-15T10:30:00",
  "category": "Economy",
  "sentiment": "negative",
  "sentiment_score": 0.91
}
```

---

## `GET /news/{news_id}`

Returns the complete information for a single article.

This includes both original article data and AI-generated results.

```text
Original Data
+
AI Sentiment
+
Topic Category
+
AI Summary
```

---

## `GET /analytics/sentiment`

Returns aggregated sentiment statistics.

Example:

```json
{
  "total": 52,
  "analyzed": 52,
  "unanalyzed": 0,
  "positive": 18,
  "neutral": 21,
  "negative": 13,
  "average_score": 0.87
}
```

Values depend on the current database contents.

---

# Dashboard

The project also includes a server-rendered dashboard using:

* FastAPI
* Jinja2
* Chart.js
* HTML / CSS

The dashboard currently displays:

```text
Total News

Positive News

Neutral News

Negative News

Average AI Confidence

Sentiment Distribution

Recent Financial News
```

The current Sprint 2.5 extends each news card with:

```text
Category
Sentiment
Confidence
AI Summary
Source
Published Time
```

Example concept:

```text
┌────────────────────────────────────────────────────┐
│ TECHNOLOGY                           POSITIVE 92.8% │
│                                                    │
│ Nvidia reports stronger AI chip demand             │
│                                                    │
│ AI SUMMARY                                         │
│ Nvidia reported stronger revenue as demand for     │
│ artificial intelligence chips continued to grow.  │
│                                                    │
│ BBC · 2026-09-15 14:20                            │
└────────────────────────────────────────────────────┘
```

The goal is not simply to visualize database rows, but to clearly demonstrate the transformation:

```text
Raw News
   ↓
AI Processing
   ↓
Structured Financial Intelligence
```

---

# Project Structure

```text
ai-financial-news-intelligence/
│
├── data/
│   └── news.db
│
├── scripts/
│
├── src/
│   │
│   ├── ai/
│   │   ├── sentiment.py
│   │   ├── topic.py
│   │   ├── summarizer.py
│   │   └── run_analysis.py
│   │
│   ├── api/
│   │   ├── main.py
│   │   ├── schemas.py
│   │   │
│   │   ├── templates/
│   │   │   └── dashboard.html
│   │   │
│   │   └── static/
│   │       └── style.css
│   │
│   ├── database/
│   │   ├── database.py
│   │   └── models.py
│   │
│   └── ...
│
├── tests/
│
├── check_database.py
├── requirements.txt
├── .env.example
└── README.md
```

> The exact structure may continue to evolve as Event Clustering is implemented.

---

# Technology Stack

### Backend

```text
Python
FastAPI
SQLAlchemy
Pydantic
SQLite
Jinja2
```

### AI / NLP

```text
PyTorch
Hugging Face Transformers
FinBERT
BART
DistilBART
```

### Data Collection

```text
RSS
feedparser
```

### Frontend / Visualization

```text
HTML
CSS
Jinja2
Chart.js
```

---

# Running the Project

Clone the repository:

```bash
git clone https://github.com/yanwei12/ai-financial-news-intelligence.git
cd ai-financial-news-intelligence
```

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS / Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Run AI Analysis

From the project root:

```bash
python -m src.ai.run_analysis
```

The script finds news records that are missing one or more AI fields and fills them incrementally.

Example output:

```text
Found 10 news item(s) with missing AI fields.

[OK] id=40 sentiment=neutral (0.503)
category=Economy
summary='Tips are central to US dining culture...'
```

---

## Start FastAPI

```bash
uvicorn src.api.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/dashboard
```

Interactive API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

---

# Why Multiple Models?

Instead of asking one general-purpose model to perform every task, the project separates the NLP responsibilities.

```text
FinBERT
Financial-domain sentiment understanding

BART-MNLI
Flexible zero-shot topic classification

DistilBART
Sequence-to-sequence news summarization
```

This design makes each model's responsibility explicit and allows individual components to be replaced or evaluated independently.

It also makes the system easier to explain, debug, and extend.

---

# Design Decisions

Several implementation decisions were made intentionally.

### Incremental AI Processing

Only missing AI fields are processed.

This avoids unnecessary model inference when rerunning the pipeline.

### Fixed Topic Categories

Topic classification uses predefined candidate labels instead of generating arbitrary category names.

This creates structured data that can later be aggregated and clustered.

### Data Quality Guard Before Summarization

Articles with obviously mismatched titles and descriptions are not summarized.

This prioritizes reliable output over always generating an answer.

### Simple Database Architecture

SQLite and SQLAlchemy are currently sufficient because the project is a prototype with a relatively small dataset.

The focus is on validating the AI and information-processing pipeline before introducing unnecessary infrastructure complexity.

### Lightweight API Architecture

The FastAPI layer currently queries SQLAlchemy directly instead of introducing repository and service layers.

The current application logic is small enough that additional abstraction would increase complexity without providing meaningful benefit.

---

# Next Step — Event Clustering

The next major feature is **Event Clustering**.

Currently:

```text
Article A → Nvidia releases earnings
Article B → Nvidia revenue exceeds estimates
Article C → Nvidia shares rise after earnings
```

are treated as three independent news records.

The next stage will attempt to identify that they describe the same underlying event:

```text
                 ┌─ Article A
Nvidia Earnings ─┼─ Article B
                 └─ Article C
```

The goal is to transform the project from a **news analyzer** into a more complete **news intelligence system**.

Possible future pipeline:

```text
News Articles
     │
     ▼
Text Embeddings
     │
     ▼
Similarity Calculation
     │
     ▼
Event Clustering
     │
     ▼
Event-level Summary
```

---

# Future Improvements

Planned or possible improvements include:

* Event clustering
* Semantic embeddings
* Similarity-based related-news detection
* Event-level summaries
* Category distribution analytics
* Time-series sentiment monitoring
* Additional RSS sources
* Automatic ingestion scheduling
* Search and filtering
* Larger database support
* Model evaluation metrics
* Deployment

---

# Project Goal

This project is not intended to predict stock prices or provide investment advice.

Its goal is to explore how modern NLP models can transform large amounts of financial news into structured, readable, and analyzable information.

The final direction is:

```text
Collect
   ↓
Understand
   ↓
Structure
   ↓
Aggregate
   ↓
Present
```

turning raw financial news into an AI-assisted financial intelligence workflow.

---

## Repository

GitHub:

`https://github.com/yanwei12/ai-financial-news-intelligence`
