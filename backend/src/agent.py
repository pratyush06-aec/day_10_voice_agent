from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RoomInputOptions,
    WorkerOptions,
    cli,
    metrics,
    tokenize,
    function_tool,
    RunContext,
)
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# import your improv helpers
from improv import pick_unique_scenarios, pick_scenario, get_scenario_by_id, SCENARIOS_PATH

logger = logging.getLogger("agent")
load_dotenv(".env.local")

# where saved sessions go
SESSIONS_DIR = Path("shared-data/day10_sessions")
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


class Assistant(Agent):
    def __init__(self, max_rounds: int = 3) -> None:
        # explanation/system prompt tailored to an improv host role
        super().__init__(
            instructions=(
                "You are the host of a high-energy improv game show called 'Improv Battle'. "
                "You introduce short improv scenarios and ask the player to act them out. "
                "After each round, briefly react (1-2 sentences) and then either prompt the next scenario or close the show. "
                'Keep reactions varied: supportive, neutral, or light-hearted critique. '
                'Always be respectful and constructive. End each GM turn with a clear prompt such as: "When you are ready, say your first line — or say End scene when finished."'
            )
        )
        self._max_rounds = max_rounds

        # Tools the LLM can call -------------------------------------------
        @function_tool()
        async def get_current_scene(self, ctx: RunContext) -> dict:
            """Return the GM text for the current scene (id, prompt, hint)."""
            state = ctx.userdata.get("improv_state", {})
            rounds = state.get("rounds", [])
            current_idx = state.get("current_round", 0)
            if not rounds:
                return {"error": "No rounds selected."}
            if current_idx < 0 or current_idx >= len(rounds):
                current_idx = 0
            return rounds[current_idx]

        @function_tool()
        async def next_round(self, ctx: RunContext) -> dict:
            """
            Advance to the next round. If already at end, return final summary / closing text.
            Returns the new current scenario dict or a final summary dict.
            """
            state = ctx.userdata.setdefault("improv_state", {})
            current = state.get("current_round", 0)
            rounds = state.get("rounds", [])
            if not rounds:
                # pick fresh rounds on demand
                rounds = pick_unique_scenarios(self._max_rounds)
                state["rounds"] = rounds
            # if the player was in the middle, increment
            if current + 1 < len(rounds):
                state["current_round"] = current + 1
                ctx.userdata["improv_state"] = state
                return rounds[state["current_round"]]
            else:
                # we've finished all rounds -> produce a short closing summary
                summary = {
                    "id": "closing",
                    "prompt": "Thanks for playing! You completed the improv show. Summarize the player's strengths and one suggestion.",
                }
                return summary

        @function_tool()
        async def save_session(self, ctx: RunContext, session_name: str | None = None) -> str:
            """Save current improv_state to shared-data/day10_sessions/session-{timestamp|name}.json"""
            state = ctx.userdata.get("improv_state", {})
            if session_name:
                fname = f"session-{session_name}.json"
            else:
                from datetime import datetime
                fname = f"session-{int(datetime.now().timestamp())}.json"
            path = SESSIONS_DIR / fname
            with path.open("w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            return str(path)

        @function_tool()
        async def restart_story(self, ctx: RunContext, seed: int | None = None) -> dict:
            """
            Restart the story for this session. Re-picks rounds and resets counters.
            Returns the first scenario.
            """
            state = {
                "player_name": None,
                "current_round": 0,
                "max_rounds": self._max_rounds,
                "rounds": pick_unique_scenarios(self._max_rounds, seed=seed),
                "phase": "intro",
                "story_history": [],
            }
            ctx.userdata["improv_state"] = state
            return state["rounds"][0] if state["rounds"] else {"id": "fallback", "prompt": "No scenarios available."}

        @function_tool()
        async def get_improv_state(self, ctx: RunContext) -> dict:
            """Return the whole improv_state for debugging or UI display."""
            return ctx.userdata.get("improv_state", {})

        # end of tool definitions -----------------------------------------


def prewarm(proc: JobProcess):
    # warm VAD model for low-latency voice detection
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    # Logging setup
    ctx.log_context_fields = {"room": ctx.room.name}

    # pick default number of rounds (you can make this configurable)
    MAX_ROUNDS = 3

    # initialize session userdata for the improv game
    # pick max rounds deterministically? You can pass seed from ctx or random.
    rounds = pick_unique_scenarios(MAX_ROUNDS)

    ctx_user_init = {
        "improv_state": {
            "player_name": None,
            "current_round": 0,
            "max_rounds": MAX_ROUNDS,
            "rounds": rounds,
            "phase": "intro",  # "intro" | "awaiting_improv" | "reacting" | "done"
            "story_history": [],
        }
    }

    # create AgentSession (voice pipeline)
    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(model="gemini-2.5-flash"),
        tts=murf.TTS(
            voice="en-US-matthew",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
        userdata=ctx_user_init,
    )

    # metrics collection
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)

    # start session with Assistant instance
    await session.start(
        agent=Assistant(max_rounds=MAX_ROUNDS),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    # connect to room (join)
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
