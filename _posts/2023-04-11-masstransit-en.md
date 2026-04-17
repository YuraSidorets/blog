---
layout: post
title: "About MassTransit"
categories: blog development c#
tags: [dotnet, messaging, architecture]
description: "A practical and opinionated look at MassTransit, including the benefits, the rough edges, and why its documentation and abstraction can cost real time."
lang: en
translation_key: mass-transit
permalink: /en/posts/about-masstransit/
---
There is this 'wonderful' project that adds convenient abstractions over popular message brokers: [MassTransit](https://masstransit.io/introduction).

The author describes it as "an open-source distributed application framework for .NET that provides a consistent abstraction on top of the supported message transports", but in practice it feels like something halfway between a framework and a fairly large ecosystem of its own.

MassTransit has enough benefits to make it worth a serious look:
  - Decoupling: it helps separate parts of a system and lets them exchange messages without exposing internal implementation details.
  - Flexibility: it supports a lot of well-known message brokers, so moving between them is easier.
  - Resilience: retry policies, dead-lettering, circuit breaker, failover, and a lot more are available out of the box.
  - Extensibility: you can add custom middleware, serializers, pipelines, and other pieces.
  - Testability: the in-memory broker makes basic testing much easier.

But I would not be writing this post if I hadn't tried this 'magical' framework in a real project. In practice, your MassTransit journey usually starts with one problem: the documentation is weak.

At the time this post was originally written, the latest MassTransit version was 8.0.14 for `net6.0` and 7.3.1 for earlier targets.

First, if you were not on `net6.0`, you could barely find any documentation at all. Older docs were effectively hidden somewhere out on the internet and only available to the chosen few who had spent a month digging through Stack Overflow, GitHub, and YouTube.

For reference, those old docs were available here: [version 7](https://masstransit-v7.netlify.app/getting-started/) and [version 6](https://masstransit-v6.netlify.app/getting-started/).

Second, even if you do find the documentation, that does not mean it will actually help. A lot of it is either incomplete, partially correct, or unnecessarily complicated. If you have never used a framework like this before, that usually means losing a few extra days just trying to understand how things fit together.

I lost two weeks on that. Really lost them. I had to go through the concepts in the docs, then dig into the code on [GitHub](https://github.com/MassTransit), and then watch talks on [YouTube](https://www.youtube.com/@PhatBoyG) because the docs alone were not enough.

Third, when the documentation says MassTransit supports a transport, that does not automatically mean the integration is equally mature. For example, before version 8.0.0, ActiveMQ support was barely usable beyond basic scenarios. That was not clearly called out anywhere. So if you plan to use it with ActiveMQ or Artemis, be careful.

Most of the code in MassTransit assumes RabbitMQ is the happy path. If your project already uses RabbitMQ, good for you.

Also, if you need a non-standard topology in your project, forget about an easy ride. You will spend a lot of time and patience figuring out how to override the default topology choices made by the library.

And if you are still wondering whether to bring it into your project, keep in mind that the built-in in-memory broker used for tests is fairly slow and has no real understanding of your custom topology. There are plenty of articles suggesting lighter alternatives for test scenarios.

The main downsides of MassTransit, at least from my experience:
  - Complexity: the framework is powerful, but only in the right hands. If you can shape it around your requirements, it can save time and make broker migrations easier. If not, you may be better off building your own abstraction layer and keeping full control.
  - Overhead: MassTransit always sits between your system and the broker, so there is extra overhead in serialization, routing, filtering, and the internal pipeline.
  - Learning curve: the documentation is very weak. There are YouTube videos, GitHub issues, and Stack Overflow threads, but it is still not enough. You should expect to spend a lot of time reading code before you really understand how to use it.
  - Abstraction: this is both the main selling point and the main drawback. You do not always know what is happening under the hood, and that makes it harder to debug or to support non-standard scenarios.
  - Performance: it is fast and efficient enough for many systems, but I would not use it for high-performance paths where latency is critical.

The short version is simple: think very carefully before adopting MassTransit. You can spend a lot of time on it and still end up without the result you wanted.
