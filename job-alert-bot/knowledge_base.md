# Project Knowledge Base

Write freely about each project below - no fixed format required, just
enough real detail (what you built, what tools you used, what the
outcome was) that the AI has facts to work with. Always include a
timeframe. Add as many projects as you want - just copy the "---"
separator pattern below for each new one.

---

## AI-Powered Job Discovery & Resume Automation
**Timeframe:** July 2026

Built a fully automated job-discovery system in Python that monitors
company career pages on a daily schedule via GitHub Actions, requiring
zero manual execution. Designed a platform auto-detection engine that
identifies a company's ATS (Greenhouse, Lever, Ashby, Workable,
SmartRecruiters, Workday) directly from its career page URL - via
direct domain matching, redirect-following, or scanning for embedded
widgets - with a schema.org structured-data fallback for fully
custom-built sites. Implemented a two-stage filtering pipeline: a
lightweight keyword pre-filter on job titles followed by LLM-based
classification of full job descriptions against experience-level and
location requirements. Built a multi-provider LLM fallback system (Groq
and Gemini) with automatic failover and task-specific routing, plus a
circuit-breaker mechanism that halts further AI calls for the rest of a
run if providers become unavailable, preventing wasted time. Developed
an AI-powered resume-tailoring pipeline that rewrites and reorders
resume content per job description under strict anti-fabrication
constraints, and computes a transparent keyword-coverage score against
each job's requirements. Built a LaTeX-based PDF rendering pipeline
using Jinja2 templating with full character-escaping. Implemented
persistent state tracking to prevent duplicate notifications and
self-healing removal of dead company URLs. Parallelized company
fetching for a ~7x speedup. Tech: Python, GitHub Actions, Groq API,
Google Gemini API, LaTeX (XeLaTeX), Jinja2, Brevo API, Requests, JSON,
REST APIs, ThreadPoolExecutor.

---

## Multimodal AI Assistant (RAG + Voice)
June 2026

Built a production-grade multimodal AI assistant using Python and
FastAPI, integrating document processing, semantic retrieval, LLMs,
speech recognition, and speech synthesis into one conversational
application. Processed documents (PDF, DOCX, TXT) using PyMuPDF,
python-docx, and BeautifulSoup, then cleaned, chunked, and converted
text into vector embeddings using Sentence Transformers (BGE). Stored
embeddings and metadata in ChromaDB to enable semantic search,
retrieving relevant document chunks via cosine similarity against user
query embeddings. Implemented a Retrieval-Augmented Generation (RAG)
pipeline that passed retrieved context to a Large Language Model (GPT)
to generate accurate, context-aware responses. Enabled voice
interaction end-to-end using OpenAI Whisper (speech-to-text) and OpenAI
TTS (text-to-speech). Used PostgreSQL for user data, chat history, and
document metadata; containerized the application with Docker and
Docker Compose. Tech: Python, FastAPI, PyMuPDF, python-docx,
BeautifulSoup, Sentence Transformers (BGE), ChromaDB, OpenAI Whisper,
OpenAI TTS, GPT, PostgreSQL, Docker, Docker Compose, Git, Postman.

---

## Data Analysis and Forecasting for Local SuperStore (US)
**Timeframe:** June 2026

Performed exploratory data analysis on sales data across regions,
products, and payment modes to uncover key business insights. Built
Python-based ETL pipelines for automated data cleaning, transformation,
and feature extraction. Designed interactive Power BI dashboards to
visualize sales trends, customer behavior, and product performance.
Developed predictive models in Python for 15-day sales forecasting,
improving inventory planning and marketing strategy. Created SQL
queries to extract and transform data for analytics. Tech: Power BI,
Python, Pandas, NumPy, SQL, Matplotlib, Excel.

---

## COVID Detection Using Machine Learning
**Timeframe:** Apr 2022 - May 2022

Developed a computer vision machine learning system to classify chest
radiography images and detect potential COVID-19 cases. Applied image
preprocessing techniques and implemented Artificial Neural Networks
(ANN) for classification. Conducted model benchmarking using accuracy,
recall, and F1-score metrics. Tech: Python, TensorFlow, Pandas, NumPy,
Matplotlib, Seaborn, Google Colab.

---

## [Add your next project here]
**Timeframe:**

Write about it here...
