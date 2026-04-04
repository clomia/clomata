---
name: parallax
description: Toggle parallax plugin on/off
---

`/parallax` command arguments: $ARGUMENTS

## Behavior

- `off`: Deactivate parallax. Create the `${CLAUDE_PLUGIN_DATA}/disabled` file.
- `on`: Activate parallax. Remove the `${CLAUDE_PLUGIN_DATA}/disabled` file.
- No arguments: Check current activation status.

## Response format

Report the result in a single line:
- `parallax: on`
- `parallax: off`
