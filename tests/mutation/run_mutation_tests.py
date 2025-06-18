#!/usr/bin/env python3
"""
Mutation Testing Runner for PANTHER

This script runs mutation testing on selected PANTHER modules to validate test quality.
It uses a lightweight mutation testing approach that doesn't require external tools.
"""

import ast
import copy
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

class SimpleMutator:
    """Simple mutation generator for Python code."""

    def __init__(self, source_code: str):
        self.source_code = source_code
        self.tree = ast.parse(source_code)
        self.mutations = []

    def generate_mutations(self) -> List[Tuple[str, str]]:
        """Generate mutations for the source code."""
        # Boolean mutations
        for node in ast.walk(self.tree):
            if isinstance(node, ast.NameConstant):
                if node.value is True:
                    mutation = self._mutate_node(node, ast.NameConstant(value=False))
                    self.mutations.append(("boolean_flip", mutation))
                elif node.value is False:
                    mutation = self._mutate_node(node, ast.NameConstant(value=True))
                    self.mutations.append(("boolean_flip", mutation))

            # Comparison operator mutations
            elif isinstance(node, ast.Compare):
                for i, op in enumerate(node.ops):
                    if isinstance(op, ast.Eq):
                        mutation = self._mutate_operator(node, i, ast.NotEq())
                        self.mutations.append(("comparison_mutation", mutation))
                    elif isinstance(op, ast.NotEq):
                        mutation = self._mutate_operator(node, i, ast.Eq())
                        self.mutations.append(("comparison_mutation", mutation))
                    elif isinstance(op, ast.Lt):
                        mutation = self._mutate_operator(node, i, ast.GtE())
                        self.mutations.append(("comparison_mutation", mutation))
                    elif isinstance(op, ast.Gt):
                        mutation = self._mutate_operator(node, i, ast.LtE())
                        self.mutations.append(("comparison_mutation", mutation))

            # Arithmetic operator mutations
            elif isinstance(node, ast.BinOp):
                if isinstance(node.op, ast.Add):
                    mutation = self._mutate_binop(node, ast.Sub())
                    self.mutations.append(("arithmetic_mutation", mutation))
                elif isinstance(node.op, ast.Sub):
                    mutation = self._mutate_binop(node, ast.Add())
                    self.mutations.append(("arithmetic_mutation", mutation))

            # Return value mutations
            elif isinstance(node, ast.Return):
                if node.value:
                    if isinstance(node.value, ast.NameConstant):
                        if node.value.value is True:
                            mutation = self._mutate_return(
                                node, ast.NameConstant(value=False)
                            )
                            self.mutations.append(("return_mutation", mutation))
                        elif node.value.value is False:
                            mutation = self._mutate_return(
                                node, ast.NameConstant(value=True)
                            )
                            self.mutations.append(("return_mutation", mutation))

        return self.mutations

    def _mutate_node(self, old_node, new_node):
        """Replace a node in the AST and return mutated code."""
        tree_copy = copy.deepcopy(self.tree)
        for node in ast.walk(tree_copy):
            for field, value in ast.iter_fields(node):
                if value is old_node or (isinstance(value, list) and old_node in value):
                    if isinstance(value, list):
                        value[value.index(old_node)] = new_node
                    else:
                        setattr(node, field, new_node)
        return ast.unparse(tree_copy)

    def _mutate_operator(self, compare_node, op_index, new_op):
        """Mutate a comparison operator."""
        tree_copy = copy.deepcopy(self.tree)
        for node in ast.walk(tree_copy):
            if isinstance(node, ast.Compare) and node.lineno == compare_node.lineno:
                node.ops[op_index] = new_op
        return ast.unparse(tree_copy)

    def _mutate_binop(self, binop_node, new_op):
        """Mutate a binary operator."""
        tree_copy = copy.deepcopy(self.tree)
        for node in ast.walk(tree_copy):
            if isinstance(node, ast.BinOp) and node.lineno == binop_node.lineno:
                node.op = new_op
        return ast.unparse(tree_copy)

    def _mutate_return(self, return_node, new_value):
        """Mutate a return value."""
        tree_copy = copy.deepcopy(self.tree)
        for node in ast.walk(tree_copy):
            if isinstance(node, ast.Return) and node.lineno == return_node.lineno:
                node.value = new_value
        return ast.unparse(tree_copy)

class MutationTester:
    """Run tests against mutated code to validate test quality."""

    def __init__(self, target_file: Path, test_command: str = "pytest -x -q"):
        self.target_file = target_file
        self.test_command = test_command
        self.original_content = target_file.read_text()
        self.results = {
            "killed": 0,
            "survived": 0,
            "timeout": 0,
            "error": 0,
            "total": 0,
        }
        self.survived_mutations = []

    def run(self, max_mutations: int = 20) -> Dict[str, Any]:
        """Run mutation testing on the target file."""
        print(f"\n🧬 Mutation testing: {self.target_file}")
        print(f"   Running up to {max_mutations} mutations...")

        # Generate mutations
        mutator = SimpleMutator(self.original_content)
        mutations = mutator.generate_mutations()

        # Limit mutations
        if len(mutations) > max_mutations:
            mutations = random.sample(mutations, max_mutations)

        # Test each mutation
        for i, (mutation_type, mutated_code) in enumerate(mutations):
            self.results["total"] += 1
            print(f"   Mutation {i+1}/{len(mutations)}: {mutation_type}", end=" ... ")

            # Apply mutation
            self.target_file.write_text(mutated_code)

            # Run tests
            start_time = time.time()
            result = self._run_tests()
            duration = time.time() - start_time

            # Categorize result
            if result == "killed":
                self.results["killed"] += 1
                print("✅ KILLED (tests detected the mutation)")
            elif result == "survived":
                self.results["survived"] += 1
                self.survived_mutations.append(
                    {
                        "type": mutation_type,
                        "file": str(self.target_file),
                        "line": i,  # Simplified line tracking
                    }
                )
                print("❌ SURVIVED (tests didn't detect the mutation)")
            elif result == "timeout":
                self.results["timeout"] += 1
                print("⏱️  TIMEOUT")
            else:
                self.results["error"] += 1
                print("⚠️  ERROR")

        # Restore original file
        self.target_file.write_text(self.original_content)

        return self.results

    def _run_tests(self, timeout: int = 30) -> str:
        """Run tests and return result status."""
        try:
            result = subprocess.run(
                self.test_command.split(),
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode == 0:
                return "survived"  # Tests passed - mutation survived
            else:
                return "killed"  # Tests failed - mutation killed

        except subprocess.TimeoutExpired:
            return "timeout"
        except Exception as e:
            print(f"Error running tests: {e}")
            return "error"

    def get_mutation_score(self) -> float:
        """Calculate mutation score (killed / total)."""
        if self.results["total"] == 0:
            return 0.0
        return (self.results["killed"] / self.results["total"]) * 100

def run_mutation_testing_suite():
    """Run mutation testing on key PANTHER modules."""
    print("🧬 PANTHER Mutation Testing Suite")
    print("=" * 50)

    # Target files for mutation testing
    target_files = [
        "panther/core/events/base/event_base.py",
        "panther/core/command_processor/command.py",
        "panther/core/observer/base/observer_interface.py",
    ]

    all_results = {}
    total_stats = {"killed": 0, "survived": 0, "timeout": 0, "error": 0, "total": 0}

    for target_path in target_files:
        target_file = Path(target_path)
        if not target_file.exists():
            print(f"⚠️  Skipping {target_path} - file not found")
            continue

        # Determine appropriate test command
        if "event" in target_path:
            test_cmd = "pytest tests/unit/test_core/test_event_system.py -x -q"
        elif "command" in target_path:
            test_cmd = "pytest tests/unit/test_core/test_command_processor.py -x -q"
        elif "observer" in target_path:
            test_cmd = "pytest tests/unit/test_core/test_observer_system.py -x -q"
        else:
            test_cmd = "pytest -x -q"

        tester = MutationTester(target_file, test_cmd)
        results = tester.run(max_mutations=10)

        # Accumulate results
        all_results[target_path] = results
        for key in total_stats:
            total_stats[key] += results[key]

        # Print module results
        score = tester.get_mutation_score()
        print(f"\n   Mutation Score: {score:.1f}%")
        print(f"   Killed: {results['killed']}, Survived: {results['survived']}")

    # Print summary
    print("\n" + "=" * 50)
    print("📊 MUTATION TESTING SUMMARY")
    print("=" * 50)
    print(f"Total Mutations: {total_stats['total']}")
    print(
        f"Killed: {total_stats['killed']} ({total_stats['killed']/max(1, total_stats['total'])*100:.1f}%)"
    )
    print(
        f"Survived: {total_stats['survived']} ({total_stats['survived']/max(1, total_stats['total'])*100:.1f}%)"
    )
    print(f"Timeout: {total_stats['timeout']}")
    print(f"Errors: {total_stats['error']}")

    overall_score = (total_stats["killed"] / max(1, total_stats["total"])) * 100
    print(f"\n🎯 Overall Mutation Score: {overall_score:.1f}%")

    if overall_score >= 80:
        print("✅ Excellent test quality!")
    elif overall_score >= 60:
        print("⚠️  Good test quality, but room for improvement")
    else:
        print("❌ Test quality needs improvement")

    return all_results

if __name__ == "__main__":
    # Ensure we're in the project root
    project_root = Path(__file__).parent.parent.parent
    os.chdir(project_root)

    # Run mutation testing
    results = run_mutation_testing_suite()
