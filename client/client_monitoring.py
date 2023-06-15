import grpc
import bidirectional_pb2_grpc as bidirectional_pb2_grpc
import bidirectional_pb2 as bidirectional_pb2
from google.protobuf import descriptor_pool, json_format
import hashlib
import os
import docker
from pprint import pprint
import json
import yaml
import datetime


# Execute the actions requested by the server
def executor(containerID, action):
	try:
		container = docker.from_env().containers.get(containerID)
	except Exception as e:
		return
	if type(action) == str:
		if action.lower() in ["remove", "rm"]:
			container.remove(force=True)
		elif action.lower() in ["restart"]:
			container.restart()
		elif action.lower() in ["stop"]:
			container.stop()

# Computes the hash of the measurements file
def hash_file(filename):
		h = hashlib.sha1()
		with open(filename,'rb') as file:
				lines = file.readlines()

		for i in lines:
				h.update(i)
		return h.hexdigest(), len(lines), lines

# Compare the values ​​of the measurements files with the previously saved values ​​looking for updates
def collector():
		global files_hash
		new_hash = {}
		diff = {}
		client = docker.from_env()
		for container_file in os.listdir(ima_path):
				if container_file in ignore:
						continue
				digest, file_length, lines = hash_file(ima_path + container_file)
				new_hash[container_file] = {"digest" : digest, "length" : file_length}
				if container_file not in files_hash:
						diff[container_file] = new_hash[container_file]
						diff[container_file]["new_file"] = True
						container_image = client.containers.get(container_file)
						new_hash[container_file]["imageName"] = container_image.attrs['Config']['Image']
						new_hash[container_file]["imageID"] = container_image.id
				elif files_hash[container_file]["digest"] != new_hash[container_file]["digest"]:
						new_hash[container_file]["imageName"] = files_hash[container_file]["imageName"]
						new_hash[container_file]["imageID"] = files_hash[container_file]["imageID"]

						diff[container_file] = dict(new_hash[container_file])
						new_lines = []
						for j in range(file_length - files_hash[container_file]["length"]):
								new_lines.append(lines[files_hash[container_file]["length"] + j].decode("utf-8"))

						del files_hash[container_file]
						diff[container_file]["new_lines"] = new_lines
						diff[container_file]["new_file"] = False
				else:
						new_hash[container_file]["imageName"] = files_hash[container_file]["imageName"]
						new_hash[container_file]["imageID"] = files_hash[container_file]["imageID"]

		diff.update(files_hash)
		files_hash = new_hash
		return diff

# Compares each new line with the expected values in the whitelist
def analyzer(image, new_lines):
	global whitelist_folder
	try:
		with open(whitelist_folder + image.replace(":","-") + ".txt",'r') as file:
			whitelist = file.readlines()
	except:
		return [(image, "NO_WHITELIST")]

	output = {}

	for line in new_lines:
		entry = line.split()
		if len(entry) == 2:
			file_hash, file_path = entry
			for j in whitelist:
				if file_path in j.split():
					if file_hash in j.split():
						if line in output:
							del output[line]
						break
					else:
						output[line] = "INVALID_HASH"
			else:
				if line not in output:
					output[line] = "ENTRY_NOT_FOUND"
		else:
			output[line] = "INVALID_ENTRY"
  
	return list(output.items())


def make_message(message):
	return bidirectional_pb2.Message(
		message=message
	)


def generate_messages():
	global files_hash
	while True:
		try:
			diff = collector()
			for containerID, container_info in diff.items():
				if "new_file" in container_info and container_info["new_file"] == False:
					notificate = analyzer(container_info["imageName"], container_info["new_lines"])
					
					if notificate:
						pprint(notificate)
						for each_notification in notificate:
							notification = {"containerID": containerID, "notificate": each_notification[1], "imageName" : files_hash[containerID]["imageName"], "imageID" : files_hash[containerID]["imageID"], "line": each_notification[0]}
							
							msg = make_message(json.dumps(notification))
							yield msg
		except Exception as e:
			print("Error on generate_messages", e)

def send_message(stub):
	responses = stub.GetServerResponse(generate_messages())
   
	for response in responses:

		
		server_msg = json.loads(response.message)
		if 'containerID' in server_msg and 'action' in server_msg:
			container_id = server_msg['containerID']
			action = server_msg['action']
			print("Action from server %s" % response.message)
			executor(container_id,action)



def run():
	global SERVER_ADRESS, SERVER_PORT
	with grpc.insecure_channel(SERVER_ADRESS + ':' + SERVER_PORT) as channel:
		stub = bidirectional_pb2_grpc.BidirectionalStub(channel)
		send_message(stub)



if __name__ == '__main__':
	global config, SERVER_ADRESS, SERVER_PORT, whitelist_folder
	try:
		with open('config.yaml', 'r') as file:
			config = yaml.safe_load(file)
	except Exception as e:
		print("Cant load config file",e)
		config = {}
	

	whitelist_folder = config.get("WHITELIST_FOLDER", "/root/TCC/whitelist/")
	SERVER_PORT = config.get("SERVER_PORT", "50051")
	SERVER_ADRESS = config.get("SERVER_ADRESS", "127.0.0.1")
	
	
	ima_path = "/sys/kernel/security/csma/"
	ignore = ['cpcr', 'hpcr', 'runtime_measurements_count', 'ascii_runtime_measurements', 'binary_runtime_measurements']

	files_hash = {}
	collector()
	print("Running...")
	run()


