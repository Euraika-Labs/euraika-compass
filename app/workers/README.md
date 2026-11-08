# Optional model workers

The base Compass install does not download weights, install Torch/Kraken or start a vision server. The application still starts and shows which routes need configuration. Actual OCR/vision runs are explicit user actions.

## Local historical HTR

Use the [Kraken worker profile](kraken/README.md). Supply the executable, separately acquired recognition weights and segmentation weights in the worker's private settings. A native Windows backend can reach an optional Linux/WSL worker through `COMPASS_KRAKEN_WORKER_URL=http://127.0.0.1:8766`. The skeleton includes this loopback HTTP sidecar but does not install or start its environment. Model provenance, script/period coverage and licenses are recorded in `app/config/models.json` and the project research document. Do not place weights in Git.

## Local Qwen vision

Run a compatible local image-capable OpenAI endpoint with Qwen3.8-27B Q5_K_M and its matching vision projector. Start it with the served alias `Qwen3.8-27B`. The tested-on-paper file budget is not a measured GPU-memory guarantee. The application does not start, download or silently replace this model in the skeleton.

Set `COMPASS_QWEN_BASE_URL=http://127.0.0.1:8081/v1` in private backend configuration. Only loopback endpoints without URL credentials are accepted. This is separate from permission to use a cloud image model. The adapter sends the selected, backend-prepared image/crop and a literal transcription request; it does not send unrelated conversation history or generate fake word boxes.

## Optional cloud OCR

The working cloud adapter is Mistral OCR 4.1 (`mistral-ocr-4-1`). Configure `MISTRAL_API_KEY` outside Git, explicitly disable local-only mode with `COMPASS_LOCAL_ONLY=false`, and enable `mistral-ocr` in the UI. All three conditions are necessary before an explicit transcription request can send an image. The returned block coordinates use provider-page pixels and are not automatically exact word regions in the original photo.

Other cloud entries are catalog profiles only. They remain explicitly `not_implemented` when enabled; no fake readings or hidden provider fallback are used. Disabling a route prevents later calls. A pinned failed route must be explicitly unpinned or reassigned.
