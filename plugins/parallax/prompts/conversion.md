Read the JSON file at the path below. This is the main agent's task execution record.
From the recorded information, produce a markdown document that enumerates every thought, attempt, and result of the main agent.

# Rules

- Content that the main agent output to the user must be preserved verbatim, every single character.
- Ignore metadata the main agent cannot be aware of. (Token usage, API turn counts, signatures, etc.)

Record file: {file_path}
