---
name: parallax
description: Control the parallax plugin — toggle on/off or check the log path
disable-model-invocation: true
argument-hint: "[on|off|log]"
---

`/parallax` arguments: $ARGUMENTS

## Behavior

- `on`: Activate parallax. Remove the `${CLAUDE_PLUGIN_DATA}/disabled` file.
- `off`: Deactivate parallax. Create the `${CLAUDE_PLUGIN_DATA}/disabled` file.
- `log`: Show the log file path for this session.
- No arguments: Check current activation status.

## Response format

### on / off / no arguments

Report in a single line: `parallax: on` or `parallax: off`

### log

Check if the log file exists at `${CLAUDE_PLUGIN_DATA}/${CLAUDE_SESSION_ID}_parallax.log`.

If the file exists, respond:

```
parallax log: ${CLAUDE_PLUGIN_DATA}/${CLAUDE_SESSION_ID}_parallax.log
This file contains the analysis prompts and directions from the latest turn, including all rounds.
```

If the file does not exist, respond:

```
parallax has not run in this session yet.
```

Do NOT read or output the log file contents.
