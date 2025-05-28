# Tester Service Plugins

> **Plugin Type**: Tester Service  
> **Verified Source Location**: `plugins/services/testers/`  

## Overview

Tester plugins provide mechanisms for evaluating implementations, generating test traffic, and validating results. They work in conjunction with Implementation Under Test (IUT) plugins to validate protocol conformance and performance.

<!-- src: /panther/plugins/services/testers/ -->

## Available Plugins

| Plugin | Description | Documentation |
|--------|-------------|---------------|
| panther_ivy | Formal verification tester using Ivy | [Documentation](panther/plugins/services/testers/panther_ivy/README.md) |


## Integration Points

Tester plugins integrate with:

1. **IUT plugins**: They test and validate IUT behavior
2. **Protocol plugins**: They understand protocol specifications
3. **Environment plugins**: They run within specific execution and network environments

## Development

To create a new tester plugin, see the [Tester Development Guide](panther/plugins/services/testers/development.md).