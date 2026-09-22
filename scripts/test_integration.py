# FlavorPilot Integration Test Script
#
# Automated integration testing for FlavorPilot system

import asyncio
import json
from pathlib import Path


async def test_golden_dataset():
    """Verify golden dataset exists and has correct structure."""
    print("✓ Testing golden dataset...")
    
    dataset_path = Path("/workspace/scratch/golden_dataset_flavorpilot.json")
    assert dataset_path.exists(), "Golden dataset not found"
    
    with open(dataset_path) as f:
        dataset = json.load(f)
    
    assert len(dataset) == 100, f"Expected 100 cases, found {len(dataset)}"
    
    # Verify structure of first case
    case = dataset[0]
    required_fields = ["id", "slice", "eval_type", "user_prompt", "mcp_tools_required", "expected_constraints"]
    for field in required_fields:
        assert field in case, f"Missing required field: {field}"
    
    print(f"  ✅ Golden dataset verified: {len(dataset)} test cases")
    return True


async def test_mcp_client():
    """Test MCP client initialization."""
    print("✓ Testing MCP client...")
    
    try:
        from backend.app.mcp import MockZomatoMCPClient
        
        async with MockZomatoMCPClient() as client:
            # Test search
            results = await client.search_restaurants(
                query="Keto Bowl",
                location="Indiranagar",
                budget_cap_inr=500.0
            )
            assert len(results) > 0, "No restaurants returned"
            assert "restaurant_id" in results[0], "Invalid restaurant structure"
        
        print("  ✅ MCP client functional")
        return True
        
    except Exception as e:
        print(f"  ❌ MCP client error: {e}")
        return False


async def test_lead_worker_orchestration():
    """Test Lead-Worker agent orchestration."""
    print("✓ Testing Lead-Worker orchestration...")
    
    try:
        from backend.app.agents import LeadAgent
        import uuid
        
        session_id = f"test_{uuid.uuid4().hex[:8]}"
        lead = LeadAgent(session_id, "Test prompt")
        
        result = await lead.execute(
            query="Keto lunch",
            location="Indiranagar",
            budget_cap_inr=500.0,
            group_size=1,
        )
        
        assert result["status"] in ["completed", "error"], "Invalid status"
        assert "restaurants" in result, "No restaurants in result"
        
        print("  ✅ Lead-Worker orchestration functional")
        return True
        
    except Exception as e:
        print(f"  ❌ Orchestration error: {e}")
        return False


async def test_evaluator():
    """Test RAG Triad evaluator."""
    print("✓ Testing evaluator...")
    
    try:
        from backend.app.evals import FlavorPilotEvaluator
        
        evaluator = FlavorPilotEvaluator()
        
        # Mock data
        user_prompt = "Find me a Keto lunch in Indiranagar under ₹500"
        tool_arguments = {
            "query": "Keto lunch",
            "location": "Indiranagar",
            "budget_cap_inr": 500.0
        }
        tool_results = {
            "restaurants": [
                {
                    "restaurant_id": "rest_001",
                    "name": "Test Restaurant",
                    "price_inr": 450.0
                }
            ]
        }
        agent_output = tool_results
        expected_constraints = {
            "max_budget_inr": 500,
            "cuisine": "Keto"
        }
        
        result = evaluator.evaluate(
            user_prompt,
            tool_arguments,
            tool_results,
            agent_output,
            expected_constraints
        )
        
        assert "groundedness_score" in result, "Missing groundedness score"
        assert "safety_score" in result, "Missing safety score"
        assert result["status"] in ["pass", "fail"], "Invalid evaluation status"
        
        print("  ✅ Evaluator functional")
        print(f"    - Groundedness: {result['groundedness_score']:.2%}")
        print(f"    - Safety: {result['safety_score']:.2%}")
        return True
        
    except Exception as e:
        print(f"  ❌ Evaluator error: {e}")
        return False


async def run_integration_tests():
    """Run all integration tests."""
    print("="*60)
    print("FlavorPilot Integration Test Suite")
    print("="*60)
    print()
    
    results = []
    
    # Test 1: Golden Dataset
    results.append(await test_golden_dataset())
    print()
    
    # Test 2: MCP Client
    results.append(await test_mcp_client())
    print()
    
    # Test 3: Lead-Worker Orchestration
    results.append(await test_lead_worker_orchestration())
    print()
    
    # Test 4: Evaluator
    results.append(await test_evaluator())
    print()
    
    # Summary
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Integration Tests: {passed}/{total} passed")
    
    if passed == total:
        print("✅ ALL TESTS PASSED")
    else:
        print(f"❌ {total - passed} tests failed")
    
    print("="*60)
    
    return passed == total


if __name__ == "__main__":
    import sys
    success = asyncio.run(run_integration_tests())
    sys.exit(0 if success else 1)
