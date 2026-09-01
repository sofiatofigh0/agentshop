"""
A tiny evaluation harness. Run it with: python evals.py

For each sample job we write down what we think the agent should do, then run it
and compare. No test framework — just a loop, a dict of expectations, and a
count at the end.

The expectations below are our judgement calls, not the agent's. If one fails,
the honest first question is whether the agent was wrong or whether the
expectation was.
"""

from agent import evaluate, parse_recommendation, report_text
from sample_jobs import SAMPLES

# recommendation: what a careful human would conclude for THIS candidate profile.
# research_useful: whether an external search could plausibly change that answer.
EXPECTED = {
    # Excellent role fit, but the posting is SF hybrid 3 days onsite and the
    # profile refuses relocation — a hard constraint, so the geography rules it
    # out regardless of how well the rest matches. Was MAYBE; the agent argued
    # SKIP three runs running and it had the better reading.
    "STRONG_FIT_AI_PRODUCT": {"recommendation": "SKIP", "research_useful": True},
    # Hits several items on the avoid-list outright. Nothing to search on — the
    # employer is anonymous, so no external fact is reachable.
    "AMBIGUOUS_ROLE": {"recommendation": "SKIP", "research_useful": False},
    # Disqualifying on the face of the posting. No external fact rescues it.
    "POOR_FIT_RED_FLAGS": {"recommendation": "SKIP", "research_useful": False},
    # Clears every hard constraint and is well specified on the role. The one
    # gap — company stage, funding, trajectory — is exactly the kind of thing a
    # search can close, and it bears on a stated preference (Series A to C).
    "REMOTE_STRONG_FIT_UNKNOWN_COMPANY": {"recommendation": "APPLY", "research_useful": True},
}


if __name__ == "__main__":
    rec_passes = 0
    search_passes = 0
    total_searches = 0
    total_input = 0
    total_output = 0

    for name, expected in EXPECTED.items():
        result = evaluate(SAMPLES[name])

        actual = parse_recommendation(report_text(result["response"]))
        searched = result["search_count"] > 0

        rec_ok = actual == expected["recommendation"]
        search_ok = searched == expected["research_useful"]

        rec_passes += rec_ok
        search_passes += search_ok
        total_searches += result["search_count"]
        total_input += result["input_tokens"]
        total_output += result["output_tokens"]

        print(f"{name}")
        print(f"  expected recommendation: {expected['recommendation']}")
        print(f"  actual recommendation:   {actual}")
        print(f"  recommendation:          {'PASS' if rec_ok else 'FAIL'}")
        print(f"  search_web calls:        {result['search_count']}")
        print(f"  searched:                {searched}")
        print(f"  research expected:       {expected['research_useful']}")
        print(f"  search behavior:         {'PASS' if search_ok else 'FAIL'}")
        print(f"  input tokens:            {result['input_tokens']}")
        print(f"  output tokens:           {result['output_tokens']}")
        print()

    total = len(EXPECTED)
    print(f"Recommendation accuracy: {rec_passes}/{total}")
    print(f"Search-behavior accuracy: {search_passes}/{total}")
    print(f"Total searches: {total_searches}")
    print(f"Total input tokens: {total_input}")
    print(f"Total output tokens: {total_output}")
