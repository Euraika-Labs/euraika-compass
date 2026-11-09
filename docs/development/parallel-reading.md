# Parallel reading in named editions

`GET /api/v1/passages/{passage_id}/parallel` returns the stored anchor, a list of
available companion passages and any alignment warnings. Each companion retains
its own reference, exact wording, language, edition, source, hashes and use limits.
The endpoint reads the local corpus. Import the editions before opening a parallel.

| Alignment | Meaning |
| --- | --- |
| `same_reference` | The two trusted editions share a verse address within the supported scope. Their wording and textual variants remain visible. |
| `mapped_reference` | A documented one-to-one verse mapping connects different Hebrew and English addresses. |
| `compare_only` | The shared address is useful for manual comparison. Different verse boundaries or an editorial variant leave the correspondence uncertain. |

The current profiles cover the pinned UXLC Hebrew Torah and remaining Tanakh,
JPS 1917 Torah, KJV Bible, SBLGNT Greek New Testament, Tanzil Uthmani Arabic Quran
and Tanzil's Pickthall English translation. Import verifies source bytes. Parallel
lookup checks the server-assigned original-download metadata, catalog hash and
exact edition identity. Manual imports remain available for research with their
own provenance. Automatic alignment is limited to these catalog editions.

The JPS eBible verse-per-line snapshot uses the same 5,852 English Torah verse
addresses as the pinned KJV edition. Its Masoretic reference annotations confirm
specific shifts, including English Genesis 32:1 and Hebrew Genesis 32:2. The
Hebrew lookup uses 1,963 one-to-one WLC/KJV pairs from the Open Scriptures map,
compressed into consecutive verse ranges. Both endpoints exist in the pinned
UXLC and KJV snapshots. Known partial and non-bijective boundaries leave gaps.
Other unverified addresses in an affected chapter are for comparison only.
[JPS edition example](https://ebible.org/engjps/GEN32.htm).

The SBLGNT follows Nestle-Aland/United Bible Societies verse divisions and has its
own editorial readings. Omitted verses stay absent. Known divided or disputed
passages, including the bracketed John 7:53–8:11 block and the closing verses of
2 Corinthians, are comparison-only when both editions provide a matching address.
This preserves the editions' textual differences for inspection.
[SBLGNT editorial introduction](https://sblgnt.com/about/introduction/).

The pinned Uthmani and Pickthall snapshots have identical sets of 6,236 surah and
ayah addresses. Their exact stored lines retain their own treatment of the
Bismillah, orthography and translation.
[Tanzil's numbering and Bismillah notes](https://tanzil.net/docs/a_note_on_bismillah).

Grounded chat may add one verified opposite-kind companion per selected anchor,
up to nine in a batch. The helper deduplicates shared companions and retains links
to their anchors. When an original Hebrew Torah passage ranks first, JPS is the
preferred English companion, with KJV available when selected and eligible. The
same explicit source selection and cloud processing permissions govern both
passages. `compare_only` passages remain available in the reader for manual review.

The numeric Hebrew mapping ranges adapt `wlc/VerseMap.xml` at commit
`65214d2bdf57f01feb4822c22c5b0d4de032891f` (SHA-256
`6cd269ca3dccef2cb944b9d9dd8afc950f929dab53a534f1268d23affa983163`).
The adaptation compresses consecutive pairs and omits ambiguous rows. Original
work of the Open Scriptures Hebrew Bible available at https://github.com/openscriptures/morphhb.
[Pinned verse map](https://github.com/openscriptures/morphhb/blob/65214d2bdf57f01feb4822c22c5b0d4de032891f/wlc/VerseMap.xml),
[source license, CC BY 4.0](https://github.com/openscriptures/morphhb/blob/master/LICENSE.md).
