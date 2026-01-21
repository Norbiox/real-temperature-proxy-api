-- wrk Lua script for testing cache performance
-- Uses the same coordinate repeatedly to maximize cache hits

request = function()
  -- Always use Berlin coordinates to test cache hits
  return wrk.format("GET", "/v1/current?lat=52.52&lon=13.41")
end

done = function(summary, latency, requests)
  io.write("------------------------------------\n")
  io.write("  CACHE HIT TEST (same coordinates)\n")
  io.write("------------------------------------\n")
  io.write(string.format("  Requests: %d\n", summary.requests))
  io.write(string.format("  Duration: %.2fs\n", summary.duration / 1000000))
  io.write(string.format("  Req/sec:  %.2f\n", summary.requests / (summary.duration / 1000000)))
  io.write(string.format("  Latency (avg): %.2fms\n", latency.mean / 1000))
  io.write(string.format("  Latency (p50): %.2fms\n", latency:percentile(50) / 1000))
  io.write(string.format("  Latency (p95): %.2fms\n", latency:percentile(95) / 1000))
  io.write(string.format("  Latency (p99): %.2fms\n", latency:percentile(99) / 1000))
  io.write("------------------------------------\n")
end
