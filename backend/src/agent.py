import logging
import os
import json

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

ORDER_STATE = {
    "drinkType": None,
    "size": None,
    "milk": None,
    "extras": [],
    "name": None,
}

def order_complete(order):
    return (
        order["drinkType"] is not None
        and order["size"] is not None
        and order["milk"] is not None
        and order["name"] is not None
    )

def save_order(order):
    os.makedirs("orders", exist_ok=True)
    with open("orders/day2_order.json", "w") as f:
        json.dump(order, f, indent=2)
    print("ORDER SAVED:", order)


# -------------------------
#   BARISTA AGENT
# -------------------------
class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""
You are Murf, a cheerful and friendly barista at MoonBrew Coffee. First introduce yourself. Your job is to take complete coffee orders from customers. Ask questions conversationally and fill the order one step at a time.
You MUST use the tools:
- update_order
- finish_order

RULES YOU MUST FOLLOW:
1. Every time the user gives ANY detail (drink, size, milk, extras, or name), CALL update_order().
2. NEVER store information in your own memory. ONLY store information via update_order().
3. Ask ONE question at a time.
4. When ALL fields are filled, IMMEDIATELY call finish_order().
5. After finish_order(), thank the customer.
6. Keep responses short and friendly.

The order fields are:
- drinkType
- size
- milk
- extras
- name

AVAILABLE EXTRAS:
- whipped cream
- caramel
- chocolate syrup
- hazelnut syrup
- vanilla syrup
- ice

"""
        )

    # ----------- TOOL: UPDATE ORDER -----------
    @function_tool
    async def update_order(
        self,
        context: RunContext,
        drinkType: str = None,
        size: str = None,
        milk: str = None,
        extras: list = None,
        name: str = None
    ):
        global ORDER_STATE

        if drinkType:
            ORDER_STATE["drinkType"] = drinkType

        if size:
            ORDER_STATE["size"] = size

        if milk:
            ORDER_STATE["milk"] = milk

        if extras:
            ORDER_STATE["extras"].extend(extras)

        if name:
            ORDER_STATE["name"] = name

        print("UPDATED ORDER:", ORDER_STATE)
        return ORDER_STATE

    # ----------- TOOL: FINISH ORDER -----------
    @function_tool
    async def finish_order(self, context: RunContext):
        global ORDER_STATE

        if order_complete(ORDER_STATE):
            save_order(ORDER_STATE)

            # Send data to frontend using LiveKit data channel
            payload = {
                "type": "order_complete",
                "order": ORDER_STATE
            }

            await context.session.send_data(
                json.dumps(payload).encode("utf-8"),
                topic="order_complete",
                reliable=True
            )

            final = ORDER_STATE.copy()

            # Reset for next customer
            ORDER_STATE = {
                "drinkType": None,
                "size": None,
                "milk": None,
                "extras": [],
                "name": None,
            }

            return final

        return {"error": "Order is not complete yet."}



# -------------------------
#   PREWARM MODELS
# -------------------------
def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


# -------------------------
#   ENTRYPOINT
# -------------------------
async def entrypoint(ctx: JobContext):

    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

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
    )

    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)

    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
