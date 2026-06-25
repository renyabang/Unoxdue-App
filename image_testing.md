# Image Integration Testing Playbook

## TEST AGENT PROMPT – IMAGE INTEGRATION RULES
Follow these rules exactly. Do not overcomplicate.

### Image Handling Rules
- Always use base64-encoded images for all tests and requests.
- Accepted formats: JPEG, PNG, WEBP only.
- Do not use SVG, BMP, HEIC, or other formats.
- Do not upload blank, solid-color, or uniform-variance images.
- Every image must contain real visual features (objects, edges, textures, shadows).
- If the image is not PNG/JPEG/WEBP, transcode it to PNG or JPEG before upload.
  - If you read a .jpg but the content is actually PNG after conversion/compression — invalid. Always re-detect and update the MIME after transformations.
- If the image is animated (GIF, APNG, WEBP animation), extract the first frame only.
- Resize large images to reasonable bounds (avoid oversized payloads).

## Notes for UnoXdue
- OCR schedine usa OpenAI Vision via Emergent LLM key (`EMERGENT_LLM_KEY`), model `gpt-5.4`.
- Endpoint: `POST /api/admin/predictions/ocr` (multipart image upload).
- Output: JSON strutturato (tipster, partite, mercati, selezioni, quote) SENZA importi/bonus/branding.
