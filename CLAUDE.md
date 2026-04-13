# ClawdHooks

## CRITICAL: Path quoting

The working directory contains a space: `Claude Projects`. Every file write, bash command, and subagent prompt **must** quote or escape this path correctly. Failure to do so splits `Claude Projects` into `Claude/` + ` Projects/`, creating phantom directories.

- Bash: always double-quote paths — `"/c/Users/reeld/OneDrive/Desktop/Claude Projects/ClawdHooks/..."`
- Write/Edit tools: use the full absolute path exactly as shown above
- Subagent prompts: include the full quoted path; do not assume agents will infer quoting
