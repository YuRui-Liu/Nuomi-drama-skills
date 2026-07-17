# nuomi-drama-skills — Claude Code Project Conventions

## Architecture Overview

```
manuscript/*.md (Single Source of Truth)
       │
       ▼
   export.py ────── gates.py (G1-G8 quality gates)
       │              │
       ▼              ▼
  Platform JSON   writing_state.json
       │
       ▼
   generate.py ────── provider_chain.py ────── providers/ (grsai/gemini/comfyui/runninghub)
       │
       ▼
   preview_server.py ── Browser preview
```

**Core modules:**
- `export.py` + `emit.py` — Markdown manuscript → platform JSON deterministic compilation
- `generate.py` — Image/video/dub/voice-design CLI
- `gates.py` — G1-G8 quality gates (G1-G4 creative-phase soft warnings, G5-G8 generation-phase hard blocks)
- `validators.py` — Frozen platform validators
- `prompt_checker.py` — LTX prompt rule validator
- `provider_chain.py` — Role-based provider fallback chain
- `director.py` — 5-verdict ShotProtocol
- `stages/` — Generation pipeline (images/video/dub/voice_design/status/targeting)
- `providers/` — Provider adapters (grsai/gemini/comfyui/runninghub)
- `commands/` — Interactive command system (new/review/compliance)
- `quality/` — Review engines (review + compliance)
- `exporters/` — Exporters (jianying/srt/ffmpeg)

## Trigger Conditions

Activate this skill when the user mentions:
短剧、微短剧、竖屏剧、AI 短剧、AI 漫剧、剧本创作、分镜、糯米短剧、长篇短剧、
爽剧、重生、穿越、赘婿、追妻、神医相师

## Core Principles

1. **Manuscript as Source of Truth**: `manuscript/*.md` is the single creative source; never hand-edit compiled JSON
2. **Idempotent and merge-safe compilation**: `export.py` preserves existing platform artifacts (episode_digests / registry / anchors / audio)
3. **Provider Adapter Pattern**: All media generation goes through abstract base classes + factory functions; CLI uses `provider_chain.py` for fallback
4. **Gate before Generate**: Generation must pass corresponding phase gates (G5-G8); failure blocks generation

## Workflow Phases

1. ideation → 2. outline → 3. bible → 4. beats → 5. scripting → 6. storyboard → 7. generating → 8. done

## Provider Configuration

Environment variables (priority: CLI args > system env > `skill.env`):
- `IMAGE_PROVIDER` — grsai | comfyui | runninghub | gemini
- `GRSAI_API_KEY` — Grsai API key
- `RUNNINGHUB_API_KEY` — RunningHub API key

## Testing

```bash
pytest tests/ -v
```

## Key Documentation

- `docs/USER_GUIDE.md` — User guide
- `references/创作方法论.md` — Creative methodology
- `references/平台契约.md` — Platform contract
- `docs/superpowers/specs/` — Design specs
- `docs/superpowers/plans/` — Implementation plans
