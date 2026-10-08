# Complete RAG Learning Guide

A structured roadmap to learn **Retrieval-Augmented Generation (RAG)** from prerequisites to advanced techniques.

---

## Part 1: Prerequisites (What to Learn Before RAG)

### 1.1 Python & Core Programming
- **Python fundamentals**: data structures, functions, classes, async/await
- **Libraries**: `numpy`, `pandas`, `requests`, `pydantic`, `fastapi`
- **Environment management**: `venv`, `poetry`, or `uv`

### 1.2 Machine Learning Basics
- **Supervised vs unsupervised learning**
- **Loss functions, gradient descent, backpropagation** (conceptual level)
- **Overfitting, regularization, train/test split**
- **Evaluation metrics**: precision, recall, F1, accuracy

### 1.3 Natural Language Processing (NLP) Foundations
- **Tokenization** — breaking text into tokens (BPE, WordPiece, SentencePiece)
- **Stop words, stemming, lemmatization**
- **TF-IDF** — classical text representation
- **N-grams, bag-of-words**
- **Named Entity Recognition (NER), POS tagging**

### 1.4 Deep Learning for NLP
- **Word embeddings**: Word2Vec, GloVe, FastText
- **Sequence models**: RNN, LSTM, GRU (conceptual)
- **Attention mechanism**
- **Transformer architecture** — encoder, decoder, self-attention, multi-head attention
- **Pretraining vs fine-tuning**

### 1.5 Large Language Models (LLMs)
- **How LLMs work**: next-token prediction, causal language modeling
- **Popular models**: GPT family, Claude, Llama, Mistral, Gemini
- **Context window, temperature, top-p, top-k sampling**
- **Prompt engineering basics**: zero-shot, few-shot, chain-of-thought
- **LLM limitations**: hallucinations, knowledge cutoff, context length limits

### 1.6 Vector Mathematics
- **Vectors, dot product, cosine similarity, Euclidean distance**
- **Dimensionality and high-dimensional spaces**
- **Matrix operations** (basic linear algebra)

### 1.7 Databases & APIs
- **SQL basics** and NoSQL concepts
- **REST APIs** and JSON handling
- **Basic understanding of indexing**

---

## Part 2: Core RAG Concepts

### 2.1 What is RAG?
**Definition**: Retrieval-Augmented Generation is an architecture that combines a **retriever** (which fetches relevant documents from an external knowledge base) with a **generator** (an LLM) to produce grounded, up-to-date, and factual responses.

**Why RAG?**
- Overcomes LLM knowledge cutoff
- Reduces hallucinations
- Enables domain-specific answers without fine-tuning
- Provides source attribution

### 2.2 The RAG Pipeline
```
User Query → Embed Query → Retrieve Top-K Docs → Augment Prompt → LLM → Response
```

### 2.3 Key Components
1. **Document Loader** — ingests PDFs, HTML, DOCX, Markdown, etc.
2. **Text Splitter / Chunker** — breaks documents into manageable pieces
3. **Embedding Model** — converts text into dense vectors
4. **Vector Store** — stores and indexes embeddings
5. **Retriever** — finds relevant chunks for a query
6. **LLM (Generator)** — produces the final answer
7. **Prompt Template** — structures how retrieved context is passed to the LLM

### 2.4 Embeddings
**Definition**: Dense vector representations of text that capture semantic meaning.
- **Popular models**: OpenAI `text-embedding-3-large`, Cohere Embed, `sentence-transformers` (BGE, E5, MPNet), Voyage AI
- **Dimensions**: typically 384, 768, 1024, 1536, or 3072
- **Trade-offs**: larger dims = better recall, higher cost/storage

### 2.5 Chunking Strategies
- **Fixed-size chunking** — split by N characters/tokens
- **Recursive chunking** — split by hierarchy (paragraphs → sentences)
- **Semantic chunking** — split at semantic boundaries using embeddings
- **Document-structure-aware** — respect headings, sections, tables
- **Chunk overlap** — preserves context across boundaries (typically 10-20%)

### 2.6 Vector Databases
- **Purpose**: Store embeddings and perform fast Approximate Nearest Neighbor (ANN) search
- **Popular options**: Pinecone, Weaviate, Milvus, Qdrant, Chroma, pgvector, FAISS, LanceDB
- **Index types**: HNSW, IVF, PQ (Product Quantization), ScaNN

### 2.7 Retrieval Methods
- **Dense retrieval** — semantic search using embeddings
- **Sparse retrieval** — keyword-based (BM25, TF-IDF)
- **Hybrid retrieval** — combines dense + sparse (best of both)
- **Similarity metrics**: cosine, dot product, Euclidean

---

## Part 3: Advanced RAG Topics

### 3.1 Query Transformation
**Definition**: Rewriting or expanding the user's query before retrieval to improve results.
- **Query rewriting** — LLM rephrases the query for clarity
- **HyDE (Hypothetical Document Embeddings)** — LLM generates a hypothetical answer, then embeds and searches with it
- **Multi-query** — generate multiple query variations, retrieve for each, merge
- **Step-back prompting** — generate a more abstract/general query first
- **Sub-question decomposition** — break complex queries into sub-questions

### 3.2 Advanced Retrieval Techniques

#### Hybrid Search
Combines dense (semantic) and sparse (BM25) retrieval, then fuses results using **Reciprocal Rank Fusion (RRF)** or weighted scoring.

#### Re-ranking
**Definition**: A second-stage model (usually a cross-encoder) re-scores the top-K retrieved documents for better precision.
- Models: Cohere Rerank, BGE Reranker, ColBERT, MonoT5
- Trade-off: adds latency but greatly improves relevance

#### Maximum Marginal Relevance (MMR)
Balances **relevance** and **diversity** in retrieved results to avoid redundant chunks.

#### Contextual Compression
Filters or compresses retrieved chunks to keep only the parts relevant to the query, reducing prompt size.

### 3.3 Advanced Chunking

#### Parent-Child (Small-to-Big) Retrieval
Embed small chunks for precise matching, but return larger parent chunks to give the LLM more context.

#### Sentence-Window Retrieval
Match on a single sentence but expand to surrounding sentences before passing to LLM.

#### Auto-Merging Retrieval
If multiple child chunks from the same parent are retrieved, return the parent instead.

### 3.4 Indexing Strategies

#### Multi-Vector Indexing
Store multiple embeddings per document (e.g., summary + full text + hypothetical questions).

#### Hierarchical Indexing
Build a tree of summaries — retrieve at coarse level, drill down as needed (e.g., **RAPTOR**).

#### Metadata Filtering
Attach metadata (date, author, category) to chunks; filter before or after vector search.

### 3.5 Agentic RAG
**Definition**: An LLM agent decides *when* and *how* to retrieve, potentially in multiple steps.
- **Self-querying retriever** — LLM builds structured queries with filters
- **Multi-hop reasoning** — retrieve, reason, retrieve again
- **Tool-using agents** — RAG as one tool among many (web search, calculators, APIs)
- **Frameworks**: LangGraph, LlamaIndex Agents, CrewAI

### 3.6 GraphRAG
**Definition**: Uses a **knowledge graph** (entities + relationships) alongside or instead of vector search to answer questions requiring multi-hop reasoning.
- Extract entities/relationships from documents into a graph
- Query graph structure + text chunks
- Excellent for connected/relational data (e.g., Microsoft GraphRAG)

### 3.7 Corrective & Self-Reflective RAG

#### CRAG (Corrective RAG)
Evaluates retrieved documents; if quality is low, falls back to web search or query rewriting.

#### Self-RAG
LLM generates special "reflection tokens" to decide whether to retrieve, and to critique its own output.

#### RAG Fusion
Generates multiple queries, retrieves for each, then fuses results using RRF.

### 3.8 Long-Context vs RAG
Modern LLMs support 1M+ token contexts. Trade-offs:
- **Long context**: simpler, but expensive, slower, and "lost in the middle" problem
- **RAG**: cheaper, scalable to billions of docs, better attribution
- **Hybrid**: RAG for retrieval + long context for reasoning

### 3.9 Multimodal RAG
Extends RAG to images, tables, audio, and video.
- **Image embeddings**: CLIP, SigLIP
- **Table understanding**: extract structured data; use text2sql for querying
- **Document AI**: layout-aware parsing (LayoutLM, Unstructured.io, LlamaParse)

### 3.10 Evaluation of RAG Systems
**Frameworks**: RAGAS, TruLens, DeepEval, ARES, LangSmith

**Key metrics**:
- **Retrieval metrics**
  - **Context Precision** — are retrieved chunks relevant?
  - **Context Recall** — did we retrieve all needed info?
  - **MRR (Mean Reciprocal Rank)**, **NDCG**, **Hit Rate**
- **Generation metrics**
  - **Faithfulness / Groundedness** — is the answer supported by context?
  - **Answer Relevance** — does it address the query?
  - **Answer Correctness** — matches ground truth?
- **End-to-end**: LLM-as-a-judge, human evaluation

### 3.11 Fine-Tuning for RAG
- **Fine-tune embedding models** on domain data for better retrieval
- **Fine-tune the LLM** to better use retrieved context (RA-DIT, RAFT)
- **Instruction-tuning** for following retrieval-augmented prompts

### 3.12 Production Concerns

#### Caching
- Cache embeddings, retrieval results, and LLM outputs
- Semantic caching (return cached response for semantically similar queries)

#### Latency Optimization
- Async retrieval, batching, streaming responses
- Smaller/faster embedding models with re-rankers on top

#### Security
- **Prompt injection defense** — sanitize retrieved content
- **PII redaction** in ingested docs
- **Access control** — user-specific document filtering
- **Data poisoning** protection

#### Observability
- Log retrieval hits, latency, token usage
- Trace end-to-end (LangSmith, Langfuse, Arize Phoenix)
- Monitor for drift in embeddings/queries

#### Scaling
- Sharding vector indexes
- Distributed vector DBs
- Incremental indexing / real-time updates

### 3.13 Advanced Architectures

| Architecture | Description |
|---|---|
| **Naive RAG** | Basic retrieve → generate |
| **Advanced RAG** | Adds pre/post-retrieval optimizations (re-ranking, query transform) |
| **Modular RAG** | Composable modules: routing, memory, fusion, prediction |
| **Agentic RAG** | LLM orchestrates retrieval decisions |
| **GraphRAG** | Knowledge-graph augmented |
| **Recursive RAG** | Iterative retrieval and refinement |
| **Adaptive RAG** | Dynamically chooses strategy based on query complexity |

---

## Part 4: Frameworks & Tools

- **Orchestration**: LangChain, LlamaIndex, Haystack, DSPy
- **Vector DBs**: Pinecone, Weaviate, Qdrant, Milvus, Chroma, pgvector
- **Embeddings**: OpenAI, Cohere, Voyage, sentence-transformers, Nomic
- **Re-rankers**: Cohere Rerank, BGE, ColBERT
- **Document parsing**: Unstructured.io, LlamaParse, PyMuPDF, Docling
- **Evaluation**: RAGAS, TruLens, DeepEval, Langfuse
- **Deployment**: FastAPI, Modal, Ray Serve, BentoML

---

## Part 5: Suggested Learning Path

1. **Week 1-2**: Python + NLP basics + transformer intuition
2. **Week 3**: LLM fundamentals + prompt engineering
3. **Week 4**: Build a naive RAG (LangChain/LlamaIndex + Chroma + OpenAI)
4. **Week 5**: Learn chunking, embedding models, vector DBs deeply
5. **Week 6**: Hybrid search, re-ranking, query transformations
6. **Week 7**: Evaluation (RAGAS) + observability
7. **Week 8**: Agentic RAG, GraphRAG, multimodal RAG
8. **Week 9-10**: Production concerns — caching, security, scaling, deployment
9. **Ongoing**: Read papers — Original RAG (Lewis et al. 2020), Self-RAG, CRAG, RAPTOR, GraphRAG

---

## Key Papers to Read

- **RAG** (Lewis et al., 2020) — the original paper
- **REALM** (Guu et al., 2020) — retrieval pretraining
- **Atlas** (Izacard et al., 2022)
- **Self-RAG** (Asai et al., 2023)
- **CRAG** (Yan et al., 2024)
- **RAPTOR** (Sarthi et al., 2024)
- **GraphRAG** (Microsoft, 2024)
- **HyDE** (Gao et al., 2022)
- **Lost in the Middle** (Liu et al., 2023)
