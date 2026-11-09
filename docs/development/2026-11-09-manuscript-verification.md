# Institutional scans and OCR verification — 9 November 2026

The app loaded the live official records and sample image renditions for
Kennicott, Nash, Bezae, Vaticanus, and the two Met Qur’an folios. The catalog is
bounded to these six entries. See the [workflow](manuscript-workflow.md)
for the official source links and use limits.

A Chrome run against a separate native PostgreSQL database selected
institutional folios, decoded their images, attached the permitted
renditions, reopened their exact saved bytes, and queued explicitly chosen
Kraken jobs. The saved bytes matched the stored SHA-256. The Greek and
Hebrew jobs completed with actual unreviewed readings:

| Actual image | Reader | Recorded result |
| --- | --- | --- |
| Kennicott Bible, fol. 5v, 2500 × 3156 | Local PP-OCRv6 medium | 1,816 characters, 1,250 Hebrew script characters; 197 detected line boxes |
| Codex Bezae, fol. 67v, 1689 × 2000 | Local PP-OCRv6 medium | 972 characters, 621 Greek script characters; 48 detected line boxes |
| Tashkent Qur’an folio, 3510 × 2811 | Local PP-OCRv6 medium | No readable text; job failed without a substitute model |
| Mamluk naskh Qur’an folio, 1500 × 2068 | Same local reader, independent full-image probe | 27 characters, 21 Arabic script characters; 5 detected line boxes |
| Tashkent Qur’an folio, public-domain crop | Mistral OCR 4.1 adapter, explicit probe | 207 characters, 182 Arabic script characters; 1 returned OCR region |

Script character counts show that the software returned text in the intended
script. They do not measure transcription accuracy or line completeness.
Early Kufic can defeat the general local segmenter; even the later naskh
example gave only sparse local output. Inspect the image and verify the reading
before using it as evidence. No private manuscript or dossier image was sent
to the cloud in these checks.

Kraken 7.1 ran in an isolated Ubuntu WSL environment with pinned publisher
weights, CPU PyTorch 2.9.1 and no persistent worker process. The BiblIA,
Meleagre and Muharaf specialist model files also loaded successfully. The
verification used their publisher files and checksums, with model weights and
credentials kept outside the repository.

The native PostgreSQL suite ran 204 tests, including the scan download,
validation, permission and provenance boundaries. Frontend typecheck, lint,
unit tests and Chrome contracts passed. The migration was exercised both from
an empty database and from an earlier database with a manual image.
