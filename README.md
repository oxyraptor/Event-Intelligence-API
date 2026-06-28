# Event Intelligence API

FastAPI backend for collecting user events, running analytics, searching events by semantic meaning, and finding users with similar behavior.

## 1. Setup Instructions

### Requirements

- Python 3.12 
- `pip`
- Optional: a virtual environment

### Install and Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a local environment file:

```powershell
Copy-Item .env.example .env
```

Apply database migrations:

```powershell
alembic upgrade head
```

Start the API:

```powershell
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

### Configuration

The application reads settings from `.env`.

| Variable | Default | Description |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./assignment.db` | SQLAlchemy database connection string. |
| `CHROMA_PERSIST_DIRECTORY` | `./chroma_data` | Directory used by the local vector store. |
| `CHROMA_COLLECTION_NAME` | `events` | Name used for the vector storage file. |
| `EMBEDDING_MODEL_NAME` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model name recorded with events. |
| `SEARCH_MIN_SCORE` | `0.35` | Default minimum semantic search score. |
| `AUTO_CREATE_TABLES` | `true` | Creates database tables at startup when enabled. |

### Run Tests

```powershell
pytest
```

## 2. API Documentation

### Health Check

Checks whether the API is running.

```http
GET /health
```

Sample response:

```json
{
  "status": "ok"
}
```

### Track Event

Stores a user event in the relational database and indexes its text representation for semantic search.

```http
POST /track
Content-Type: application/json
```

Sample request:

```json
{
  "userId": "user_123",
  "event": "product_viewed",
  "timestamp": "2026-06-27T18:00:00Z",
  "metadata": {
    "productId": "sku_456",
    "category": "electronics",
    "price": 1299
  }
}
```

Sample response:

```json
{
  "event": {
    "id": "4f75e0c4-9db1-49e7-8d76-4db4a4d2a62f",
    "userId": "user_123",
    "event": "product_viewed",
    "timestamp": "2026-06-27T18:00:00Z",
    "createdAt": "2026-06-27T18:00:02.100000",
    "metadata": {
      "productId": "sku_456",
      "category": "electronics",
      "price": 1299
    },
    "rawText": "product_viewed -- category: electronics | price: 1299 | productId: sku_456",
    "embeddingModel": "sentence-transformers/all-MiniLM-L6-v2"
  },
  "vectorIndexed": true
}
```

Notes:

- `timestamp` is optional. If omitted, the event is still stored with a server-side `createdAt` value.
- `metadata` defaults to an empty object.
- If vector indexing fails, the event remains persisted and `vectorIndexed` is returned as `false`.

### Analytics

Returns aggregate event counts, distinct user counts, event breakdowns, and top users.

```http
GET /analytics
```

Query parameters:

| Parameter | Required | Description |
| --- | --- | --- |
| `event` | No | Filter by event name. |
| `userId` | No | Filter by user ID. |
| `from` | No | Start timestamp filter. |
| `to` | No | End timestamp filter. |
| `topN` | No | Number of top users to return. Default `10`, max `100`. |

Sample request:

```http
GET /analytics?event=product_viewed&from=2026-06-01T00:00:00Z&to=2026-06-30T23:59:59Z&topN=5
```

Sample response:

```json
{
  "totalCount": 42,
  "distinctUsers": 12,
  "eventBreakdown": [
    {
      "key": "product_viewed",
      "count": 42
    }
  ],
  "topUsers": [
    {
      "key": "user_123",
      "count": 8
    },
    {
      "key": "user_987",
      "count": 5
    }
  ]
}
```

Error response when `from` is after `to`:

```json
{
  "detail": "from must be less than or equal to to"
}
```

### Semantic Search

Searches indexed events using an embedded query and returns matching stored events.

```http
GET /search
```

Query parameters:

| Parameter | Required | Description |
| --- | --- | --- |
| `query` | Yes | Search text. |
| `topK` | No | Maximum number of vector matches to inspect. Default `10`, max `50`. |
| `minScore` | No | Minimum score to include. Defaults to `SEARCH_MIN_SCORE`. |

Sample request:

```http
GET /search?query=electronics%20products&topK=3&minScore=0.25
```

Sample response:

```json
{
  "query": "electronics products",
  "results": [
    {
      "event": {
        "id": "4f75e0c4-9db1-49e7-8d76-4db4a4d2a62f",
        "userId": "user_123",
        "event": "product_viewed",
        "timestamp": "2026-06-27T18:00:00Z",
        "createdAt": "2026-06-27T18:00:02.100000",
        "metadata": {
          "productId": "sku_456",
          "category": "electronics",
          "price": 1299
        },
        "rawText": "product_viewed -- category: electronics | price: 1299 | productId: sku_456",
        "embeddingModel": "sentence-transformers/all-MiniLM-L6-v2"
      },
      "score": 0.82
    }
  ]
}
```

### Similar Users

Finds users whose stored event embeddings are most similar to a target user's event profile.

```http
GET /similar-users
```

Query parameters:

| Parameter | Required | Description |
| --- | --- | --- |
| `userId` | Yes | Target user ID. |
| `topN` | No | Number of similar users to return. Default `5`, max `50`. |

Sample request:

```http
GET /similar-users?userId=user_123&topN=3
```

Sample response:

```json
{
  "userId": "user_123",
  "results": [
    {
      "userId": "user_987",
      "score": 0.91
    },
    {
      "userId": "user_555",
      "score": 0.77
    }
  ]
}
```

Sample not-found response:

```json
{
  "detail": "No events found for user_id=user_123"
}
```

## 3. Design Decisions

### FastAPI for the HTTP Layer

FastAPI provides request validation, response serialization, generated OpenAPI documentation, and dependency injection with minimal boilerplate. Pydantic schemas define the external API contract separately from the database models.

### Relational Database as the Source of Truth

Events are stored first in the SQL database through SQLAlchemy. This keeps structured event data reliable and queryable for analytics. The vector index is treated as a derived search structure, not the primary store.

### Vector Indexing After Persistence

`POST /track` writes the event row before attempting vector indexing. If indexing fails, the API logs the failure and returns `vectorIndexed: false` while preserving the event. This avoids losing analytics data because of an embedding or vector-store problem.

### Search Hydrates Results from the Database

Semantic search uses the vector store to find candidate event IDs, then loads the full event records from the database. This avoids duplicating the complete event payload in vector storage and keeps responses consistent with the relational source of truth.

### Deterministic Embedding Fallback

The embedding service attempts to use `sentence-transformers` when available. If the model cannot be loaded, it falls back to a deterministic hash-based embedding. This keeps local development and tests usable even without downloading a model.

### User Similarity by Average Event Profile

Similar-user matching averages each user's event embeddings into a normalized profile vector. The service compares users with cosine similarity and returns the highest-scoring users. This is simple, explainable, and works well for an assignment-scale event dataset.

### Service and Repository Separation

Routes stay thin and delegate business logic to services. Database access is isolated in the repository layer. This makes endpoints easier to read, keeps SQL concerns in one place, and makes the application easier to test.

