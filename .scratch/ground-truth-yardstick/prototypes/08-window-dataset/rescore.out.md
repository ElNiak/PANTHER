## Reproduction check: OLD dataset (tip 6d36838), pilot v1 A1
matched 8/35; identical to SP7d t11/gt-pilot: True

## NEW dataset (anchor 509065a), per draft

### pilot v1 A1
{
  "reachable recall": "11/26 = 0.423",
  "all-facts recall": "11/26 = 0.423",
  "ceiling": "26/26 = 1.000",
  "claim accuracy": "1.000 (11 attempted of 26 reachable)",
  "named (diagnostic)": 0,
  "per kind": {
    "error_code": {
      "scored": 17,
      "matched": 2,
      "mismatched": 0,
      "named": 0,
      "absent": 15
    },
    "frame_type": {
      "scored": 9,
      "matched": 9,
      "mismatched": 0,
      "named": 0,
      "absent": 0
    }
  }
}

### pilot v1 A2
{
  "reachable recall": "11/26 = 0.423",
  "all-facts recall": "11/26 = 0.423",
  "ceiling": "26/26 = 1.000",
  "claim accuracy": "1.000 (11 attempted of 26 reachable)",
  "named (diagnostic)": 0,
  "per kind": {
    "error_code": {
      "scored": 17,
      "matched": 2,
      "mismatched": 0,
      "named": 0,
      "absent": 15
    },
    "frame_type": {
      "scored": 9,
      "matched": 9,
      "mismatched": 0,
      "named": 0,
      "absent": 0
    }
  }
}

### v2 A1
{
  "reachable recall": "9/26 = 0.346",
  "all-facts recall": "9/26 = 0.346",
  "ceiling": "26/26 = 1.000",
  "claim accuracy": "1.000 (9 attempted of 26 reachable)",
  "named (diagnostic)": 2,
  "per kind": {
    "error_code": {
      "scored": 17,
      "matched": 0,
      "mismatched": 0,
      "named": 2,
      "absent": 15
    },
    "frame_type": {
      "scored": 9,
      "matched": 9,
      "mismatched": 0,
      "named": 0,
      "absent": 0
    }
  }
}

### v2 A2
{
  "reachable recall": "10/26 = 0.385",
  "all-facts recall": "10/26 = 0.385",
  "ceiling": "26/26 = 1.000",
  "claim accuracy": "1.000 (10 attempted of 26 reachable)",
  "named (diagnostic)": 1,
  "per kind": {
    "error_code": {
      "scored": 17,
      "matched": 1,
      "mismatched": 0,
      "named": 1,
      "absent": 15
    },
    "frame_type": {
      "scored": 9,
      "matched": 9,
      "mismatched": 0,
      "named": 0,
      "absent": 0
    }
  }
}

## Per-fact state (scored facts only; all 26 reachable)
| fact | kind | pilot v1 A1 | pilot v1 A2 | v2 A1 | v2 A2 |
|---|---|---|---|---|---|
| `HTTP_NO_ERROR` = 0x00 | error_code | absent | absent | absent | absent |
| `HTTP_GENERAL_PROTOCOL_ERROR` = 0x01 | error_code | absent | absent | absent | absent |
| `HTTP_INTERNAL_ERROR` = 0x03 | error_code | absent | absent | absent | absent |
| `HTTP_REQUEST_CANCELLED` = 0x05 | error_code | absent | absent | absent | absent |
| `HTTP_INCOMPLETE_REQUEST` = 0x06 | error_code | absent | absent | absent | absent |
| `HTTP_CONNECT_ERROR` = 0x07 | error_code | absent | absent | absent | absent |
| `HTTP_EXCESSIVE_LOAD` = 0x08 | error_code | absent | absent | absent | absent |
| `HTTP_VERSION_FALLBACK` = 0x09 | error_code | absent | absent | absent | absent |
| `HTTP_WRONG_STREAM` = 0x0A | error_code | matched | matched | named | matched |
| `HTTP_ID_ERROR` = 0x0B | error_code | absent | absent | absent | absent |
| `HTTP_STREAM_CREATION_ERROR` = 0x0D | error_code | absent | absent | absent | absent |
| `HTTP_CLOSED_CRITICAL_STREAM` = 0x0F | error_code | absent | absent | absent | absent |
| `HTTP_EARLY_RESPONSE` = 0x11 | error_code | absent | absent | absent | absent |
| `HTTP_MISSING_SETTINGS` = 0x12 | error_code | absent | absent | absent | absent |
| `HTTP_UNEXPECTED_FRAME` = 0x13 | error_code | matched | matched | named | named |
| `HTTP_REQUEST_REJECTED` = 0x14 | error_code | absent | absent | absent | absent |
| `HTTP_SETTINGS_ERROR` = 0xFF | error_code | absent | absent | absent | absent |
| `DATA` = 0x0 | frame_type | matched | matched | matched | matched |
| `HEADERS` = 0x1 | frame_type | matched | matched | matched | matched |
| `PRIORITY` = 0x2 | frame_type | matched | matched | matched | matched |
| `CANCEL_PUSH` = 0x3 | frame_type | matched | matched | matched | matched |
| `SETTINGS` = 0x4 | frame_type | matched | matched | matched | matched |
| `PUSH_PROMISE` = 0x5 | frame_type | matched | matched | matched | matched |
| `GOAWAY` = 0x7 | frame_type | matched | matched | matched | matched |
| `MAX_PUSH_ID` = 0xD | frame_type | matched | matched | matched | matched |
| `DUPLICATE_PUSH` = 0xE | frame_type | matched | matched | matched | matched |

## Truncation check: whole-token scorer vs the pinned scorer
no outcome changes on either dataset
