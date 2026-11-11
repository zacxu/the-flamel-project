# The Flamel Project — five-minute website presentation

**Website:** [theflamelproject.42web.io](https://theflamelproject.42web.io/)

Read the quoted paragraphs aloud. The **On screen** instructions are actions, not spoken lines. Follow the timestamps as checkpoints: the spoken text takes approximately four minutes ten seconds at 120 words per minute, leaving about fifty seconds for navigation and pointing. Pause on the visuals rather than rushing to the next section.

## Before presenting — outside the five minutes

- Open the website on a laptop or desktop. Visit each of the six views once so the data and viewer can load before the presentation.
- Rehearse the three Crystal Lab examples used below: **Known MgO sequence**, **CaMg₂O₃ · prototype**, and **CaMg₂O₃ · excluded 12 atoms**.
- Return to **Overview** and click **Reset exploration** in the footer, then scroll back to the top. This restores the aggregate Quality-versus-Full comparison at 50 queries.
- Leave **Start guided tour** idle. That button runs a separate three-minute presentation; this five-minute script uses manual navigation.
- Keep this script on a second screen or device. If 3D is slow, use **Use saved scientific figure** and continue speaking.

## 0:00–0:35 — Overview: the question and the invention

**On screen:** Stay on **Overview**. Point to the research question and the saved MgO structure.

> Hello everyone. This is The Flamel Project, an interactive research prototype for exploring crystal discovery.
>
> Our question is: can symmetry-aware generation and predictive uncertainty help us use a limited validation budget more effectively?
>
> We built a working experiment around pretrained models, then made its results inspectable here. The site shows saved research; it does not run new calculations when we click.

## 0:35–1:05 — Workflow: how the experiment works

**On screen:** Click **Workflow**, then **Screen**. Point to the two scientific tracks below the workflow.

> We start with a composition proposal, generate candidate crystals, screen them, and validate promising structures.
>
> Symmetry constrains how atoms can be arranged. Uncertainty helps us decide where to spend labels or calculations.
>
> We tested selection on historical materials and generation on fresh structures as separate tracks. They did not become a completed discovery loop.

## 1:05–2:00 — Replay: test the hypothesis against a baseline

**On screen:** Click **Replay**. Keep **Split → Aggregate · five overlapping splits**, Quality and Full visible, and 50 completed queries. Point to the near-stable hit comparison, then select **Chemical systems** under **Chart metric**.

> Replay compares policies at the same fifty-query budget. “Near-stable” means a saved signed hull-distance target at or below zero point zero five electronvolts per atom. These are existing labels, not new DFT runs.
>
> Across five overlapping splits, quality ranking found an average of forty-one point two near-stable records, versus twenty-nine point four for the Full uncertainty-and-diversity policy.
>
> Switching to chemical systems shows the trade-off: Full covered forty-two point two systems on average, compared with thirty-two point eight for Quality.
>
> Our Full policy did not improve hit yield. It explored wider chemistry. We preserve that result rather than presenting the hypothesis as proven.

## 2:00–3:00 — Crystal Lab: inspect real structures and their status

**On screen:** Click **Crystal Lab → Known MgO sequence**. In **Saved stage**, select **DFT validated: known phase/reference** and briefly rotate the cell. Then select **CaMg₂O₃ · prototype**, showing **CHGNet relaxed**. Finish with **CaMg₂O₃ · excluded 12 atoms**. Make these changes as you reach the corresponding paragraph.

> This is an actual saved magnesium oxide structure. I can rotate it and inspect the recorded stages.
>
> Its accepted DFT geometry recovers known rock salt. It demonstrates our validation pipeline for this control, not that we discovered magnesium oxide.
>
> Here is the separate calcium-magnesium-oxide prototype, relaxed with CHGNet. That is a model result, not DFT-confirmed stability.
>
> The excluded twelve-atom example shows another safeguard: its reduced formula may look right, but its cell failed our predefined gate. Displaying a structure does not make it a success.

## 3:00–3:45 — Findings: symmetry and new composition proposals

**On screen:** Click **Findings → Symmetry & compositions**. Keep **Primary · first eight** selected and choose MgO under **Control composition**. Point to validity and unique yield, then scroll to the six composition proposals.

> For the MgO control, nontrivial symmetry conditioning gave seven valid cells out of eight, versus zero with P1 conditioning. However, there was only one unique valid structure.
>
> Both arms use the same pretrained architecture, so this compares conditioning, not an architecture with symmetry removed.
>
> We also tested six proposed compositions: none of forty-eight transformer draws passed the exact-cell gate. These proposals were absent from two pinned reference catalogs; global novelty remains unproven.

## 3:45–4:20 — Findings: how trustworthy is uncertainty?

**On screen:** Click **Uncertainty & selective risk**. Point to **Does the nominal interval cover the target?** Keep the Full endpoint selected. Move **Requested retained fraction** from 100% to 10%, then restore it to 100%.

> Uncertainty also needs checking. This panel compares nominal ninety-percent intervals with their actual held-out coverage.
>
> Coverage varies across splits, so we cannot promise reliability in any unfamiliar chemical space.
>
> The retention control shows a trade-off: keeping fewer, lower-disagreement predictions can reduce error on that subset. It does not improve predictions for every material.

## 4:20–5:00 — Evidence: what we can claim and what comes next

**On screen:** Click **Evidence**. Show **The complete QE ledger**, then select **Job role → perturbation** as you mention incomplete work. Point to **An incomplete reference inventory** for the second paragraph. Finish on this view; the **Sources** control is available if the audience asks for provenance.

> Finally, this ledger preserves all nineteen Quantum ESPRESSO attempts, including incomplete work. Three relaxed geometries passed the recorded finite checks.
>
> The competing-phase reference inventory is incomplete, so we have not established a new stable material.
>
> Our contribution is a traceable prototype: matched generation controls, equal-budget selection comparisons, real structures and explicit evidence.
>
> Next, we need eligible candidates and complete reference comparisons to test discoveries per DFT budget.
>
> Thank you.

## If a page loads slowly or time runs short

Continue speaking while the recorded data loads. For Crystal Lab, use the saved figure rather than waiting for 3D. If behind schedule, skip displaying the prototype and excluded example and briefly state their distinction instead. Preserve the final statement that no new stable material was established.

## Source notes — not spoken

The script follows the [frozen Phase 6 report](../reports/phase6_report.md), the current website controls and the [W7 live verification](reports/W7_COMPLETION.md). The three accepted geometries are the generated known-MgO control, its separate MgO source reference and a CaO source reference; they are not three novel materials. The five historical splits overlap. The generation-conditioning experiment, historical selection benchmark and fresh DFT checks have separate evidential scopes.

The existing [guided-tour contract](contracts/GUIDED_TOUR_CONTRACT.md) describes the separate automatic three-minute tour. For an offline presentation, use the local HTTP preview instructions in [LOCAL_PREVIEW.md](LOCAL_PREVIEW.md).
