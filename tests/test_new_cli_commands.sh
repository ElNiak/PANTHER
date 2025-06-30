#!/bin/bash
# Test script for new CLI commands

echo "=== Testing PANTHER CLI Migration ==="
echo

echo "1. Testing tools command:"
python -m panther tools list
echo

echo "2. Testing check command help:"
python -m panther check --help | head -10
echo

echo "3. Testing metrics command help:"
python -m panther metrics --help | head -10
echo

echo "4. Testing admin docker help:"
python -m panther admin docker --help | head -10
echo

echo "5. Testing migration messages in panther_builder.py:"
echo "   Trying 'python panther_builder.py check':"
python panther_builder.py check 2>&1 | tail -5
echo

echo "   Trying 'python panther_builder.py install-slim':"
python panther_builder.py install-slim 2>&1 | tail -5
echo

echo "=== All tests completed ==="