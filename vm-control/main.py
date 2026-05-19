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
