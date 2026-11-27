"""Starting point for a Paper Trail adapter. Copy this file and fill in answer().

    python scripts/run_custom.py --system-id my-system --adapter scripts/adapters/my_adapter.py --split open

The runner calls answer() once per question, each time in a fresh process, and stops it
at 10 minutes. Anything expensive to load (an index, a model) belongs in a service this
function calls, not in the function itself.
"""

# Describes your system in the submission file. See submission-template.json.
SYSTEM = {
    "name": "Your system name",
    "harness": "The agent or assistant that runs the model",
    "harness_version": "Version or date of the harness",
    "model": "Exact model name or id",
    "reasoning_effort": "Effort or thinking setting, if any",
    "content_system": "Where the library is stored and indexed",
    "retrieval": "How the harness searches and reads it",
    "ingestion": {
        "no_human_categorization": None,  # set to True or False
        "schema_mode": "auto or human_authored",
        "description": "How the library was ingested and processed",
    },
}


def answer(question):
    """question has: id, question (as written), reference_date, prompt (date + question).

    Return the answer text, or a dict with the library paths you used and your token counts.
    """
    # Replace this with a call to your system, for example:
    #   reply = my_agent.ask(question["prompt"])
    #   return {"answer": reply.text, "sources": reply.paths,
    #           "input_tokens": reply.input_tokens, "output_tokens": reply.output_tokens}
    return {"answer": "", "sources": [], "input_tokens": None, "output_tokens": None}
