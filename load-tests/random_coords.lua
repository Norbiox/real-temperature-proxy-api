-- wrk Lua script for testing with random coordinates
-- This ensures we test both cache hits and misses

-- List of test coordinates (major cities around the world)
local coords = {
  "lat=52.52&lon=13.41",   -- Berlin
  "lat=51.51&lon=-0.13",   -- London
  "lat=48.85&lon=2.35",    -- Paris
  "lat=40.71&lon=-74.01",  -- New York
  "lat=35.68&lon=139.65",  -- Tokyo
  "lat=-33.87&lon=151.21", -- Sydney
  "lat=37.77&lon=-122.42", -- San Francisco
  "lat=55.75&lon=37.62",   -- Moscow
  "lat=19.43&lon=-99.13",  -- Mexico City
  "lat=-23.55&lon=-46.63", -- São Paulo
}

-- Initialize random seed
math.randomseed(os.time())

-- Called for each request
request = function()
  -- Pick random coordinates
  local coord = coords[math.random(#coords)]
  local path = "/v1/current?" .. coord

  return wrk.format("GET", path)
end

-- Print results
done = function(summary, latency, requests)
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
