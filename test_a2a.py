import json
import unittest

from a2a import invoke_agent, orchestrate_purchase


class FakeResponse:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text


class FakeResponses:
    def __init__(self, project: "FakeProject", agent_name: str) -> None:
        self.project = project
        self.agent_name = agent_name

    def create(self, *, input: str) -> FakeResponse:
        self.project.calls.append((self.agent_name, input))
        return FakeResponse(self.project.outputs[self.agent_name])


class FakeOpenAIClient:
    def __init__(self, project: "FakeProject", agent_name: str) -> None:
        self.responses = FakeResponses(project, agent_name)

    def __enter__(self) -> "FakeOpenAIClient":
        return self

    def __exit__(self, *args: object) -> None:
        return None


class FakeProject:
    def __init__(self, outputs: dict[str, str]) -> None:
        self.outputs = outputs
        self.calls: list[tuple[str, str]] = []

    def get_openai_client(self, *, agent_name: str) -> FakeOpenAIClient:
        return FakeOpenAIClient(self, agent_name)


class OrchestratorTests(unittest.TestCase):
    def test_passes_intake_output_to_supplier_as_json(self) -> None:
        project = FakeProject(
            {
                "intake": '{"item":"keyboard","quantity":25}',
                "supplier": "Stored at Files/purchases/order.json",
            }
        )

        result = orchestrate_purchase(project, "Buy 25 keyboards")

        self.assertEqual(result, "Stored at Files/purchases/order.json")
        self.assertEqual([call[0] for call in project.calls], ["intake", "supplier"])
        supplier_prompt = project.calls[1][1]
        context_text = supplier_prompt.split(
            "PURCHASE CONTEXT JSON\n", maxsplit=1
        )[1].split("\nEND PURCHASE CONTEXT JSON", maxsplit=1)[0]
        context = json.loads(context_text)
        self.assertEqual(context["original_purchase_request"], "Buy 25 keyboards")
        self.assertEqual(
            context["intake_result"], '{"item":"keyboard","quantity":25}'
        )
        self.assertEqual(context["source_agent"], "intake")

    def test_rejects_empty_agent_output(self) -> None:
        project = FakeProject({"intake": "   "})

        with self.assertRaisesRegex(RuntimeError, "returned no text output"):
            invoke_agent(project, "intake", "request")


if __name__ == "__main__":
    unittest.main()