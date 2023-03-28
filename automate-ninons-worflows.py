import os
import time
import subprocess
from kubernetes import client, config, stream
from kubernetes.stream import stream

github_for_aligner = ["Nine-s/nextflow_RS1_salmon", "Nine-s/nextflow_RS2_salmon"]
branch = ["master", "main"] 
experiments = ["RS1", "RS2"]
datasets = ["D1", "D2", "D3"]
path_to_work_folder = "/data/vasilis/"
path_to_trace_files = "/data/vasilis/"
path_to_nextflow = "nextflow"
name_of_volume = "nextflow-ninon"  
namespace = "default"  
helper_pod = "ubuntu-pod"
helper_container = "ubuntu-pod"


# Load the Kubernetes configuration
config.load_kube_config('/home/vasilis/.kube/config')

# Create an API client
api = client.CoreV1Api()

def check_pod_status(pod_name):
    pod = api.read_namespaced_pod_status(pod_name, namespace)
    return pod.status.phase


def execute_command_in_container(input_command):
    try:
        response = stream(api.connect_get_namespaced_pod_exec, helper_pod, namespace, command=['/bin/bash', '-c', input_command], container=helper_container, stderr=True, stdout=True)

        if response:
            print(f"Response: {response}")
        else:
            print("Empty response received. This does not indicate an error.")
    except Exception as e:
        print(f"An error occurred while executing the command: {e}")


for replicate in range(1, 4):
    for i in range(len(github_for_aligner)):
        for dataset in datasets:

            # ### get command to run the wfs
            name_of_config_file = "droso_" + experiments[i] + "_C4_" + dataset + "_salmon.config"
            print("Running " + name_of_config_file + "...")

            command_to_run = path_to_nextflow + " kuberun " + github_for_aligner[i] + " -r " + branch[i] + " -c " + name_of_config_file + " -v " + name_of_volume
            result = subprocess.run(command_to_run, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True) 
            output_lines = result.stdout.splitlines()
            print('Searching for pod name...')


            for line in output_lines:
                if "Pod started:" in line:
                    # Extract the pod name
                    pod_name = line.split("Pod started: ")[-1]
                    break
            
            try:
                print(f"Pod name: {pod_name}")
            except:
                print("Pod name not found. Exiting...")
                exit(1)

            while True:
                status = check_pod_status(pod_name)
                if status == "Succeeded":
                    print(f"Pod {pod_name} has succeeded.")
                    break
                elif status == "Failed":
                    print(f"Pod {pod_name} has failed.")
                    break
                else:
                    print(f"Pod {pod_name} is still running. Current status: {status}")
                    time.sleep(60)  # Sleep for 1 minute (60 seconds)


            # move trace files and rename the "work" folder
            new_folder_name = name_of_config_file.split(".config")[0] + "_replicate_" + str(replicate)
            move_traces_files_command = "mv "  + path_to_trace_files + "_* " + path_to_work_folder + "work"
            rename_work_folder = "mv " + path_to_work_folder + "work " + path_to_work_folder + new_folder_name

            # Prepare and execute the first command
            execute_command_in_container(move_traces_files_command)
            execute_command_in_container(rename_work_folder)
