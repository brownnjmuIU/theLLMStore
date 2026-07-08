# PPLLM Studio Transfer Document

Prepared for: Prof. Nick Brown and future FADS/PPLLM developers  
Prepared by: Manas Dani  
Last updated: July 8, 2026

## 1. Executive Summary

PPLLM Studio is a privacy-first, local-first educational AI prototype. The project began as a way to process local files into usable text/chunk artifacts for external LLM tools, then evolved into a more complete desktop application with its own local Assistant and public website presence.

The current project has three major pieces:

- **PPLLM Studio desktop app**
  - Python/PySide6 desktop app.
  - Processes local files into raw text and chunk JSON artifacts.
  - Optionally encrypts generated artifacts.
  - Includes a local Assistant powered by Ollama.
- **theLLMStore.com**
  - Static public research/education website.
  - Hosts the PPLLM Studio product/resource page.
  - Provides the Windows download link and setup notes.
- **Browser-based PPLLM Studio prototype**
  - Static front-end proof of concept for NSF/IU grant review.
  - Simulates the local workflow in a browser.
  - No real upload, backend, API, model, or server processing.

The project tone should remain research-oriented, educational, privacy-focused, and public-benefit oriented. Avoid making the site feel like a commercial marketplace or sales product.

## 2. People and Ownership

- **Prof. Nick Brown**
  - Project lead and supervisor.
  - Provides weekly task instructions.
  - Owns the GitHub/Render/Cloudflare deployment context.
- **Manas Dani**
  - Student/developer who built the PPLLM Studio prototype, Assistant, website, Qualtrics prototype, and Week 22 browser proof of concept.
- **Future developer**
  - Should first read this file, `FADS_PROJECT_CONTEXT.md`, and `FADS Summer/summer_progress.md`.

## 3. Important Repositories and Paths

Local FADS workspace:

```text
/Users/manasdani/Documents/FADS
```

Primary local project context:

```text
/Users/manasdani/Documents/FADS/FADS_PROJECT_CONTEXT.md
/Users/manasdani/Documents/FADS/FADS Summer/summer_progress.md
```

Polished UI/website worktree:

```text
/Users/manasdani/Documents/FADS/.worktrees/ppllm-ui-redesign
```

Nick deployment repository copy:

```text
/Users/manasdani/Documents/FADS/.worktrees/ppllm-ui-redesign/.deploy/theLLMStore
```

GitHub deployment repository:

```text
https://github.com/brownnjmuIU/theLLMStore
```

Deployment branch:

```text
ppllm-studio-site
```

Live production site:

```text
https://thellmstore.com
https://thellmstore.com/ppllm-studio.html
```

New Week 22 browser prototype path after Render redeploy:

```text
https://thellmstore.com/ppllm-browser.html
```

## 4. Project History by Phase

### Early Direction

The project originally focused on helping users prepare local files for LLM workflows. The broader PPLLM idea is to give users more control over data permissions, file processing, privacy, and responsible AI use.

Core local workflow:

1. Select local files.
2. Extract readable text.
3. Clean/process text.
4. Create chunks.
5. Optionally encrypt local output artifacts.
6. Use processed chunks for source-grounded AI assistance.

### Week 18: Built-In Assistant Prototype

Nick asked whether PPLLM could include its own LLM/chatbot interface instead of requiring users to move chunk JSON files into AnythingLLM or another external application.

Completed:

- Added chatbot backend modules.
- Loaded PPLLM chunk JSON artifacts.
- Built a simple keyword retriever.
- Built a RAG-style prompt builder.
- Added an Ollama model connector.
- Added a fake connector for tests.
- Added a service layer connecting chunks, retrieval, prompt building, model response, and source IDs.
- Added a CLI path for testing outside the UI.
- Added an Assistant tab inside the PySide6 desktop app.

Important files:

```text
chatbot/chunk_loader.py
chatbot/retriever.py
chatbot/model_connectors.py
chatbot/rag_service.py
chatbot_cli.py
desktop_app.py
```

Important model assumption:

```text
ollama pull llama3.1:8b
```

The Assistant uses local Ollama at:

```text
http://127.0.0.1:11434/api/generate
```

### Week 19: Educational Interventions and Source Transparency

The goal shifted from only making the Assistant work to making the UI teach responsible AI concepts.

Completed:

- Renamed/redesigned the app as **PPLLM Studio**.
- Added a calmer, more beginner-friendly PySide6 UI.
- Added workflow rail: Ingest, Process, Assistant, Export.
- Added local-first messaging.
- Added hover guidance and `i` explanations.
- Added chunking explanation and simple chunk visual.
- Added a data journey flow showing file -> chunks -> local JSON -> encryption.
- Made source chips clickable.
- Added a custom source preview dialog showing chunk ID, source file, and chunk text.
- Improved retrieval behavior for broad overview and listed-item questions.
- Added UI polish: collapsible workflow sidebar, compact activity log, chat avatars, Stop button, permission review, Copy Path, and Open Folder.

Verification at that point:

- 43 chatbot/UI tests passing.
- Python compile checks passing for the main chatbot modules and `desktop_app.py`.

Remaining from this phase:

- Retrieval is still keyword/basic heuristic retrieval, not semantic RAG.
- Model settings UI is not built.
- Full persistent activity history tab is not built.
- Source display can be tightened further.

### Week 20: Public Rollout and theLLMStore

Nick asked to make PPLLM Studio available through theLLMStore.com and prepare a public research/education website.

Completed:

- Created static website under `website/`.
- Preserved old repository files rather than deleting old AI Visibility Tool code.
- Built homepage for `theLLMStore` as a public local-AI research/resource hub.
- Built PPLLM Studio product/resource page.
- Added Windows download section.
- Added setup instructions and SmartScreen note.
- Added Ollama setup instructions.
- Added FAQ for first-time Windows users and classroom testers.
- Published the Windows ZIP as a GitHub Release asset.
- Connected Render and Cloudflare.

Important live URLs:

```text
https://thellmstore.com
https://thellmstore.com/ppllm-studio.html
https://github.com/brownnjmuIU/theLLMStore/releases/tag/v0.1
```

Important release asset:

```text
PPLLM-Studio-Windows-v0.1.zip
```

Important packaging note:

- The Windows build is a PyInstaller `--onedir` build.
- Users must unzip the full folder.
- Users must keep `_internal/` next to `LLM_Bundler_Desktop.exe`.
- The executable should not be moved by itself.
- Windows SmartScreen may appear because this is an unsigned early prototype.

### Week 21: Qualtrics Evaluation Prototype

Nick asked whether a portion of PPLLM Studio could run inside Qualtrics for Prolific/product evaluation without redirecting participants away from the Qualtrics survey.

Completed:

- Confirmed Qualtrics feasibility.
- Created a Text / Graphic Qualtrics question.
- Used Qualtrics Question JavaScript to inject a front-end-only PPLLM Studio simulation directly into the survey.
- Kept participants inside Qualtrics.
- Avoided real file upload, backend calls, API calls, and live model calls.

Important file:

```text
/Users/manasdani/Documents/FADS/qualtrics-prototype/qualtrics-inline.js
```

Prototype features:

- Ingest step.
- Process file step.
- Assistant interaction.
- Source transparency/citation preview.
- Simulated/hardcoded Assistant response.

Nick later said he would take over Qualtrics from that point forward.

### Week 22: Browser-Based PPLLM Studio

Nick asked for a lightweight browser-based PPLLM Studio on theLLMStore.com so NSF and IU grant managers could interact with the concept before funding arrives.

Completed:

- Added a standalone static browser proof-of-concept page:

```text
website/ppllm-browser.html
```

- Linked it from:

```text
website/index.html
website/ppllm-studio.html
```

- Added browser app styles to:

```text
website/styles.css
```

- Added Week 22 specific notes:

```text
WEEK22_TRANSFER.md
```

The browser prototype simulates:

- local file selection,
- text extraction,
- cleaning,
- chunking,
- optional encryption,
- Assistant responses,
- source citation inspection.

It intentionally does not:

- upload files,
- read real file bytes,
- extract PDFs,
- call Ollama,
- call a hosted LLM,
- use an API key,
- require a backend,
- require a database.

GitHub state:

- Week 22 browser prototype commit:

```text
fff0998 Add browser PPLLM Studio prototype
```

- Empty redeploy trigger commit:

```text
3c11c0d Trigger Render redeploy
```

As of July 8, 2026, the code is pushed to GitHub, but Render was still serving the older June 27 build. Manual Render redeploy may be required.

## 5. Current Desktop App State

The desktop app is built with:

- Python
- PySide6
- PyInstaller for Windows packaging
- Ollama for local Assistant responses

Core user workflow:

1. Open PPLLM Studio.
2. Select a local file.
3. Review local file/permission guidance.
4. Extract readable text.
5. Process into chunks.
6. Optionally encrypt output artifacts.
7. Ask questions in the Assistant.
8. Inspect source chunks.
9. Export/use local artifacts.

Current strengths:

- Local-first workflow is clear.
- Assistant can answer from processed chunks.
- Streaming avoids freezing the UI.
- Source chips support transparency.
- Educational cues explain local AI, chunks, source grounding, and artifact handling.

Current limitations:

- Retrieval is still keyword/basic heuristic.
- No semantic embeddings or vector database yet.
- Model selection UI is not implemented.
- Assistant currently expects Ollama and `llama3.1:8b`.
- Error handling around missing Ollama/model can be clearer.
- Windows build should eventually use PyInstaller `--windowed`.
- Desktop build should be revalidated before a broader release.

## 6. Current Website State

Website location in deployment repo:

```text
website/
```

Main files:

```text
website/index.html
website/ppllm-studio.html
website/ppllm-browser.html
website/styles.css
render.yaml
```

Render config:

```yaml
services:
  - type: web
    name: thellmstore
    runtime: static
    buildCommand: ""
    staticPublishPath: website
```

Current website purpose:

- Public home for local AI research and education resources.
- PPLLM Studio as the first research tool/resource.
- Future home for demos, papers, survey findings, videos, and classroom materials.

Important tone:

- Scientific communication.
- Societal benefit.
- Responsible AI education.
- Privacy-first local workflows.
- Avoid commercial marketplace language.

## 7. Deployment Status

GitHub:

- Repository: `brownnjmuIU/theLLMStore`
- Branch: `ppllm-studio-site`
- Latest pushed commit as of this transfer document: `3c11c0d`

Render:

- Service name: `theLLMStore`
- Static publish path: `website`
- Render URL: `https://thellmstore-wd92.onrender.com`

Cloudflare:

- `thellmstore.com` points to the Render service.
- `www.thellmstore.com` redirects to `thellmstore.com`.

Known deployment issue:

- The GitHub branch contains the Week 22 browser prototype.
- Render did not automatically redeploy after the Week 22 push or the empty redeploy trigger commit.
- Manual Render redeploy is likely needed.

Manual redeploy path:

1. Log in to Render.
2. Open service `theLLMStore`.
3. Click `Manual Deploy`.
4. Choose `Deploy latest commit`.
5. Confirm the deployed branch is `ppllm-studio-site`.
6. Confirm the publish path is `website`.
7. Test:

```text
https://thellmstore.com/ppllm-browser.html
```

## 8. Local Testing Instructions

To test the website locally from the deployment repository:

```bash
cd /Users/manasdani/Documents/FADS/.worktrees/ppllm-ui-redesign/.deploy/theLLMStore/website
python3 -m http.server 8013 --bind 127.0.0.1
```

Open:

```text
http://127.0.0.1:8013/
http://127.0.0.1:8013/ppllm-studio.html
http://127.0.0.1:8013/ppllm-browser.html
```

Week 22 local verification completed:

- `/` returned HTTP `200`.
- `/ppllm-studio.html` returned HTTP `200`.
- `/ppllm-browser.html` returned HTTP `200`.
- Browser demo interaction worked:
  - sample file selection,
  - sample processing,
  - Assistant response,
  - source modal preview.
- Desktop and mobile checks showed no horizontal overflow.

## 9. Security and Secrets

Do not commit or write any passwords, API keys, Render credentials, GitHub tokens, Cloudflare passwords, or model API keys into files.

If account access is needed, Nick should provide credentials through a secure channel. Do not copy credentials into transfer files, code comments, commits, or chat logs.

The current Week 22 browser prototype is safe from an API/secret standpoint because it is static and does not call external services.

## 10. Recommended Next Developer Priorities

### Immediate

1. Redeploy Render so the Week 22 browser page is live.
2. Confirm:

```text
https://thellmstore.com/ppllm-browser.html
```

3. Send Nick the live URL and a short summary of what is simulated.

### Short Term

1. Improve browser prototype copy if Nick wants more grant-facing polish.
2. Add screenshots or short GIF/video walkthroughs if needed for NSF/IU materials.
3. Update `FADS_PROJECT_CONTEXT.md` and `summer_progress.md` after deployment is live.
4. Review whether `WEEK22_TRANSFER.md` should be merged into this broader `TRANSFER.md`.

### Desktop App Improvements

1. Add model settings UI for Ollama model choice.
2. Add clearer error messages when Ollama is missing or not running.
3. Add semantic or hybrid retrieval.
4. Improve source preview metadata with page numbers where extractors support it.
5. Add persistent activity/history view.
6. Rebuild and retest Windows package using PyInstaller `--windowed`.

### Future Funded Web App Path

If funding supports a real browser/server version, do not simply bolt a backend onto the static prototype. First define the API contract.

Recommended future architecture:

1. Browser frontend.
2. Auth or study/session layer if needed.
3. File upload or browser-local file access policy.
4. Server-side extraction workers.
5. Chunk artifact storage.
6. Optional encryption.
7. Retrieval service.
8. Model connector.
9. Source preview endpoint.
10. Admin/research logging that respects IRB/privacy requirements.

## 11. What Not To Do

- Do not remove old AI Visibility Tool code unless Nick explicitly asks.
- Do not turn theLLMStore into a purely commercial marketplace.
- Do not add paid APIs or hosted model calls before Nick confirms funding and IRB/product-evaluation needs.
- Do not upload real participant files in the current browser prototype.
- Do not claim the browser prototype performs real extraction or real AI inference.
- Do not commit secrets.

## 12. Best Next Email Summary for Nick

The concise status to give Nick is:

```text
The browser-based PPLLM Studio prototype is complete and pushed to the GitHub deployment branch. It works locally as a front-end proof of concept with simulated ingest, processing, Assistant interaction, and source citations. The transfer documentation has also been prepared. The only remaining deployment step is a Render redeploy so the new page appears live at https://thellmstore.com/ppllm-browser.html.
```

## 13. Final Handoff Note

The strongest project direction is to keep PPLLM Studio as a local-first educational AI tool, with theLLMStore acting as the public research communication hub. The current browser prototype is useful for grants and stakeholder review, but the desktop app remains the real privacy-preserving implementation until funding supports a proper backend-connected web version.
