"""Database seeding script for Golden Dataset."""
import asyncio
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.db import init_db, get_session
from backend.db.models import EvalCase


async def seed_golden_dataset():
    """Seed eval_cases table from golden_dataset_flavorpilot.json."""
    
    # Load golden dataset
    dataset_path = Path("/workspace/scratch/golden_dataset_flavorpilot.json")
    
    if not dataset_path.exists():
        print(f"Error: Golden dataset not found at {dataset_path}")
        print("Please run: python seed_data_flavorpilot.py first")
        return
    
    with open(dataset_path) as f:
        test_cases = json.load(f)
    
    print(f"Loading {len(test_cases)} test cases from golden dataset...")
    
    # Initialize database
    await init_db()
    print("Database initialized")
    
    # Insert test cases
    async with get_session() as session:
        for case in test_cases:
            eval_case = EvalCase(
                id=case["id"],
                slice=case["slice"],
                eval_type=case["eval_type"],
                user_prompt=case["user_prompt"],
                mcp_tools_required=case["mcp_tools_required"],
                expected_constraints=case["expected_constraints"],
                ground_truth_schema=case.get("ground_truth_schema"),
                eval_rubric=case.get("eval_rubric"),
            )
            session.add(eval_case)
        
        await session.commit()
    
    print(f"✅ Successfully seeded {len(test_cases)} evaluation cases")
    
    # Summary by slice
    from collections import Counter
    slice_counts = Counter(case["slice"] for case in test_cases)
    print("\nBreakdown by evaluation slice:")
    for slice_name, count in slice_counts.items():
        print(f"  - {slice_name}: {count} cases")


if __name__ == "__main__":
    asyncio.run(seed_golden_dataset())
