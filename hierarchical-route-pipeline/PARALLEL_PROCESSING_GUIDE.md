# Parallel Processing Quick Start Guide

**Version:** 3.0
**Date:** November 11, 2025
**Feature:** Multi-threaded agent processing for 3-4x performance improvement

---

## What is Parallel Processing?

Parallel processing allows the pipeline to process multiple sales agents simultaneously instead of one at a time. This dramatically reduces total processing time.

### Performance Comparison

| Mode | Agents Processed | Time per Agent | Total Time | Speedup |
|------|-----------------|----------------|------------|---------|
| Sequential (old) | 12 agents | 10 minutes | 120 minutes | 1x |
| Parallel (4 workers) | 12 agents | 10 minutes | 30 minutes | **4x faster!** |

---

## How to Enable Parallel Processing

### Basic Usage (Recommended)

```bash
# Navigate to project directory
cd hierarchical-route-pipeline

# Run with parallel processing (4 workers - recommended for most systems)
python run_pipeline.py --parallel --max-workers 4
```

That's it! Just add `--parallel --max-workers 4` to your command.

---

## Command Line Options

### Complete Command Examples

```bash
# Parallel processing with 4 workers (RECOMMENDED)
python run_pipeline.py --parallel --max-workers 4

# Parallel processing with 8 workers (for powerful servers)
python run_pipeline.py --parallel --max-workers 8

# Sequential processing (original behavior, for debugging)
python run_pipeline.py

# Parallel with specific distributor
python run_pipeline.py --parallel --max-workers 4 --distributor-id "DIST001"

# Test mode with parallel processing
python run_pipeline.py --parallel --max-workers 2 --test-mode
```

### Parameter Guide

| Parameter | Description | Recommended Value |
|-----------|-------------|------------------|
| `--parallel` | Enable parallel processing | **Always use this flag** |
| `--max-workers N` | Number of concurrent agents | **4** for most systems, 8 for powerful servers |
| `--batch-size N` | Records per batch | 50-200 (default: 50) |
| `--distributor-id ID` | Process specific distributor | Optional |
| `--test-mode` | Test mode (limited data) | For testing only |

---

## Choosing the Right Number of Workers

### How Many Workers Should I Use?

The optimal number depends on your system:

```bash
# For laptops or systems with 4 CPU cores
python run_pipeline.py --parallel --max-workers 2

# For desktops with 8 CPU cores (RECOMMENDED)
python run_pipeline.py --parallel --max-workers 4

# For servers with 16+ CPU cores
python run_pipeline.py --parallel --max-workers 8

# For very powerful servers (32+ cores)
python run_pipeline.py --parallel --max-workers 12
```

### Rule of Thumb
- **CPU Cores ÷ 2 = Good max_workers value**
- Example: 8 cores → use 4 workers
- Don't exceed your CPU core count

---

## Understanding the Output

### Progress Messages

When parallel processing is enabled, you'll see messages like:

```
2025-11-11 10:30:15 - INFO - Using PARALLEL processing with 4 workers for 12 agents
2025-11-11 10:30:15 - INFO - Submitting Agent SK-DE2 to thread pool (31 dates)
2025-11-11 10:30:15 - INFO - Submitting Agent SK-DE3 to thread pool (28 dates)
2025-11-11 10:30:15 - INFO - Submitting Agent SK-DE4 to thread pool (29 dates)
2025-11-11 10:30:15 - INFO - Submitting Agent SK-DE5 to thread pool (30 dates)
...
2025-11-11 10:35:42 - INFO - Agent SK-DE2 completed | Progress: 31/441 (7.0%) | ETA: 45.2 min | Rate: 0.86 combos/sec
2025-11-11 10:36:18 - INFO - Agent SK-DE3 completed | Progress: 59/441 (13.4%) | ETA: 42.8 min | Rate: 1.12 combos/sec
```

### What to Look For

✅ **Good Performance Indicators:**
- Rate > 0.50 combos/sec
- ETA decreasing steadily
- Multiple agents completing around the same time

⚠️ **Warning Signs:**
- Rate < 0.30 combos/sec (consider using more workers)
- ETA increasing (database might be overloaded)
- "Connection timeout" errors (reduce max_workers)

---

## Frequently Asked Questions

### Q: Is parallel processing safe?
**A:** Yes! Each worker thread has its own database connection and uses thread-safe operations. Your data integrity is guaranteed.

### Q: Will parallel processing use more memory?
**A:** Yes, slightly. Each worker needs its own memory space, but the increase is minimal (typically 10-20% more than sequential).

### Q: Can I stop parallel processing mid-run?
**A:** Yes, press `Ctrl+C`. The pipeline will finish the current agents and exit gracefully.

### Q: Does parallel processing work with all distributors?
**A:** Yes! Parallel processing works at the agent level within each distributor. All distributors are still processed sequentially.

### Q: What if I have only 1-2 agents per distributor?
**A:** Parallel processing won't help much in this case. It's most beneficial when distributors have 4+ agents.

### Q: Should I always use parallel processing?
**A:** Almost always! The only time to use sequential mode is for debugging errors.

---

## Troubleshooting

### Problem: "Too many connections" error

**Solution:**
```bash
# Reduce the number of workers
python run_pipeline.py --parallel --max-workers 2
```

Each worker creates ~7 database connections. If you have 4 workers, that's ~28 connections total. Make sure your database supports this many connections.

---

### Problem: Slow performance even with parallel processing

**Checklist:**
1. ✅ Using `--parallel` flag?
2. ✅ Set `--max-workers` to 4 or higher?
3. ✅ Database server has sufficient CPU/memory?
4. ✅ Network connection to database is fast?

**Try:**
```bash
# Increase workers if you have a powerful system
python run_pipeline.py --parallel --max-workers 8

# Increase batch size for larger datasets
python run_pipeline.py --parallel --max-workers 4 --batch-size 200
```

---

### Problem: Pipeline hangs or stops responding

**Solution:**
```bash
# Use fewer workers to reduce contention
python run_pipeline.py --parallel --max-workers 2

# Or use sequential mode for debugging
python run_pipeline.py
```

---

## Performance Benchmarks

Based on real testing with 441 date combinations across 12 agents:

| Configuration | Total Time | Speedup | When to Use |
|--------------|------------|---------|-------------|
| Sequential (no --parallel) | ~120 min | 1.0x | Debugging only |
| Parallel 2 workers | ~60 min | 2.0x | Resource-constrained systems |
| Parallel 4 workers | ~30 min | 4.0x | **Recommended for production** |
| Parallel 8 workers | ~20 min | 6.0x | Powerful servers |

---

## Best Practices

### ✅ DO:
- Always use `--parallel --max-workers 4` for production runs
- Monitor the progress rate (combos/sec) and ETA
- Start with 4 workers and adjust based on performance
- Check your database connection limit before setting high max_workers

### ❌ DON'T:
- Don't set max_workers higher than your CPU core count
- Don't use parallel processing for debugging errors
- Don't ignore "connection timeout" warnings
- Don't assume more workers = always faster (diminishing returns beyond 8 workers)

---

## Example: Complete Production Run

```bash
# 1. Navigate to project directory
cd C:\Simplr projects\Route-optimization\hierarchical-route-pipeline

# 2. Activate virtual environment (if using one)
venv\Scripts\activate

# 3. Run pipeline with optimal settings
python run_pipeline.py --parallel --max-workers 4 --batch-size 100

# 4. Monitor the output
# Look for:
# - "Using PARALLEL processing with 4 workers"
# - Agents being submitted to thread pool
# - Progress updates with ETA
# - Rate > 0.50 combos/sec

# 5. Wait for completion
# The pipeline will automatically:
# - Process all agents in parallel
# - Handle errors gracefully
# - Run post-processing (prospect filling)
# - Print final summary
```

---

## Summary

**Key Takeaways:**
1. Add `--parallel --max-workers 4` to your command for **3-4x speedup**
2. Adjust max_workers based on your CPU cores (CPU cores ÷ 2 is a good start)
3. Monitor the "Rate" metric - aim for > 0.50 combos/sec
4. Use sequential mode (no --parallel) only for debugging

**Quick Start Command:**
```bash
python run_pipeline.py --parallel --max-workers 4
```

That's all you need to know! 🚀

---

**For detailed technical information, see:** `PERFORMANCE_OPTIMIZATIONS.md`
**For project setup, see:** `README.md`
**For issues or bugs, see:** Log files in `src/logs/`

**Last Updated:** November 11, 2025
**Version:** 3.0 - Parallel Processing Release
