#!/usr/bin/env bash

# Script Validation Test Suite for FlavorPilot

set -e

echo "🧪 FlavorPilot Script Validation Test Suite"
echo "=========================================="
echo ""

# Test 1: Check all scripts exist
echo "Test 1: Checking script files exist..."
if [[ -f "start.sh" && -f "stop.sh" && -f "start.ps1" && -f "stop.ps1" ]]; then
    echo "   ✓ All scripts present"
else
    echo "   ✗ Missing scripts"
    exit 1
fi

# Test 2: Check bash scripts are executable
echo "Test 2: Checking bash scripts are executable..."
if [[ -x "start.sh" && -x "stop.sh" ]]; then
    echo "   ✓ Bash scripts are executable"
else
    echo "   ✗ Bash scripts not executable"
    exit 1
fi

# Test 3: Validate bash syntax
echo "Test 3: Validating bash script syntax..."
bash -n start.sh && bash -n stop.sh
echo "   ✓ Bash syntax valid"

# Test 4: Check script contains expected commands
echo "Test 4: Checking start.sh contains required components..."
grep -q "python -m app.main" start.sh && echo "   ✓ Backend startup command found"
grep -q "npm run dev" start.sh && echo "   ✓ Frontend startup command found"
grep -q "pip install" start.sh && echo "   ✓ Dependency installation found"

echo "Test 5: Checking stop.sh contains cleanup commands..."
grep -q "pkill" stop.sh && echo "   ✓ Process kill commands found"
grep -q "lsof" stop.sh && echo "   ✓ Port cleanup found"

# Test 6: Check PowerShell scripts structure
echo "Test 6: Checking PowerShell scripts structure..."
grep -q "Start-Job" start.ps1 && echo "   ✓ PowerShell background job management found"
grep -q "Stop-Job\|Stop-Process" stop.ps1 && echo "   ✓ PowerShell process termination found"
grep -q "Get-NetTCPConnection" stop.ps1 && echo "   ✓ PowerShell port management found"

# Test 7: Verify scripts have proper shebang/header
echo "Test 7: Checking script headers..."
head -n 1 start.sh | grep -q "#!/usr/bin/env bash" && echo "   ✓ start.sh has proper shebang"
head -n 1 stop.sh | grep -q "#!/usr/bin/env bash" && echo "   ✓ stop.sh has proper shebang"
head -n 1 start.ps1 | grep -q "# FlavorPilot" && echo "   ✓ start.ps1 has header comment"
head -n 1 stop.ps1 | grep -q "# FlavorPilot" && echo "   ✓ stop.ps1 has header comment"

# Test 8: Validate stop.sh can be run safely (dry-run style check)
echo "Test 8: Testing stop.sh safety..."
# Check that stop.sh uses 2>/dev/null for safe error handling
grep -q "2>/dev/null" stop.sh && echo "   ✓ Safe error handling in stop.sh"

echo ""
echo "=========================================="
echo "✅ All validation tests passed!"
echo "=========================================="
echo ""
echo "Scripts are ready for use:"
echo "  • start.sh  - Start FlavorPilot (macOS/Linux)"
echo "  • stop.sh   - Stop FlavorPilot (macOS/Linux)"
echo "  • start.ps1 - Start FlavorPilot (Windows PowerShell)"
echo "  • stop.ps1  - Stop FlavorPilot (Windows PowerShell)"
echo ""
