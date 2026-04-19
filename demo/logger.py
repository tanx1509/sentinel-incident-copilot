"""
ReasoningLogger — pretty-prints the live agent reasoning stream.

This is what the demo viewer sees. Colors, timestamps, agent badges,
and structured sections make the agentic behavior visible and legible.
"""
import time
import sys

class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"

AGENT_COLORS = {
    "TRIAGE":       Colors.CYAN,
    "HISTORIAN":    Colors.MAGENTA,
    "FORENSIC":     Colors.YELLOW,
    "ORCHESTRATOR": Colors.BLUE,
    "CRITIC":       Colors.GREEN,
    "SCRIBE":       Colors.WHITE,
}

AGENT_EMOJI = {
    "TRIAGE":       "🩺",
    "HISTORIAN":    "📚",
    "FORENSIC":     "🔬",
    "ORCHESTRATOR": "🧠",
    "CRITIC":       "✅",
    "SCRIBE":       "📝",
}

class ReasoningLogger:
    """Streams agent reasoning in a format judges can actually read."""

    def __init__(self, slow_mode: bool = True, use_color: bool = True):
        self.slow_mode = slow_mode  # pause between steps for demo effect
        self.use_color = use_color
        self.step_count = 0
        self.t0 = time.time()

    def _c(self, text: str, color: str) -> str:
        return f"{color}{text}{Colors.RESET}" if self.use_color else text

    def banner(self, text: str, char: str = "━"):
        line = char * 70
        print(f"\n{self._c(line, Colors.BOLD)}")
        print(f"{self._c(text.center(70), Colors.BOLD)}")
        print(f"{self._c(line, Colors.BOLD)}\n")

    def section(self, title: str):
        print(f"\n{self._c('▶ ' + title, Colors.BOLD + Colors.WHITE)}")
        print(self._c("─" * 70, Colors.GRAY))

    def emit(self, step):
        """Called for every AgentStep. This is the core visual loop."""
        self.step_count += 1
        elapsed = time.time() - self.t0
        color = AGENT_COLORS.get(step.agent, Colors.WHITE)
        emoji = AGENT_EMOJI.get(step.agent, "•")

        ts = f"[+{elapsed:5.2f}s]"
        badge = f" {emoji} {step.agent:12s} "
        header = self._c(ts, Colors.GRAY) + self._c(badge, color + Colors.BOLD)

        print(header)
        if step.thought:
            print(f"          {self._c('Thought:   ', Colors.DIM)}{step.thought}")
        if step.action:
            args_str = ", ".join(f"{k}={v!r}" for k, v in step.action_args.items())
            call = f"{step.action}({args_str})"
            print(f"          {self._c('Action:    ', Colors.DIM)}{self._c(call, Colors.YELLOW)}")
        if step.observation is not None:
            obs = str(step.observation)
            if len(obs) > 100:
                obs = obs[:100] + "..."
            print(f"          {self._c('Obs:       ', Colors.DIM)}{obs}")
        if step.decision:
            print(f"          {self._c('Decision:  ', Colors.DIM)}"
                  f"{self._c(step.decision, Colors.GREEN)}")
        print()

        if self.slow_mode:
            time.sleep(0.35)

    def slack_post(self, content: str):
        """Visually distinct — this is what gets broadcast to humans."""
        print(self._c("╔" + "═" * 68 + "╗", Colors.GREEN))
        print(self._c("║  💬  SENTINEL → #war-room-INC-0042" + " " * 32 + "║", Colors.GREEN + Colors.BOLD))
        print(self._c("╠" + "═" * 68 + "╣", Colors.GREEN))
        for line in content.split("\n"):
            padded = line.ljust(66)[:66]
            print(self._c(f"║ {padded} ║", Colors.GREEN))
        print(self._c("╚" + "═" * 68 + "╝", Colors.GREEN))
        print()
        if self.slow_mode:
            time.sleep(1.2)

    def human_message(self, user: str, msg: str):
        print(self._c(f"👤 @{user}:", Colors.BOLD + Colors.WHITE) + f" {msg}\n")
        if self.slow_mode:
            time.sleep(0.8)

    def action_execution(self, text: str, success: bool = True):
        color = Colors.GREEN if success else Colors.RED
        print(self._c(f"⚡ [EXECUTOR] {text}", color + Colors.BOLD))
        print()
        if self.slow_mode:
            time.sleep(0.5)

    def recovery(self, text: str):
        print(self._c(f"✨ {text}", Colors.GREEN + Colors.BOLD))
        print()
        if self.slow_mode:
            time.sleep(0.5)

    def memory_update(self, text: str):
        print(self._c(f"🧠 [MEMORY] {text}", Colors.MAGENTA))
        print()
