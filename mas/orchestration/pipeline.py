"""
mas.orchestration.pipeline: Sequential SOP-Driven Assembly Line for artifact generation.
Architect: Acinonyx
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union
from mas.core.agent import BaseAgent
from mas.core.message import ContentType, Message, MessageMetadata, Role
from mas.validation import SchemaSpec, validate_against_schema


@dataclass
class SOPStage:
    name: str
    agent: BaseAgent
    output_key: str
    instruction_template: str = "{input}"
    validator: Optional[Callable[[str], bool]] = None
    schema: Optional[SchemaSpec] = None


class SOPPipeline:
    """
    Standard Operating Procedure (SOP) Assembly Line.
    Executes stages in strict sequence, validating intermediate artifacts
    via callables and/or SchemaSpec, and passing accumulated context downstream.
    """

    def __init__(self, name: str = "SOP-Pipeline") -> None:
        self.name = name
        self.stages: List[SOPStage] = []
        self.artifacts: Dict[str, str] = {}

    def add_stage(
        self,
        name: str,
        agent: BaseAgent,
        output_key: str,
        instruction_template: str = "{input}",
        validator: Optional[Callable[[str], bool]] = None,
        schema: Optional[SchemaSpec] = None,
    ) -> None:
        self.stages.append(
            SOPStage(
                name=name,
                agent=agent,
                output_key=output_key,
                instruction_template=instruction_template,
                validator=validator,
                schema=schema,
            )
        )

    async def execute(self, initial_input: str) -> Dict[str, str]:
        """Execute assembly line stages sequentially."""
        current_input = initial_input
        self.artifacts["initial_input"] = initial_input

        for stage in self.stages:
            formatted_instruction = stage.instruction_template.format(
                input=current_input,
                **self.artifacts,
            )

            msg = Message(
                sender="sop_orchestrator",
                recipient=stage.agent.name,
                role=Role.USER,
                content=formatted_instruction,
                content_type=ContentType.TEXT,
                metadata=MessageMetadata(topic="sop_pipeline"),
            )

            response = await stage.agent.step(msg)
            output_content = response.content

            if stage.schema is not None:
                ok, reason = validate_against_schema(output_content, stage.schema)
                if not ok:
                    raise ValueError(
                        f"Stage '{stage.name}' failed schema validation for key "
                        f"'{stage.output_key}': {reason}"
                    )

            if stage.validator:
                valid = stage.validator(output_content)
                if not valid:
                    raise ValueError(
                        f"Stage '{stage.name}' failed artifact validation for key '{stage.output_key}'"
                    )

            self.artifacts[stage.output_key] = output_content
            current_input = output_content

        return self.artifacts
