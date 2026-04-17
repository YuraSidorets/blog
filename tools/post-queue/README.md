# Post Queue

Put markdown files you want to publish later into `tools/post-queue/pending/`.

The scheduled workflow will periodically scan that folder and move any due files into `_posts/`.
That push then triggers the normal Pages deploy workflow.

## Required shape

Queued files must be normal markdown posts with YAML frontmatter.

Example:

```md
---
layout: post
title: "My next post"
categories: blog development
tags: [dotnet, automation]
description: "Short summary used for SEO."
lang: en
permalink: /en/posts/my-next-post/
publish_on: 2026-04-21
post_slug: my-next-post
---

Post body goes here.
```

## Queue-only fields

- `publish_on`
  Publishes on that UTC date at `00:00`.
- `publish_at`
  Publishes at that exact UTC timestamp, for example `2026-04-21T08:30:00Z`.
- `post_slug`
  Optional explicit slug for the generated `_posts` filename.

The workflow removes these queue-only fields when the post is published.

## Result

When a queued post is due, it is moved to:

```text
_posts/YYYY-MM-DD-your-slug.md
```

If neither `publish_on` nor `publish_at` is set, the post is published on the next workflow run.
