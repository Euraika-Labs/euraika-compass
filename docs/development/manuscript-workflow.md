# Find and read manuscript scans

Open **Manuscripts** in Compass. Search by title, institution, or shelfmark,
or filter by manuscript language. The starting catalog covers five institutional
witnesses. Compass reads the live IIIF manifests or collection record and
loads the selected folio's institutional image. This catalog is deliberately
bounded. It does not crawl arbitrary links or claim to identify passages from
folio numbers.

| Witness | Holding institution and official record | Compass use |
| --- | --- | --- |
| Kennicott Bible, MS. Kennicott 1 | [Bodleian Libraries](https://digital.bodleian.ox.ac.uk/objects/8c264b23-f6cc-4f18-98cf-9d75f7175b54/) | View, private copy, local reading |
| Nash Papyrus, MS Or.233 | [Cambridge University Library](https://cudl.lib.cam.ac.uk/view/MS-OR-00233/1) | View, private copy, local reading |
| Codex Bezae, MS Nn.2.41 | [Cambridge University Library](https://cudl.lib.cam.ac.uk/view/MS-NN-00002-00041/1) | View, private copy, local reading |
| Codex Vaticanus, Vat.gr.1209 | [Vatican Library](https://digi.vatlib.it/view/MSS_Vat.gr.1209/0050) | Preview; use the library's site for its own options |
| Tashkent Qur’an folio, 2004.87 | [The Metropolitan Museum of Art](https://www.metmuseum.org/art/collection/search/454661) | View, save and local reading; image eligible for explicitly selected cloud OCR |

Select a folio to see the image, holder, shelfmark, attribution and source terms.
Where permitted, select a dossier and choose **Add folio to dossier**. Then open
the saved scan in **Research**. Compass keeps the bytes of the official image
rendition, its SHA-256, the institution and catalog link, record and folio
identity, the exact image URL, retrieval time and use limits. A change to the
source snapshot does not overwrite a previously saved image. Reopening a
saved scan uses its private local bytes.

Choose an available OCR/HTR route and **Read text**. To read a smaller area,
enable the image region and enter its pixel bounds. Compass sends the selected
page or crop only to the chosen route. For scans licensed for private use only,
the cloud routes are unavailable. No route silently falls back to another
model. On this Windows setup the local [Kraken profiles](../../app/workers/kraken/README.md)
run on demand in WSL. The app does not put model weights or manuscript files in
the public repository.

Treat the result as an **unreviewed machine reading**. Historical handwriting,
abbreviations, damage and line order can lead to missed or wrong text.
Where the model returns coordinates, Compass records them against the actual
input region. It does not infer missing glyphs or use a stored scripture
edition to fill in a manuscript. Save corrections as separate revisions.
