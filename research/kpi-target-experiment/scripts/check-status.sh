#!/bin/bash

echo "=============================================="
echo "KPI TARGET EXPERIMENT STATUS"
echo "Time: $(date)"
echo "=============================================="
echo ""

# SQL domain
SQL_DONE=$(ls research/kpi-target-experiment/domains/sql-query/results/*.json 2>/dev/null | wc -l)
echo "SQL Query Domain:"
echo "  Progress: ${SQL_DONE}/60 runs"
if [[ $SQL_DONE -gt 0 ]]; then
    echo "  Last file: $(ls -t research/kpi-target-experiment/domains/sql-query/results/*.json | head -1 | xargs basename)"
fi
echo ""

# Chart domain
CHART_DONE=$(ls research/kpi-target-experiment/domains/chart/results/*.json 2>/dev/null | wc -l)
echo "Chart Domain:"
echo "  Progress: ${CHART_DONE}/60 runs"
if [[ $CHART_DONE -gt 0 ]]; then
    echo "  Last file: $(ls -t research/kpi-target-experiment/domains/chart/results/*.json | head -1 | xargs basename)"
fi
echo ""

# Overall
TOTAL=$((SQL_DONE + CHART_DONE))
echo "Overall: ${TOTAL}/120 runs ($(( TOTAL * 100 / 120 ))%)"
echo ""

# Log tails
echo "Recent SQL activity:"
tail -2 /tmp/sql-experiment.log 2>/dev/null | sed 's/^/  /'
echo ""

echo "Recent Chart activity:"
tail -2 /tmp/chart-experiment.log 2>/dev/null | sed 's/^/  /'

# Check if processes are still running
echo ""
if pgrep -f "run-experiment.sh --domain sql-query" > /dev/null; then
    echo "SQL experiment: RUNNING"
else
    echo "SQL experiment: NOT RUNNING"
fi

if pgrep -f "run-experiment.sh --domain chart" > /dev/null; then
    echo "Chart experiment: RUNNING"
else
    echo "Chart experiment: NOT RUNNING"
fi
