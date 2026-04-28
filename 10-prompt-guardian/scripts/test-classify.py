"""
Prompt Guardian — Phase 1 Test Runner
Sends all 30 test prompts to the /classify endpoint and shows results.
Usage: python test-classify.py <function_url>
"""

import json
import sys
import urllib.request
import urllib.error
from datetime import datetime

def test_prompt(url: str, prompt_data: dict) -> dict:
    payload = json.dumps({"prompt": prompt_data["prompt"]}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "X-User-ID": "meek-test"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
            return result
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()}"}
    except Exception as e:
        return {"error": str(e)}

def color(text, code):
    codes = {"green": "32", "red": "31", "yellow": "33", "cyan": "36", "gray": "90"}
    return f"\033[{codes.get(code,'0')}m{text}\033[0m"

def main():
    if len(sys.argv) < 2:
        print("Usage: python test-classify.py <function_url>")
        print("Example: python test-classify.py https://fn-promptguard-abc123.azurewebsites.net/api/classify")
        sys.exit(1)

    url = sys.argv[1]

    with open("../scripts/prompt-guardian-test-data.json") as f:
        test_data = json.load(f)

    prompts = test_data["test_prompts"]
    print(f"\n{'='*70}")
    print(f"Prompt Guardian — Classification Test Runner")
    print(f"Endpoint: {url}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total prompts: {len(prompts)}")
    print(f"{'='*70}\n")

    passed = 0
    failed = 0
    errors = 0
    results = []

    for p in prompts:
        expected = p["expected_action"]
        category = p["category"]
        pid      = p["id"]
        short    = p["prompt"][:80] + "..." if len(p["prompt"]) > 80 else p["prompt"]

        print(f"[{pid:02d}] {color(category, 'cyan')} | Expected: {color(expected, 'gray')}")
        print(f"     {short}")

        result = test_prompt(url, p)

        if "error" in result:
            print(f"     {color('ERROR: ' + result['error'], 'red')}\n")
            errors += 1
            results.append({**p, "actual": "ERROR", "match": False})
            continue

        actual     = result.get("action", "UNKNOWN")
        severity   = result.get("severity", "?")
        confidence = result.get("confidence", "?")
        summary    = result.get("summary", "")[:100]
        match      = actual == expected

        if match:
            passed += 1
            status = color(f"PASS — {actual}", "green")
        else:
            failed += 1
            status = color(f"FAIL — got {actual}, expected {expected}", "red")

        print(f"     {status} | severity: {severity} | confidence: {confidence}")
        print(f"     {color(summary, 'gray')}\n")

        results.append({**p, "actual": actual, "result": result, "match": match})

    # Summary
    print(f"{'='*70}")
    print(f"Results: {color(str(passed) + ' passed', 'green')} | {color(str(failed) + ' failed', 'red')} | {str(errors) + ' errors'}")
    print(f"Accuracy: {round(passed / (len(prompts) - errors) * 100, 1)}%")

    # Breakdown by category
    print(f"\nBy category:")
    cats = {}
    for r in results:
        cat = r["category"]
        if cat not in cats:
            cats[cat] = {"pass": 0, "fail": 0}
        if r["match"]:
            cats[cat]["pass"] += 1
        else:
            cats[cat]["fail"] += 1

    for cat, counts in sorted(cats.items()):
        total   = counts["pass"] + counts["fail"]
        pct     = round(counts["pass"] / total * 100)
        bar     = color(f"{counts['pass']}/{total} ({pct}%)", "green" if pct == 100 else "yellow" if pct >= 80 else "red")
        print(f"  {cat:<15} {bar}")

    print(f"{'='*70}\n")

    # Save results
    output_file = f"test-results-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump({
            "endpoint":   url,
            "timestamp":  datetime.now().isoformat(),
            "passed":     passed,
            "failed":     failed,
            "errors":     errors,
            "accuracy":   round(passed / (len(prompts) - errors) * 100, 1),
            "results":    results
        }, f, indent=2)
    print(f"Full results saved to: {output_file}")

if __name__ == "__main__":
    main()
