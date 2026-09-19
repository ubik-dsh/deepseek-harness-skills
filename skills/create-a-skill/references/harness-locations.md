# Where a harness keeps its skills

The Agent Skills format is an open standard — `SKILL.md` with `name` and
`description` — but **where a harness looks for those files is not part of it**.
Every tool answers that question differently, and a skill installed in the wrong
place fails in the worst possible way: silently.

The body of this skill is written to be harness-neutral. This file carries the
part that is not, so that the rest stays portable.

## DeepSeek Harness

Verified against DSH `0.1.5-rc.2` by reading `@deepseek-ai/dsh-skill` and
`@deepseek-ai/dsh-skill-filesystem` and by watching the session catalogue change
after writing a file.

| Root | Rank | Use it for |
|---|---|---|
| `<project>/.dsh/skills` | 100 | a project's own skills |
| `<project>/.agents/skills` | 200 | skills that travel with a repository — **prefer this** |
| a runtime registration | 250 | skills a plugin registers while running |
| custom roots, if configured | 300 | an installation's own arrangement |
| `$DSH_HOME/skills` | 400 | one person's skills, for every project |
| `$DSH_AGENTS_HOME`, default `~/.agents`, then `/skills` | 500 | shared across a machine's agents |
| the bundled directory | 600 | shipped with the harness, and trusted |

**The lower rank wins** when two roots offer the same name, and a nearer layer
beats a duplicate outright. All roots are watched: writing the file is enough,
with no restart and no install.

`.agents/skills` is the portable choice even on DSH — several harnesses read that
name, so a repository that carries it gives every agent that opens it the same
capability.

## Other harnesses

- **Claude Code and Claude.ai** read `.claude/skills/` in a project and
  `~/.claude/skills/` for the user. Plugins can also ship skills.
- **Codex, Gemini CLI, Cursor, Copilot and others** each have their own location
  and their own spelling of the folder name; several read `.agents/skills/`.

Do not guess. Check the harness's own documentation, and then confirm by
observation:

1. write a file with valid frontmatter into the root you believe is right;
2. ask the session for its skill catalogue;
3. if the skill is absent, the root is wrong or the frontmatter is.

Observation beats documentation here, because the documentation describes the
version its author had.

## When a location is not writable

A skill does not have to be copied into a harness's own folder to be useful. It
can live in a repository and be read from there — an agent that is given a path
to a `SKILL.md` can follow it, whether or not the harness indexed it. That is the
fallback when a harness offers no user-level root at all: hand over the path.
