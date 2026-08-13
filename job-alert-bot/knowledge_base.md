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

Developed an end-to-end Multimodal Retrieval-Augmented Generation (RAG) AI Assistant enabling users to interact with PDF, DOCX, TXT, Markdown, images, tables, charts, and voice queries using a completely local, zero-cost architecture. Built the document ingestion pipeline with PyMuPDF, python-docx, OCR, LangChain document loaders, semantic chunking, and metadata extraction, generating embeddings using BGE/Sentence Transformers and storing them in ChromaDB with HNSW-based approximate nearest-neighbor indexing.

Designed a stateful RAG workflow using LangGraph to orchestrate query processing, retrieval, reranking, context validation, response generation, citation extraction, and fallback handling. Used LangChain for LLM integration, prompt management, document abstractions, retrievers, and model/tool orchestration. Implemented multi-stage retrieval comprising query embedding, Top-K vector search, similarity filtering, deduplication, cross-encoder reranking, and context selection, before passing relevant evidence to locally hosted open-source LLMs through Ollama. Implemented grounded prompting, source citations, and unanswerable-query detection to reduce hallucinations and unsupported responses.

Integrated Faster-Whisper for local speech-to-text and open-source TTS for voice interaction. Extended the system with OCR and Vision-Language Models (VLMs) to process scanned pages, images, tables, and charts, enabling multimodal question answering over textual and visual context. Used PostgreSQL for users, documents, metadata, conversations, and application state, while ChromaDB handled semantic vector storage and retrieval. Developed the backend with FastAPI and containerized the complete system using Docker/Docker Compose.

Created an evaluation framework with 250+ benchmark questions covering factual, multi-hop, table, chart/image, and unanswerable queries. Evaluated retrieval using Recall@5, Precision@5, MRR, and NDCG@5, and RAG quality using Faithfulness, Context Precision, Context Recall, Answer Relevancy, and Multimodal Faithfulness. Established targets of ≥90% Recall@5, ≥85% Context Precision, ≥85% Context Recall, ≥90% Faithfulness, ≥85% Answer Relevancy, <300 ms retrieval latency, and <3 s P95 end-to-end latency. Maintained the complete implementation, evaluation suite, automated tests, documentation, and reproducible setup in a public GitHub repository.

Tech Stack: Python, FastAPI, LangChain, LangGraph, ChromaDB, PostgreSQL, BGE/Sentence Transformers, Cross-Encoder Reranker, Ollama, Open-Source LLMs/VLMs, Faster-Whisper, TTS, OCR, PyMuPDF, python-docx, Docker, Docker Compose, Git, GitHub, RAGAS, NumPy, Pandas.

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
