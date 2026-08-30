# Code Archaeologist — Figma handoff

This is the submission-safe design story for the implemented product. It is deliberately based on the current interface; it does not propose a redesign.

## Figma file

Create one file named **Code Archaeologist — Product Design & User Flow** with the three frames below. Recommended frame size: **1440 × 1024**. Use a 48 px outer margin and 24 px gaps.

### Frame 1 — Product Flow

**Title:** From repository URL to evidence-backed understanding

Use five connected cards in one row (or wrap after the third card):

```text
EXCAVATE → VISUALIZE → INVESTIGATE → TRACE → VERIFY
```

1. **EXCAVATE**  
   Paste a public GitHub repository. Code Archaeologist extracts real commits, files, authors, timestamps, additions, and deletions.
2. **VISUALIZE**  
   Explore the repository evolution graph and select a commit in chronological context.
3. **INVESTIGATE**  
   Ask natural-language questions. Relevant Git evidence is retrieved before any optional AI explanation.
4. **TRACE**  
   Follow the Butterfly Effect to find earlier and later commits that touched the same files.
5. **VERIFY**  
   Inspect commit hashes, changed paths, authors, timestamps, and diff statistics behind every finding.

Footer note: **The AI explains retrieved evidence; it does not invent the repository history.**

### Frame 2 — Design System

**Title:** A focused interface for software forensics

#### Color tokens

| Token | Hex | Use |
| --- | --- | --- |
| Background / primary | `#0d1117` | Page canvas and header |
| Background / secondary | `#161b22` | Inputs, panels, cards |
| Background / elevated | `#21262d` | Hover and selected surfaces |
| Border / default | `#30363d` | Dividers, controls, panel outlines |
| Text / primary | `#f0f6fc` | Headings and high-emphasis content |
| Text / secondary | `#8b949e` | Supporting copy and metadata |
| Text / muted | `#6e7681` | Labels and low-emphasis hints |
| Accent | `#2f81f7` | Ask action and keyboard focus |
| Accent / emphasis | `#58a6ff` | Links and interactive emphasis |
| Success / button | `#238636` | Primary repository action |
| Addition | `#3fb950` | Added lines and positive change |
| Deletion | `#f85149` | Deleted lines and errors |
| Warning | `#d29922` | Warnings and attention states |
| On accent | `#ffffff` | Text on filled actions |

#### Type and shape

- UI: Segoe UI / system sans-serif, 14 px base, 1.5 line height
- Evidence: Cascadia Code / system monospace for hashes, paths, and code metadata
- Radius: 6 px
- Header: 48 px high
- Content width: 1120 px maximum
- Focus: 2 px blue outline with 2 px offset
- Motion: restrained 160 ms transitions

#### Component specimens

Arrange these as a compact specimen sheet:

- **Repository input** — dark secondary surface, 1 px default border, 40 px height
- **Excavate repository** — green primary button with white semibold text
- **Ask Code Archaeologist** — blue action button paired with the investigation input
- **Commit node** — short monospace hash, message, author/time metadata, selected blue state
- **Diff statistics** — green `+ additions` and red `− deletions`
- **Evidence citation** — clickable short commit hash in accent blue
- **Panel/card** — secondary surface, default border, 6 px radius
- **Status/error** — plain status copy; error panel with a red left edge

### Frame 3 — Annotated Final Screen

**Title:** One workspace, from overview to proof

Run the app in demo mode, analyze the prepared demo repository, and capture the complete investigation workspace. Place the screenshot on the left at roughly 1100 px wide. Add these numbered callouts on the right, connected with thin `#30363d` leader lines:

1. **Repository overview** — scope and statistics for the analyzed history window
2. **Ask Code Archaeologist** — repository-wide, evidence-grounded investigation
3. **Repository evolution** — real commits arranged from older to newer
4. **Commit details** — selected change, files, author, timestamp, and diff statistics
5. **Butterfly Effect** — same-file history before and after the selected commit; correlation, not causation
6. **Archaeologist notes** — deterministic patterns found in the analyzed Git window
7. **Evidence / commit history** — searchable source material used to verify findings

Caption: **Design → implemented product. Every visible claim can be traced back to Git evidence.**

## Five-minute Figma assembly

1. Create the file and three 1440 × 1024 frames.
2. Set every frame background to `#0d1117`; use `#161b22` cards with `#30363d` borders and 6 px corners.
3. Paste the Frame 1 copy, connect the five cards with arrows, and emphasize the five verbs in `#58a6ff`.
4. Paste the Frame 2 tokens and add one small specimen for each component.
5. Paste the current product screenshot into Frame 3 and add the seven callouts above.
6. Set sharing to **Anyone with the link can view**, then replace the README placeholder.

## Submission copy

> Figma documents the implemented product flow, visual system, and final interface. The five-stage journey—EXCAVATE → VISUALIZE → INVESTIGATE → TRACE → VERIFY—connects every interaction to inspectable Git evidence.

