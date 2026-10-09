---
name: figma-mapping-interview
description: Use when a Figma design must be tied to the DOM elements of a real screen so that style verification can run — reads a design fingerprint, works out which nodes are worth asking about, proposes a mapping, and writes it only after the developer decides. Also use when an existing mapping stops matching the screen.
---

# Figma Mapping Interview

Tie each Figma node to the element that renders it, so a runner can compare the design's values
against the browser's computed style.

**The tool proposes. The developer decides.** Which element a design node became depends on design
intent, and a fingerprint holds only coordinates and values.

## The Figma tree is not the DOM tree

This is the fact the whole skill is built around, and it is measured, not assumed. Figma's tree
belongs to a drawing tool: groups that auto-layout created disappear when the design becomes HTML,
and that is correct rather than a defect.

On one measured screen:

| Design says | Screen has |
|---|---|
| a row holding 1 group | 3 sibling elements |
| a 3-part info group | 2 elements |
| a 4-button footer | 2 buttons |

Nine of that screen's **twenty-one** nodes had no element at all — the fingerprint holds 21 nodes
and the mapping 12 entries. A mapping check that treats a missing element as an error stops on all
nine, and none of them is a bug.

(The check reported 23 *findings*, not 23 nodes: one node appears once per contract it breaks.
Dividing nine by the finding count would make the ratio look better than it is.)

## Two moments, two halves

| When | What is decided | Why then |
|---|---|---|
| before implementation | which node becomes which component, and **which nodes become no element** | it answers *what shall we build*, and it doubles as an instruction to whoever builds it |
| after implementation | the CSS selector | `.comment-item:first-of-type` was expected to match one element and matched five. You cannot count matches on a screen that does not exist |

The component half is nearly free when a planning step already named the file. What is worth
writing down is the second column — the nodes that deliberately get no element. Without that
list, a later reader cannot tell an intended absence from a mapping mistake.

**The before-implementation half has not been exercised yet.** Every measurement here comes from
mapping onto code that already existed. Treat it as reasoned, not proven, and say so when you use
it. What would settle it: write the "these nodes get no element" list at design time, then check
after implementation how many were wrong.

## Choose what to ask, do not answer it

Asking about every node exhausts the person answering. Mechanical judgment is for narrowing the
list. On the measured screen this turned nine questions into three.

| Situation | Do |
|---|---|
| an **unmapped** node whose contract values are character-identical to exactly one mapped node | propose that element and take a confirmation — do not make it a question. Only when there is exactly one such candidate; two candidates is a question again |
| two nodes collapse onto one element **and** either their contract values differ, or a contract measures the distance between them | a finding, not a question. One element cannot satisfy 15px and 13px at once; and a distance across a collapse is always 0, so even matching values leave the judgment vacuous. Collapses that trip neither condition are legitimate and pass |
| a group of same-natured nodes | one question for the group. The group key is `(nearest mapped ancestor, kind)` — see below |
| a node carrying only `reference`-grade values that is no distance endpoint | contributes to no judgment — do not ask |

The first row compares against the fingerprint, not the screen: an unmapped node has no element
yet, so what you can observe is that it *would* collapse, not that it did.

### The nearest mapped ancestor, and why kinds are checked in order

The grouping ancestor comes from the **component-nesting chain inside the node id**, not from the
design tree: `I<a>;<b>;<c>` is c inside instance b inside instance a. Trim one segment at a time
(`I<a>;<b>;<c>` → `I<a>;<b>` → `<a>`) and stop at the first id the mapping already has. Without
this rule the same screen groups differently on different days.

The three kinds are decided **in this order, and the order carries meaning**:

1. **inside a component** — the path to the mapped ancestor crosses a component boundary nobody
   mapped, two or more layers deep
2. **never drawn at all**
3. **absent in this screen's state**

Check the first one first. A node inside a component states contracts of its own — the `Main`
inside a design-system button declares its own 8px sides — so reversing the order reads every
"not this screen's concern" as "never drawn", and this screen ends up owning the insides of
somebody else's component.

**Narrowing reduces questions, not the mapping.** A node that was answered with a proposal, or
skipped as contributing to no judgment, is still unmapped — and the generator skips an unmapped
node whole, so its contracts are judged nowhere. Unmapped nodes block whether or not any questions
remain. Zero questions is not a pass.

What survives is the part that genuinely needs a person:

1. this group has no element — what do we measure the design's 16px against instead?
2. is this node missing only on this screen, or not built at all? (one screen cannot tell)
3. do we verify the inside of a design-system component on this screen?

## Process

1. Read the fingerprint for the target node and viewport. Every item carries a grade: `contract`
   (the value must match), `relation` (two places must agree), `reference` (not judged).
2. Open the screen if it exists. Without it you can do the structure half only.
3. Narrow the node list with the table above. Report how many nodes you started from and how many
   questions remain — the ratio is the evidence that the narrowing worked.
4. Put the remaining questions to the developer, grouped, with your proposal for each.
5. Write the mapping only after the answers come back.
6. Verify each claim before handing off (see below). Report failures as *setup blocked*, not as
   design defects.

## A mapping is a claim, and claims get falsified

"This selector's element is that Figma node" is a person's assertion, not something the tool
proved. If it is wrong the runner measures the wrong element and reports the result as a design
judgment — a silent wrong answer, the most expensive failure available here.

You cannot prove it. You can falsify it. Six checks run, but **one of them is not a falsification
at all** — `completeness` asks a question rather than refuting a claim, and it is the one the nine
blocked on. Keep it separate when you report, or a question reads as a defect.

| Check | What it looks at |
|---|---|
| completeness — **asks, not falsifies** | every fingerprint node has a selector. Unmapped nodes become the questions in the section above |
| uniqueness | the selector matches exactly one element — 0 means a typo or a changed screen, 2+ means nothing is pinned down |
| containment | a child node's box sits inside its parent node's box; Figma's containment survives a different CSS structure |
| magnitude | the size is not off by an order — 40×40 against 198×40 is a different element |
| order | reading order matches the design |
| collapse | two nodes point at one element only where that breaks something — differing contract values, or a contract measuring between them. Compare the elements, **not the selector strings**: `#x` and `div#x` are different strings and the same element. Judging the string instead lets the same legitimate collapse pass or fail depending on how someone typed the selector |

Two ways the checks went quiet while reporting zero problems, both found and closed: a 0×0 box
with no place on screen passed all six, and the string-only collapse comparison above. A
falsification device that cannot falsify is worse than none, because it reports success.

What still escapes them: elements interchangeable under every check, such as same-sized icons side
by side under one parent. Say so rather than implying the mapping is verified.

## Output

The mapping file lives in the **E2E asset repository** next to the fingerprint, not in a personal
note vault — the runner reads it and QA and CI have no vault. One entry per node:

```yaml
- node: "https://www.figma.com/design/<fileKey>/<name>?node-id=I8060-17975;8013-21679"
  viewport: mobile
  variant:
    Property 1: "커피"
    theme: "light"
  runtime:
    Property 1: "gift_item.ice_cream"
    theme: null
  component: src/pages/...               # often already known from the task's target_files
  selector: ".comments-panel__wrap > div:first-child .comment-item"
  path: /test/comment/gift
```

`node` takes the **whole Figma URL**, not a bare node id — the loader rejects `"8060-17975"`. The
file key has to be checked against the fingerprint's, so that a mapping and a fingerprint pointing
at different files cannot go unnoticed.

`runtime` gives each variant property the value it takes at run time, and the loader rejects the
entry if it is missing. The Figma name and the runtime value are not the same thing: the same
product was written 치킨 in the requirement and 치맥 in the design. `null` means *not chosen on
this screen* and is deliberately different from leaving the key out — the same distinction this
skill insists on everywhere else, already built into that field.

### Recording a node that has no element

`selector` and `absent` are **exclusive, and one of them must be there.**

```yaml
  path: /test/comment/gift          # required even with no element
  # component is optional only here — naming a file that does not draw it would be a lie
  absent:
    kind: 안그림                     # 안그림 | 상태 | 부품속
    why: "구현은 아바타·본문·하단을 묶는 행 래퍼를 쓰지 않는다"
    instead:                        # 안그림 only; the loader rejects a missing edge
      left:   "…?node-id=I8060-17975;8013-21679"
      top:    "…?node-id=I8060-17975;8013-21679"
      right:  "…?node-id=I8060-17975;8014-18551"
      bottom: null                  # a loss that was **decided**, not overlooked
```

The three `kind` words are the same words the runner uses for its questions, so a question and its
answer are written alike.

`path` stays required with no element, because *absent in this screen's state* is a statement
about a screen — without saying which screen, it means nothing.

`instead` belongs to `안그림` alone. The other two must not carry it: a `상태` node reappears on
another screen and a `부품속` node belongs to the component's own screen, so re-pointing it here
would be the wrong answer rather than a missing one.

Its keys are edges and axes (`left right top bottom x y`). If any edge of a *judged* distance that
used this node as an endpoint is left out, the loader stops and names the edge. `null` passes,
because it is a loss someone chose, and coverage counts it.

**Making omission impossible beats counting omissions.** The loader refuses what was left out; what
remains is a decided loss, and that gets counted. Those are different things and only the second
one is safe to let through.

**The re-pointing answer is not always unique.** Measured: the design's right-hand 16px was 16px to
both the body and the footer. The body was chosen because it never disappears, but a short comment
could make that wrong. When you propose a re-point, say the alternatives you did not take.

The three kinds answer the three questions above one for one:

| Kind | Example | Why it cannot share a slot |
|---|---|---|
| never drawn at all | the row that groups avatar and body — the implementation does not use that wrapper | **the contracts that used this node as an endpoint have to be re-pointed, and where to must be written down.** Otherwise the design's 16px on the card quietly disappears — the silent bypass this whole design exists to stop |
| absent in this screen's state | no crown, because this user has no badge | it must appear on other screens, so recording it as a permanent exemption is wrong |
| not this screen's concern | the inside of a design-system component | otherwise every screen re-verifies the same button |

Collapse them into one slot and the second kind hardens into the first.

A node decided to have no element is recorded as such, with its kind and reason, rather than
omitted. Omission and absence look identical in a file and only one of them is a decision.

## Constraints

- Never write a mapping the developer has not approved.
- Never silently drop a node. A node with no element is recorded with its reason.
- Never report a check as passed when it examined nothing. A narrowed fingerprint that yields
  zero nodes for the current viewport is a blocked setup, not a pass.
- Do not put the mapping or the fingerprint in a note vault.
- Do not claim the before-implementation mode is proven. It has not been run.
- Never record `안그림` without `instead`. A node with no element and nowhere to re-point is how
  a design value disappears without anyone noticing.
