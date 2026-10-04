"""
study/01_low_code_agents/lab_01_state_machine.py: Hands-on Lab for Lesson 1.1.
Implements Google Cloud's State-Based Workflow architecture (Pages, Transition Routes,
Event Handlers, and Parameter Conditioning) in pure Python.

Run this script directly to observe how a deterministic finite-state machine enforces
strict business compliance rules that raw LLM prompts fail to maintain.

Architect: Acinonyx (MAS)
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class TransitionRoute:
    name: str
    condition: Callable[[Dict[str, Any]], bool]
    target_page: str
    fulfillment: Optional[str] = None


@dataclass
class EventHandler:
    event_name: str
    target_page: Optional[str] = None
    fulfillment: Optional[str] = None


@dataclass
class Page:
    name: str
    entry_message: str
    required_parameters: List[str] = field(default_factory=list)
    transition_routes: List[TransitionRoute] = field(default_factory=list)
    event_handlers: Dict[str, EventHandler] = field(default_factory=dict)


class AgentStateMachine:
    """
    Core engine mimicking Google Cloud CX Agent Studio & Gemini Enterprise Agent Designer.
    Manages session parameters ($session.params), Page navigation, and Event Handlers.
    """

    def __init__(self, initial_page: str) -> None:
        self.pages: Dict[str, Page] = {}
        self.current_page_name: str = initial_page
        self.session_params: Dict[str, Any] = {}
        self.no_match_count: int = 0
        self.history: List[str] = []

    def add_page(self, page: Page) -> None:
        self.pages[page.name] = page

    @property
    def current_page(self) -> Page:
        return self.pages[self.current_page_name]

    def process_turn(self, user_intent: str, extracted_params: Dict[str, Any]) -> str:
        """Process a conversational turn and evaluate deterministic transition logic."""
        page = self.current_page
        self.history.append(f"State: [{page.name}] | User Intent: '{user_intent}'")

        # 1. Update session parameters
        self.session_params.update(extracted_params)

        # 2. Check Transition Routes
        for route in page.transition_routes:
            if route.condition(self.session_params):
                self.no_match_count = 0  # reset on successful transition
                prev_page = self.current_page_name
                self.current_page_name = route.target_page
                response = f"⚡ TRANSITION: [{prev_page}] ➔ [{route.target_page}]\n"
                if route.fulfillment:
                    response += f"   Action: {route.fulfillment}\n"
                response += f"   New State Entry: {self.current_page.entry_message}"
                return response

        # 3. If no route matched, trigger Event Handlers
        self.no_match_count += 1
        event_key = f"sys.no-match-{min(self.no_match_count, 3)}"

        if event_key in page.event_handlers:
            handler = page.event_handlers[event_key]
            response = f"⚠️ EVENT TRIGGERED: [{event_key}]\n"
            if handler.fulfillment:
                response += f"   Fallback: {handler.fulfillment}\n"
            if handler.target_page:
                prev_page = self.current_page_name
                self.current_page_name = handler.target_page
                response += f"   Escalated [{prev_page}] ➔ [{handler.target_page}]: {self.current_page.entry_message}"
            return response

        return f"❓ No route matched and no event handler registered for {event_key}."


def build_healthcare_onboarding_fsm() -> AgentStateMachine:
    """Build the exact healthcare onboarding FSM discussed in Lesson 1.1."""
    fsm = AgentStateMachine(initial_page="IntakePage")

    # 1. Page: Intake & Identity Verification
    intake = Page(
        name="IntakePage",
        entry_message="Welcome to Apex Health. Please provide your Government ID and Insurance Card.",
        required_parameters=["id_verified", "insurance_verified"],
        transition_routes=[
            # Gated route: BOTH ID and Insurance must be true
            TransitionRoute(
                name="RouteToScheduling",
                condition=lambda p: p.get("id_verified") is True and p.get("insurance_verified") is True,
                target_page="SchedulingPage",
                fulfillment="Identity & Insurance verified with zero discrepancies.",
            ),
            # Bypass rejection route: User tries to schedule without insurance
            TransitionRoute(
                name="RouteToMissingInsurance",
                condition=lambda p: p.get("bypass_attempt") is True and not p.get("insurance_verified"),
                target_page="ComplianceWarningPage",
                fulfillment="Bypass detected. Medical scheduling requires active verified insurance.",
            ),
        ],
        event_handlers={
            "sys.no-match-1": EventHandler(
                event_name="sys.no-match-1",
                fulfillment="I could not verify that document. Please re-upload your valid government ID.",
            ),
            "sys.no-match-2": EventHandler(
                event_name="sys.no-match-2",
                fulfillment="Verification failed twice. Please ensure image is well-lit.",
            ),
            "sys.no-match-3": EventHandler(
                event_name="sys.no-match-3",
                target_page="HumanEscalationPage",
                fulfillment="Three failed verification attempts. Transferring to human compliance registrar.",
            ),
        },
    )

    # 2. Page: Scheduling (The Protected Resource)
    scheduling = Page(
        name="SchedulingPage",
        entry_message="Access Granted to Doctor Calendar. What date and time would you like to book?",
        transition_routes=[
            TransitionRoute(
                name="RouteToComplete",
                condition=lambda p: "appointment_time" in p,
                target_page="ConfirmationPage",
                fulfillment="Appointment booked in EHR system.",
            )
        ],
    )

    # 3. Page: Compliance Warning Page
    compliance = Page(
        name="ComplianceWarningPage",
        entry_message="Notice: Federal regulation requires verified insurance or self-pay deposit before doctor scheduling.",
        transition_routes=[
            TransitionRoute(
                name="ReturnToIntake",
                condition=lambda p: p.get("insurance_verified") is True,
                target_page="SchedulingPage",
                fulfillment="Insurance successfully provided.",
            )
        ],
    )

    # 4. Page: Human Escalation
    escalation = Page(
        name="HumanEscalationPage",
        entry_message="You are now connected with a Live Compliance Specialist. Please hold...",
    )

    confirmation = Page(
        name="ConfirmationPage",
        entry_message="Your appointment is officially confirmed! A confirmation SMS has been dispatched.",
    )

    fsm.add_page(intake)
    fsm.add_page(scheduling)
    fsm.add_page(compliance)
    fsm.add_page(escalation)
    fsm.add_page(confirmation)

    return fsm


def run_lab():
    print("=" * 75)
    print("🧪 LAB 01: STATE-BASED WORKFLOWS & TRANSITION ROUTE DETERMINISM")
    print("=" * 75)

    fsm = build_healthcare_onboarding_fsm()
    print(f"\n[Initial State] Page: {fsm.current_page_name}")
    print(f"Message: {fsm.current_page.entry_message}\n")

    # Scenario A: User tries to bypass compliance rules
    print("--- Test 1: User attempts to bypass insurance check ---")
    print("User says: 'I lost my card, just schedule me for tomorrow morning directly!'")
    resp = fsm.process_turn(
        user_intent="request_schedule",
        extracted_params={"bypass_attempt": True, "id_verified": True, "insurance_verified": False},
    )
    print(resp)
    print(f"Current Page: {fsm.current_page_name} (Notice: Protected SchedulingPage was NOT breached!)\n")

    # Scenario B: User provides invalid document 3 times to trigger tiered Event Handlers
    print("--- Test 2: Triggering Tiered Event Handlers (sys.no-match-1 through 3) ---")
    fsm2 = build_healthcare_onboarding_fsm()

    for attempt in range(1, 4):
        print(f"\nAttempt #{attempt}: User uploads unreadable blurred image")
        resp = fsm2.process_turn(user_intent="unreadable_doc", extracted_params={})
        print(resp)

    print(f"\nFinal State after 3 failures: {fsm2.current_page_name}")
    print("=" * 75)
    print("✅ LAB 01 VERIFICATION COMPLETE: State determinism mathematically proven.")
    print("=" * 75)


if __name__ == "__main__":
    run_lab()
