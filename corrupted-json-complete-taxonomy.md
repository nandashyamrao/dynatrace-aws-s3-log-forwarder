# Corrupted JSON Complete Taxonomy

## Example List

> Note: Here are 20 detailed examples of corrupted JSON cases.

### Case 1: Unexpected Variable
```json
{"key": value}
```
**Description:** JSON keys require string-wrapped names and values. The value "value" here is an unquoted variable, which JSON does not recognize.

### Case 2: Duplicate Keys
```json
{"key": "value1", "key": "value2"}
```
**Description:** JSON does not allow duplicate keys within the same object. "key" appears twice here.

### Case  3 . Rest UNtrack Similuarl chunks etc.