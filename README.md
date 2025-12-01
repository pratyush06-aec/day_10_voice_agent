Day 10 — Voice Improv Battle (Improv Game Show)

Voice-first improv game show — “Improv Battle”
This repo turns your voice agent into a TV-style improv host that runs short improv rounds, listens to the player’s performance, reacts with varied feedback, and advances through rounds — all via realtime voice (LiveKit + STT + LLM + TTS). It’s Day 10 of the 10 Days of Voice Agents series.

🚀 What this project does (MVP)

Hosts a single-player improv game show entirely via voice.

Loads a set of improv scenarios from JSON (shared-data/day10_scenarios.json).

Runs N rounds (configurable), each:

Host announces the scenario and asks the player to act.

Player performs (voice input).

Host reacts (supportive / neutral / lightly critical).

Host advances to next scenario or ends the show.

Persists session state and supports saving / restarting sessions.

All speech is live: Deepgram (STT) -> Gemini (LLM) -> Murf (TTS) via LiveKit (pipeline).

📁 Important files & folders
backend/
  src/
    agent.py                # Main agent Worker for Day 10 (voice pipeline + Assistant)
    improv.py               # Helpers for loading/picking scenarios (utility module)
    day10_scenarios.json    # Scenario list (shared-data path in repo root)
    ...other support files
shared-data/
  day10_scenarios.json      # Scenarios JSON (editable)
  day10_sessions/           # Saved sessions (auto-created)
  day10_world.json?         # optional: world file if you want a world model
frontend/                   # Optional UI (join room, show transcript, controls)
README.md                   # This file

🧩 Scenario JSON format

File: shared-data/day10_scenarios.json
Each entry is an object with at least id, prompt, and hint:

[
  {
    "id": "dimension-barista",
    "prompt": "You are a barista who must politely inform a customer that their latte foam is swirling into a tiny portal to another dimension.",
    "hint": "Be calm, casual, as if this happens every morning rush."
  },
  {
    "id": "runaway-taxi",
    "prompt": "You are a taxi driver explaining to your passenger that the car has developed a 'mind of its own' and has chosen a different destination.",
    "hint": "Speak as if this is normal and inconvenient rather than terrifying."
  }
  // ...
]


Add 8–12+ scenarios for richer playthroughs. Use clear prompts that ask the player to act.

🧠 Agent behavior & prompts

The LLM agent (Assistant) is seeded with a system prompt that makes it behave as a TV improv host:

High-energy, witty, and constructive.

Explain rules on start.

After each host narration, the agent must end with a clear cue for the player (example: "When you're ready, begin — or say 'End scene' when finished.").

Reactions should be short (1–2 sentences) and vary in tone.

The agent exposes function-tools the LLM can call:

get_current_scene(ctx) — returns current scenario for TTS

next_round(ctx) — advances to next scenario

save_session(ctx, name) — saves improv_state to disk

restart_story(ctx) — resets rounds & counters

get_improv_state(ctx) — debug / UI view

🧾 State model (per session)

Stored in ctx.userdata["improv_state"]:

{
  "player_name": "Alice",
  "current_round": 0,
  "max_rounds": 3,
  "rounds": [ { "id": "...", "prompt": "...", "hint": "..." }, ... ],
  "phase": "intro" | "awaiting_improv" | "reacting" | "done",
  "story_history": [ {"speaker":"GM","text":"..."}, {"speaker":"player","text":"..."} ]
}

🔧 How to run (local dev)

Prereqs

Python 3.10+ (venv)

Node.js & npm (if using frontend)

Set .env.local with keys: LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_SECRET, MURF_API_KEY, etc.

Backend

# from repo root
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# mac/linux:
source .venv/bin/activate

pip install -r requirements.txt
# Ensure shared-data/day10_scenarios.json exists (edit scenarios if you want)

# Run worker (development mode)
uv run python src/agent.py dev


Frontend (optional)

cd frontend
npm install
npm run dev
# Open the URL printed (commonly http://localhost:3000)
# Join the agent room from the UI to begin voice play

🧪 Testing locally without voice

You can run small harnesses to drive the agent with text-only calls (if you have an inference LLM configured), or unit-test improv.py helpers:

improv.pick_unique_scenarios(n, seed) — deterministically returns scenarios.

improv.get_scenario_by_id(id) — verify scenario loaded.

Add pytest tests under backend/tests/ for:

scenario JSON validation

saving and loading sessions

saving a session file is created in shared-data/day10_sessions/

✅ MVP checklist (Day 10)

 shared-data/day10_scenarios.json (8–12 scenarios)

 improv.py loads & validates scenarios

 agent.py seeds session userdata with improv_state

 Assistant has function tools: get_current_scene, next_round, save_session, restart_story, get_improv_state

 Host ends narration with an explicit prompt for player action

 Session state persists to shared-data/day10_sessions/ when saved


#VoiceAI #AgenticCommerce #ACP #LiveKit #MurfAI #Gemini #STT #TTS #Ecommerce #BuildInPublic #Day9 #10DaysofAIVoiceAgents
 Host provides varied, constructive reactions after each round

 Playthrough runs for max_rounds and provides closing summary
