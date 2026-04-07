---
name: parallax-log
description: Read and summarize the parallax analysis log for this session
model: haiku
---

`/parallax-log`

## Context

parallax is an advisory agent that surfaces regions the main agent has not considered. It analyzes the main agent's work after each stop and, if unconsidered regions remain, injects a new region to prompt further work. Each injection is a "round." This repeats until no more unconsidered regions are found.

## Behavior

Read the log file at `${CLAUDE_PLUGIN_DATA}/${CLAUDE_SESSION_ID}_parallax.log`.

If the file does not exist, respond:

```
parallax has not run in this session yet.
```

If the file exists, read its contents and respond with:

1. A concise summary of the analysis rounds recorded in the log.
2. The log file path at the end:

```
Log file: ${CLAUDE_PLUGIN_DATA}/${CLAUDE_SESSION_ID}_parallax.log
```
