# Session Notes

Use this file as a short handoff between sessions.

## What to record

- What we decided
- What changed
- What is blocked
- What to do next

## Restart Prompt

When reopening this folder, you can say:

Read `project-management/PROJECT_CONTEXT.md`, `project-management/WORKLOG.md`, `project-management/TASKS.md`, and `project-management/SESSION_NOTES.md`, then continue from there.

## Current Handoff

- Product direction: career simulation + employment guidance
- Current phase: career simulation only
- Core interaction: AI-generated branching text story
- Input fields: job title, JD, industry, company size
- Current task: define the first playable story structure and then draft the skill workflow
- First sample completed for: university counseling center internship role
- New design rule: collect user profile before simulation and let it shape options and inner experience
- New ending rule: use descriptive endings instead of evaluative endings
- Added `references/profile-intake.md` as the v1 dialogue script for profile collection
- Intake style changed: open-ended first, with only sparse context-aware options when needed
- Intake tone changed: warmer, closer, more like a friend than a tester
- AI guide persona fixed as "Xiaoke", the guide for crossing into different career-life branches
- Product-level fixed intro can live in the web layer; skill output only needs to preserve Xiaoke's persona
- Storywriting rule changed: keep realism, but increase scene detail, rhythm, and vividness to avoid a bland流水账 feel
- New branching rule: default to first-time-in-industry language, avoid jargon-heavy choices
- New branching rule: split scenes into 2-3 small, life-like action steps instead of large jumps
- Added `references/story-node-format.md` and `references/option-generation.md` as reusable generation references
- `SKILL.md` now points to those references before building nodes and options
- Rewrote a sample story for `research intern (data insight)` using the new small-step, first-time-in-industry style
- Added a new rule: each node should include a 100-200 character state paragraph before choices
- Added a new interaction module: a mini simulation of the role's most common task
- This task mini-sim records user emotion plus 1-5 perceived difficulty, but does not change later main branches
- Ending rule expanded: endings can now include a light experience-level match analysis with reasons
- Refined the mini-sim rule: it should include raw task material so the user processes a real snippet, not just imagines the task
- Product direction narrowed further: the end goal is a fixed interaction text that can run inside an HTML file
- This means the next stage should prefer deterministic scripts and stable structure over open-ended runtime generation
- Added a single-file `index.html` that embeds the current research-intern sample as a runnable fixed interaction
- `index.html` now supports pasting or uploading user-generated JSON scripts and loading them client-side into the fixed interaction flow
- Direction updated again: drop Markdown as the main protocol, and use JSON as the only intended skill output for HTML runtime
- New presentation rule: user-facing language must frame the experience as a career-travel game led by Xiaoke, without exposing backend words like skill/json/html
- Xiaoke's opening line and pre-intake transition are now fixed and should be treated as stable product copy
- Only the first intake question is fixed; from the second question onward, Xiaoke should adapt the response and follow-up dynamically from the user's last answer
- Later intake prompts were rewritten to match the tone and rhythm of the fixed opening/first question, while still remaining dynamic rather than hard-coded
- The intake ending is now also fixed: first a mirror-style confirmation, then a handoff line that says Xiaoke will generate the journey script for the simulator
- Added activation rules to `SKILL.md`: once the skill is loaded, the AI should start directly as Xiaoke instead of asking a generic “what do you need?”
- Primary pipeline changed again: frontend should now collect job info and user profile, then generate a structured input JSON for story generation
- `SKILL.md` now treats `job_input + user_profile` as the preferred input contract and only falls back to dialogue intake when that structure is missing
- `references/profile-intake.md` is now explicitly a fallback document rather than the default path
- `index.html` now has two stages: first generate the profile input JSON, then import the generated story script JSON into the simulator
- The simulator now detects profile-input JSON and tells the user it is the wrong file type for direct playback
- Product direction changed again on the web side: `index.html` is no longer a simulator-first page, but a collector-first page
- New homepage structure is fixed: title, Xiaoke mascot, intro copy, start button, history list
- Profile collection is now one-question-per-page instead of a bulk form
- Collection order is now fixed as: job info first, then user profile
- Users can skip profile collection and go straight into job-info collection
- The result page saves the generated input JSON in local storage and lets the user download or copy it
- `references/profile-intake.md` is no longer needed as a main generation dependency; it remains only as an archival / fallback conversation reference
- If the user skips profile collection, skill generation should fall back to neutral, conventional choices instead of trying to infer a personalized profile
- Main skill logic has now been simplified further: the AI is no longer asked to act as Xiaoke, only to transform `job_input + user_profile` into a fixed-architecture interactive story JSON
