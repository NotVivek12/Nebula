class PlatformMetrics:
    """Telemetry collector compiling statistics in standard Prometheus format."""

    def __init__(self) -> None:
        self.token_consumption = 0
        self.messages_count = 0
        self.failures_count = 0
        self.tool_execution_count = 0
        self.workflow_execution_count = 0
        self.total_latency = 0.0

    def increment_tokens(self, count: int) -> None:
        self.token_consumption += count

    def increment_messages(self) -> None:
        self.messages_count += 1

    def increment_failures(self) -> None:
        self.failures_count += 1

    def increment_tools(self) -> None:
        self.tool_execution_count += 1

    def increment_workflows(self) -> None:
        self.workflow_execution_count += 1

    def record_latency(self, seconds: float) -> None:
        self.total_latency += seconds

    def get_prometheus_metrics(self) -> str:
        """Returns collected telemetry values formatted in Prometheus plain-text spec."""
        lines = [
            "# HELP nebula_token_consumption Cumulative tokens consumed by LLM integrations.",
            "# TYPE nebula_token_consumption counter",
            f"nebula_token_consumption {self.token_consumption}",
            "# HELP nebula_messages_count Total processed customer and agent messages count.",
            "# TYPE nebula_messages_count counter",
            f"nebula_messages_count {self.messages_count}",
            "# HELP nebula_failures_count Total execution failure counts.",
            "# TYPE nebula_failures_count counter",
            f"nebula_failures_count {self.failures_count}",
            "# HELP nebula_tools_execution_count Total invocations of tools plugins.",
            "# TYPE nebula_tools_execution_count counter",
            f"nebula_tools_execution_count {self.tool_execution_count}",
            "# HELP nebula_workflows_execution_count Total workflow runs triggers.",
            "# TYPE nebula_workflows_execution_count counter",
            f"nebula_workflows_execution_count {self.workflow_execution_count}",
            "# HELP nebula_total_latency_seconds Cumulative system latency summation.",
            "# TYPE nebula_total_latency_seconds counter",
            f"nebula_total_latency_seconds {self.total_latency:.4f}",
        ]
        return "\n".join(lines) + "\n"


# Global singleton instance of PlatformMetrics collector
metrics = PlatformMetrics()
