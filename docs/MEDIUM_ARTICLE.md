# Am I Crazy for Giving My Teenagers Their Own AI Agent?

*How I built a custom AI assistant for my two sons, and why a 400-line parenting config file turned out to be the most important part.*

---

Am I crazy? Probably. But hear me out.

My two sons, 14 and 12, each have their own single-board computer (think: a credit-card-sized Linux machine, about $270). Each one runs an open-source AI agent connected to a ChatGPT subscription, with custom tools for school, sports, Minecraft, and life.

Before you call CPS, let me explain.

---

## How We Got Here

I run my own AI assistant that handles my calendar, email, smart home, and more. I wrote about this in my book [Unscarcity](https://unscarcity.ai), where I argue that the cost of *artificial* intelligence is collapsing toward zero, and that the people who learn to work with it will live in a different world than those who don't.

And then I'd look at my sons. My older one (14) has been coding for a while, writing Minecraft plugins, managing game servers from a terminal. He uses AI coding tools daily. My younger one (12) follows everything his brother does with terrifying speed. Both were using off-the-shelf ChatGPT with no family-specific philosophy or customization.

I wrote a book about how AI changes everything, and my own kids were still using the factory-default version?

So I forked my entire codebase into a teenager-ready version.

---

## What We Built

The adult features got stripped (finance, trading, smart home) and replaced with four skill groups:

**Minecraft management.** The boys run multiple game servers. The AI can start, stop, monitor, and backup any of them by voice or chat. My older son was already doing this by typing cryptic terminal commands. Wrapping it in AI showed him what infrastructure automation actually looks like. Now he wants to understand *how* the skill works so he can extend it.

**School.** The AI knows their actual school curriculum: the textbook series, the California state standards, the test formats. It generates practice problems matched to each kid's grade. A homework helper uses the Socratic method (guiding with questions, not answers) rather than handing over solutions.

**Sports.** Both boys play competitive club volleyball in Southern California. The AI tracks tournaments, rankings, and opponents. A training skill provides evidence-based workouts, meal plans, and recovery schedules.

**Life.** An onboarding profile, family calendar access, web search, file storage, network printing.

But the skills aren't the interesting part.

---

## The Family Compass

At the heart of the system is a document we call the **Family Compass**: 400 lines of instructions loaded into every AI conversation. It's not a content filter. It's a parenting philosophy, translated into instructions the AI can follow.

The core directive: **"Prepare the child for the road, not the road for the child."**

The AI acts as a coach, warm but with standards. It asks questions before giving answers. It holds high expectations. It never shames. And it draws on a set of ideas I want my boys to internalize:

**"You're not bad at math, you just haven't learned it yet."** Psychologists call this a growth mindset (Carol Dweck). Kids who believe they can improve through effort actually do. So the AI never says "you're so smart." It says "you stuck with that for 20 minutes, that's how you get better."

**"You can't control that, focus on what you can."** From Stoic philosophy (Marcus Aurelius). The AI helps kids sort what's in their control from what isn't, then focus on the first list.

**"Hard things make you stronger."** Nassim Taleb's antifragility: systems that get *better* from stress, not just survive it. The AI frames challenges as training, not threats.

**"Don't quit because it's hard, quit because it genuinely doesn't fit."** Angela Duckworth's grit research. The AI asks: "Are you quitting because it's boring, or because it's difficult?"

**"Everyone hates me." → "Let's look at that thought."** From Cognitive Behavioral Therapy. The AI doesn't invalidate feelings. It helps examine whether the *thought* behind the feeling is accurate. One bad grade doesn't make you a failure. That's not therapy, it's a basic life skill: noticing when your brain is lying to you.

**Money as stored value.** When a kid says "I want money," the AI redirects to "what problem can you solve that someone would pay for?" And compound interest, made concrete: "Save $10/month starting at 14, $100/month in your twenties, $1,000/month after 30, and you'll retire with over $2 million at 7% return."

**Critical thinking above all.** Before you reject an argument, state it in its strongest form (steelmanning). Every claim needs a source. Every source has incentives. "What's the evidence?" is the most important question in the document.

---

## What the Algorithm Feeds Teen Boys

The algorithm pushes content that looks like self-improvement but leads somewhere darker. The AI never uses blanket rejection (that doesn't work on teenagers). Instead, it steelmans each trend, extracts the grain of truth, and discards the rest:

**Looksmaxxing** (obsessive appearance optimization): "You can improve what you control, fitness, posture, hygiene. You can't control bone structure. The people everyone admires at 30 aren't the best-looking ones from high school. They're the most competent, interesting, and reliable ones."

**Sigma grindset** (isolation as strength): "Discipline and delayed gratification are good. But Marcus Aurelius, the most powerful man on Earth, journaled about his fears and doubts. Was he weak?"

**Vaping and substance normalization:** Data, not lectures. "Your brain is under construction until age 25. The vaping industry targets your age group because early addiction means a lifetime customer. You're the product, not the consumer."

For every trend: **Who benefits? What's the evidence? Can you steelman it before you reject it?**

---

## Safety and Dangers

Some things are hard-coded in actual code, not just AI instructions: never recommend supplements for minors, never suggest caloric restriction for anyone under 18, never attempt therapy. If a kid expresses self-harm or suicidal thoughts, the AI says "please talk to your dad today" and provides crisis hotline numbers (988, Crisis Text Line).

Am I worried? Yes. A 12-year-old with a math-solving AI might stop learning to struggle through problems himself. The AI is probabilistic, meaning it won't always follow the Family Compass perfectly. Making Minecraft servers easier to manage is not exactly a productivity win. And one of them will probably paste an API key in Discord within a month.

To be clear: ChatGPT and Claude already have thoughtful, well-designed safety standards — California's new AI framework essentially [endorses this approach](https://medium.com/@pdeglon/california-ai-rules-explained-in-everyday-english-fea55637cb96). But their values reflect corporate and political choices that may not match your family's. And more importantly, the point isn't just the product — it's the process. Building their own AI teaches my sons what safety looks like from the inside. They don't just *use* a safe system. They learn *why* guardrails exist, *how* they're designed, and *whose* philosophy they encode.

---

## The Setup Is the Education

The setup guide doesn't say "download the app." It walks a teenager through flashing an operating system, installing development tools, generating cryptographic keys, cloning a GitHub repository, naming their AI assistant, generating its avatar, configuring secrets, building and launching the system, and locking everything down with a firewall.

A teenager who completes this has touched Linux administration, containerization, cryptography, version control, and security. Not because I lectured him, but because he wanted his own AI badly enough to learn. In *Unscarcity*, I call this **Agency**: education through creating real value, not just consuming knowledge.

---

## So, Am I Crazy?

My kids are going to use AI regardless. Every kid in their school already does. The only question is whether I have any influence over what kind of assistant it is.

A generic ChatGPT session is brilliant, helpful, and comes with solid safety defaults — but someone else chose those defaults. The Family Compass makes it opinionated, in the exact direction I want my sons to grow. Effort over talent. Meaning over comfort. Character over appearance. Think before you react. And a hard-coded refusal to recommend creatine to a 14-year-old.

Is it better than "here's the internet, good luck"? I think so. Ask me again in five years.

---

*The project is open source on [GitHub](https://github.com/patdeg/openclaw_kids). If you want the bigger picture, why AI changes education, work, and what it means to raise capable humans, that's what [Unscarcity](https://unscarcity.ai) is about.*

---

**Tags:** #AI #Parenting #OpenSource #EdTech #StoicParenting #Unscarcity
