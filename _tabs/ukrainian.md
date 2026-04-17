---
title: Українською
icon: fas fa-language
order: 6
lang: uk-UA
---
Пости, доступні українською.

{% assign ukrainian_posts = site.posts | where: "lang", "uk-UA" %}
{% for post in ukrainian_posts %}
- [{{ post.title }}]({{ post.url | relative_url }})
{% endfor %}
