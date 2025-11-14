#!/bin/bash
# Monitor regression test progress
while true; do
    clear
    echo "=============================================="
    echo "  FULL REGRESSION TEST - PROGRESS MONITOR"
    echo "=============================================="
    echo ""
    
    # Count completed cards
    COMPLETED=$(grep -c "\[Card.*✓" outputs/full-regression-final.txt 2>/dev/null || echo "0")
    echo "✅ Cards completed: $COMPLETED / 142"
    
    # Show last 3 cards
    echo ""
    echo "📍 Recent cards:"
    tail -200 outputs/full-regression-final.txt 2>/dev/null | grep "\[Card.*✓" | tail -3
    
    # Check if done
    if grep -q "FINAL VERDICT" outputs/full-regression-final.txt 2>/dev/null; then
        echo ""
        echo "🎉 TEST COMPLETE!"
        echo ""
        grep "Website extraction rate" outputs/full-regression-final.txt | tail -1
        break
    fi
    
    echo ""
    echo "⏱️  Last update: $(date '+%H:%M:%S')"
    echo "   (Updates every 30 seconds)"
    sleep 30
done

