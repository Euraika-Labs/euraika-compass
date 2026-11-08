# Kraken worker profile

The selected initial recognizer is **Kraken 7.1 / historical PP-OCRv6 medium**, model DOI [`10.5281/zenodo.21788410`](https://zenodo.org/records/21788410). Specialist recognition models are optional profiles, not guarantees for every manuscript. The executable and checkpoint versions must be compatible. Old `.mlmodel` profiles may need a separate older environment.

The official Kraken installation route is Linux/macOS. On Windows, use an isolated Linux/WSL environment rather than pretending native support has been verified. No installation, WSL distribution creation, GPU runtime modification or weight download happens in this skeleton.

In that environment, install a compatible Kraken version according to its official guide. Obtain both recognition and matching segmentation weights separately. Record hashes and model identity. Do not let a default segmentation step download an undisclosed model.

For a directly executable worker, set these private backend variables:

```dotenv
COMPASS_KRAKEN_EXECUTABLE=/absolute/path/to/venv/bin/kraken
COMPASS_KRAKEN_SEGMENTATION_MODEL=/private/models/segmentation.safetensors
COMPASS_KRAKEN_MEDIUM_MODEL=/private/models/medium.safetensors
```

The adapter executes structured arguments with no shell:

```text
kraken -a -i INPUT_IMAGE TEMPORARY_OUTPUT.xml segment -bl -m SEGMENTATION_MODEL ocr -m RECOGNITION_MODEL
```

ALTO text and actual line boxes are preserved. Missing coordinates and confidence are not invented. The task has a timeout and terminates its owned subprocess on cancellation; temporary output is cleaned up. Warnings remind the user that abbreviation and diacritic conventions can differ.

For the other profiles, configure `COMPASS_KRAKEN_BIBLIA_MODEL`, `COMPASS_KRAKEN_MELEAGRE_MODEL`, `COMPASS_KRAKEN_MUHARAF_MODEL` or `COMPASS_KRAKEN_ARAMS_MODEL`. Each also requires an appropriate explicitly configured segmenter.

## Native Windows backend with a Linux/WSL worker

Do not put `wsl.exe` into `COMPASS_KRAKEN_EXECUTABLE`: it is not a Kraken-compatible executable interface, and Windows paths do not automatically become Linux paths. The provided sidecar transfers only the selected image bytes over loopback, so no caller-controlled path or command is translated across that boundary.

In a separately prepared Linux/WSL Python environment, install the backend package and the optional worker requirements. Run from the repository root after configuring the Linux executable and checkpoint paths shown above:

```text
python -m pip install -e app/backend
python -m pip install -r app/workers/kraken/requirements.txt
python app/workers/kraken/serve.py --port 8766
```

The third command binds only to `127.0.0.1`. The first two may install a substantial ML runtime and are deliberate setup steps, not commands run by Compass's base install. Older specialist profiles can use their own compatible environment instead of the medium profile's requirement file.

In the native Windows backend settings, set:

```dotenv
COMPASS_KRAKEN_WORKER_URL=http://127.0.0.1:8766
```

The sidecar exposes `GET /health` and `POST /transcribe`, accepts only cataloged Kraken profile IDs, validates bounded PNG/JPEG/WebP uploads, and uses temporary private files. It reads model/executable paths from its own environment, never from a client request. It ignores its own worker-URL setting to prevent proxy recursion. The backend marks this route configured without network probing; a missing profile or unavailable worker produces an explicit error when the user starts a task.

The worker must be started and stopped explicitly in this skeleton. WSL creation, dependency installation, checkpoint download and native/WSL lifecycle supervision remain separate integration work; no such operation was executed while building these files.

References: [Kraken installation](https://kraken.re/main/getting_started.html), [historical model research](../../../docs/research/2026-11-08-ocr-htr-model-selection.md).
