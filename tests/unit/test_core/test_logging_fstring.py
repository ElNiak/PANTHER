#!/usr/bin/env python3
import logging

def test_function():
    raw_version_config = {"version": "1.0", "features": ["ping", "pong"]}
    logging.debug(f"Loaded raw PingPong version config: {raw_version_config}")
    
    # Also test logger variant
    logger = logging.getLogger(__name__)
    logger.debug(f"Another test with logger: {raw_version_config}")
    
    # Test with string before f-string
    logging.info("Some prefix", f"Inline f-string: {raw_version_config}")
