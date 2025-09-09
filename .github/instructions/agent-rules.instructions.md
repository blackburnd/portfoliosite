---
applyTo: '**'

Never add css <style> blocks to html, css belongs in css files only.

Never offer to commit and push changes unless you have actually made meaningful changes to files. Check git status or git diff first to verify there are actual changes to commit.

Do not ask for permission before running basic git commands like git status or git add.

DO NOT attempt to run the application locally or install requirements. This is a PRODUCTION application that runs on Google Cloud Platform. Do not pollute the local environment with package installations. Use production logs and debugging endpoints instead.

IMPORTANT: Production logs can ONLY be read from the VM instance running on Google Cloud. Use 'gcloud compute instances list' first to find the instance, then SSH into it to access logs via journalctl or application log files. Local logs are not relevant for production debugging.

---
Provide project context and coding guidelines that AI should follow when generating code, answering questions, or reviewing changes.