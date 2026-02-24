#!/bin/bash

# Test script for different command types

echo 'Testing variable_assignment:'
TARGET_IP=127.0.0.1; echo $TARGET_IP
echo '----------'

echo 'Testing shell_builtin:'
set -e; echo 'Set command executed'
echo '----------'

echo 'Testing control_structure:'
for i in 1 2 3; do echo $i; done
echo '----------'

echo 'Testing nested_quotes:'
export PS4="+ [${BASH_SOURCE:-sh}:${LINENO}] "; echo $PS4
echo '----------'
