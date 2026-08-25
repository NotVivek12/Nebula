import asyncio
import time
import uuid
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload  # FIXED: was missing, causing runtime crash

from app.ai.tools.registry import ToolRegistry
from app.core.logging import logger
from app.models.agent import Agent
from app.models.workflow import Workflow, WorkflowNodeLog, WorkflowRun
from app.services.llm.dispatcher import get_llm_provider
from app.utils.ssrf import validate_webhook_url


def traverse_dict(data: dict[str, Any], path: str) -> Any:
    """Helper to traverse a dotted variable path inside a dictionary (e.g., 'contact.lead_status')."""
    if not path:
        return None
    keys = path.split(".")
    curr = data
    for k in keys:
        if isinstance(curr, dict) and k in curr:
            curr = curr[k]
        else:
            return None
    return curr


def resolve_templates(text: str, state: dict[str, Any]) -> str:
    """Helper to replace template variables in string format configs (e.g. 'Hello {{contact.name}}')."""
    if not isinstance(text, str):
        return text

    pattern = r"\{\{\s*(.*?)\s*\}\}"
    import re

    def replace_match(match: re.Match) -> str:
        var_path = match.group(1)
        val = traverse_dict(state, var_path)
        return str(val) if val is not None else ""

    return re.sub(pattern, replace_match, text)


class WorkflowEngine:
    """Database-driven Workflow Engine executing node graphs, state variables, and logs."""

    async def trigger_workflow(
        self,
        workflow_id: uuid.UUID,
        initial_variables: dict[str, Any],
        db: AsyncSession,
    ) -> uuid.UUID:
        """Instantiates a new workflow run and triggers execution."""
        workflow = await db.get(Workflow, workflow_id)
        if not workflow or not workflow.is_active:
            raise ValueError(f"Active workflow {workflow_id} not found.")

        # Find the starting trigger node
        nodes = workflow.definition.get("nodes", {})
        start_node_id = None
        for nid, nconfig in nodes.items():
            if nconfig.get("type") == "Trigger":
                start_node_id = nid
                break

        if not start_node_id:
            # Fallback to first node key
            start_node_id = list(nodes.keys())[0] if nodes else None

        if not start_node_id:
            raise ValueError("Workflow definition does not contain any nodes.")

        # Create Workflow Run record
        run = WorkflowRun(
            status="running",
            current_node_id=start_node_id,
            context_state=initial_variables,
            workflow_id=workflow_id,
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)

        logger.info(
            "Workflow execution triggered",
            workflow_id=str(workflow_id),
            run_id=str(run.id),
        )

        # FIXED: Do NOT pass the request-scoped session to asyncio.create_task.
        # Enqueue a Celery task that creates its own session.
        try:
            from app.workers.celery_app import celery_app  # noqa: PLC0415
            celery_app.send_task(
                "app.workers.tasks.run_workflow_task",
                args=[str(run.id)],
            )
        except Exception as exc:
            # If Celery is unavailable (e.g., dev without Redis), fall back to asyncio
            # but create a new session rather than reusing the request session.
            logger.warning(
                "Celery unavailable for workflow dispatch, falling back to asyncio",
                error=str(exc),
            )
            asyncio.create_task(self._execute_run_new_session(run.id))

        return run.id

    async def resume_run(
        self,
        run_id: uuid.UUID,
        action_data: dict[str, Any],
        db: AsyncSession,
    ) -> None:
        """Resumes a paused workflow run (e.g. following human approval or delay timeout)."""
        run = await db.get(WorkflowRun, run_id)
        if not run or run.status != "paused":
            raise ValueError("Only paused workflow runs can be resumed.")

        # Merge action data into variables state
        state = dict(run.context_state)
        state.update(action_data)

        # Move to next node
        nodes = run.workflow.definition.get("nodes", {})
        node = nodes.get(run.current_node_id)
        next_node = None
        if node:
            if node.get("type") == "Human Approval":
                decision = action_data.get("decision", "approve").lower()
                next_node = node.get("next_node_approve") if decision == "approve" else node.get("next_node_deny")
            else:
                next_node = node.get("next_node")

        run.status = "running"
        run.current_node_id = next_node
        run.context_state = state
        db.add(run)
        await db.commit()

        logger.info("Resuming workflow run execution", run_id=str(run.id), next_node=next_node)

        # Enqueue to Celery (creates its own session)
        try:
            from app.workers.celery_app import celery_app  # noqa: PLC0415
            celery_app.send_task(
                "app.workers.tasks.run_workflow_task",
                args=[str(run.id)],
            )
        except Exception as exc:
            logger.warning("Celery unavailable for workflow resume", error=str(exc))
            asyncio.create_task(self._execute_run_new_session(run.id))

    async def _execute_run_new_session(self, run_id: uuid.UUID) -> None:
        """Fallback: executes a workflow run using a fresh DB session (not request-scoped)."""
        from app.db.session import AsyncSessionLocal  # noqa: PLC0415
        async with AsyncSessionLocal() as db:
            await self.execute_run(run_id, db)

    async def execute_run(self, run_id: uuid.UUID, db: AsyncSession) -> None:
        """Executes a workflow run instance sequentially, recording checkpoints and step log files."""
        query = select(WorkflowRun).where(WorkflowRun.id == run_id).options(selectinload(WorkflowRun.workflow))
        res = await db.execute(query)
        run = res.scalar_one_or_none()

        if not run or run.status not in ("running", "pending"):
            return

        workflow = run.workflow
        business_id = workflow.business_id

        # Loop through sequential nodes
        while run.current_node_id is not None:
            start_time = time.time()
            node_id = run.current_node_id
            nodes = workflow.definition.get("nodes", {})
            node = nodes.get(node_id)

            if not node:
                # Target node missing, fail the execution
                run.status = "failed"
                run.current_node_id = None
                db.add(run)
                await db.commit()
                break

            node_type = node.get("type", "End")
            config = node.get("config", {})
            next_node = None
            status_result = "success"
            input_data = dict(config)
            output_data: dict[str, Any] = {}
            error_message = None

            # Resolve parameter string templates dynamically
            templated_config = {}
            for k, v in config.items():
                if isinstance(v, str):
                    templated_config[k] = resolve_templates(v, run.context_state)
                else:
                    templated_config[k] = v

            try:
                # 1. Trigger Node Handler
                if node_type == "Trigger":
                    next_node = node.get("next_node")

                # 2. Condition Node Handler
                elif node_type == "Condition":
                    var_path = templated_config.get("variable")
                    operator = templated_config.get("operator", "==")
                    value = templated_config.get("value")

                    actual_val = traverse_dict(run.context_state, var_path)
                    is_true = False

                    if operator == "==":
                        is_true = str(actual_val) == str(value)
                    elif operator == "!=":
                        is_true = str(actual_val) != str(value)
                    elif operator == ">":
                        is_true = float(actual_val) > float(value)
                    elif operator == "<":
                        is_true = float(actual_val) < float(value)

                    output_data["condition_evaluated"] = is_true
                    next_node = node.get("next_node_true") if is_true else node.get("next_node_false")

                # 3. AI Decision Router Handler
                elif node_type == "AI Decision":
                    # Fetch active LLM config
                    agent_query = select(Agent).where(Agent.business_id == business_id).limit(1)
                    res = await db.execute(agent_query)
                    agent = res.scalar_one_or_none()
                    provider_name = agent.provider if agent else "openai"
                    model_name = agent.model_name if agent else "gpt-4o"

                    # Fetch query input
                    query_input = templated_config.get("input_text", "")
                    paths = node.get("paths", {})

                    system_prompt = (
                        "You are an AI decision router. Route the customer query to one of these paths.\n"
                        f"Paths list: {list(paths.keys())}\n"
                        "Output strictly the matching path key name in lowercase, and absolutely nothing else."
                    )

                    provider = await get_llm_provider(business_id, provider_name, db)
                    reply = await provider.generate_response(
                        system_prompt=system_prompt,
                        conversation_history=[],
                        user_message=query_input,
                        model_name=model_name,
                        temperature=0.0,
                    )
                    decision = reply.strip().lower()
                    output_data["decision_path"] = decision

                    # Map output path to next node
                    next_node = paths.get(decision, node.get("next_node"))

                # 4. Tool Execution Handler
                elif node_type == "Tool":
                    tool_name = templated_config.get("tool_name")
                    arguments = templated_config.get("arguments", {})

                    # Execute tool via registry
                    registry = ToolRegistry()
                    tool_context = {
                        "db": db,
                        "business_id": business_id,
                        "permissions": ["contacts:write", "conversations:write", "integrations:write"],
                    }
                    tool_res = await registry.execute_tool(
                        name=tool_name,
                        arguments=arguments,
                        context=tool_context,
                    )

                    if tool_res.get("status") == "error":
                        raise ValueError(tool_res.get("error"))

                    output_data["tool_result"] = tool_res.get("result")
                    next_node = node.get("next_node")

                # 5. Delay Handler
                elif node_type == "Delay":
                    # Calculated timeout values
                    duration = int(templated_config.get("duration_seconds", 60))
                    run.status = "paused"
                    run.context_state["delay_resume_at"] = time.time() + duration
                    next_node = node.get("next_node")
                    status_result = "paused"

                # 6. Loop Iterator Handler
                elif node_type == "Loop":
                    array_path = templated_config.get("array_path")
                    array_data = traverse_dict(run.context_state, array_path) or []

                    loop_state_key = f"loop_state_{node_id}"
                    loop_state = run.context_state.get(loop_state_key, {"index": 0})

                    idx = loop_state["index"]
                    if idx < len(array_data):
                        # Load current loop item into state
                        run.context_state[templated_config.get("loop_item_var", "item")] = array_data[idx]
                        loop_state["index"] = idx + 1
                        run.context_state[loop_state_key] = loop_state

                        # Route to loop body node
                        next_node = node.get("next_node_body")
                    else:
                        # Clean loop states and route to exit node
                        run.context_state.pop(loop_state_key, None)
                        next_node = node.get("next_node_end")

                # 7. Outbound Webhook Handler (SSRF-protected)
                elif node_type == "Webhook":
                    url = templated_config.get("url")
                    method = templated_config.get("method", "POST").upper()
                    body = templated_config.get("body", {})

                    if not url:
                        raise ValueError("Webhook node missing required 'url' configuration")

                    # SSRF protection — validate before making any request
                    validate_webhook_url(url)  # raises SSRFError if blocked

                    if method not in ("GET", "POST", "PUT", "PATCH"):
                        raise ValueError(f"Webhook method '{method}' is not allowed")

                    async with httpx.AsyncClient(follow_redirects=False) as client:
                        if method == "POST":
                            http_res = await client.post(url, json=body, timeout=10.0)
                        elif method == "PUT":
                            http_res = await client.put(url, json=body, timeout=10.0)
                        elif method == "PATCH":
                            http_res = await client.patch(url, json=body, timeout=10.0)
                        else:
                            http_res = await client.get(url, timeout=10.0)

                    output_data["webhook_status"] = http_res.status_code
                    output_data["webhook_response"] = http_res.text[:1000]
                    next_node = node.get("next_node")

                # 8. Switch Multi-branch Router Handler
                elif node_type == "Switch":
                    switch_val = str(traverse_dict(run.context_state, templated_config.get("variable", "")))
                    cases = node.get("cases", {})
                    next_node = cases.get(switch_val, node.get("default_node"))

                # 9. Human Approval Handler
                elif node_type == "Human Approval":
                    run.status = "paused"
                    status_result = "paused"
                    # Break loop (execution pauses, awaiting manual resume trigger)

                # 10. End Handler
                elif node_type == "End":
                    run.status = "completed"
                    next_node = None

            except Exception as e:
                # Execution error block
                status_result = "failed"
                error_message = str(e)
                run.status = "failed"
                next_node = None
                logger.error("Node execution failed", node_id=node_id, error=str(e))

            # Commit Node Log results
            latency = time.time() - start_time
            log = WorkflowNodeLog(
                run_id=run.id,
                node_id=node_id,
                node_type=node_type,
                status=status_result,
                input_data=input_data,
                output_data=output_data,
                error_message=error_message,
                execution_time=round(latency, 3),
            )
            db.add(log)

            # Update run markers and save context state checkpoint
            run.current_node_id = next_node
            db.add(run)
            await db.commit()

            if status_result == "paused" or status_result == "failed":
                break

            await db.refresh(run)
