---
title: English
icon: fas fa-globe
order: 5
lang: en
---
Posts available in English.

{% assign english_posts = site.posts | where: "lang", "en" %}
{% for post in english_posts %}
- [{{ post.title }}]({{ post.url | relative_url }})
{% endfor %}
