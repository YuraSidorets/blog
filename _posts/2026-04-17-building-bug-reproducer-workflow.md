---
layout: post
title: "Building a Bug Reproducer Workflow with Playwright"
categories: blog development github actions ai testing
---

The goal for this workflow was straightforward: take fresh bug reports, figure out which ones are concrete enough to automate, and run a browser-based reproduction against the existing test setup.

What I did not want was another isolated automation path with its own helpers, its own execution model, and its own idea of what a result looks like. If the repo already has Playwright, the bug reproducer should lean on that instead of pretending to be a separate framework.

## Start with triage, not execution

The first part of the workflow has nothing to do with browsers.

It pulls recent bugs from Azure DevOps through MCP, then filters them against a small cache so the same items are not processed over and over again. After that it fetches the full work item details and strips the noisy HTML fields down to plain text.

That gives the agent enough context to answer a simple question:

is this report detailed enough to turn into a runnable test?

That question comes before everything else. If the report is too vague, there is no value in forcing it through Playwright just to get a bad result.

## The workflow handles vague reports explicitly

One rule in this workflow is that “not enough information” is its own outcome.

If the report does not clearly describe where to start, what to do, and what should happen, the workflow does not label the bug as “not reproduced.” It posts an insufficient-information result back to Azure DevOps and sends the item back to the reporter.

That keeps the output honest.

A vague report and a failed reproduction are not the same thing, and the workflow treats them differently on purpose.

The decision is roughly:

```ts
const actionable =
  hasStartingPoint(description) &&
  hasSteps(description) &&
  hasExpectedVsActual(description);
```

## The agent only generates the test, it does not own the whole run

When a bug looks actionable, the agent writes a temporary Playwright spec and a manifest file that describes what was generated.

That temporary part is important. The workflow is trying to answer whether the bug can be reproduced now. It is not trying to silently turn every bug into permanent test coverage.

The generated spec still stays close to the real suite:

- it uses the shared Playwright helpers
- it relies on the existing authenticated setup
- it uses the configured base URL

So the generated test runs inside the same environment as the rest of the browser suite instead of creating a parallel path just for this workflow.

## Why the manifest exists

The manifest is the handoff between reasoning and execution.

The agent decides which specs should exist. The runtime looks at the manifest and executes only those files. That is a cleaner boundary than asking the agent to directly control the whole browser run from start to finish.

The flow becomes:

1. collect recent bugs
2. decide which ones are actionable
3. generate temporary specs
4. record them in the manifest
5. let the runtime execute what the manifest describes

That separation makes the workflow easier to reason about and easier to debug.

The manifest itself is just enough metadata to connect a generated file back to a bug:

```json
[
  {
    "bug_id": "12345",
    "generated_spec_file": "bug-12345.spec.ts"
  }
]
```

## Why execution happens in post-steps

The current version runs the repro execution in post-steps.

That was mostly a maintenance decision. Keeping the execution path in the workflow source means the behavior survives normal `gh aw compile` runs. Earlier approaches that depended on compiled workflow edits were too easy to lose.

Once post-steps start, the rest of the flow is pretty boring in a good way:

- inspect the manifest
- install e2e dependencies if there is work to do
- install the required Playwright browser
- run the generated specs
- collect reports and artifacts
- post the result back to Azure DevOps

That is the right place for boring code. The agent handles interpretation. The scripts handle deterministic work.

## Result handling is stricter than generation

The workflow does not consider a bug “done” just because it managed to generate a test.

A generated repro only becomes complete after two things happen:

- the Playwright run finishes
- the result is posted back successfully

Only then does the workflow update its processed-bug cache.

That rule prevents an easy failure mode where generation succeeds, execution fails, feedback fails, and the bug quietly disappears from future runs because the cache was updated too early.

The cache update is intentionally late:

```ts
if (playwrightRunSucceeded && commentPostedSuccessfully) {
  cache.processedBugIds.push(bugId);
}
```

## What comes back out

The output is intentionally small and explicit:

- reproduced
- not reproduced
- reproduction failed
- insufficient information

Alongside that status, the workflow uploads the usual browser evidence so the work item can point back to something real: logs, reports, screenshots, and the workflow run itself.

That makes the workflow useful as a first-pass investigation tool, not just as a status generator.

## Why this is a good fit for an agentic workflow

This kind of workflow sits in an awkward middle ground if you try to build it as pure scripting.

It has to combine:

- Azure DevOps work item data
- cache state
- judgment about whether a report is automatable
- generation of a focused browser test
- deterministic execution and feedback

That is where the agent helps. It handles the messy interpretation step. Everything after that goes back to normal, predictable code.

That balance is what makes the workflow useful. It uses the agent where flexibility helps and avoids using the agent where repeatability matters more.
