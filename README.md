# raysearch-sdk-py

Python SDK for the RaySearch personal API service.

The SDK provides:
- top-level `RaySearch` and `AsyncRaySearch` clients
- search, fetch, and answer helpers
- a dedicated `research` client for async research task workflows

## Install

```bash
uv add raysdk-py
```

```bash
pip install raysdk-py
```

Requires Python 3.11+

By default the SDK targets `http://localhost:8000`.

Authentication uses a bearer token:
- pass `api_key="..."` explicitly
- or set `RAYSEARCH_API_KEY`

## Quick Start

```python
from raysdk_py import RaySearch

client = RaySearch(api_key="your-api-key")

search_response = client.search(
    "latest multimodal model papers",
    user_location="US",
    fetchs={"content": True},
)

answer_response = client.answer(
    "What are the key findings from recent multimodal model papers?",
    content=True,
)
```

## Search

```python
results = client.search(
    "latest AI research papers",
    user_location="US",
    fetchs={"content": True},
)
```

```python
results = client.search(
    "climate tech news",
    user_location="US",
    mode="deep",
    max_results=10,
    additional_queries=["climate startup funding", "battery storage news"],
    include_domains=["techcrunch.com", "reuters.com"],
    start_published_date="2024-01-01",
    fetchs={
        "content": {"detail": "standard", "max_chars": 5000},
        "abstracts": {"query": "main findings", "max_chars": 300},
        "overview": True,
    },
)
```

```python
results = client.search(
    "multimodal benchmark papers",
    user_location="US",
    include_text=["benchmark"],
    exclude_text=["advertisement"],
    fetchs={
        "content": {"detail": "concise"},
        "subpages": {"max_subpages": 2, "subpage_keywords": ["method", "results"]},
        "others": {"max_links": 5},
    },
)
```

Use `fetchs` to control what extra content is produced for each search result:
- `content`
- `abstracts`
- `subpages`
- `overview`
- `others`

## Fetch

```python
response = client.fetch(
    ["https://docs.python.org/3/", "https://pydantic.dev/"],
    content=True,
)
```

```python
response = client.fetch(
    "https://arxiv.org/abs/2401.00123",
    crawl_mode="preferred",
    content={"detail": "full", "max_chars": 12000},
    abstracts={"query": "main contribution", "max_chars": 400},
    overview={
        "query": "Summarize the paper contributions",
        "json_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "contributions": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["contributions"],
        },
    },
    others={"max_links": 10, "max_image_links": 5},
)
```

Fetch responses include:
- `results`: successful extracted pages
- `statuses`: per-URL success/error status entries

## Answer

```python
response = client.answer("What caused the 2008 financial crisis?")
print(response.answer)
```

```python
response = client.answer(
    "Summarize recent multimodal model trends",
    json_schema={
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "key_papers": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["summary", "key_papers"],
    },
    content=True,
)

print(response.answer)
for citation in response.citations:
    print(citation.title, citation.url)
```

Set `content=True` to include citation content snippets in the response.

## Research

Research uses a task workflow:
1. create a research task
2. poll or fetch the task until it finishes
3. inspect the final `output`

```python
task = client.research.create(
    themes="Current trends in multimodal AI research",
    search_mode="research",
)

print(task.research_id)
print(task.status)
```

```python
task = client.research.create(
    themes="State of battery storage startups in 2025",
    search_mode="research-pro",
    json_schema={
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "companies": {"type": "array", "items": {"type": "string"}},
            "key_trends": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["summary", "companies", "key_trends"],
    },
)
```

```python
task = client.research.get("your-research-id")
print(task.status)
if task.output is not None:
    print(task.output.content)
    print(task.output.structured)
```

```python
task = client.research.poll_until_finished(
    "your-research-id",
    poll_interval=1000,
    timeout_ms=600000,
)

print(task.status)
print(task.output.content if task.output else None)
```

```python
tasks = client.research.list(limit=10)
print(tasks.has_more, tasks.next_cursor)

for task in tasks.data:
    print(task.research_id, task.status)
```

```python
for task in client.research.list_all(limit=20):
    print(task.research_id, task.status)
```

```python
canceled = client.research.cancel("your-research-id")
print(canceled.status)
```

Research task statuses:
- `pending`
- `running`
- `completed`
- `canceled`
- `failed`

Research search modes:
- `research-fast`
- `research`
- `research-pro`

## Health Check

```python
health = client.healthz()
print(health.status, health.engine_ready)
```

## Async

```python
from raysdk_py import AsyncRaySearch

client = AsyncRaySearch(api_key="your-api-key")

search_response = await client.search(
    "async search example",
    user_location="US",
    fetchs={"content": True},
)

research_task = await client.research.create(
    themes="Recent open-source multimodal models",
    search_mode="research",
)

completed = await client.research.poll_until_finished(research_task.research_id)
print(completed.status)
```

## More

Main entry points:
- `RaySearch`
- `AsyncRaySearch`

Main operation groups:
- `search(...)`
- `fetch(...)`
- `answer(...)`
- `research.create(...)`
- `research.get(...)`
- `research.list(...)`
- `research.poll_until_finished(...)`
