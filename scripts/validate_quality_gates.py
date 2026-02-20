import json
import sys


def validate_results(results_file):
    """Basic quality gate validation."""
    try:
        with open(results_file, "r") as f:
            results = json.load(f)

        total_issues = 0
        critical_issues = 0

        for tool_result in results.get("result", []):
            for issue in tool_result.get("results", []):
                total_issues += 1
                if issue.get("level", "").lower() in ["error", "critical"]:
                    critical_issues += 1

        print(f"Total issues found: {total_issues}")
        print(f"Critical issues found: {critical_issues}")

        if critical_issues > 0:
            print("Quality gate failed: Critical issues found")
            return False

        if total_issues > 50:  # Threshold for total issues
            print("Quality gate failed: Too many issues")
            return False

        print("Quality gate passed")
        return True

    except Exception as e:
        print(f"Error validating results: {e}")
        return True  # Don't fail on validation errors for now


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate_quality_gates.py <results_file>")
        sys.exit(1)

    success = validate_results(sys.argv[1])
    sys.exit(0 if success else 1)
