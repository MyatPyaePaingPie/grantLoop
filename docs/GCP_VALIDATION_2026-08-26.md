# GCP / Gemini validation — 2026-08-26

Run from Aria's machine, account `ariaxhan@gmail.com`, project `modelmind-491801`.

## Result summary

| Check | Status | Evidence |
|---|---|---|
| gcloud CLI | OK | SDK 571.0.0 |
| ADC present | OK | `~/.config/gcloud/application_default_credentials.json` |
| Vertex AI API enabled | OK | `aiplatform.googleapis.com` in `gcloud services list --enabled` |
| Pub/Sub API enabled | OK | `pubsub.googleapis.com` |
| Cloud Run enabled | **NO** | absent from enabled services |
| Firestore enabled | **NO** | absent from enabled services |
| Artifact Registry / Cloud Build enabled | **NO** | absent from enabled services |
| `gemini-2.5-flash` generateContent | **OK (200)** | 3/3 successful calls, us-central1 |
| `gemini-2.5-pro` | 404 | us-central1 |
| `gemini-3-pro-preview` | 404 | us-central1 and global |
| `gemini-3-flash-preview` | 404 | us-central1 |
| `gemini-3.5-pro` | 404 | us-central1 and global |
| `gemini-3.5-flash` | 404 | us-central1 |
| Google ADK python package | not installed | `import google.adk` -> ModuleNotFoundError |

## Gotcha found (would have cost hours)

Raw REST calls to Vertex with user ADC fail with:

> `PERMISSION_DENIED` — "authenticating by using local Application Default Credentials.
> The aiplatform.googleapis.com API requires a quota project, which is not set by default."

Fix — either set it once:

```
gcloud auth application-default set-quota-project modelmind-491801
```

or send the header on every call: `x-goog-user-project: modelmind-491801`.
The ADK/`google-genai` SDK path needs the same thing via
`GOOGLE_CLOUD_PROJECT` + `GOOGLE_GENAI_USE_VERTEXAI=true`.

Working call, verified:

```
curl -X POST \
 "https://us-central1-aiplatform.googleapis.com/v1/projects/modelmind-491801/locations/us-central1/publishers/google/models/gemini-2.5-flash:generateContent" \
 -H "Authorization: Bearer $(gcloud auth print-access-token)" \
 -H "x-goog-user-project: modelmind-491801" \
 -H "Content-Type: application/json" \
 -d '{"contents":[{"role":"user","parts":[{"text":"hi"}]}]}'
```

## BLOCKER

The submission requires Gemini 3.5+. On this project, **only `gemini-2.5-flash`
answers**; every 3.x model id returns 404. A 404 on a publisher model means the
model is not served to this project/region combination — it is not an auth error.

Unresolved, and I could not resolve it from here. Likely causes, in order:
1. Gemini 3.x needs to be enabled/allowlisted in Vertex Model Garden for the project.
2. It is served from a different region than us-central1/global for this account.
3. It is available on the AI Studio / `generativelanguage.googleapis.com` key path
   rather than the Vertex ADC path (needs a `GEMINI_API_KEY`, which is not in env here).

**Action for Aria, in the browser, today:** open Vertex AI Model Garden in
`modelmind-491801`, confirm which Gemini 3.x ids are enabled and in which region,
and grab an AI Studio API key as the fallback path.
Until a 3.x id returns 200, build against `gemini-2.5-flash` behind a single
`MODEL_ID` env var so the swap is one line.

## Enable the rest of the APIs (not yet run — needs billing confirmation)

```
gcloud services enable run.googleapis.com firestore.googleapis.com \
  artifactregistry.googleapis.com cloudbuild.googleapis.com \
  eventarc.googleapis.com --project=modelmind-491801
```
