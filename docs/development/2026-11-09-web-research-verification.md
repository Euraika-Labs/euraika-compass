# Web research verification — 9 November 2026

Verified on the managed Pinokio app on Windows with the existing
`mistral-large-4-0` connection and the imported local editions. The updated app
reported 7 sources, 80,578 passages and the same two saved conversations.
The live question was a temporary synthetic QA turn and was not saved.

The Chrome test asked Compass to compare Greek and English John 1:1 and find
scholarly background on the Logos. Both DOAJ and Wikimedia responded. The answer
cited SBL Greek New Testament and KJV passages alongside two publisher abstract
excerpts and one encyclopedic excerpt. The abstract cards showed authors,
publication, retrieval time, licence, DOI and the index record. The test opened
an edition citation and an online citation, matched the edition quote against
the stored passage, and checked the online excerpt hash and target URL.

Examples of the actual linked articles:

- [Parallelisms and revelatory concepts of the Johannine Prologue in Greco-Roman context](https://doi.org/10.4102/hts.v72i3.3115)
- [The logos Christology in the fourth gospel](https://doi.org/10.4102/hts.v79i4.8946)

The initial live draft used Wikipedia context alone. The follow-up run used
publisher abstracts after making the preference for relevant scholarly evidence
explicit. This verifies mixed retrieval, citation inspection and attribution for
this question; it does not verify the full articles or all interpretive claims.

Checks passed: 182 backend tests against the native PostgreSQL test environment,
Ruff, frontend typecheck/lint/build, 19 frontend unit tests, and four Chrome tests.
The browser contracts also cover opt-in, local-only, saved chat and parallel
reading. Provider boundary tests cover failure, limits, source provenance and
cloud-processing eligibility.
