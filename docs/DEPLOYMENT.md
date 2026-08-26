# Deployment

✅ **live on Cloud Run** — `grantloop-orchestrator`, project `active-future-506706-s7`, region `us-central1`.

```
https://grantloop-orchestrator-361788129265.us-central1.run.app
```

⚠️ **The URL requires authentication.** An org policy on the project
(`constraints/iam.allowedPolicyMemberDomains`) blocks granting `allUsers`, so the service cannot be
made public from this account. This does **not** affect eligibility: the rules state the app
"does not need to be publicly accessible or live at the exact moment of submission or judging" and
that clear proof of Google Cloud deployment in the demo video and repo is what is required.

Reach it with an identity token:

```bash
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://grantloop-orchestrator-361788129265.us-central1.run.app/api/health
```

## Deploy

```bash
gcloud run deploy grantloop-orchestrator --source . --region us-central1 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=active-future-506706-s7,MODEL_ID=gemini-3.5-flash,GOOGLE_CLOUD_LOCATION=global,GRANTLOOP_ROOT=/app" \
  --memory 512Mi --cpu 1 --max-instances 3 --timeout 60
```

Nothing is baked into the image. Both the project and the model have moved once already.

## Verified live

| Check | Result |
|---|---|
| `/api/health` | `mode: cloud`, `citations_verified: true` |
| Gemini 3.5 reachable | `model_lane.questions_drafted_by` includes `gemini` |
| Escalation question | model-written, names the actual counterparty |
| Dashboard | served from the same origin at `/dashboard/` |

<details>
<summary>Four things that broke on the way, and what they teach</summary>

**Vertex serves Gemini 3.x from `global` only.** `us-central1` returns 404 for
`gemini-3.5-flash`. A 404 on a publisher model reads like an auth failure and is not one.
Verified directly: global 200, us-central1 404.

**ADC and the gcloud CLI can be different accounts.** `curl` with `gcloud auth print-access-token`
worked while the SDK got 403, because application-default credentials on that machine belonged to
an entirely different Google account. Check with the userinfo endpoint, not by assuming.

**Gemini 3.x thinking tokens come out of `max_output_tokens`.** At 200 the answer was truncated
mid-sentence and our own usability check rejected it, so the model lane silently never worked while
every screen looked correct. A tight budget does not produce a short answer, it produces a
truncated one.

**setuptools flat-layout discovery** treats `schema/`, `seed/` and `dashboard/` as packages and
refuses to build. Packages are declared explicitly, and data paths resolve through
`grantloop/paths.py` with `GRANTLOOP_ROOT` rather than from `__file__`.

The third one was only findable because the previous commit made the fallback reason visible in
`/api/health`. A silent fallback is correct behaviour and a terrible diagnostic.

</details>

## Open

Public access needs the project owner to permit `allUsers` (org policy) and then grant
`roles/run.invoker`. Optional, per the rules above.
