# GCP Serverless VM Start/Stop Demo (AWS Lambda Equivalent)

This demo shows how to use **Google Cloud Functions Gen2** (AWS Lambda equivalent) to start and stop a Compute Engine VM via HTTP trigger.

Architecture:

```text
HTTP Request --> Cloud Function --> Compute Engine API --> Start/Stop VM
```


# 1. Set Variables

```bash
export PROJECT_ID=$(gcloud config get-value project)
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
export REGION=us-central1
export ZONE=us-central1-a
export VM_NAME=demo-vm
export FUNCTION_NAME=vm-controller
export FUNCTION_SA=vm-function-sa
export BUCKET_NAME=${PROJECT_ID}-function-demo-$(date +%s)
```

Verify:

```bash
echo $PROJECT_ID
echo $PROJECT_NUMBER
```

---

# 2. Enable Required APIs

```bash
gcloud services enable \
  compute.googleapis.com \
  cloudfunctions.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  run.googleapis.com \
  storage.googleapis.com
```

---

# 3. Create VM

```bash
gcloud compute instances create $VM_NAME \
  --zone=$ZONE \
  --machine-type=e2-micro \
  --image-family=debian-12 \
  --image-project=debian-cloud
```

Check:

```bash
gcloud compute instances list
```

---

# 4. Create Storage Bucket

```bash
gcloud storage buckets create gs://$BUCKET_NAME --location=$REGION
```

Check:

```bash
gcloud storage buckets list
```

---

# 5. Create Service Account

```bash
gcloud iam service-accounts create $FUNCTION_SA \
  --display-name="VM Function Service Account"
```

---

# 6. Grant IAM Permissions

## Function service account permissions

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${FUNCTION_SA}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/compute.instanceAdmin.v1"
```

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${FUNCTION_SA}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

---

## Build service account permissions (required for Gen2)

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.builder"
```

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"
```

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/logging.logWriter"
```

---

# 7. Create Function Code

Create folder:

```bash
mkdir vm-control
cd vm-control
```

---

## main.py

```python
from googleapiclient import discovery
import functions_framework
import os

PROJECT = os.environ["PROJECT_ID"]
ZONE = os.environ["ZONE"]
VM_NAME = os.environ["VM_NAME"]

@functions_framework.http
def vm_control(request):
    action = request.args.get("action")

    compute = discovery.build("compute", "v1")

    if action == "start":
        compute.instances().start(
            project=PROJECT,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        return f"{VM_NAME} starting"

    elif action == "stop":
        compute.instances().stop(
            project=PROJECT,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        return f"{VM_NAME} stopping"

    else:
        return "Use ?action=start or ?action=stop", 400
```

---

## requirements.txt

```txt
google-api-python-client
functions-framework
```

---

# 8. Deploy Function

```bash
gcloud functions deploy $FUNCTION_NAME \
  --gen2 \
  --runtime python311 \
  --region=$REGION \
  --source=. \
  --entry-point vm_control \
  --trigger-http \
  --allow-unauthenticated \
  --service-account=${FUNCTION_SA}@${PROJECT_ID}.iam.gserviceaccount.com \
  --set-env-vars PROJECT_ID=$PROJECT_ID,ZONE=$ZONE,VM_NAME=$VM_NAME
```

---

# 9. Get Function URL

```bash
gcloud functions describe $FUNCTION_NAME \
  --region=$REGION \
  --format="value(serviceConfig.uri)"
```

Save:

```bash
export FUNCTION_URL=$(gcloud functions describe $FUNCTION_NAME \
  --region=$REGION \
  --format="value(serviceConfig.uri)")
```

---

# 10. Test Start VM

```bash
curl "$FUNCTION_URL?action=start"
```

Expected:

```text
demo-vm starting
```

Check:

```bash
gcloud compute instances list
```

Expected status:

```text
RUNNING
```

---

# 11. Test Stop VM

```bash
curl "$FUNCTION_URL?action=stop"
```

Expected:

```text
demo-vm stopping
```

Check:

```bash
gcloud compute instances list
```

Expected:

```text
TERMINATED
```

---

# Troubleshooting

Check builds:

```bash
gcloud builds list
```

View logs:

```bash
gcloud builds log BUILD_ID --region=$REGION
```

Function logs:

```bash
gcloud functions logs read $FUNCTION_NAME --region=$REGION
```

---

# Cleanup (Delete Everything)

## Delete Cloud Function

```bash
gcloud functions delete $FUNCTION_NAME \
  --region=$REGION \
  --quiet
```

---

## Delete VM

```bash
gcloud compute instances delete $VM_NAME \
  --zone=$ZONE \
  --quiet
```

---

## Delete Bucket

```bash
gcloud storage rm --recursive gs://$BUCKET_NAME
```

Then:

```bash
gcloud storage buckets delete gs://$BUCKET_NAME
```

---

## Delete Service Account

```bash
gcloud iam service-accounts delete \
  ${FUNCTION_SA}@${PROJECT_ID}.iam.gserviceaccount.com \
  --quiet
```

---

# Optional: Remove IAM Bindings

```bash
gcloud projects remove-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.builder"
```

```bash
gcloud projects remove-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"
```

```bash
gcloud projects remove-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/logging.logWriter"
```

```bash
gcloud projects remove-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${FUNCTION_SA}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/compute.instanceAdmin.v1"
```

```bash
gcloud projects remove-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${FUNCTION_SA}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

---

# Demo Flow

1. Show VM stopped
2. Trigger start
3. Show VM running
4. Trigger stop
5. Show VM terminated

Commands:

```bash
curl "$FUNCTION_URL?action=start"
curl "$FUNCTION_URL?action=stop"
```

---

# End
