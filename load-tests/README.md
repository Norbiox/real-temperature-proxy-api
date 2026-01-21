# Load Testing

This directory contains load testing scripts and documentation for the Real Temperature Proxy API.

## Prerequisites

Install wrk (HTTP benchmarking tool):

```bash
# Arch Linux
sudo pacman -S wrk

# macOS
brew install wrk

# Ubuntu/Debian
sudo apt-get install wrk

# From source
git clone https://github.com/wg/wrk.git
cd wrk
make
sudo cp wrk /usr/local/bin
```

## Quick Start

Start the application:
```bash
python main.py
# or
uv run uvicorn src.real_temperature_proxy_api.app:app --host 0.0.0.0 --port 8000
```

Run a basic load test:
```bash
wrk -t2 -c10 -d10s http://localhost:8000/v1/current?lat=52.52\&lon=13.41
```

## Test Scenarios

### 1. Cache Hit Performance Test

Tests how fast the API serves cached responses using the same coordinates repeatedly:

```bash
wrk -t4 -c100 -d30s -s load-tests/cache_test.lua http://localhost:8000
```

**Expected Results:**
- High throughput (1000+ req/sec)
- Low latency (<5ms average)
- Near 100% cache hit ratio

### 2. Mixed Workload Test (Recommended)

Simulates real-world usage with requests to 10 different major cities:

```bash
wrk -t4 -c100 -d30s -s load-tests/random_coords.lua http://localhost:8000
```

**Expected Results:**
- Mix of cache hits and misses
- Demonstrates caching effectiveness
- More realistic performance metrics

### 3. High Concurrency Stress Test

Tests system behavior under high load:

```bash
wrk -t8 -c200 -d30s -s load-tests/random_coords.lua http://localhost:8000
```

**Expected Results:**
- Tests request coalescing for concurrent identical requests
- Identifies performance bottlenecks
- Validates error handling under stress

### 4. Sustained Load Test

Long-running test to check for memory leaks or performance degradation:

```bash
wrk -t4 -c50 -d300s -s load-tests/random_coords.lua http://localhost:8000
```

**Expected Results:**
- Stable performance over 5 minutes
- No memory leaks
- Consistent latency

### 5. Single Coordinate Test

Simple baseline test without Lua scripts:

```bash
wrk -t2 -c10 -d10s http://localhost:8000/v1/current?lat=52.52\&lon=13.41
```

## wrk Parameters Explained

- `-t` : Number of threads to use (typically 2-8)
- `-c` : Number of concurrent HTTP connections (10-200)
- `-d` : Duration of test (e.g., 10s, 1m, 300s)
- `-s` : Lua script for custom request logic
- `-H` : Add custom header (e.g., `-H "Accept: application/json"`)

## Monitoring During Tests

### Watch Metrics

Monitor Prometheus metrics in real-time:

```bash
watch -n 1 'curl -s http://localhost:8000/metrics | grep -E "(temperature_requests_total|temperature_request_duration|cache_hits|cache_misses)"'
```

### View Application Logs

Tail the application logs to see what's happening:

```bash
# If running with python main.py, logs go to stdout
# If running in background, redirect to a file:
uv run uvicorn src.real_temperature_proxy_api.app:app --host 0.0.0.0 --port 8000 > /tmp/app.log 2>&1 &
tail -f /tmp/app.log
```

### Check Health Endpoints

```bash
# Liveness check
curl http://localhost:8000/health

# Readiness check
curl http://localhost:8000/ready
```

## Performance Expectations

Based on the API architecture and caching strategy:

| Scenario | Throughput | Latency (p50) | Latency (p99) |
|----------|-----------|---------------|---------------|
| **Cache hits** (same coordinates) | 1000-5000 req/sec | <5ms | <10ms |
| **Cache misses** (unique coordinates) | 10-50 req/sec | ~1000ms | ~1100ms |
| **Mixed workload** (10 cities) | 200-500 req/sec | <100ms | ~1000ms |

### Key Factors

1. **Cache TTL**: 60 seconds (configurable via `CACHE_TTL`)
2. **Upstream timeout**: 1 second (configurable via `UPSTREAM_TIMEOUT`)
3. **Retry logic**: 3 retries with exponential backoff
4. **Request coalescing**: Concurrent requests for same coordinates are coalesced
5. **Cache size**: 10,000 entries with LRU eviction

## Interpreting Results

### Sample Output

```
Running 30s test @ http://localhost:8000
  4 threads and 100 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency    45.23ms   12.34ms  123.45ms   75.23%
    Req/Sec   551.23     45.67     678.90     82.34%
  66000 requests in 30.03s, 12.34MB read
Requests/sec:   2198.67
Transfer/sec:    420.56KB
```

**Key Metrics:**
- **Latency Avg**: Average response time (lower is better)
- **Latency Stdev**: Consistency of response times (lower is better)
- **Req/Sec**: Throughput per thread (higher is better)
- **Total Requests**: Total requests completed during test
- **Requests/sec**: Overall throughput (higher is better)

### Warning Signs

- **High latency variance**: Investigate upstream API issues or retry logic
- **Decreasing throughput over time**: Possible memory leak or resource exhaustion
- **Many 5xx errors**: Check application logs for errors
- **Low cache hit ratio**: Verify cache configuration and TTL settings

## Advanced Testing

### Custom Lua Scripts

Create your own wrk Lua scripts for specific scenarios:

```lua
-- custom_test.lua
request = function()
  -- Your custom logic here
  return wrk.format("GET", "/v1/current?lat=52.52&lon=13.41")
end
```

Run with:
```bash
wrk -t4 -c100 -d30s -s custom_test.lua http://localhost:8000
```

### Testing with Different Configurations

Test with different cache TTLs:

```bash
CACHE_TTL=30 python main.py &  # 30 second cache
wrk -t4 -c100 -d60s -s load-tests/random_coords.lua http://localhost:8000
```

### Compare Cache vs No-Cache

```bash
# With caching (default)
wrk -t4 -c100 -d30s -s load-tests/cache_test.lua http://localhost:8000

# To simulate no cache, use many unique coordinates
# (requires writing a script that generates unique coords each time)
```

## Cleanup

Stop the application:

```bash
# If running in foreground, press Ctrl+C

# If running in background
pkill -f "uvicorn src.real_temperature_proxy_api.app:app"

# Or find and kill specific PID
ps aux | grep uvicorn
kill <PID>
```

## Troubleshooting

### Connection Refused

```bash
# Check if application is running
curl http://localhost:8000/health

# Check if port is in use
lsof -i :8000

# Check application logs
tail -f /tmp/app.log
```

### Too Many Open Files

If you see "too many open files" errors with high connection counts:

```bash
# Increase file descriptor limit (Linux)
ulimit -n 65536
```

### Upstream API Rate Limiting

If Open-Meteo rate limits your requests during testing:
1. Set `OPENMETEO_API_KEY` environment variable if you have an API key
2. Use the cache test script to minimize upstream calls
3. Reduce concurrency or test duration

## Contributing

When adding new load test scenarios:
1. Create descriptive Lua script names
2. Document expected results
3. Update this README with the new scenario
4. Consider edge cases and error conditions
