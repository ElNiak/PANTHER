# TASK-CS-001: Cache File Security Enhancement

## Objective
Implement secure cache file management for DockerImageCache to prevent unauthorized access, ensure atomic writes, and add proper file permission controls to protect cached Docker image metadata.

## Technical Details

### Current Issues
- Cache file created with default permissions (potentially world-readable)
- Non-atomic cache writes risk corruption during concurrent access
- Missing cache file permission validation
- No secure temp file handling during cache updates

### Proposed Solution
Enhance cache file security by:
1. Setting secure file permissions (600) for cache files
2. Implementing atomic write operations to prevent corruption
3. Adding cache directory security validation
4. Proper cleanup of temporary files on errors

## Files to Modify

### Primary File
- `REPOS/PANTHER/panther/core/docker_builder/caching/docker_image_cache.py`

### Specific Changes

#### 1. Update cache file initialization in `__init__()` method (lines 80-98)

**Current Code:**
```python
self.cache_file = (
    cache_file or Path.home() / ".panther" / "docker_image_cache.json"
)
self.retry_count = retry_count
self.retry_delay = retry_delay

# Thread-safe cache storage
self._cache: Dict[str, CachedImage] = {}
self._cache_lock = threading.RLock()
self._last_refresh = 0.0

# Docker client (will be set by DockerBuilder)
self._docker_client: Optional[docker.DockerClient] = None

# Create cache directory
self.cache_file.parent.mkdir(parents=True, exist_ok=True)

# Load existing cache
self._load_cache()
```

**New Code:**
```python
self.cache_file = (
    cache_file or Path.home() / ".panther" / "docker_image_cache.json"
)
self.retry_count = retry_count
self.retry_delay = retry_delay

# Thread-safe cache storage
self._cache: Dict[str, CachedImage] = {}
self._cache_lock = threading.RLock()
self._last_refresh = 0.0

# Docker client (will be set by DockerBuilder)
self._docker_client: Optional[docker.DockerClient] = None

# Initialize secure cache file and directory
self._initialize_secure_cache_file()

# Load existing cache
self._load_cache()
```

#### 2. Add secure cache file initialization method

```python
def _initialize_secure_cache_file(self) -> None:
    """
    Initialize cache file and directory with secure permissions.

    Creates cache directory with 700 permissions (owner read/write/execute only)
    and ensures cache file has 600 permissions (owner read/write only).
    """
    try:
        # Create cache directory with secure permissions (700 - owner only)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

        # Ensure directory has correct permissions (in case it already existed)
        self.cache_file.parent.chmod(0o700)

        # If cache file exists, ensure it has secure permissions
        if self.cache_file.exists():
            self.cache_file.chmod(0o600)  # Owner read/write only
            self.logger.debug(f"Secured existing cache file permissions: {self.cache_file}")

        self.logger.debug(f"Cache directory initialized with secure permissions: {self.cache_file.parent}")

    except (OSError, PermissionError) as e:
        self.logger.error(f"Failed to initialize secure cache file: {e}")
        # Don't raise exception - allow cache to work without security if necessary
        self.logger.warning("Cache will operate with default permissions")
```

#### 3. Replace `_save_cache()` method with atomic writes (lines 140-158)

**Current Code:**
```python
def _save_cache(self):
    """Save cache to persistent storage."""
    try:
        cache_data = {
            "images": {
                image_id: image.to_dict() for image_id, image in self._cache.items()
            },
            "last_refresh": self._last_refresh,
            "saved_at": time.time(),
        }

        with open(self.cache_file, "w") as f:
            json.dump(cache_data, f, indent=2)

        self.logger.debug(f"Saved {len(self._cache)} images to cache file")

    except (OSError, json.JSONEncodeError) as e:
        self.logger.error(f"Failed to save cache file: {e}")
```

**New Code:**
```python
def _save_cache(self) -> None:
    """
    Save cache to persistent storage using atomic writes.

    Uses atomic write pattern (write to temp file, then rename) to prevent
    cache corruption from concurrent access or interrupted writes.
    """
    temp_file = None
    try:
        cache_data = {
            "images": {
                image_id: image.to_dict() for image_id, image in self._cache.items()
            },
            "last_refresh": self._last_refresh,
            "saved_at": time.time(),
            "version": "1.0"  # Add version for future compatibility
        }

        # Create temporary file in same directory for atomic rename
        temp_file = self.cache_file.with_suffix('.tmp')

        # Write to temporary file with secure permissions
        with open(temp_file, "w") as f:
            json.dump(cache_data, f, indent=2)

        # Set secure permissions on temp file
        temp_file.chmod(0o600)

        # Atomic rename (replaces original file)
        temp_file.replace(self.cache_file)

        self.logger.debug(f"Atomically saved {len(self._cache)} images to cache file")

    except (OSError, json.JSONEncodeError, PermissionError) as e:
        self.logger.error(f"Failed to save cache file: {e}")

        # Clean up temp file if it exists
        if temp_file and temp_file.exists():
            try:
                temp_file.unlink()
                self.logger.debug("Cleaned up temporary cache file after error")
            except OSError as cleanup_error:
                self.logger.warning(f"Failed to cleanup temp file: {cleanup_error}")

    except Exception as e:
        self.logger.error(f"Unexpected error saving cache: {e}")

        # Clean up temp file if it exists
        if temp_file and temp_file.exists():
            try:
                temp_file.unlink()
            except OSError:
                pass  # Best effort cleanup
```

#### 4. Add cache file validation method

```python
def _validate_cache_file_security(self) -> bool:
    """
    Validate cache file and directory have secure permissions.

    Returns:
        bool: True if permissions are secure, False otherwise
    """
    try:
        # Check directory permissions (should be 700)
        dir_stat = self.cache_file.parent.stat()
        dir_perms = stat.filemode(dir_stat.st_mode)[-3:]  # Last 3 chars (owner perms)

        if dir_perms != "rwx":
            self.logger.warning(
                f"Cache directory permissions not secure: {dir_perms} "
                f"(expected: rwx, path: {self.cache_file.parent})"
            )
            return False

        # Check file permissions if file exists (should be 600)
        if self.cache_file.exists():
            file_stat = self.cache_file.stat()
            file_perms = stat.filemode(file_stat.st_mode)[-3:]  # Last 3 chars (owner perms)

            if file_perms != "rw-":
                self.logger.warning(
                    f"Cache file permissions not secure: {file_perms} "
                    f"(expected: rw-, path: {self.cache_file})"
                )
                return False

        self.logger.debug("Cache file security validation passed")
        return True

    except (OSError, AttributeError) as e:
        self.logger.error(f"Failed to validate cache file security: {e}")
        return False
```

#### 5. Update `_load_cache()` method to include security validation (lines 110-139)

Add security validation at the beginning of the method:

```python
def _load_cache(self):
    """Load cache from persistent storage with security validation."""
    # Validate cache file security
    if not self._validate_cache_file_security():
        self.logger.warning("Cache file security validation failed, proceeding anyway")

    if not self.cache_file.exists():
        self.logger.debug("No cache file found, starting with empty cache")
        return

    try:
        with open(self.cache_file, "r") as f:
            data = json.load(f)

        # Validate cache file version for future compatibility
        cache_version = data.get("version", "unknown")
        if cache_version != "1.0" and cache_version != "unknown":
            self.logger.warning(f"Unknown cache version: {cache_version}, proceeding anyway")

        with self._cache_lock:
            self._cache = {
                image_id: CachedImage.from_dict(image_data)
                for image_id, image_data in data.get("images", {}).items()
            }
            self._last_refresh = data.get("last_refresh", 0.0)

        # Clean expired entries
        self._clean_expired_entries()

        self.logger.info(
            f"Loaded {len(self._cache)} cached images from {self.cache_file}"
        )

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        self.logger.warning(f"Failed to load cache file: {e}, starting fresh")
        with self._cache_lock:
            self._cache = {}
            self._last_refresh = 0.0
```

#### 6. Add required imports

Add to imports section (around line 15):
```python
import stat  # For file permission checking
```

#### 7. Add cache security validation to `get_cache_stats()` method

Update the `get_cache_stats()` method (around line 348) to include security information:

```python
def get_cache_stats(self) -> Dict[str, Union[int, float, str, bool]]:
    """
    Get cache statistics including security status.

    Returns:
        Dictionary with cache statistics and security information
    """
    current_time = time.time()

    with self._cache_lock:
        cache_age = current_time - self._last_refresh
        total_size = sum(image.size for image in self._cache.values())
        security_valid = self._validate_cache_file_security()

        return {
            "total_images": len(self._cache),
            "cache_age_seconds": cache_age,
            "cache_fresh": self._is_cache_fresh(),
            "total_size_mb": total_size / (1024 * 1024),
            "cache_file": str(self.cache_file),
            "cache_secure": security_valid,
            "last_refresh": datetime.fromtimestamp(self._last_refresh).isoformat()
            if self._last_refresh
            else "never",
        }
```

## Dependencies
- None (independent security enhancement)

## Testing Requirements

### Unit Tests

1. **Test secure cache file initialization**
   ```python
   def test_secure_cache_initialization(self):
       """Test cache file and directory created with secure permissions."""
       temp_dir = tempfile.mkdtemp()
       cache_file = Path(temp_dir) / "test_cache.json"

       cache = DockerImageCache(cache_file=cache_file)

       # Check directory permissions (700)
       dir_stat = cache_file.parent.stat()
       self.assertEqual(stat.filemode(dir_stat.st_mode)[-3:], "rwx")

       # Create cache file and check permissions (600)
       cache._save_cache()
       file_stat = cache_file.stat()
       self.assertEqual(stat.filemode(file_stat.st_mode)[-3:], "rw-")
   ```

2. **Test atomic cache writes**
   ```python
   def test_atomic_cache_writes(self):
       """Test cache writes are atomic and don't corrupt existing data."""
       temp_dir = tempfile.mkdtemp()
       cache_file = Path(temp_dir) / "test_cache.json"

       cache = DockerImageCache(cache_file=cache_file)

       # Add test data and save
       test_image = CachedImage("test-id", ["test:tag"], 1000, "2023-01-01", time.time())
       cache._cache["test-id"] = test_image
       cache._save_cache()

       # Verify file exists and has correct permissions
       self.assertTrue(cache_file.exists())
       file_stat = cache_file.stat()
       self.assertEqual(stat.filemode(file_stat.st_mode)[-3:], "rw-")

       # Verify no temp files left behind
       temp_files = list(cache_file.parent.glob("*.tmp"))
       self.assertEqual(len(temp_files), 0)
   ```

3. **Test cache file validation**
   ```python
   def test_cache_security_validation(self):
       """Test cache file security validation works correctly."""
       temp_dir = tempfile.mkdtemp()
       cache_file = Path(temp_dir) / "test_cache.json"

       cache = DockerImageCache(cache_file=cache_file)

       # Should pass validation initially
       self.assertTrue(cache._validate_cache_file_security())

       # Create file with insecure permissions
       cache_file.touch()
       cache_file.chmod(0o644)  # World readable

       # Should fail validation
       self.assertFalse(cache._validate_cache_file_security())
   ```

### Integration Tests

1. **Test concurrent cache access**
   - Multiple threads reading/writing cache simultaneously
   - Verify no corruption occurs with atomic writes
   - Test cleanup of temporary files on errors

2. **Test permission inheritance**
   - Create cache in directory with different permissions
   - Verify cache file gets correct permissions regardless
   - Test cache operation when permissions can't be set

## Risk Assessment

### Risk Level: Low

### Potential Issues
1. **Permission Errors**: May fail on filesystems that don't support Unix permissions
2. **Performance Impact**: Atomic writes and permission checks add overhead
3. **Backup Compatibility**: Changing file format (adding version) might affect backups

### Mitigation Strategies
1. **Graceful Degradation**: Continue operation if permission setting fails
2. **Performance Monitoring**: Measure overhead and optimize if needed
3. **Backward Compatibility**: Support loading old cache format without version

## Acceptance Criteria

### Must Have
- [ ] Cache directory created with 700 permissions (owner only)
- [ ] Cache file created with 600 permissions (owner read/write only)
- [ ] Cache writes are atomic (no corruption from interruption)
- [ ] Temporary files are cleaned up on errors
- [ ] Security validation works correctly
- [ ] All existing cache functionality continues to work

### Should Have
- [ ] Performance impact is minimal (< 5ms overhead per save operation)
- [ ] Cache stats include security validation status
- [ ] Graceful handling when permissions cannot be set
- [ ] Backward compatibility with existing cache files

### Nice to Have
- [ ] Configurable cache file permissions
- [ ] Metrics for security validation failures
- [ ] Automated security testing in CI/CD

## Implementation Notes

### Development Steps
1. Create feature branch: `feature/secure-cache-files`
2. Add new secure initialization method
3. Replace save method with atomic writes
4. Add security validation methods
5. Update cache stats to include security info
6. Write comprehensive unit tests
7. Test on different filesystems and operating systems
8. Performance testing and optimization

### Security Considerations
- Cache files may contain sensitive Docker image metadata
- Directory traversal protection (cache files in controlled locations)
- Race condition prevention during atomic writes
- Proper cleanup to prevent information leakage

### Performance Considerations
- Atomic writes add one extra filesystem operation per save
- Permission checks add minimal overhead (< 1ms)
- Security validation should be lightweight
- Consider caching permission validation results

## Related Tasks
- **TASK-CS-002**: Platform-Aware Caching (uses same cache file structure)
- **TASK-DM-002**: Monitoring Implementation (can monitor cache security metrics)

## Success Metrics
- Cache files created with secure permissions in 100% of test cases
- Zero cache corruption incidents with atomic writes
- Security validation correctly identifies insecure permissions
- Performance overhead stays below 5ms per cache operation
- All existing cache functionality maintains compatibility
