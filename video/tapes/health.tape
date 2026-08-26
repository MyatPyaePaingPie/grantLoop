# Beat 6b: the Google Cloud proof shot.
#
# A live request to the deployed Cloud Run service. Shows mode cloud, the Gemini
# model id, location global, and the model lane reporting that Gemini actually
# answered rather than falling back. This single frame is the GCP + Gemini proof.
Output video/build/shots/health.mp4
Set Theme "Catppuccin Mocha"
Set FontSize 18
Set Width 1500
Set Height 700
Set Padding 30
Set TypingSpeed 25ms

Type 'TOKEN=$(gcloud auth print-identity-token)'
Sleep 400ms
Enter
Sleep 2s
Type 'SERVICE=https://grantloop-orchestrator-361788129265.us-central1.run.app'
Sleep 400ms
Enter
Sleep 500ms
Type 'curl -s -H "Authorization: Bearer $TOKEN" $SERVICE/api/health | jq'
Sleep 700ms
Enter
Sleep 11s
