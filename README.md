# Atlas

Atlas is a local-first, privacy-preserving personal voice assistant starter for Python. It ships with a runnable daemon loop, optional offline audio providers, bounded conversation memory, and Home Assistant control for lights and thermostats.

## Architecture

```text
idle
  -> wake word detector (openWakeWord, with text fallback)
  -> utterance listener (microphone + webrtcvad, with text fallback)
  -> speech-to-text (faster-whisper, with passthrough fallback)
  -> intent router
       -> Home Assistant action executor
       -> or local chat model (Ollama, with local fallback)
  -> text-to-speech (Piper, with console fallback)
  -> idle
```

Core package layout:

```text
atlas/
  apps/daemon/        CLI entrypoint
  config/             Config loader + dataclasses
  core/audio/         Wake word + VAD listener adapters
  core/stt/           STT providers
  core/llm/           Chat model adapters
  core/tts/           TTS adapters
  core/dialog/        Bounded short-term memory
  core/intents/       Command/chat routing
  core/actions/       Home Assistant mapping + policy scaffold
  core/runtime/       State machine orchestration
config/
  atlas.example.yaml  Example runtime configuration
tests/
  test_intent_router.py
  test_home_assistant_mapping.py
```

## Quickstart

1. Create a virtualenv and install Atlas:
   ```bash
   python -m venv .venv
   . .venv/bin/activate
   pip install -e .
   ```
2. Install optional offline providers when you are ready:
   ```bash
   pip install -e .[audio,wakeword,stt]
   ```
3. Copy the sample environment file and add your Home Assistant token:
   ```bash
   cp .env.example .env
   ```
4. Review `config/atlas.example.yaml` and update device mappings.
5. Run a local dry-run loop in text mode:
   ```bash
   atlas-daemon --config config/atlas.example.yaml --text-mode --dry-run --once
   ```

## Configuration

- `audio`: sample rate, wake word phrase, VAD timing, optional `openwakeword_model_path`.
- `stt`: local `faster-whisper` model selection.
- `llm`: local Ollama host, model, and system prompt.
- `tts`: Piper command and voice model.
- `runtime`: bounded memory length, log level, and dry-run mode.
- `home_assistant`: local URL, token env var, SSL behavior, and friendly-name entity mappings.

Atlas is config-driven by design so you can swap wake word, STT, LLM, and TTS providers without changing the runtime loop.

## Home Assistant setup

1. Create a long-lived access token in Home Assistant.
2. Put the token in `.env` as `HOME_ASSISTANT_TOKEN`.
3. Map friendly room names to entity IDs in `config/atlas.example.yaml`.
4. Start Atlas without `--dry-run` once your local API is reachable.

Supported action mappings:
- `turn on/off <room> lights`
- `dim/set <room> lights to <percent>`
- `set <zone> thermostat to <temperature>`

## Conversation and policy behavior

- Responses are concise by default.
- Recent turns are stored in bounded short-term memory for local context.
- High-confidence commands execute immediately.
- Ambiguous commands trigger a short clarifying question.
- Potentially risky actions are scaffolded in `atlas/core/actions/policy.py` and currently require confirmation for extreme thermostat changes.
- Confirmation and speaking paths include hook points for future interruption/barge-in support.

## Developer notes

- Customize wake-word behavior in `atlas/core/audio/wakeword.py` and `config/atlas.example.yaml`.
- Extend command parsing in `atlas/core/intents/router.py`.
- Expand Home Assistant device mappings in `config/atlas.example.yaml`.
- Run tests with:
  ```bash
  python -m unittest discover -s tests
  ```

## Troubleshooting

- If Atlas falls back to text I/O, install optional audio dependencies with `pip install -e .[audio,wakeword,stt]`.
- If Piper is missing, Atlas will print responses to the console instead of speaking them.
- If Ollama is not running, Atlas will reply with a local fallback message instead of using cloud services.
- If Home Assistant calls fail, verify the URL, token, and entity IDs in your config.

## Privacy notes

- Core flow is local-first and requires no cloud service.
- Ollama, faster-whisper, Piper, and Home Assistant are expected to run on local hardware or your LAN.
- Secrets stay in `.env`, which is gitignored by default.
- Optional fallbacks remain local and produce actionable setup guidance instead of sending data to external APIs.

## Optional enhancements

- Real streaming partial transcripts and barge-in.
- More Home Assistant domains and richer safety policies.
- Richer summarization memory beyond bounded recent turns.
- A tray UI or dashboard for assistant state.
