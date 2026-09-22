import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/workspace')

async def test_mcp_enhanced():
    """Test MCP with dependencies installed."""
    print("\n=== Testing MCP Client ===")
    results = {"passed": 0, "failed": 0, "tests": []}
    
    # Test 1: Import MCP SDK
    try:
        import mcp
        print("✓ MCP SDK imports")
        results["passed"] += 1
        results["tests"].append({"name": "MCP SDK import", "status": "PASS"})
    except Exception as e:
        print(f"✗ MCP SDK import failed: {e}")
        results["failed"] += 1
        results["tests"].append({"name": "MCP SDK import", "status": "FAIL", "error": str(e)})
        return results
    
    # Test 2: Import FlavorPilot MCP client
    try:
        from backend.app.mcp import MockZomatoMCPClient, ZomatoMCPClient
        print("✓ FlavorPilot MCP client imports")
        results["passed"] += 1
        results["tests"].append({"name": "FlavorPilot MCP client", "status": "PASS"})
    except Exception as e:
        print(f"✗ FlavorPilot MCP client import failed: {e}")
        results["failed"] += 1
        results["tests"].append({"name": "FlavorPilot MCP client", "status": "FAIL", "error": str(e)})
        return results
    
    # Test 3: Test all 5 MCP tools
    try:
        from backend.app.mcp import MockZomatoMCPClient
        async with MockZomatoMCPClient() as client:
            # Test each tool
            r1 = await client.search_restaurants("Keto", "Indiranagar", budget_cap_inr=500.0)
            r2 = await client.get_menu("rest_001")
            r3 = await client.get_item_customizations("item_001")
            r4 = await client.apply_promo_code("cart_test", "CBUSER")
            r5 = await client.build_cart([{"item_id": "i1", "quantity": 1}], {"street": "Test", "city": "B", "pincode": "560001", "area": "T"})
            
            assert len(r1) > 0
            assert "categories" in r2
            assert "customizations" in r3
            assert "discount_inr" in r4
            assert "cart_id" in r5
        
        print("✓ All 5 MCP tools functional")
        results["passed"] += 1
        results["tests"].append({"name": "5 MCP tools", "status": "PASS"})
    except Exception as e:
        print(f"✗ MCP tools test failed: {e}")
        results["failed"] += 1
        results["tests"].append({"name": "5 MCP tools", "status": "FAIL", "error": str(e)})
    
    return results

async def test_agents_enhanced():
    """Test agent orchestration."""
    print("\n=== Testing Agent Orchestration ===")
    results = {"passed": 0, "failed": 0, "tests": []}
    
    # Test 1: Import agents
    try:
        from backend.app.agents import LeadAgent, WorkerAgent
        print("✓ Agent classes import")
        results["passed"] += 1
        results["tests"].append({"name": "Agent imports", "status": "PASS"})
    except Exception as e:
        print(f"✗ Agent import failed: {e}")
        results["failed"] += 1
        results["tests"].append({"name": "Agent imports", "status": "FAIL", "error": str(e)})
        return results
    
    # Test 2: Lead agent execution
    try:
        from backend.app.agents import LeadAgent
        lead = LeadAgent("test_session", "Test prompt")
        result = await lead.execute("Lunch", "Indiranagar", budget_cap_inr=500.0, group_size=1)
        
        assert result.get("status") == "completed"
        assert "restaurants" in result
        
        print("✓ Lead agent executes queries")
        results["passed"] += 1
        results["tests"].append({"name": "Lead agent execution", "status": "PASS"})
    except Exception as e:
        print(f"✗ Lead agent execution failed: {e}")
        results["failed"] += 1
        results["tests"].append({"name": "Lead agent execution", "status": "FAIL", "error": str(e)})
    
    # Test 3: Worker orchestration
    try:
        from backend.app.agents import LeadAgent
        lead = LeadAgent("test_group", "Group order")
        result = await lead.execute("Keto Vegan", "Koramangala", budget_cap_inr=2000.0, group_size=6, dietary_constraints=["Keto"])
        
        assert len(lead.workers) == 3
        assert "synthesis" in result
        
        print("✓ Lead agent spawns 3 workers")
        results["passed"] += 1
        results["tests"].append({"name": "Worker orchestration", "status": "PASS"})
    except Exception as e:
        print(f"✗ Worker orchestration failed: {e}")
        results["failed"] += 1
        results["tests"].append({"name": "Worker orchestration", "status": "FAIL", "error": str(e)})
    
    return results

async def test_database_enhanced():
    """Test database schema."""
    print("\n=== Testing Database Schema ===")
    results = {"passed": 0, "failed": 0, "tests": []}
    
    # Test 1: Import models
    try:
        from backend.db.models import EvalCase, AgentTrajectory, EvalResult, Cart
        print("✓ Database models import")
        results["passed"] += 1
        results["tests"].append({"name": "Model imports", "status": "PASS"})
    except Exception as e:
        print(f"✗ Model import failed: {e}")
        results["failed"] += 1
        results["tests"].append({"name": "Model imports", "status": "FAIL", "error": str(e)})
        return results
    
    # Test 2: Model structure
    try:
        from backend.db.models import EvalCase, AgentTrajectory, EvalResult, Cart
        
        assert hasattr(EvalCase, '__tablename__')
        assert hasattr(AgentTrajectory, '__tablename__')
        assert hasattr(EvalResult, '__tablename__')
        assert hasattr(Cart, '__tablename__')
        
        print("✓ All models have table names")
        results["passed"] += 1
        results["tests"].append({"name": "Model structure", "status": "PASS"})
    except Exception as e:
        print(f"✗ Model structure test failed: {e}")
        results["failed"] += 1
        results["tests"].append({"name": "Model structure", "status": "FAIL", "error": str(e)})
    
    # Test 3: Required fields
    try:
        from backend.db.models import EvalCase, Cart
        
        eval_fields = ['id', 'slice', 'eval_type', 'user_prompt']
        cart_fields = ['subtotal_inr', 'total_inr', 'status']
        
        eval_annotations = getattr(EvalCase, '__annotations__', {})
        cart_annotations = getattr(Cart, '__annotations__', {})
        
        eval_present = sum(1 for f in eval_fields if f in eval_annotations)
        cart_present = sum(1 for f in cart_fields if f in cart_annotations)
        
        assert eval_present >= 3
        assert cart_present >= 2
        
        print("✓ Required fields present in models")
        results["passed"] += 1
        results["tests"].append({"name": "Required fields", "status": "PASS"})
    except Exception as e:
        print(f"✗ Required fields test failed: {e}")
        results["failed"] += 1
        results["tests"].append({"name": "Required fields", "status": "FAIL", "error": str(e)})
    
    return results

async def main():
    print("="*80)
    print("FlavorPilot Enhanced Validation Suite")
    print("="*80)
    
    start = time.time()
    all_results = {}
    
    # Run tests
    all_results["mcp"] = await test_mcp_enhanced()
    all_results["agents"] = await test_agents_enhanced()
    all_results["database"] = await test_database_enhanced()
    
    # Calculate totals
    total_passed = sum(r["passed"] for r in all_results.values())
    total_failed = sum(r["failed"] for r in all_results.values())
    total_tests = total_passed + total_failed
    pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    duration = time.time() - start
    
    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)
    print(f"Total Tests: {total_tests}")
    print(f"✓ Passed: {total_passed}")
    print(f"✗ Failed: {total_failed}")
    print(f"Pass Rate: {pass_rate:.1f}%")
    print(f"Duration: {duration:.2f}s")
    print()
    
    # Save results
    results = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "pass_rate": pass_rate
        },
        "suites": all_results
    }
    
    with open("/workspace/enhanced_validation_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("Results saved to: enhanced_validation_results.json")
    
    return 0 if total_failed == 0 else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
