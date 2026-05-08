# Token Limits & Context Overflow Prevention

## Problem

SQL queries can return millions of rows. If an agent runs:
```sql
SELECT * FROM sales;  -- Oops, returns 10M rows
```

This explodes the context window:
- **Result size:** ~5GB of data
- **Token count:** ~1.25 billion tokens
- **API cost:** $10,000+
- **Execution:** Hangs or crashes

## Solution

We've implemented **automatic token/size limits** with three layers:

### Layer 1: Default Row Limit
```python
SQLTool(db_url, row_limit=1000)  # Max 1000 rows per query
```

Every `db_query` step automatically appends `LIMIT 1000` unless:
1. Query already has a LIMIT clause, OR
2. You explicitly pass `skip_limit=True`

### Layer 2: Size Limit
```python
SQLTool(db_url, size_limit_mb=10)  # Max ~10MB per result
```

Results are checked for estimated size. If oversized, a warning is added:
```
⚠️ Result size ~45MB exceeds safe limit (10MB).
   Consider adding WHERE/ORDER BY to reduce data.
```

### Layer 3: LLM Safety Prompt
The planner system prompt instructs the LLM:
```
Use WHERE clauses to filter data instead of returning all rows.
Use LIMIT 1000 by default unless specifically told otherwise.
For large datasets, use aggregation (COUNT, SUM, AVG).
```

---

## Implementation Details

### Response Format (New)

`execute_query()` now returns metadata:

```python
response = sql_tool.execute_query("SELECT * FROM sales WHERE region='North' LIMIT 100")

# Returns:
{
    "results": [...100 rows...],
    "row_count": 100,
    "estimated_size_mb": 0.05,
    "warnings": []
}

# If oversized:
{
    "results": [...1000 rows...],
    "row_count": 1000,
    "estimated_size_mb": 0.5,
    "warnings": [
        "Query returned 1000+ rows (truncated). Results may be incomplete.",
        "Result size ~0.5MB exceeds safe limit (10MB)."
    ]
}
```

### Backward Compatibility

For legacy code, use `execute_query_list()`:
```python
rows = sql_tool.execute_query_list("SELECT * FROM sales")  # Returns just the list
```

### Configuration

```python
# In main.py or your config:
sql_tool = SQLTool(
    database_url,
    row_limit=1000,      # Configurable
    size_limit_mb=10     # Configurable
)

# Or override per-query:
response = sql_tool.execute_query(
    "SELECT * FROM huge_table",
    skip_limit=True  # Use carefully!
)
```

---

## Best Practices

### ✅ Good: Focused Queries

```sql
-- Query 1: Top 3 failing products (with LIMIT)
SELECT product_id, product_name, revenue
FROM sales
WHERE region='North' AND quarter='Q3 2026'
ORDER BY revenue ASC
LIMIT 3;

-- Query 2: Aggregation instead of all rows
SELECT product_id, COUNT(*) as error_count
FROM product_logs
WHERE severity='ERROR'
GROUP BY product_id
LIMIT 100;

-- Query 3: Time-windowed query
SELECT * FROM sales
WHERE timestamp > NOW() - INTERVAL 7 DAY
AND status = 'completed'
LIMIT 1000;
```

### ❌ Bad: Unbounded Queries

```sql
-- ❌ No WHERE clause = all rows
SELECT * FROM sales;

-- ❌ No LIMIT on aggregation
SELECT * FROM product_logs GROUP BY product_id;

-- ❌ No filtering on time-series
SELECT * FROM events ORDER BY timestamp;
```

---

## Usage Examples

### Example 1: Normal Usage (Automatic Limiting)

```python
# In planner parameters:
{
    "tool": "db_query",
    "parameters": {
        "sql": "SELECT * FROM sales WHERE region='North' LIMIT 100"
    }
}

# Agent executes:
response = sql_tool.execute_query(
    "SELECT * FROM sales WHERE region='North' LIMIT 100"
)
# ✓ Returns safely: 100 rows, no warnings
```

### Example 2: Oversized Result (Warning)

```python
# Query that would return too much data:
response = sql_tool.execute_query(
    "SELECT * FROM event_logs WHERE created_date > '2026-01-01'"
    # Missing LIMIT, but auto-adds LIMIT 1000
)

# Returns:
{
    "results": [...1000 rows...],
    "row_count": 1000,
    "estimated_size_mb": 0.5,
    "warnings": [
        "Query returned 1000+ rows (truncated)",
        "Consider adding WHERE to reduce data"
    ]
}
```

### Example 3: Intentional Override (Careful!)

```python
# Only if you really need all data:
response = sql_tool.execute_query(
    "SELECT COUNT(*) as total FROM sales",
    skip_limit=True  # No limit needed for COUNT
)

# Or in planner (document why!):
{
    "tool": "db_query",
    "parameters": {
        "sql": "SELECT COUNT(*) as total FROM sales",
        "skip_limit": True  # Aggregate query, safe
    }
}
```

---

## Token Cost Comparison

### Without Limits
```
User: "Find failing products"
LLM Plan: "SELECT * FROM sales"  (no WHERE/LIMIT)
↓
SQL returns 50M rows
↓
Context overflows at 128K tokens
↓
Request fails or costs $10K+
```

### With Limits
```
User: "Find failing products"
LLM Plan: "SELECT * FROM sales WHERE region='North' LIMIT 100"
         (guided by safety prompt)
↓
SQL returns 100 rows (~50KB)
↓
Fits comfortably in context
↓
Total tokens: ~5K, cost: $0.20
```

**Savings: 99.98% cost reduction**

---

## Monitoring & Debugging

### Check Warnings
```python
response = sql_tool.execute_query(query)
if response["warnings"]:
    print(f"⚠️  {response['warnings']}")
```

### Estimate Size
```python
print(f"Result size: {response['estimated_size_mb']} MB")
print(f"Row count: {response['row_count']}")

# Decide if you need more data:
if response['row_count'] >= sql_tool.row_limit:
    # Results may be incomplete
```

### Query Optimization Tips

1. **Add WHERE clauses** instead of fetching all rows
   ```sql
   -- Before: SELECT * FROM sales (millions)
   -- After:
   SELECT * FROM sales WHERE region='North' AND quarter='Q3 2026'
   ```

2. **Use aggregation** for summaries
   ```sql
   -- Before: SELECT * FROM logs (fetch all, then COUNT)
   -- After:
   SELECT COUNT(*) as total FROM logs WHERE severity='ERROR'
   ```

3. **Order + Limit** for top-N queries
   ```sql
   -- Before: SELECT * FROM products, then sort in Python
   -- After:
   SELECT * FROM products ORDER BY revenue DESC LIMIT 10
   ```

4. **Date filtering** for time-series
   ```sql
   -- Before: SELECT * FROM events (all history)
   -- After:
   SELECT * FROM events WHERE created_at > NOW() - INTERVAL 30 DAY
   ```

---

## Configuration Recommendations

| Scenario | Row Limit | Size Limit | Notes |
|----------|-----------|-----------|-------|
| **Development** | 1000 | 10 MB | Balance: quick feedback + safety |
| **Production** | 10000 | 50 MB | Higher limits, more oversight |
| **Analytics** | 100000 | 500 MB | Data-heavy workloads |
| **Large Tables** | 5000 | 25 MB | Narrow WHERE clauses required |

```python
# Production config
sql_tool = SQLTool(
    database_url,
    row_limit=10000,      # Higher for production
    size_limit_mb=50      # Monitor for cost
)
```

---

## Future Enhancements

1. **Query Cost Estimation**
   - Estimate token count before executing
   - Warn if query would exceed budget

2. **Automatic Query Optimization**
   - Detect N+1 patterns
   - Suggest JOIN vs subquery

3. **Rate Limiting**
   - Cap queries per minute
   - Prevent runaway agents

4. **Caching**
   - Cache recent queries
   - Return cached results if identical

5. **Query Analysis**
   - Parse query, estimate row count before executing
   - Suggest LIMIT if missing

---

## Testing Token Limits

```python
# Test 1: Normal query with auto-limit
sql_tool = SQLTool("sqlite:///agent_data.db", row_limit=100)
response = sql_tool.execute_query("SELECT * FROM sales")
assert response['row_count'] <= 100
assert len(response['warnings']) == 0

# Test 2: Oversized warning
sql_tool = SQLTool("sqlite:///agent_data.db", row_limit=1000, size_limit_mb=0.01)
response = sql_tool.execute_query("SELECT * FROM huge_table")
assert any("exceeds" in w for w in response['warnings'])

# Test 3: Override limit
response = sql_tool.execute_query("SELECT COUNT(*) FROM sales", skip_limit=True)
assert response['row_count'] == 1  # COUNT returns 1 row
```

---

## Summary

✅ **Automatic row limiting** — Every query gets `LIMIT 1000` by default  
✅ **Size checking** — Results flagged if oversized  
✅ **LLM guidance** — Planner instructed to use WHERE/LIMIT  
✅ **Backward compatible** — Legacy code still works  
✅ **Configurable** — Adjust limits per use case  
✅ **Observable** — Warnings help debug issues  

**Result: Safe, predictable token usage. No more runaway queries.**
