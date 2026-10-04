"""
mas.orchestration.debate: Anti-sycophantic Multi-Agent Debate (MAD) engine.
Architect: Acinonyx
"""

from __future__ import annotations
import asyncio
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from mas.core.agent import BaseAgent
from mas.core.message import ContentType, Message, MessageMetadata, Role


@dataclass
class DebateTurn:
    round_number: int
    agent_id: str
    masked_label: str
    claim: str
    critique: str = ""


def _tokenize(text: str) -> Set[str]:
    return set(re.findall(r"[a-z0-9]{4,}", (text or "").lower()))


class DebateEngine:
    """
    Multi-Agent Debate (MAD) with Anti-Sycophancy Guardrails:
    1. Blind Identity Masking (Agents see 'Debater 1', 'Debater 2' rather than names/roles).
    2. Explicit Contrarian / Devil's Advocate participation.
    3. Bounded iterative rounds (K <= 3).
    4. Impartial Synthesizer / Moderator evaluation.
    5. Sycophancy scoring (agreement / novelty) with optional hard fail.
    """

    def __init__(
        self,
        debaters: List[BaseAgent],
        moderator: BaseAgent,
        contrarian: Optional[BaseAgent] = None,
        max_rounds: int = 3,
        max_sycophancy: float = 0.9,
        fail_on_high_sycophancy: bool = False,
    ) -> None:
        self.debaters = debaters
        self.moderator = moderator
        self.contrarian = contrarian
        self.max_rounds = max_rounds
        self.max_sycophancy = max_sycophancy
        self.fail_on_high_sycophancy = fail_on_high_sycophancy
        self.transcript: List[DebateTurn] = []
        self._sycophancy_score: float = 0.0

    def sycophancy_score(self) -> float:
        """
        Approximate sycophancy as mean pairwise lexical overlap across final-round claims.
        Lower is better (more independent reasoning). Returns 0.0 if insufficient data.
        """
        if self._sycophancy_score:
            return self._sycophancy_score
        return self._compute_sycophancy()

    def _compute_sycophancy(self) -> float:
        if not self.transcript:
            return 0.0
        last_round = max(t.round_number for t in self.transcript)
        claims = [t.claim for t in self.transcript if t.round_number == last_round]
        if len(claims) < 2:
            return 0.0
        token_sets = [_tokenize(c) for c in claims]
        overlaps = []
        for i in range(len(token_sets)):
            for j in range(i + 1, len(token_sets)):
                a, b = token_sets[i], token_sets[j]
                if not a or not b:
                    continue
                overlaps.append(len(a & b) / max(len(a | b), 1))
        self._sycophancy_score = sum(overlaps) / len(overlaps) if overlaps else 0.0
        return self._sycophancy_score

    async def conduct_debate(self, proposition_or_problem: str) -> str:
        """Execute full multi-round debate with blind masking and moderator synthesis."""
        all_participants: List[BaseAgent] = list(self.debaters)
        if self.contrarian:
            all_participants.append(self.contrarian)

        labels: Dict[str, str] = {
            agent.name: f"Debater {i+1}"
            for i, agent in enumerate(all_participants)
        }

        latest_statements: Dict[str, str] = {}

        for round_idx in range(1, self.max_rounds + 1):
            round_tasks = []

            for agent in all_participants:
                masked_context_lines = []
                for other_name, stmt in latest_statements.items():
                    if other_name != agent.name:
                        masked_context_lines.append(f"{labels[other_name]}: {stmt}")

                masked_context = "\n".join(masked_context_lines)
                if round_idx == 1:
                    prompt = (
                        f"Round 1: Propose your rigorous solution/perspective on:\n"
                        f"'{proposition_or_problem}'"
                    )
                else:
                    prompt = (
                        f"Round {round_idx}: Review the masked arguments from peer debaters:\n"
                        f"{masked_context}\n\n"
                        f"Identify logical flaws, verify factual claims, and defend or refine your solution to:\n"
                        f"'{proposition_or_problem}'. Do NOT defer to peers out of politeness; maintain critical scrutiny."
                    )

                msg = Message(
                    sender="debate_engine",
                    recipient=agent.name,
                    role=Role.MODERATOR,
                    content=prompt,
                    metadata=MessageMetadata(topic="debate"),
                )

                async def _get_turn(ag: BaseAgent, m: Message):
                    resp = await ag.step(m)
                    return ag.name, resp.content

                round_tasks.append(_get_turn(agent, msg))

            turn_results = await asyncio.gather(*round_tasks)

            for agent_name, response_text in turn_results:
                latest_statements[agent_name] = response_text
                self.transcript.append(
                    DebateTurn(
                        round_number=round_idx,
                        agent_id=agent_name,
                        masked_label=labels[agent_name],
                        claim=response_text,
                    )
                )

        syc = self._compute_sycophancy()
        if self.fail_on_high_sycophancy and syc > self.max_sycophancy:
            raise RuntimeError(
                f"Debate rejected: sycophancy_score={syc:.3f} exceeds max={self.max_sycophancy}"
            )

        synthesis_prompt_lines = [
            f"You are the Impartial Moderator Judge.",
            f"Analyze the following {self.max_rounds}-round multi-agent debate transcript for '{proposition_or_problem}':\n",
            f"(Anti-sycophancy score={syc:.3f}; lower means more independent claims)\n",
        ]
        for turn in self.transcript:
            synthesis_prompt_lines.append(
                f"[Round {turn.round_number}] {turn.masked_label}: {turn.claim}"
            )
        synthesis_prompt_lines.append(
            "\nEvaluate all arguments for logical soundness, factual validity, and resilience against counter-arguments. "
            "Render the final authoritative consensus decision and rationale."
        )

        moderator_msg = Message(
            sender="debate_engine",
            recipient=self.moderator.name,
            role=Role.SYSTEM,
            content="\n".join(synthesis_prompt_lines),
            metadata=MessageMetadata(topic="debate_synthesis"),
        )

        verdict_msg = await self.moderator.step(moderator_msg)
        return verdict_msg.content
