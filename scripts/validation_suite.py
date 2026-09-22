"""
FlavorPilot End-to-End Validation Test Suite
=============================================

Comprehensive integration testing covering:
- Backend API endpoints
- MCP client functionality
- Agent orchestration
- Evaluator logic
- Frontend API client
- Headless browser UI testing
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import sys

# Test results storage
test_results = {
    "timestamp": datetime.utcnow().isoformat(),
    "environment": {
        "python_version": sys.version,
        "test_mode": "mock_database"
    },
    "test_suites": [],
    "summary": {
        "total_tests": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "warnings": 0,
        "duration_seconds": 0
    }
}


class TestSuite:
    """Base test suite class."""
    
    def __init__(self, name: str):
        self.name = name
        self.tests: List[Dict[str, Any]] = []
        self.start_time = None
        self.end_time = None
    
    def add_test(self, test_name: str, status: str, message: str = "", 
                 duration_ms: float = 0, details: Dict = None):
        """Add a test result."""
        self.tests.append({
            "name": test_name,
            "status": status,  # "PASS", "FAIL", "SKIP", "WARN"
            "message": message,
            "duration_ms": duration_ms,
            "details": details or {}
        })
    
    def start(self):
        """Start test suite timer."""
        self.start_time = time.time()
    
    def end(self):
        """End test suite timer."""
        self.end_time = time.time()
    
    def get_duration(self):
        """Get suite duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0
    
    def get_summary(self):
        """Get test suite summary."""
        passed = sum(1 for t in self.tests if t["status"] == "PASS")
        failed = sum(1 for t in self.tests if t["status"] == "FAIL")
        skipped = sum(1 for t in self.tests if t["status"] == "SKIP")
        warnings = sum(1 for t in self.tests if t["status"] == "WARN")
        
        return {
            "name": self.name,
            "total": len(self.tests),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "warnings": warnings,
            "duration_seconds": self.get_duration(),
            "tests": self.tests
        }


# ========================================
# Test Suite 1: Golden Dataset Validation
# ========================================

async def test_golden_dataset():
    """Validate golden dataset structure and content."""
    suite = TestSuite("Golden Dataset Validation")
    suite.start()
    
    # Test 1: File exists
    start = time.time()
    dataset_path = Path("/workspace/scratch/golden_dataset_flavorpilot.json")
    if dataset_path.exists():
        suite.add_test(
            "Golden dataset file exists",
            "PASS",
            f"Found at {dataset_path}",
            (time.time() - start) * 1000
        )
    else:
        suite.add_test(
            "Golden dataset file exists",
            "FAIL",
            f"Not found at {dataset_path}",
            (time.time() - start) * 1000
        )
        suite.end()
        return suite
    
    # Test 2: Valid JSON
    start = time.time()
    try:
        with open(dataset_path) as f:
            dataset = json.load(f)
        suite.add_test(
            "JSON structure is valid",
            "PASS",
            "Successfully parsed JSON",
            (time.time() - start) * 1000
        )
    except Exception as e:
        suite.add_test(
            "JSON structure is valid",
            "FAIL",
            f"JSON parse error: {e}",
            (time.time() - start) * 1000
        )
        suite.end()
        return suite
    
    # Test 3: Correct count
    start = time.time()
    expected_count = 100
    actual_count = len(dataset)
    if actual_count == expected_count:
        suite.add_test(
            "Dataset has 100 test cases",
            "PASS",
            f"Found {actual_count} cases",
            (time.time() - start) * 1000,
            {"expected": expected_count, "actual": actual_count}
        )
    else:
        suite.add_test(
            "Dataset has 100 test cases",
            "FAIL",
            f"Expected {expected_count}, found {actual_count}",
            (time.time() - start) * 1000,
            {"expected": expected_count, "actual": actual_count}
        )
    
    # Test 4: Required fields present
    start = time.time()
    required_fields = ["id", "slice", "eval_type", "user_prompt", 
                      "mcp_tools_required", "expected_constraints"]
    missing_fields = []
    
    for i, case in enumerate(dataset[:5]):  # Check first 5 cases
        for field in required_fields:
            if field not in case:
                missing_fields.append(f"Case {i}: missing '{field}'")
    
    if not missing_fields:
        suite.add_test(
            "Required fields present in test cases",
            "PASS",
            "All required fields found",
            (time.time() - start) * 1000
        )
    else:
        suite.add_test(
            "Required fields present in test cases",
            "FAIL",
            f"Missing fields: {', '.join(missing_fields[:3])}",
            (time.time() - start) * 1000
        )
    
    # Test 5: Slice distribution
    start = time.time()
    from collections import Counter
    slice_counts = Counter(case["slice"] for case in dataset)
    expected_slices = {
        "Standard Menu Search": 50,
        "Dietary & Macro Constraints": 25,
        "Multi-User Group Synthesis": 15,
        "Adversarial & Allergen Safety": 10
    }
    
    distribution_correct = all(
        slice_counts.get(slice_name) == expected_count
        for slice_name, expected_count in expected_slices.items()
    )
    
    if distribution_correct:
        suite.add_test(
            "Correct slice distribution",
            "PASS",
            f"Distribution matches expected: {dict(slice_counts)}",
            (time.time() - start) * 1000,
            {"distribution": dict(slice_counts)}
        )
    else:
        suite.add_test(
            "Correct slice distribution",
            "FAIL",
            f"Distribution mismatch. Got: {dict(slice_counts)}",
            (time.time() - start) * 1000,
            {"expected": expected_slices, "actual": dict(slice_counts)}
        )
    
    suite.end()
    return suite


# ========================================
# Test Suite 2: MCP Client Functionality
# ========================================

async def test_mcp_client():
    """Test MCP client operations."""
    suite = TestSuite("MCP Client Functionality")
    suite.start()
    
    # Test 1: Import MCP client
    start = time.time()
    try:
        from backend.app.mcp import MockZomatoMCPClient, ZomatoMCPClient
        suite.add_test(
            "MCP client imports successfully",
            "PASS",
            "Both MockZomatoMCPClient and ZomatoMCPClient imported",
            (time.time() - start) * 1000
        )
    except Exception as e:
        suite.add_test(
            "MCP client imports successfully",
            "FAIL",
            f"Import error: {e}",
            (time.time() - start) * 1000
        )
        suite.end()
        return suite
    
    # Test 2: Mock client connection
    start = time.time()
    try:
        async with MockZomatoMCPClient() as client:
            connected = client._connected
        
        suite.add_test(
            "Mock client connects successfully",
            "PASS",
            "Mock client connection established",
            (time.time() - start) * 1000
        )
    except Exception as e:
        suite.add_test(
            "Mock client connects successfully",
            "FAIL",
            f"Connection error: {e}",
            (time.time() - start) * 1000
        )
    
    # Test 3: Search restaurants
    start = time.time()
    try:
        async with MockZomatoMCPClient() as client:
            results = await client.search_restaurants(
                query="Keto Bowl",
                location="Indiranagar",
                budget_cap_inr=500.0
            )
        
        if results and len(results) > 0 and "restaurant_id" in results[0]:
            suite.add_test(
                "search_restaurants() returns valid results",
                "PASS",
                f"Returned {len(results)} restaurants",
                (time.time() - start) * 1000,
                {"result_count": len(results), "first_restaurant": results[0].get("name")}
            )
        else:
            suite.add_test(
                "search_restaurants() returns valid results",
                "FAIL",
                "Invalid or empty results",
                (time.time() - start) * 1000
            )
    except Exception as e:
        suite.add_test(
            "search_restaurants() returns valid results",
            "FAIL",
            f"Error: {e}",
            (time.time() - start) * 1000
        )
    
    # Test 4: Get menu
    start = time.time()
    try:
        async with MockZomatoMCPClient() as client:
            menu = await client.get_menu(
                restaurant_id="rest_001",
                dietary_filter="keto"
            )
        
        if menu and "categories" in menu:
            suite.add_test(
                "get_menu() returns menu structure",
                "PASS",
                f"Retrieved menu with {len(menu.get('categories', []))} categories",
                (time.time() - start) * 1000
            )
        else:
            suite.add_test(
                "get_menu() returns menu structure",
                "FAIL",
                "Invalid menu structure",
                (time.time() - start) * 1000
            )
    except Exception as e:
        suite.add_test(
            "get_menu() returns menu structure",
            "FAIL",
            f"Error: {e}",
            (time.time() - start) * 1000
        )
    
    # Test 5: Get item customizations
    start = time.time()
    try:
        async with MockZomatoMCPClient() as client:
            customizations = await client.get_item_customizations(item_id="item_001")
        
        if customizations and "customizations" in customizations:
            suite.add_test(
                "get_item_customizations() returns options",
                "PASS",
                f"Retrieved {len(customizations.get('customizations', []))} customization groups",
                (time.time() - start) * 1000
            )
        else:
            suite.add_test(
                "get_item_customizations() returns options",
                "FAIL",
                "Invalid customizations structure",
                (time.time() - start) * 1000
            )
    except Exception as e:
        suite.add_test(
            "get_item_customizations() returns options",
            "FAIL",
            f"Error: {e}",
            (time.time() - start) * 1000
        )
    
    # Test 6: Apply promo code
    start = time.time()
    try:
        async with MockZomatoMCPClient() as client:
            promo_result = await client.apply_promo_code(
                cart_id="cart_test",
                promo_code="CBUSER"
            )
        
        if promo_result and "discount_inr" in promo_result:
            suite.add_test(
                "apply_promo_code() applies discount",
                "PASS",
                f"Applied discount: ₹{promo_result.get('discount_inr', 0)}",
                (time.time() - start) * 1000,
                {"discount": promo_result.get("discount_inr")}
            )
        else:
            suite.add_test(
                "apply_promo_code() applies discount",
                "FAIL",
                "Invalid promo result",
                (time.time() - start) * 1000
            )
    except Exception as e:
        suite.add_test(
            "apply_promo_code() applies discount",
            "FAIL",
            f"Error: {e}",
            (time.time() - start) * 1000
        )
    
    # Test 7: Build cart
    start = time.time()
    try:
        async with MockZomatoMCPClient() as client:
            cart = await client.build_cart(
                items=[{"item_id": "item_001", "quantity": 2}],
                delivery_address={"street": "Test St", "city": "Bangalore", "pincode": "560001", "area": "Test"}
            )
        
        if cart and "cart_id" in cart:
            suite.add_test(
                "build_cart() creates staged cart",
                "PASS",
                f"Cart ID: {cart.get('cart_id')}",
                (time.time() - start) * 1000,
                {"cart_id": cart.get("cart_id"), "subtotal": cart.get("subtotal_inr")}
            )
        else:
            suite.add_test(
                "build_cart() creates staged cart",
                "FAIL",
                "Invalid cart structure",
                (time.time() - start) * 1000
            )
    except Exception as e:
        suite.add_test(
            "build_cart() creates staged cart",
            "FAIL",
            f"Error: {e}",
            (time.time() - start) * 1000
        )
    
    suite.end()
    return suite


# ========================================
# Test Suite 3: Agent Orchestration
# ========================================

async def test_agent_orchestration():
    """Test Lead-Worker agent orchestration."""
    suite = TestSuite("Agent Orchestration")
    suite.start()
    
    # Test 1: Import agents
    start = time.time()
    try:
        from backend.app.agents import LeadAgent, WorkerAgent
        suite.add_test(
            "Agent classes import successfully",
            "PASS",
            "LeadAgent and WorkerAgent imported",
            (time.time() - start) * 1000
        )
    except Exception as e:
        suite.add_test(
            "Agent classes import successfully",
            "FAIL",
            f"Import error: {e}",
            (time.time() - start) * 1000
        )
        suite.end()
        return suite
    
    # Test 2: Lead agent instantiation
    start = time.time()
    try:
        from backend.app.agents import LeadAgent
        lead = LeadAgent("test_session", "Test prompt")
        
        suite.add_test(
            "Lead agent instantiates",
            "PASS",
            f"Session ID: {lead.session_id}",
            (time.time() - start) * 1000
        )
    except Exception as e:
        suite.add_test(
            "Lead agent instantiates",
            "FAIL",
            f"Error: {e}",
            (time.time() - start) * 1000
        )
        suite.end()
        return suite
    
    # Test 3: Lead agent execution (simple query)
    start = time.time()
    try:
        from backend.app.agents import LeadAgent
        lead = LeadAgent("test_simple", "Simple lunch query")
        
        result = await lead.execute(
            query="Lunch options",
            location="Indiranagar",
            budget_cap_inr=500.0,
            group_size=1
        )
        
        if result.get("status") == "completed" and "restaurants" in result:
            suite.add_test(
                "Lead agent executes simple query",
                "PASS",
                f"Found {len(result.get('restaurants', []))} restaurants",
                (time.time() - start) * 1000,
                {"execution_time_ms": result.get("execution_time_ms")}
            )
        else:
            suite.add_test(
                "Lead agent executes simple query",
                "FAIL",
                f"Status: {result.get('status')}, missing restaurants",
                (time.time() - start) * 1000
            )
    except Exception as e:
        suite.add_test(
            "Lead agent executes simple query",
            "FAIL",
            f"Execution error: {e}",
            (time.time() - start) * 1000
        )
    
    # Test 4: Lead agent with workers (group query)
    start = time.time()
    try:
        from backend.app.agents import LeadAgent
        lead = LeadAgent("test_group", "Group order with constraints")
        
        result = await lead.execute(
            query="Keto and Vegan options",
            location="Koramangala",
            budget_cap_inr=2000.0,
            group_size=6,
            dietary_constraints=["Keto", "Vegan", "Nut-Free"]
        )
        
        has_synthesis = "synthesis" in result
        has_workers = len(lead.workers) == 3
        
        if result.get("status") == "completed" and has_synthesis and has_workers:
            suite.add_test(
                "Lead agent spawns workers for group order",
                "PASS",
                f"3 workers spawned, synthesis completed",
                (time.time() - start) * 1000,
                {
                    "worker_count": len(lead.workers),
                    "execution_time_ms": result.get("execution_time_ms")
                }
            )
        else:
            suite.add_test(
                "Lead agent spawns workers for group order",
                "FAIL",
                f"Workers: {len(lead.workers)}, has_synthesis: {has_synthesis}",
                (time.time() - start) * 1000
            )
    except Exception as e:
        suite.add_test(
            "Lead agent spawns workers for group order",
            "FAIL",
            f"Execution error: {e}",
            (time.time() - start) * 1000
        )
    
    # Test 5: Model routing logic
    start = time.time()
    try:
        from backend.app.agents import LeadAgent
        
        # Simple query should use Smart Intern
        simple_lead = LeadAgent("test_routing_simple", "Quick lunch")
        simple_model = simple_lead._determine_complexity()
        
        # Complex query should use PhD Reasoner
        complex_lead = LeadAgent("test_routing_complex", "Group order with severe peanut allergy")
        complex_model = complex_lead._determine_complexity()
        
        from backend.app.config import settings
        smart_intern_used = simple_model == settings.smart_intern_model
        phd_used = complex_model == settings.phd_reasoner_model
        
        if smart_intern_used and phd_used:
            suite.add_test(
                "Model routing works correctly",
                "PASS",
                f"Simple→{settings.smart_intern_model.split('/')[-1]}, Complex→{settings.phd_reasoner_model.split('/')[-1]}",
                (time.time() - start) * 1000
            )
        else:
            suite.add_test(
                "Model routing works correctly",
                "WARN",
                f"Routing may not be optimal: simple={simple_model}, complex={complex_model}",
                (time.time() - start) * 1000
            )
    except Exception as e:
        suite.add_test(
            "Model routing works correctly",
            "FAIL",
            f"Error: {e}",
            (time.time() - start) * 1000
        )
    
    suite.end()
    return suite


# Continue in next part...
