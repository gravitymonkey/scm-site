---
title: About this site
slug: about
author: jason
date: 2026-03-11T16:29:32+00:00
updated: 2026-03-15T17:27:47+00:00
schema_type: AboutPage
excerpt: "I have a confession that will resonate with anyone who has spent time doing software engineering: for most of the history of the profession, the bottleneck was me."
---
![monkey playing the piano](/assets/images/of4Vf-monkey-playing-bach.png)

I have a confession that will resonate with anyone who has spent time doing software engineering: for most of the history of the profession, the bottleneck was me. Well, not just me, I mean more like us, the humans. Specifically, the painful, glorious slowness with which humans write and read code — line by line, review by review, architecture debate by architecture debate, tabs versus spaces (tabs, ffs, always).

It become so much a part of the culture that many of the coder humans that grew into management felt that slowing everything down was the primary task. That friction was annoying. Sometimes product-hurting or company-killing.

The difficulty of producing code meant that the difficulty of *understanding* it served as a natural constraint. You couldn't really change a system faster than the humans could comprehend what they were changing, cowboy-coding-be-damned. Complexity had weight you could feel. Deployment rituals, code reviews, the whole ceremony of shipping software — these weren't bureaucratic superstition. This was more like some kind of evolutionary selection pressure, but hidden in passive-aggressive PR comments.

Then AI showed up and made code cheap, and, well, crap, now we have a fresh problem.

AI is not great at understanding what your system needs to become. It is extraordinary at producing code once someone has figured that part out. These are different skills, and only one of them has collapsed in cost.

The complexity hasn't gone anywhere. Dependency management doesn't simplify because generation got easier. Failure modes don't politely Homer-into-the-hedge. Architectural coupling — the beautiful, terrible tangle of decisions that propagate through every service and data pipeline — remains exactly as fragile as it ever was. It actually gets more fragile faster, because the rate of change just left the atmosphere without a plan for controlled descent.

In music, for example, variation is easy and cheap. Give Bach a theme and he could unfold it into dozens of transformations—shifted in rhythm, inverted, stretched, broken apart and recombined. But variation alone does not produce music. Composition happens only when someone decides which variations matter and which ones are trash. Remove that selection and you do not get development, you get a bunch of mindless noodling. That's why concerts aren't (usually) filled with someone just fingering scales.

Software is entering the same dynamic, which brings us to our title.

For years, programmers used "code monkey" as the anxious punchline of their own imposter syndrome — the fear of being revealed as nothing more than a mechanical syntax producer, an expensive keyboard in a hoodie. AI has turned that anxiety sideways. The monkeys have arrived. Some claim AI is nothing but a "stochastic parrot", but I don't believe that holds at all, and certainly not for code. My buddies may be stochastic code monkey agents, generating code endlessly, with admirable enthusiasm and vigor and no particular stake in the outcome.

The scarce skill in this environment is no longer writing code.

It's designing the selection mechanisms — the evaluation gates, rollback policies, architectural guardrails, and operational boundaries that determine which mutations and variations persist and which ones die quietly in a feature branch or get kicked to the curb before a human even sees it. If you're a dev who evolved out of the expensive-keyboard-in-a-hoodie role, and "elevated" to engineering leadership in any form, you'll hopefully recognize that's it: that's the whole gig, right there. We are no longer writing code for systems, we're creating a system to write code, and then to run it and manage it safely, over time.

**Stochastic Code Monkeys** is about that problem. How do you govern the evolution of software systems when generation is no longer the bottleneck? What does it mean to be an engineer when the hard part shifts from producing code to shaping the environments where code is allowed to survive?

The monkeys will write anything you ask, enough to rocket you into space.

The question is what you let ship. And knowing how to have a safe landing.
