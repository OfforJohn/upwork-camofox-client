"""Test clean output contract with real Camofox session."""

import asyncio
import json
import sys
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.domain_camofox.session import SessionManager, SessionConfig
from packages.domain_actions.runner import ActionRunner, ActionEnvelope, ActionType


async def main():
    """Test the clean output contract with real browser."""
    print("Testing clean output contract with real Camofox session...")
    
    # Create runner
    runner = ActionRunner()
    
    # Create action envelope for search
    action = ActionEnvelope(
        type=ActionType.JOBS_SEARCH,
        account_id="test_account",
        payload={"query": "python"},
    )
    
    print("\nExecuting search action...")
    result = await runner.execute(action)
    
    print(f"\nSuccess: {result.success}")
    if result.error:
        print(f"Error: {result.error}")
    
    if result.data:
        print(f"\nResponse data:")
        print(json.dumps(result.data, indent=2, default=str))
        
        # Check for jobs array
        if "jobs" in result.data:
            print(f"\n✅ Jobs array found in response")
            jobs = result.data["jobs"]
            print(f"Number of jobs: {len(jobs)}")
            
            if jobs:
                print(f"\nFirst job structure:")
                print(json.dumps(jobs[0], indent=2, default=str))
                
                # Verify required fields
                required_fields = ["job_id", "title", "description", "client_id", "client_name", "posted_date", "url", "status", "tags"]
                first_job = jobs[0]
                missing_fields = [field for field in required_fields if field not in first_job]
                
                if missing_fields:
                    print(f"\n❌ Missing required fields: {missing_fields}")
                else:
                    print(f"\n✅ All required fields present")
                    
                # Check that deprecated fields are not present
                deprecated_fields = ["id", "created_at", "updated_at"]
                found_deprecated = [field for field in deprecated_fields if field in first_job]
                
                if found_deprecated:
                    print(f"\n❌ Found deprecated fields: {found_deprecated}")
                else:
                    print(f"\n✅ No deprecated fields present")
        else:
            print(f"\n❌ Jobs array not found in response")
    else:
        print(f"\n❌ No data in response")


if __name__ == "__main__":
    asyncio.run(main())
