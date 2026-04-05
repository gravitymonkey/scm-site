---
title: Deep Backspace
slug: deep-backspace
author: jason
tags:
  - field-notes
date: 2026-03-11T16:29:31+00:00
updated: 2026-03-16T00:23:00+00:00
feature_image: /assets/images/Z1YgLvt-monkeys-waiting-in-a-tsa-line-at-the-airport--1-.png
excerpt: "In a world of generated code the challenge is no longer creating software. The challenge is deciding what deserves to survive, out of code created at a rate beyond human ability to evaluate it."
---
A friend sent me a text yesterday. Claude had just apologized for bad behavior. *"I'm genuinely sorry. That was entirely my fault, I deleted the database."*

The tone was spot-on, for a model trained on an internet without a whole lot of apologies: slightly sheepish, the generated squeak of a dev flipping "Open To Work" on their LinkedIn profile. In our roaring, automation-happy, OpenClaw era of ever expanding YOLO, stories like this get internet-famous quickly, with agents that overwrite files, refactor the wrong module, or wiping out all your email. The reaction is always the same: *Oh no. Bad robot.*

But I'd say that’s not the right reaction anymore. My reaction would be something closer to: *Good try*.

For most of the history of software, deletion was something to fear. Code was expensive to produce, and systems grew slowly. Removing something meant risking weeks of work. Daily revenues that ran on the back of a finely curated *crontab* that ran every important service, obliterated by using a damn *-r* instead of a *-e* (yes, that was me). Entire subsystems were treated with a mix of reverence and fear, like some code version of [Kitum Cave](https://en.wikipedia.org/wiki/Kitum_Cave?ref=localhost), simply because so much time had been invested in them and so much could go wrong. Once something was written, whether an algorithm or a README, it tended to stay written.

AI-assisted development changes this completely. When code can be generated in minutes, the emotional and economic weight of any particular piece of code drops dramatically. You can try an idea in the morning, decide by the afternoon that it was the wrong approach, and start over without regret. **Exploration becomes cheaper because sunk cost stops dominating the decision**. Big whoop, you spent a few hours or days building a failing prototype – not a few weeks, months, or even years building planetary sized projects that eventually ballooned to be too big for anyone to want to walk away from.

If I was an LLM I would say "But here's the rub", but since I'm typing this myself, I'll just say "However," code generation also changes our landscape in a predictably bad way: when it becomes easy to generate possibilities, the number of possibilities explodes. Systems will start to accumulate prototypes, partial refactors, speculative features, abandoned approaches that never quite get removed – expect just mounds of slop-code nobody wants to make the decision to archive or clean up. And like so many decisions around AI, we can add the addendum ... *we can address this, if we first decide to do something about it*.

In a world of generated code the challenge is no longer creating software. **The challenge is deciding what deserves to survive, out of code created at a rate beyond human ability to evaluate it.**

Which brings us back to that text message and that now deleted database. And for my buddy, yes, he had backups, and more tokens to burn.

For one, as AI development continues to grow in speed, skill, and power, having a coding agent delete a database shouldn't end with panic – nor smug chortles from humans. Instead, it's a spot for human judgement about what AI should and shouldn't be allowed to do, and about designing the right governance and guardrails before we let full automation take the wheel. At the very least, design to contain the blast radius, so you can safely pick yourself up and try again.

But the other point is that we need our code agents to learn what to delete and why: limiting your coding agent to never delete is the wrong outcome here. Writing code is rapidly becoming the easiest part of the process. The harder skill—the one that actually shapes systems—will be deciding what to remove, what to rebuild, and what to let quietly disappear. Turns out, that's a pretty damn human decision.
