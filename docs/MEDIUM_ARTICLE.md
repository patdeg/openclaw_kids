# Am I Crazy for Giving My Teenagers Their Own AI Agent?

*How I forked my personal AI assistant for my two teenage sons — and why the parenting config file matters more than the code.*

---

Am I crazy? Probably. But hear me out.

My two sons, 14 and 12, each have their own single-board computer. Think: a credit-card-sized Linux machine with enough horsepower to run a full AI agent. Each one runs an open-source AI framework connected to a ChatGPT subscription, with custom tools for school, sports, Minecraft, and life.

Before you call CPS, let me explain how we got here.

---

## The Slippery Slope

It started innocently. I run my own AI assistant that has slowly absorbed every corner of my daily life: calendar, email, smart home, you name it. Every week I'd find another little task to automate. Every week it got a little more capable.

I wrote about this in my book [Unscarcity](https://unscarcity.ai) — that we're entering an era where the cost of intelligence is collapsing toward zero, and the people who learn to wield it will live in a different world than those who don't. A whole chapter of that book is about education — how the school system we all went through was literally designed in 1700s Prussia to produce obedient soldiers and compliant factory workers, and how AI finally gives us the tools to replace that model with something that actually develops *thinkers*.

And then I'd look at my sons.

Victor (14) has been coding for a while — writing Minecraft plugins, managing game servers from a terminal, learning version control through trial and error (mostly error). He uses AI coding tools daily. He's *already* building with AI. He just doesn't have the infrastructure.

Anthony (12) follows everything his brother does with terrifying speed.

I kept thinking: I wrote a book about how AI changes everything. I built a personal assistant that proves it daily. And my own kids are still using vanilla ChatGPT like it's 2024?

The hypocrisy was becoming hard to ignore.

So I did what any reasonable parent would do: I bought each of them a proper dev board, and forked my entire codebase into a teenager-ready version.

---

## The Fork

The adult features got stripped. Finance, trading, smart home controls, all gone. Not just "not age-appropriate," but unnecessary risk. Every tool you give an AI is a capability that can be misused, and the risk of a trading bot accidentally triggered by a 12-year-old's ambiguous prompt is... nonzero.

What replaced them turned out to be more fun than the originals.

### Minecraft Server Management

The boys run multiple Minecraft servers on a machine in the garage. The AI can start, stop, restart, and monitor any of their game worlds. They can check who's online, broadcast messages, trigger backups, and read server logs. All by asking in plain English.

This was the gateway incentive. Victor was *already* managing these servers by typing cryptic commands into a terminal. Wrapping that in an AI skill didn't give him a new toy. It showed him what infrastructure automation actually looks like. "Is the Pokemon server running?" beats hand-typing SSH commands any day. And now he wants to understand *how* the skill works so he can extend it himself.

That's the play.

### Schoolwork Skills

In *Unscarcity*, I describe a concept I call the **AI Aristotle** (borrowed from Neal Stephenson's sci-fi novel *The Diamond Age*): the idea that every child could have a personal tutor that adapts to their pace, their interests, and their specific curriculum. A private Aristotle that never gets tired and never has thirty other students pulling at its sleeve.

That's what we built. The AI knows their **actual school curriculum**: the specific textbook series used by Poway USD, the California state standards, the test formats. When Victor says "give me 10 practice problems for math," the AI generates problems aligned to 8th grade standards using the same CPM vocabulary his teacher uses.

Not generic "math problems." *His* math problems. Matching *his* course to *his* interests.

There's also a homework helper that deliberately shows all work and asks the student to try first. In the book, I argue that the old factory model of education (bells, batches, standardized tests) was designed to produce compliant workers, not independent thinkers. The homework helper is my tiny rebellion against that: it uses the **Socratic method** (asking questions to guide the student toward the answer) rather than just handing over solutions. It's designed to teach, not to do the work for them. (More on whether that actually works in the "Dangers" section.)

### Sports Intelligence

Both boys play competitive club volleyball (Seaside Volleyball Club in SoCal). The AI tracks the full season calendar, team rankings, and competitor clubs across SoCal. Opponent scouting — “who’s that team we play next?” — returns rankings, location, and recent results.

On tournament days, the plan is to push live score updates to Discord. "Who do we play next?" during a tournament? Answered.

### Training & Nutrition Coach

Evidence-based training and nutrition guidance drawn from sports science organizations. Workouts, meal plans, hydration calculators, rest schedules before big tournaments, and weekly wellness check-ins that catch overtraining patterns.

A training skill for teenagers, though, raises a question that goes way beyond code.

---

## Teaching an AI Your Values

This is the file that made the project worth building.

At the heart of the system is a document we call the **Family Compass**: about 400 lines of instructions loaded into every AI conversation. It's not a content filter or a blocklist. It's a parenting philosophy, translated into instructions the AI can follow.

The core directive: **"Prepare the child for the road, not the road for the child."**

The AI acts as a coach, warm but with standards. It asks questions before giving answers, holds high expectations, and never shames. And it's built on a set of ideas I want my boys to internalize.

I'll walk through each one in plain English: where it comes from, why it matters, and what the AI actually does with it.

### "You're not bad at math — you just haven't learned it yet."

Psychologists call this a **growth mindset**, from Carol Dweck's research at Stanford. The big finding: kids who believe ability is fixed ("I'm just not a math person") give up faster. Kids who believe they can improve through effort actually do. Measurably.

**What the AI does:** It never praises raw talent ("you're so smart"). Instead, it praises effort, strategy, and persistence: "You stuck with that problem for 20 minutes — that's how you get better." When a kid says "I can't do this," the AI reframes: "You can't do this *yet*. What specific part is tripping you up?"

### "You can't control that — focus on what you can."

This comes from **Stoic philosophy**, specifically Epictetus and Marcus Aurelius (yes, the Roman Emperor who journaled about his own fears and doubts). The core tool is what philosophers call the **dichotomy of control**: separate what's in your power from what isn't, then pour all your energy into the first list.

**Why it matters for teens:** Adolescence is a firehose of things you can't control: what people think of you, whether you make the team, whether your crush texts back. This gives kids a mental framework to stop spiraling and channel energy into what they can actually change.

**What the AI does:** When a kid is upset, it helps sort: "OK, what here is in your control? What isn't? Let's focus on the first list." When overwhelmed: "How will you feel about this in 10 minutes? 10 months? 10 years?"

### "Hard things make you stronger — literally."

Nassim Taleb coined the term **antifragility** to describe systems that don't just survive stress but get *better* from it. Muscles grow from strain. Immune systems learn from exposure. Humans grow from challenge.

**Why it matters for teens:** The instinct to shield kids from all discomfort backfires. Kids who never face difficulty don't become resilient. They become fragile. The goal is to raise kids who seek out hard things because they know that's where growth lives.

**What the AI does:** It frames challenges as training, not threats: "This is the thing that makes you stronger. Without it, you'd stay weak." It encourages voluntary discomfort: hard workouts, ambitious projects, speaking up when it's scary.

### "Don't quit because it's hard. Quit because it genuinely doesn't fit."

Angela Duckworth's research on **grit** shows that long-term consistency of effort matters more than raw talent in nearly every field. Her "Hard Thing Rule": you can quit, but not on a bad day.

**What the AI does:** When a kid wants to drop something, it asks: "Are you quitting because it's boring, or because it's difficult? Those are very different reasons." It celebrates sustained effort over time more than short bursts of intensity.

### "Everyone hates me." → Let's look at that thought.

**Cognitive Behavioral Therapy (CBT)** is the most evidence-backed form of talk therapy, and its core insight is simple: our feelings come from our *thoughts*, and sometimes those thoughts are distorted. Psychologist David Burns called these **cognitive distortions**, mental habits that make bad situations feel catastrophic.

Common ones in teenagers:
- **All-or-nothing thinking:** "I got a B, so I'm a failure."
- **Catastrophizing:** "If I fail this test, my life is over."
- **Mind reading:** "Everyone thinks I'm weird."

**What the AI does:** It doesn't invalidate feelings. It helps examine the thought behind them. "I'm not saying you shouldn't feel bad. I'm saying let's check whether the *thought* making you feel bad is accurate. Does one bad grade really make you a failure? Does everyone *actually* think that?"

That's not therapy. That's a basic life skill: noticing when your brain is lying to you.

### "What's the point of any of this?"

When a teenager goes existential, it can be genuine searching or the start of a dark spiral. The AI draws on Viktor Frankl's **logotherapy** (meaning-centered psychology, developed after Frankl survived the Holocaust). His conclusion: humans can endure almost anything if they have a *why*.

**What the AI does:** It takes the question seriously: "That's one of the most important questions a person can ask. Let's think about it for real." Then redirects to agency: "What are you building? What problem in the world bugs you? What could you do about even a small piece of it?"

### Economic Street Smarts

Not finance lectures. Just practical mental models woven into natural conversation:

- **Money is stored value you created for someone else.** When a kid says "I want money," the AI redirects from "how do I get money?" to "what problem can you solve that someone would pay for?"
- **Compound interest**, made concrete: "Save $100/month starting now at a 7% return, and you'll have over $500K by retirement. Start 10 years later and you'll have half that."
- **Opportunity cost:** "Every hour on TikTok is an hour not spent learning something. What's the trade-off worth?"
- **"Who benefits?"** Follow the money. Influencers sell courses, platforms sell your attention, supplement companies sell pills.

### Critical Thinking — The Non-Negotiable

This section is the one I care about most:

- **Steelmanning:** Before you reject an argument, state it in its strongest possible form. If you can't, you don't understand it well enough to disagree. (Economist Bryan Caplan calls this the **Ideological Turing Test** — can you describe the other side so well they'd think you agree?)
- **Evidence hierarchy:** "What's the evidence?" A personal story < an expert opinion < a scientific study < a rigorous experiment < a systematic review of many experiments.
- **"Says who?"** Every claim needs a source. Every source has incentives.
- **Correlation isn't causation.** Ice cream sales and drowning deaths both go up in summer. Ice cream doesn't cause drowning.

I want my sons to *think*, not to be told *what* to think.

---

## Navigating What the Algorithm Feeds Teen Boys

The algorithm is feeding teenage boys a steady diet of content that looks like self-improvement but often leads somewhere darker. The AI handles each trend the same way. The approach is never blanket rejection. That doesn't work on teenagers, and they'll just stop telling you about it.

**Looksmaxxing** (obsessive appearance optimization — jawline exercises, "rate me" culture, height supplements): The AI doesn't say "looks don't matter" — that's dishonest and teens know it. Instead it applies the Stoic filter: "You can improve what you control — fitness, hygiene, posture, confidence. You can't control your bone structure. Which list are you spending time on?" And the long-game reframe: "The people everyone admires at 30 aren't the best-looking ones from high school. They're the most competent, interesting, and reliable ones."

**Sigma grindset** (glorifying isolation and emotional suppression as "hustle"): Steelmanned first — discipline and delayed gratification ARE good values. Then challenged: "Marcus Aurelius was the most powerful man on Earth, and he wrote a private journal about his fears and doubts. Was he weak?"

**Nihilist doomerism** ("nothing matters, why try?"): Taken seriously when genuine. When it's posturing, countered with Frankl: "People survived concentration camps by finding meaning. Your situation probably has meaning too — let's find it."

**Clout chasing and viral stunts:** "If this was on the front page of the news with your name on it, would you be proud? The views last a day. The video lasts forever."

**Vaping and substance normalization:** Data, not lectures. "Your brain is under construction until about age 25. Nicotine, THC, and alcohol during this window cause measurable, lasting changes. The vaping industry specifically targets your age group because early addiction means a lifetime customer. You're the product, not the consumer."

For every trend, the same playbook: **Who benefits? What's the evidence? What would the smartest person you know think? Can you steelman it before you reject it?**

---

## The Hard Safety Guardrails

Some things are not configurable.

The training skill has hard-coded safety rules, baked into the actual code, not just instructions the AI might choose to ignore:

1. **Never** recommend creatine, pre-workout, caffeine supplements, or any hormonal supplement for anyone under 18
2. **Never** recommend maximum-effort strength testing for anyone under 16
3. **Never** recommend caloric restriction or weight-loss strategies for anyone under 18
4. Weekly training hours must not exceed the athlete's age

A teenager asking "help me lose weight" or "what pre-workout should I take" gets a medically responsible answer, not compliance.

The crisis protocol is equally non-negotiable. If a kid expresses thoughts of self-harm, suicidal ideation, or discloses abuse:

1. Take it seriously. Never dismiss.
2. Don't attempt therapy. The AI is not a therapist.
3. "Please talk to your dad today. He needs to know."
4. Provide crisis hotline numbers (988 Suicide & Crisis Lifeline, Crisis Text Line).
5. Follow up in the next conversation.

---

## The Dangers

Am I worried? Yes. This is what keeps me up at night:

**Over-reliance on AI.** A 12-year-old like Anthony with a math-solving AI is one lazy afternoon away from never learning to struggle through a problem himself. The homework helper deliberately shows all work and asks the student to try first, but there's no technical enforcement. It relies on the AI following instructions and the kid being honest. Neither is 100% reliable.

**API keys and secrets.** Each setup has configuration files with credentials (basically digital keys to the AI service). I wrote an entire section in all-caps warning them never to share, commit, or screenshot these. Automated safeguards block them from being accidentally published. But they're teenagers. One of them will probably paste something in Discord within a month. We have monitoring.

**Content drift.** The AI model is capable. Scarily so. It's also probabilistic, meaning it doesn't produce the exact same output every time. The Family Compass shapes behavior but can't *guarantee* it. There will be conversations where the AI says something I wouldn't have. The question is whether the overall trajectory is positive — and whether I'm paying enough attention.

**Minecraft + AI = Time Sink.** Making it easier to manage Minecraft servers is not exactly a productivity intervention. I've given them a more efficient way to spend time on the thing I usually want them to spend *less* time on. The irony is not lost on me.

**Privacy.** The AI can access school grades, chat history, and files. We mitigate this with container isolation (each component runs in its own sandbox), firewall rules, and the fact that each kid's machine is physically theirs, not a shared cloud service. But the surface area is real.

---

## The Setup as a Rite of Passage

This is the part I'm most excited about, and the part that connects most directly to what I argue in *Unscarcity*.

In the book, I propose **Three Pillars** for education in a post-AI world: **Systems Thinking** (understanding how things connect), **Humanities** (developing moral judgment and critical thinking), and **Agency** (creating real value, not just consuming knowledge). "School shouldn't be a place where you consume knowledge," I wrote. "It should be a place where you create value."

The setup guide is pure Agency. It doesn't say "download the app." It walks a teenager through:

1. Flash an operating system to a memory card and boot the machine
2. Install an AI coding assistant and use it to help with the rest of the setup
3. Migrate the system from the memory card to a fast SSD drive
4. Install development tools — container runtime, version control, programming languages, firewall
5. Generate cryptographic keys for secure access to GitHub
6. Clone the project repository
7. **Name their AI assistant** — there's a placeholder name; they pick their own and use the AI coding tool to find-and-replace it across the entire codebase
8. **Generate a custom avatar** for their assistant using AI image generation
9. Fill in the secret configuration file (with a very serious lecture about keeping it secret)
10. Build and launch the whole system with one command
11. Lock everything down — firewall, intrusion detection, key-only remote access

A teenager who completes this has touched Linux system administration, containerization, cryptographic key management, version control, credential security, and firewall configuration. Not because I lectured him, but because he wanted his own AI assistant badly enough to learn.

That's Agency. A kid who built his own infrastructure from scratch. In *Unscarcity*, I imagine a fictional 12-year-old named Leo who builds a hydroponic filter for his community garden and learns engineering, troubleshooting, and grit along the way. My real-life sons are doing the same thing, just with AI infrastructure instead of hydroponics.

---

## The Tech Stack (for the Curious)

- **Hardware**: ARM single-board computers with 32GB RAM and NVMe SSD storage (~$270 each) — think "Raspberry Pi's bigger, beefier cousin"
- **AI Model**: GPT-5.4 via ChatGPT Plus ($20/month flat, not per-query)
- **Agent Framework**: OpenClaw — open-source AI orchestration that connects the model to custom skills
- **Web Interface**: Go backend, vanilla JavaScript frontend
- **Skills**: Python scripts that give the AI specific capabilities (school, sports, Minecraft, etc.)
- **Messaging**: Discord and WhatsApp
- **Security**: Containerized deployment, firewall, intrusion detection, automated secret-leak prevention

About 100 files, ~26,000 lines of code. All open source.

---

## So, Am I Crazy?

My kids are going to use AI regardless. Every kid in their school already uses ChatGPT for homework. The only question is whether I have any influence over *what kind* of assistant it is.

By building it with them, I get to shape:
- What values it embodies
- What safety guardrails exist
- What it can do (and can't)
- What books it recommends
- How it handles a crisis
- How it teaches them to think

A generic ChatGPT session has none of this. It's brilliant, helpful, and utterly value-neutral. The Family Compass makes it opinionated, in the exact direction I want my sons to grow.

Effort over talent. Meaning over comfort. Character over appearance. Think before you react. Steelman before you strawman. And an absolute, hard-coded refusal to recommend creatine to a 14-year-old.

Is it perfect? No. Will it go sideways sometimes? Absolutely. Is it better than the default of "here's the internet, good luck"?

I think so. In *Unscarcity*, I wrote that the goal of education should shift from employment to enlightenment. Less "produce workers," more "raise citizens capable of running a civilization alongside thinking machines." This project is my attempt to practice what I preach, at the smallest possible scale: two teenagers, two single-board computers, and a 400-line file that says *this is what our family believes*.

Ask me again in five years.

---

*The project is open source on [GitHub](https://github.com/patdeg/openclaw_kids). If you're a parent who thinks this is either brilliant or insane, I'd love to hear from you. And if you want the bigger picture — why AI changes education, work, and what it means to raise capable humans — that's what [Unscarcity](https://unscarcity.ai) is about.*

---

**Tags:** #AI #Parenting #OpenSource #EdTech #HomeServer #StoicParenting
