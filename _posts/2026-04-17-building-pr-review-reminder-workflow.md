---
layout: post
title: "Building a PR Review Reminder Workflow"
categories: blog development github actions ai
tags: [github-actions, automation, azure-devops, ai]
lang: en
permalink: /en/posts/building-pr-review-reminder-workflow/
---

I wanted a workflow that detects pull requests waiting too long for review and sends a reminder only when it is actually needed.

At first glance this looks simple, but there are a few places where reminder workflows usually become noisy or unreliable:

- determine pending reviewers from review history
- track reminder state
- take task priority into account
- avoid marking a reminder as sent when delivery failed

## The basic flow

The GitHub agentic workflow runs on a schedule and reads open pull requests through GitHub MCP.

For each PR it collects:

- title
- body
- labels
- author
- requested reviewers
- review history
- PR URL

That gives the workflow enough information to decide whether the PR is still waiting on someone.

The next step is to cross-check the actual reviews and remove reviewers who already approved, requested changes, or commented. What remains is the real pending reviewer set.

A simplified version of that logic looks like this:

```ts
const reviewed = new Set(
  reviews
    .filter(r => ['APPROVED', 'CHANGES_REQUESTED', 'COMMENTED'].includes(r.state))
    .map(r => r.author.login)
);

const pending = requestedReviewers.filter(r => !reviewed.has(r.login));
```

## How priority is resolved

Once the workflow knows a PR is reviewable and still waiting, it tries to work out urgency.

It scans the PR body for an Azure DevOps work item reference. If it finds one, it asks Azure DevOps MCP for priority metadata. That becomes the source for the reminder schedule.

If the Azure DevOps lookup fails, the workflow falls back to labels. If labels are not useful either, it falls back again to a default schedule.

The fallback order is explicit:

```ts
const priority =
  adoPriority ??
  labelPriority ??
  defaultPriority;
```

## Reminder timing

The workflow tracks reminder history in a small state file stored through the workflow cache.

It tracks:

- which reviewer was reminded for which PR
- when the last reminder was sent
- how many reminders have already gone out

With that state, the workflow can apply timing rules:

- first reminder after some delay
- repeated reminders at a fixed interval
- no reminder if the last send was too recent

The workflow also resets reminder state when the pending reviewer set changes. That avoids stale state when reviewers are added, removed, or finish their review.

The due check is just state plus timestamps:

```ts
const due =
  !entry.lastRemindedAt ||
  hoursSince(entry.lastRemindedAt) >= entry.intervalHours;
```

## Delivery

The delivery side is intentionally small.

Once the workflow decides a reminder is due, it sends a JSON payload to a Power Automate HTTP endpoint:

```json
{
  "recipient": "user@example.com",
  "message": "..."
}
```

The recipient comes from a mapping between GitHub usernames and the address used for direct Teams delivery.

The workflow updates reminder state only after the HTTP call succeeds. That keeps the cache aligned with reality and avoids situations where the workflow thinks a reminder was sent even though delivery failed.

That state update is the part that matters most:

```ts
const response = await sendReminder(recipient, message);

if (response.ok) {
  entry.lastRemindedAt = now;
  entry.reminderCount += 1;
}
```

## Why GitHub Agentic Workflow

This is a good fit for an agentic workflow because it has to combine:

- GitHub review state
- Azure DevOps metadata
- reviewer mapping
- timing rules
- delivery status

There is some judgment involved, but the boundaries are still clear. The agent decides whether a reminder is due and what it should contain, while the actual send stays deterministic.
