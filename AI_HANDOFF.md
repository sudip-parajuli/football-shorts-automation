# 🤖 AI Handoff Document

> **Purpose**: This file lets any AI assistant (KiloCode, OpenCode, Antigravity, or others) pick up exactly where we left off. Update this file at every meaningful milestone.
>
> **Last Updated**: 2026-06-10T11:45:00+05:45  
> **Updated By**: Antigravity (Gemini 3.5 Flash)

---

## 🎯 Current Task Goal

Configure free OpenRouter models into KiloCode and OpenCode so that when Antigravity IDE hits quota limits, work on `football-shorts-automation` (and other projects) can continue without interruption.

Specifically:
- **KiloCode** (VS Code extension inside Antigravity IDE) → Connected to OpenRouter, default model: `qwen/qwen3-coder:free`
- **OpenCode** (global CLI/desktop agent) → Connected to OpenRouter, default model: `openrouter/qwen/qwen3-coder:free`
- Both tools configured system-wide to work across ALL projects.

---

## 📁 Files Modified So Far

| File | Change | Reason |
|------|--------|--------|
| `AI_HANDOFF.md` (this file) | Updated | Documented completed setup, defaults, and usage. |
| `C:\Users\Acer\AppData\Roaming\Antigravity IDE\User\settings.json` | Configured | Added KiloCode OpenRouter provider, API key, default model, and all 16 free models. |
| `C:\Users\Acer\.config\opencode\opencode.jsonc` | Configured | Added OpenCode OpenRouter provider, default model, and all 16 free models under `options.apiKey`. |

---

## 🔑 Key Decisions Made

| Decision | Reason |
|----------|--------|
| KiloCode default = `qwen/qwen3-coder:free` | User explicitly requested this; Qwen3 Coder 480B is highly capable for coding tasks. |
| OpenCode default = `openrouter/qwen/qwen3-coder:free` | Changed from `openrouter/free` because the auto-router routes to models that do not support tool calling (which OpenCode requires to execute commands, read files, etc.). |
| All 16 free models added to both tools | Maximum fallback options if a specific model is rate-limited. |
| OpenRouter API key stored in local configuration files | Essential for local dev tools to work. The configurations are stored in user-profile folders (`AppData` and `.config`) so they will not be committed to Git. |

### Free Models Configured

| Model Name | Model ID |
|---|---|
| Free Models Router (AUTO) | `openrouter/free` *(Note: May fail in OpenCode if routed to a non-tool-calling model)* |
| Poolside Laguna M.1 | `poolside/laguna-m.1:free` |
| NVIDIA Nemotron 3 Ultra | `nvidia/nemotron-3-ultra-550b-a55b:free` |
| NVIDIA Nemotron 3 Super | `nvidia/nemotron-3-super-120b-a12b:free` |
| OpenAI GPT-OSS 120B | `openai/gpt-oss-120b:free` |
| Poolside Laguna XS.2 | `poolside/laguna-xs.2:free` |
| OpenAI GPT-OSS 20B | `openai/gpt-oss-20b:free` |
| Nex AGI Nex-N2-Pro | `nex-agi/nex-n2-pro:free` |
| Google Gemma 4 31B | `google/gemma-4-31b-it:free` |
| NVIDIA Nemotron 3 Nano 30B | `nvidia/nemotron-3-nano-30b-a3b:free` |
| MoonshotAI Kimi K2.6 | `moonshotai/kimi-k2.6:free` |
| NVIDIA Nemotron 3 Nano Omni | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` |
| Google Gemma 4 26B | `google/gemma-4-26b-a4b-it:free` |
| Qwen3 Next 80B | `qwen/qwen3-next-80b-a3b-instruct:free` |
| Meta Llama 3.3 70B | `meta-llama/llama-3.3-70b-instruct:free` |
| **Qwen3 Coder 480B** ⭐ *(Default)* | `qwen/qwen3-coder:free` |

---

## ⚠️ Fallback Tools (Configuration Gotchas)

These are non-obvious gotchas discovered during setup that will cause silent failures or crashes if you ever have to reconfigure from scratch:

1. **OpenCode Model ID Parsing**:
   - *Behavior*: OpenCode splits the model ID string by `/` to separate the provider from the model. E.g., `"model": "openrouter/free"` parses as provider `openrouter` and model `free`. If the key in the `models` dictionary is `"openrouter/free"`, OpenCode cannot find the model and throws `ProviderModelNotFoundError`.
   - *Fix*: The key under the `models` dictionary in `opencode.jsonc` must be `"free"`, not `"openrouter/free"`.
2. **`openrouter/free` Auto-Router Breaks Tool Calling**:
   - *Behavior*: OpenCode exposes local developer tools (like `bash`) to the LLM. The `openrouter/free` auto-router routes requests to whichever free model is currently available. Some of these free models do not support function/tool calling, which causes OpenCode to crash immediately on start.
   - *Fix*: Never use the auto-router `openrouter/free` as a default in OpenCode or other agentic tools. Instead, set the default to a specific free model that supports tool calling (e.g. `openrouter/qwen/qwen3-coder:free` or `openrouter/meta-llama/llama-3.3-70b-instruct:free`).
3. **API Key Field Name in `opencode.jsonc`**:
   - *Behavior*: Placing the API key under `"api"` key (e.g., `"api": "sk-or-v1-..."`) inside the provider block is not recognized. The CLI fails silently with no loud error, claiming that the API key is missing.
   - *Fix*: Define the API key inside `"options": { "apiKey": "sk-or-v1-..." }` inside the provider block.

---

## ⚡ Exact Next Steps

All tasks for this migration have been completed:
- [x] Create this AI_HANDOFF.md file
- [x] Configure KiloCode → OpenRouter in `settings.json`
- [x] Configure OpenCode → OpenRouter in `opencode.jsonc`
- [x] Store OpenRouter API key for OpenCode
- [x] Verify both configs and model runs successfully
- [x] Update this file with final tool invocation instructions

---

## 🔄 How to Continue Work After a Quota Limit

### Option A — KiloCode (inside Antigravity IDE)
1. Click the **Kilo Code icon** in the Antigravity IDE sidebar (left panel).
2. Start a new task or paste the handoff context.
3. The model is pre-set to `qwen/qwen3-coder:free` via OpenRouter.
4. **To switch models**: Click the model name dropdown in the KiloCode sidebar panel.

### Option B — OpenCode (terminal / desktop app)
1. Open a terminal and navigate to your project:
   ```powershell
   cd "C:\Users\Acer\Desktop\football-shorts-automation"
   ```
2. Run the OpenCode TUI:
   ```powershell
   opencode
   ```
   *Note: OpenCode is pre-set to use `qwen/qwen3-coder:free` by default. You can switch models in the chat using `/model openrouter/<model-id>` (e.g. `/model openrouter/meta-llama/llama-3.3-70b-instruct:free`).*

### Passing Context Between Tools
Antigravity does **not** automatically share conversation history with KiloCode/OpenCode.  
When switching tools, copy this prompt template:

```
I was working on: [brief description]
The current state is: [what was done]
The next step is: [exact next action]
Relevant files: [list key files]
See AI_HANDOFF.md in the project root for full context.
```

---

## Global Skills Installed
Location: ~/.gemini/antigravity/skills/ (Antigravity)
         ~/.claude/skills/ (KiloCode)
         ~/.config/opencode/skills/ (OpenCode)

Active skills: senior-fullstack, senior-frontend, senior-backend,
               senior-architect, code-reviewer

These load automatically in every project. No per-project setup needed.
Source: github.com/alirezarezvani/claude-skills (engineering-team)

---

## 📌 Project Context (football-shorts-automation)

- **Workspace**: `c:\Users\Acer\Desktop\football-shorts-automation`
- **Purpose**: Automated football shorts generation/processing pipeline
- **Key Stack**: See project files for details

---

*⚠️ QUOTA WARNING HABIT: If Antigravity is about to stop due to limits, it will update this file first with current state before pausing.*
