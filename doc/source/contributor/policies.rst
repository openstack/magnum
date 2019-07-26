###########################
Magnum Development Policies
###########################
.. contents::

Magnum is made possible by a wide base of contributors from numerous
countries and time zones around the world. We work as a team in accordance
with the `Guiding Principles
<https://governance.openstack.org/tc/reference/principles.html>`_ of the
OpenStack Community. We all want to be valued members of a successful team
on an inspiring mission. Code contributions are merged into our code base
through a democratic voting process. Anyone may vote on patches submitted
by our contributors, and everyone is encouraged to make actionable and
helpful suggestions for how patches can be improved prior to merging. We
strive to strike a sensible balance between the speed of our work, and
the quality of each contribution. This document describes the correct
balance in accordance with the prevailing wishes of our team.

This document is an extension of the `OpenStack Governance
<https://governance.openstack.org/>`_ that explicitly converts our tribal
knowledge into a codified record. If any conflict is discovered between
the OpenStack governance, and this document, the OpenStack documents shall
prevail.

*********************
Team Responsibilities
*********************

Responsibilities for Everyone
=============================
`Everyone` in our community is expected to know and comply with the
`OpenStack Community Code of Conduct
<https://www.openstack.org/legal/community-code-of-conduct/>`_.
We all need to work together to maintain a thriving team that enjoys working
together to solve challenges.

Responsibilities for Contributors
=================================
When making contributions to any Magnum code repository, contributors shall
expect their work to be peer reviewed. See `Merge Criteria`_ for details
about how reviewed code is approved for merge.

Expect reviewers to vote against merging a patch, along with actionable
suggestions for improvement prior to merging the code. Understand that such
a vote is normal, and is essential to our quality process.

If you receive votes against your review submission, please revise your
work in accordance with any requests, or leave comments indicating why you
believe the work should be further considered without revision.

If you leave your review without further comments or revision for an extended
period, you should mark your patch as `Abandoned`, or it may be marked as
`Abandoned` by another team member as a courtesy to you. A patch with no
revisions for multiple weeks should be abandoned, or changed to work in
progress (WIP) with the `workflow-1` flag. We want all code in the review
queue to be actionable by reviewers. Note that an `Abandoned` status shall
be considered temporary, and that your patch may be restored and revised
if and when you are ready to continue working on it. Note that a core
reviewer may un-abandon a patch to allow subsequent revisions by you or
another contributor, as needed.

When making revisions to patches, please acknowledge and confirm each
previous review comment as Done or with an explanation for why the
comment was not addressed in your subsequent revision.

Summary of Contributor Responsibilities
---------------------------------------
* Includes the `Everyone` responsibilities, plus:
* Recognize that revisions are a normal part of our review process.
* Make revisions to your patches to address reviewer comments.
* Mark each inline comment as `Done` once it has been addressed.
* Indicate why any requests have not been acted upon.
* Set `workflow-1` until a patch is ready for merge consideration.
* Consider patches without requested revisions as abandoned after a few weeks.

Responsibilities for Reviewers
==============================
Each reviewer is responsible for upholding the quality of our code.
By making constructive and actionable requests for revisions to patches,
together we make better software. When making requests for revisions,
each reviewer shall carefully consider our aim to merge contributions in
a timely manner, while improving them. **Contributions do not need to be
perfect in order to be merged.** You may make comments with a "0" vote to
call out stylistic preferences that will not result in a material change
to the software if/when resolved.

If a patch improves our code but has been through enough revisions that
delaying it further is worse than including it now in imperfect form, you
may file a tech-debt bug ticket against the code, and vote to merge the
imperfect patch.

When a reviewer requests a revision to a patch, he or she is expected to
review the subsequent revision to verify the change addressed the concern.

Summary of Reviewer Responsibilities
------------------------------------
* Includes the Everyone responsibilities, plus:
* Uphold quality of our code.
* Provide helpful and constructive requests for patch revisions.
* Carefully balance need to keep moving while improving contributions.
* Submit tech-debt bugs to merge imperfect code with known problems.
* Review your requested revisions to verify them.

Responsibilities for Core Reviewers
===================================
Core reviewers have all the responsibilities mentioned above, as well as
a responsibility to judge the readiness of a patch for merge, and to set
the `workflow+1` flag to order a patch to be merged once at least one
other core reviewers has issued a +2 vote. See: `Merge Criteria`_.

Reviewers who use the -2 vote shall:

1. Explain what scenarios can/will lift the -2 or downgrade it to a -1
   (non-sticky), or explain "this is unmergable for reason <X>".
   Non-negotiable reasons such as breaks API contract, or introduces
   fundamental security issues are acceptable.
2. Recognize that a -2 needs more justification than a -1 does. Both
   require actionable notes, but a -2 comment shall outline the reason
   for the sticky vote rather than a -1.
3. Closely monitor comments and revisions to that review so the vote is
   promptly downgraded or removed once addressed by the contributor.

All core reviewers shall be responsible for setting a positive and welcoming
tone toward other reviewers and contributors.

Summary of Core Reviewer Responsibilities
-----------------------------------------
* Includes the Reviewer responsibilities, plus:
* Judge readiness of patches for merge.
* Approve patches for merge when requirements are met.
* Set a positive and welcoming tone toward other reviewers and contributors.

PTL Responsibilities
====================
In accordance with our `Project Team Guide for PTLs
<https://docs.openstack.org/project-team-guide/ptl.html>`_
our PTL carries all the responsibilities referenced above plus:

* Select and target blueprints for each release cycle.
* Determine Team Consensus. Resolve disagreements among our team.
* May delegate his/her responsibilities to others.
* Add and remove core reviewers in accordance with his/her judgement.
    * Note that in accordance with the Project Team Guide, selection or
      removal of core reviewers is not a democratic process.
    * Our PTL shall maintain a core reviewer group that works well together
      as a team. Our PTL will seek advice from our community when making
      such changes, but ultimately decides.
    * Clearly communicate additions to the developer mailing list.

##########################
Our Development Philosophy
##########################
********
Overview
********
* Continuous iterative improvements.
* Small contributions preferred.
* Perfect is the enemy of good.
* We need a compass, not a master plan.

**********
Discussion
**********
We believe in making continuous iterative improvements to our software.
Making several small improvements is preferred over making fewer large
changes. Contributions of about perhaps 400 lines of change or less are
considered ideal because they are easier to review. This makes them
more efficient from a review perspective than larger contributions are,
because they get reviewed more quickly, and are faster to revise than
larger works. We also encourage unrelated changes to be contributed in
separate patches to make reasoning about each one simpler.

Although we should strive for perfection in our work, we must recognize that
what matters more than absolute perfection is that our software is
consistently improving over time. When contributions are slowed down by too
many revisions, we should decide to merge code even when it is imperfect,
as long as we have systematically tracked the weaknesses so we can revisit
them with subsequent revision efforts.

Rule of Thumb
=============
Our rule of thumb shall be the answer to two simple questions:

1. Is this patch making Magnum better?
2. Will this patch cause instability, or prevent others from using Magnum
   effectively?

If the answers respectively are *yes* and *no*, and our objections can be
effectively addressed in a follow-up patch, then we should decide to merge
code with tech-debt bug tickets to systematically track our desired
improvements.

*********************
How We Make Decisions
*********************
Team Consensus
==============
On the Magnum team, we rely on Team Consensus to make key decisions.
Team Consensus is the harmonious and peaceful agreement of the majority
of our participating team. That means that we seek a clear indication of
agreement of those engaged in discussion of a topic. Consensus shall not
be confused with the concept of Unanimous Consent where all participants
are in full agreement. Our decisions do not require Unanimous Consent. We
may still have a team consensus even if we have a small number of team
members who disagree with the majority viewpoint. We must recognize that
we will not always agree on every key decision. What's more important than
our individual position on an argument is that the interests of our team
are met.

We shall take reasonable efforts to address all opposition by fairly
considering it before making a decision. Although Unanimous Consent
is not required to make a key decision, we shall not overlook legitimate
questions or concerns. Once each such concern has been addressed, we may
advance to making a determination of Team Consensus.

Some code level changes are controversial in nature. If this happens, and
a core reviewer judges the minority viewpoint to be reasonably considered,
he or she may conclude we have Team Consensus and approve the patch for
merge using the normal voting guidelines. We shall allow reasonable time
for discussion and socialization when controversial decisions are considered.

If any contributor disagrees with a merged patch, and believes our decision
should be reconsidered, (s)he may consult our `Reverting Patches`_
guidelines.

No Deadlocks
============
We shall not accept any philosophy of "agree to disagree". This form of
deadlock is not decision making, but the absence of it. Instead, we shall
proceed to decision making in a timely fashion once all input has been
fairly considered. We shall accept when a decision does not go our way.

Handling Disagreement
=====================
When we disagree, we shall first consult the
`OpenStack Community Code of Conduct
<https://www.openstack.org/legal/community-code-of-conduct/>`_ for guidance.
In accordance with our code of conduct, our disagreements shall be handled
with patience, respect, and fair consideration for those who don't share
the same point of view. When we do not agree, we take care to ask why. We
strive to understand the reasons we disagree, and seek opportunities to
reach a compromise.

Our PTL is responsible for determining Team Consensus when it can not be
reached otherwise. In extreme cases, it may be possible to appeal a PTL
decision to the `OpenStack TC
<https://www.openstack.org/foundation/tech-committee/>`_.

*******************
Open Design Process
*******************
One of the `four open
<https://governance.openstack.org/tc/reference/opens.html>`_
principles embraced by the OpenStack community is Open Design. We
collaborate openly to design new features and capabilities, as well as
planning major improvements to our software. We use multiple venues to
conduct our design, including:

* Written specifications
* Blueprints
* Bug tickets
* PTG meetings
* Summit meetings
* IRC meetings
* Mailing list discussions
* Review comments
* IRC channel discussion

The above list is ordered by formality level. Notes and/or minutes from
meetings shall be recorded in etherpad documents so they can be accessed
by participants not present in the meetings. Meetings shall be open, and
shall not intentionally exclude any stakeholders.

Specifications
==============
The most formal venue for open design are written specifications. These
are RST format documents that are proposed in the magnum-specs code
repository by release cycle name. The repository holds a template for
the format of the document, as required by our PTL for each release cycle.

Specifications are intended to be a high level description of a major
feature or capability, expressed in a way to demonstrate that the feature
has been well contemplated, and is acceptable by Team Consensus. Using
specifications allows us to change direction without requiring code rework
because input can be considered before code has been written.

Specifications do not require specific implementation details. They shall
describe the implementation in enough detail to give reviewers a high level
sense of what to expect, with examples to make new concepts clear. We do
not require specifications that detail every aspect of the implementation.
We recognize that it is more effective to express implementations with
patches than conveying them in the abstract. If a proposed patch set for
an implementation is not acceptable, we can address such concerns using
review comments on those patches. If a reviewer has an alternate idea for
implementation, they are welcome to develop another patch in WIP or
completed form to demonstrate an alternative approach for consideration.
This option for submitting an alternative review is available for alternate
specification ideas that reach beyond the scope of a simple review comment.
Offering reviewers multiple choices for contributions is welcome, and is
not considered wasteful.

Implementations of features do not require merged specifications. However,
major features or refactoring should be expressed in a specification so
reviewers will know what to expect prior to considering code for review.
Contributors are welcome to start implementation before the specifications
are merged, but should be ready to revise the implementation as needed to
conform with changes in the merged specification.

Reviews
=======
A review is a patch set that includes a proposal for inclusion in our code
base. We follow the process outlined in the `Code Review
<https://docs.openstack.org/infra/manual/developers.html#code-review>`_
section of the `OpenStack Developer's Guide
<https://docs.openstack.org/infra/manual/developers.html>`_.
The following workflow states may by applied to each review:

========== ================== =============================================
State      Meaning            Detail
========== ================== =============================================
workflow-1 Work in progress    This patch is submitted for team input,
                               but should not yet be considered for merge.
                               May be set by a core reviewer as a courtesy.
                               It can be set after workflow+1 but prior to
                               merge in order to prevent a gate breaking
                               merge.
workflow-0 Ready for reviews   This patch should be considered for merge.
workflow+1 Approved            This patch has received at least two +2
                               votes, and is approved for merge. Also
                               known as a "+A" vote.
========== ================== =============================================

The following votes may be applied to a review:

====== ====================================================================
 Vote   Meaning
====== ====================================================================
 -2     Do Not Merge
         * WARNING: Use extreme caution applying this vote, because
           contributors perceive this action as hostile unless it is
           accompanied with a genuine offer to help remedy a critical
           concern collaboratively.
         * This vote is a veto that indicates a critical problem with
           the contribution. It is sticky, meaning it must be removed
           by the individual who added it, even if further revisions
           are made.
         * All -2 votes shall be accompanied with a polite comment that
           clearly states what can be changed by the contributor to result
           in reversal or downgrade of the vote to a -1.
         * Core reviewers may use this vote:
             * To indicate a critical problem to address, such as a
               security vulnerability that other core reviewers may be
               unable to recognize.
             * To indicate a decision that the patch is not consistent
               with the direction of the project, subsequent to conference
               with the PTL about the matter.
         * The PTL may use this vote:
             * To indicate a decision that the patch is not consistent
               with the direction of the project.
             * While coordinating a release to prevent incompatible changes
               from merging before the release is tagged.
             * To address a critical concern with the contribution.
         * Example uses of this vote that are not considered appropriate:
             * To ensure more reviews before merge.
             * To block competing patches.
             * In cases when you lack the time to follow up closely afterward.
         * To avoid a -2 vote on your contribution, discuss your plans
           with the development team prior to writing code, and post a
           WIP (`workflow-1`) patch while you are working on it, and ask
           for input before you submit it for merge review.
 -1     This patch needs further work before it can be merged
         * This vote indicates an opportunity to make our code better
           before it is merged.
         * It asks the submitter to make a revision in accordance with
           your feedback before core reviewers should consider this code
           for merge.
         * This vote shall be accompanied with constructive and actionable
           feedback for how to improve the submission.
         * If you use a -1 vote to ask a question, and the contributor
           answers the question, please respond acknowledging the answer.
           Either change your vote or follow up with additional rationale
           for why this should remain a -1 comment.
         * These votes will be cleared when you make a revision to a patch
           set, and resubmit it for review.
         * NOTE: Upon fair consideration of the viewpoint shared with this
           vote, reviewers are encouraged to vote in accordance with their
           own view of the contribution. This guidance applies when any
           reviewer (PTL, core, etc.) has voted against it. Such opposing
           views must be freely expressed to reach Team Consensus. When you
           agree with a -1 vote, you may also vote -1 on the review to
           echo the same concern.
  0     No Score
         * Used to make remarks or ask questions that may not require a
           revision to answer.
         * Used to confirm that your prior -1 vote concern was addressed.
 +1     Looks good to me, but someone else must approve
         * Used to validate the quality of a contribution and express
           agreement with the implementation.
         * Resist the temptation to blindly +1 code without reviewing
           it in sufficient detail to form an opinion.
         * A core reviewer may use this if they:
             * Provided a revision to the patch to fix something, but agree
               with the rest of the patch.
             * Agree with the patch but have outstanding questions that
               do not warrant a -1 but would be nice to have answered.
             * Agree with the patch with some uncertainty before using
               a +2. It can indicate support while awaiting test results
               or additional input from others.
 +2     Looks good to me (core reviewer)
         * Used by core reviewers to indicate acceptance of the patch
           in its current form.
         * Two of these votes are required for +A.
         * Apply our `Rule of Thumb`_
 +A     Approval for merge
         * This means setting the workflow+1 state, and is typically
           added together with the final +2 vote upon `Merge Criteria`_
           being met.
====== ====================================================================

Merge Criteria
--------------
We want code to merge relatively quickly in order to keep a rapid pace of
innovation. Rather than asking reviewers to wait a prescribed arbitrary
time before merging patches, we instead use a simple `2 +2s` policy for
approving new code for merge. The following criteria apply when judging
readiness to merge a patch:

1. All contributions shall be peer reviewed and approved with a +2 vote by
   at least two core reviewers prior to being merged. Exceptions known as
   `Fast Merge`_ commits may bypass peer review as allowed by this policy.
2. The approving reviewer shall verify that all open questions and concerns
   have been adequately addressed prior to voting +A by adding the
   workflow+1 to merge a patch. This judgement verifies that
   `Team Consensus`_ has been reached.

Note: We discourage any `workflow+1` vote on patches that only have two +2
votes from cores from the same affiliation. This guideline applies when
reviewer diversity allows for it.

See `Reverting Patches`_ for details about how to remedy mistakes when code
is merged too quickly.

Reverting Patches
-----------------
Moving quickly with our `Merge Criteria`_ means that sometimes we might
make mistakes. If we do, we may revert problematic patches. The following
options may be applied:

1. Any contributor may revert a change by submitting a patch to undo the
   objection and include a reference to the original patch in the
   commit message. The commit message shall include clear rationale for
   considering the revert. Normal voting rules apply.
2. Any contributor may re-implement a feature using an alternate approach
   at any time, even after a previous implementation has merged. Normal
   voting rules apply.
3. If a core reviewer wishes to revert a change (s)he may use the options
   described above, or may apply the `Fast Revert`_ policy.

Fast Merge
----------
Sometimes we need to merge code quickly by bypassing the peer review process
when justified. Allowed exceptions include:

* PTL (Project Team Lead) Intervention / Core intervention
    * Emergency un-break gate.
    * `VMT <https://security.openstack.org/vmt-process.html>`_ embargoed
      patch submitted to Gerrit.
* Automatic proposals (e.g. requirements updates).
* PTL / Core discretion (with comment) that a patch already received a
  +2 but minor (typo/rebase) fixes were addressed by another core reviewer
  and the `correcting` reviewer has opted to carry forward the other +2.
  The `correcting` reviewer shall not be the original patch submitter.

We recognize that mistakes may happen when changes are merged quickly. When
concerns with any `Fast Merge` surface, our `Fast Revert`_ policy may be
applied.

Fast Revert
-----------
This policy was adapted from nova's `Reverts for Retrospective Vetos
<https://docs.openstack.org/nova/latest/policies.html>`_ policy in 2017.
Sometimes our simple `2 +2s` approval policy will result in errors when we
move quickly. These errors might be a bug that was missed, or equally
importantly, it might be that other cores feel that there is a need for
further discussion on the implementation of a given piece of code.

Rather than an enforced time-based solution - for example, a patch could
not be merged until it has been up for review for 3 days - we have chosen
an honor-based system of `Team Consensus`_ where core reviewers do not
approve controversial patches until proposals are sufficiently socialized
and everyone has a chance to raise any concerns.

Recognizing that mistakes can happen, we also have a policy where contentious
patches which were quickly approved may be reverted so that the discussion
around the proposal may continue as if the patch had never been merged in the
first place. In such a situation, the procedure is:

1. The commit to be reverted must not have been released.
2. The core team member who has a -2 worthy objection may propose a
   revert, stating the specific concerns that they feel need addressing.
3. Any subsequent patches depending on the to-be-reverted patch shall be
   reverted also, as needed.
4. Other core team members shall quickly approve the revert. No detailed
   debate is needed at this point. A -2 vote on a revert is strongly
   discouraged, because it effectively blocks the right of cores approving
   the revert from -2 voting on the original patch.
5. The original patch submitter may re-submit the change, with a reference
   to the original patch and the revert.
6. The original reviewers of the patch shall restore their votes and attempt
   to summarize their previous reasons for their votes.
7. The patch shall not be re-approved until the concerns of the opponents
   are fairly considered. A mailing list discussion or design spec may be
   the best way to achieve this.

This policy shall not be used in situations where `Team Consensus`_ was
fairly reached over a reasonable period of time. A `Fast Revert` applies
only to new concerns that were not part of the `Team Consensus`_
determination when the patch was merged.

See also: `Team Consensus`_.

Continuous Improvement
======================
If any part of this document is not clear, or if you have suggestions for
how to improve it, please contact our PTL for help.
