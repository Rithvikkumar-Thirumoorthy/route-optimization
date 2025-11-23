@echo off
echo Running hierarchical pipeline for Agent SK-SAT6...
echo.

cd "C:\Simplr projects\Route-optimization"

REM Run for specific agent with test mode (first 3 dates only)
python full_pipeline\run_specific_agent.py --distributor 11814 --agent SK-SAT6 --test-mode

echo.
echo Processing completed. Check the logs for results.
pause