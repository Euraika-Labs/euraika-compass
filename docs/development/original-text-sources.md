# Original-language text editions

The corpus catalog downloads these editions into the private data directory when the user imports them. The app verifies the SHA-256 and expected passage count before writing an edition. All three downloads were checked with the live import parsers on 9 November 2026.

| Starter | Edition and selection | Passages | Download bytes |
| --- | --- | ---: | ---: |
| `uxlc-he-torah` | UXLC 2.6, build 27.7, Genesis–Deuteronomy | 5,853 | 1,590,651 |
| `uxlc-he-tanakh-rest` | UXLC 2.6, build 27.7, Prophets and Writings | 17,360 | 1,590,651, same snapshot |
| `sblgnt-grc` | SBL Greek New Testament 1.2, all 27 books | 7,939 | 1,414,687 |
| `tanzil-uthmani-ar` | Tanzil Uthmani Arabic Quran 1.1, all 114 surahs | 6,236 | 1,396,684 |

The two Hebrew selections cover the 39 book files in the same edition. They share one original archive and index disjoint sets of passages. The Torah belongs to both the Torah and Bible search collections. The language tag is `he` for this Hebrew Bible edition, which also includes Aramaic passages. Tanach.us identifies UXLC as its revised electronic transcription derived from the Westminster Leningrad Codex. The app reads the publisher's Full/Accents text with its cantillation, vocalization, ketiv/qere and transcription markers. It removes the surrounding file structure and verse-number framing. [Tanach.us edition](https://www.tanach.us/) · [Text format](https://www.tanach.us/Pages/TextFiles.html) · [Terms](https://www.tanach.us/License.html) · [Download](https://www.tanach.us/TextFiles/Tanach.txt.zip)

The Greek starter reads the base text files in Michael W. Holmes's critical edition from the publisher's repository at commit `d7f35adca9ec410e1d1499c63b4dd989d76c8d4d`. It retains punctuation and editorial brackets, including the marked reading at John 7:53–8:11. The original archive also holds the apparatus. [Publisher download page](https://sblgnt.com/download/) · [Pinned source](https://github.com/Faithlife/SBLGNT/tree/d7f35adca9ec410e1d1499c63b4dd989d76c8d4d) · [CC BY 4.0 terms](https://sblgnt.com/license/)

The Arabic starter uses Tanzil's Unicode encoding of the Medina Mushaf in verse-numbered text format. The verified download includes pause marks, sajdah signs, rub-el-hizb signs, superscript alefs and tatweel. The app retains the exact UTF-8 verse payloads and the original download with its copyright footer. [Uthmani edition](https://tanzil.net/docs/Uthmani) · [Publisher download form](https://tanzil.net/download/) · [Text terms](https://tanzil.net/docs/text_license)

| Snapshot | SHA-256 |
| --- | --- |
| UXLC `Tanach.txt.zip` | `71d958aec48ec62d11240bc5d13e7a2234ee921c1d162bdd1664f09c4688e446` |
| Pinned SBLGNT publisher ZIP | `bcb9cfd8678a863be77c01641aab14c31515e7057852b5abfe0920aac73cbf56` |
| Tanzil Uthmani numbered text | `7f30c647331a61100ebf24a80507dc0fcdd9f2df97f1312b5b2dfcb982a7f326` |

References use English book labels with the edition's own chapter and verse numbering, for example `Exodus 20:26` and `1 John 4:8`. Arabic references use `surah:ayah`, for example `2:156`. Common Dutch aliases such as `Johannes 1:1`, `Psalmen 23:1` and `Gen. 1:1` resolve to the source's stored reference. Matching numbers across editions can refer to different material. The UXLC numbering includes Joel chapter 4 and a numbered superscription in Psalm 3. SBLGNT contains edition-specific gaps and bracketed material. The import keeps these differences.

The app stores each original archive or text file under `sources/<sha256>/original`. Import reads only the named text members in each ZIP, in memory and within download, member and decompression limits. The live UXLC and Tanzil URLs can change at the publisher. A change to any snapshot byte, including a publisher footer, requires review of the new download before updating the pinned hash.

The `Passage.text` and citation quote retain the published Unicode sequence. For search, the app adds ASCII tokens to `search_text` after case folding and removing diacritics and tatweel. This allows PostgreSQL's simple full-text index to match pointed and unpointed Greek, Hebrew and Arabic queries under locale `C`. The Arabic index also matches alef wasla to plain alef. This is lexical search, with the displayed text always taken from the stored verse.

Sources and citations retain the publisher and licence links. Tanach.us permits copying of the biblical text and requests attribution. SBLGNT is © 2010 Society of Biblical Literature and Logos Bible Software under CC BY 4.0. These two original editions allow passage processing when the user enables a cloud connection. The app keeps the original Tanzil edition local under its verbatim-copy policy and records the copyright notice from the verified download, Copyright (C) 2007–2026 Tanzil Project. [Tanach.us terms](https://www.tanach.us/License.html) · [SBLGNT terms](https://sblgnt.com/license/) · [Tanzil text terms](https://tanzil.net/docs/text_license)
