import logging
import os
import json
from datetime import datetime

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
    RunContext
)
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")

load_dotenv(".env.local")

WELLNESS_LOG = r"backend\wellness_log.json"


# -------------------------
# JSON LOADING & SAVING
# -------------------------

def load_previous_entries():
    if not os.path.exists(WELLNESS_LOG):
        return []
    with open(WELLNESS_LOG, "r") as f:
        return json.load(f)


def save_entry(entry):
    data = load_previous_entries()
    data.append(entry)
    with open(WELLNESS_LOG, "w") as f:
        json.dump(data, f, indent=2)


# -------------------------
# WELLNESS AGENT
# -------------------------

class Assistant(Agent):
    def __init__(self):
        past_entries = load_previous_entries()
        last_note = ""

        if past_entries:
            last = past_entries[-1]
            last_note = f"""
Last time you talked to the user, they felt '{last['mood']}' and their energy was '{last['energy']}'.
Their goals were: {', '.join(last['goals'])}.
"""

        super().__init__(
            instructions=f"""
You are a supportive, grounded daily wellness companion, Murf. 
First introduce yourself warmly and say you're here for their daily check-in.
Avoid medical advice or diagnoses.

{last_note}

Your job each day:
1. Ask about mood and energy.
2. Ask about 1–3 simple goals.
3. Give small, grounded, NON-medical suggestions.
4. Summarize the check-in.
5. Call save_checkin at the end.

Rules:
- Keep responses warm, calm, and short.
- Ask ONE question at a time.
- Use update_checkin to store the details.
"""
        )

    # -------------------------
    # TOOL: UPDATE CHECK-IN
    # -------------------------
    # -------- TOOL: UPDATE CHECK-IN --------
@function_tool
async def update_checkin(
    self,
    context: RunContext,
    mood: str = None,
    energy: str = None,
    goals: list = None
):
    """Store today's check-in data."""
    ctx = context.session.userdata

    if "checkin" not in ctx:
        ctx["checkin"] = {"mood": None, "energy": None, "goals": []}

    if mood:
        ctx["checkin"]["mood"] = mood

    if energy:
        ctx["checkin"]["energy"] = energy

    if goals:
        ctx["checkin"]["goals"].extend(goals)

    return ctx["checkin"]


# -------- TOOL: SAVE CHECK-IN --------
@function_tool
async def save_checkin(self, context: RunContext):
    """Save today's check-in and send it to the frontend."""
    ctx = context.session.userdata

    if "checkin" not in ctx:
        return {"error": "Check-in incomplete"}

    entry = {
        "timestamp": datetime.now().isoformat(),
        "mood": ctx["checkin"].get("mood"),
        "energy": ctx["checkin"].get("energy"),
        "goals": ctx["checkin"].get("goals"),
        "summary": (
            f"You felt {ctx['checkin'].get('mood')} with "
            f"{ctx['checkin'].get('energy')} energy and planned goals: "
            f"{ctx['checkin'].get('goals')}"
        ),
    }

    save_entry(entry)

    await context.session.send_data(
        json.dumps({
            "type": "wellness_update",
            "data": entry
        }).encode("utf-8"),
        topic="wellness_update",
        reliable=True
    )

    return entry



# -------------------------
# PREWARM MODELS
# -------------------------

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


# -------------------------
# ENTRYPOINT
# -------------------------

async def entrypoint(ctx: JobContext):

    ctx.log_context_fields = {"room": ctx.room.name}

    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(model="gemini-2.5-flash"),
        tts=murf.TTS(
            voice="en-US-matthew",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        vad=ctx.proc.userdata["vad"],
        turn_detection=MultilingualModel(),
        preemptive_generation=True,
    )

    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on(ev: MetricsCollectedEvent):
        usage_collector.collect(ev.metrics)

    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC()
        ),
    )

    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm
        )
    )
