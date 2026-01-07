"""Manual test script for POST /v1/full-review endpoint.

This script demonstrates how to use the full-review endpoint.
It requires a valid OPENAI_API_KEY environment variable.

Usage:
    export OPENAI_API_KEY=your-key-here
    python examples/test_full_review.py
"""

import json
import sys

import httpx


def test_full_review():
    """Test the full-review endpoint with a sample idea."""
    url = "http://localhost:8000/v1/full-review"

    # Sample request
    request_data = {
        "idea": "Build a REST API for user management with authentication.",
        "extra_context": {
            "language": "Python",
            "version": "3.11+",
            "features": ["auth", "CRUD", "role-based access"],
        },
    }

    print("=" * 80)
    print("Testing POST /v1/full-review endpoint")
    print("=" * 80)
    print("\nRequest:")
    print(json.dumps(request_data, indent=2))
    print("\nSending request...")

    try:
        response = httpx.post(url, json=request_data, timeout=60.0)

        print(f"\nStatus Code: {response.status_code}")
        print(f"Request ID: {response.headers.get('X-Request-ID', 'N/A')}")

        if response.status_code == 200:
            data = response.json()
            print("\n" + "=" * 80)
            print("SUCCESS RESPONSE")
            print("=" * 80)

            # Print expanded proposal summary
            print("\n1. EXPANDED PROPOSAL:")
            proposal = data["expanded_proposal"]
            print(f"   Problem: {proposal['problem_statement'][:100]}...")
            print(f"   Solution: {proposal['proposed_solution'][:100]}...")
            print(f"   Assumptions: {len(proposal['assumptions'])} items")
            print(f"   Scope/Non-Goals: {len(proposal['scope_non_goals'])} items")

            # Print persona reviews summary
            print("\n2. PERSONA REVIEWS:")
            for i, review in enumerate(data["persona_reviews"], 1):
                print(f"   {i}. {review['persona_name']} (ID: {review['persona_id']}):")
                print(f"      Confidence: {review['confidence_score']:.2f}")
                print(f"      Strengths: {len(review['strengths'])} items")
                print(f"      Concerns: {len(review['concerns'])} items")
                print(f"      Blocking Issues: {len(review['blocking_issues'])} items")

            # Print decision
            print("\n3. FINAL DECISION:")
            decision = data["decision"]
            print(f"   Decision: {decision['decision'].upper()}")
            print(f"   Weighted Confidence: {decision['weighted_confidence']:.4f}")

            # Print score breakdown
            breakdown = decision.get("detailed_score_breakdown", {})
            if breakdown:
                print("   Persona Weights:")
                for persona_id, weight in breakdown["weights"].items():
                    score = breakdown["individual_scores"][persona_id]
                    contrib = breakdown["weighted_contributions"][persona_id]
                    print(
                        f"     - {persona_id}: weight={weight:.2f}, "
                        f"score={score:.2f}, contribution={contrib:.4f}"
                    )

            # Print minority reports if any
            minority_reports = decision.get("minority_reports")
            if minority_reports:
                print(f"\n4. MINORITY REPORTS ({len(minority_reports)}):")
                for report in minority_reports:
                    print(f"   - {report['persona_name']}:")
                    print(f"     Blocking Summary: {report['blocking_summary'][:80]}...")
                    print(f"     Mitigation: {report['mitigation_recommendation'][:80]}...")

            # Print run metadata
            print("\n5. RUN METADATA:")
            print(f"   Run ID: {data['run_id']}")
            print(f"   Total Elapsed Time: {data['elapsed_time']:.2f}s")
            print(f"   Expand Time: {proposal['metadata']['elapsed_time']:.2f}s")

        else:
            # Error response
            print("\n" + "=" * 80)
            print("ERROR RESPONSE")
            print("=" * 80)
            error_data = response.json()
            print(f"\nError Code: {error_data.get('code', 'UNKNOWN')}")
            print(f"Message: {error_data.get('message', 'N/A')}")
            print(f"Failed Step: {error_data.get('failed_step', 'N/A')}")
            print(f"Run ID: {error_data.get('run_id', 'N/A')}")

            if error_data.get("partial_results"):
                print("\nPartial Results Available:")
                print(f"  Keys: {list(error_data['partial_results'].keys())}")

    except httpx.ConnectError:
        print("\nERROR: Could not connect to server at http://localhost:8000")
        print("Make sure the server is running:")
        print("  uvicorn consensus_engine.app:app --reload")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    test_full_review()
