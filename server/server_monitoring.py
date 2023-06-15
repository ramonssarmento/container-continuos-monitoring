from concurrent import futures
import yaml

import grpc
import bidirectional_pb2_grpc as bidirectional_pb2_grpc
import bidirectional_pb2 as bidirectional_pb2
import json
from google.protobuf import json_format

def make_message(message):
	return bidirectional_pb2.Message(
		message=message
	)


def resolver(message):
	global config
	try:
		with open('config.yaml', 'r') as file:
			config = yaml.safe_load(file)
	except:
		print("Cant load config file")
		config = {}
	
	with open('log.txt', 'a') as file:
		current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		file.write("[%s] %s\n" % (current_date, message))
	
	msg = json.loads(json.loads(json_format.MessageToJson(message)).get('message',"{}"))	
	print(msg)
	
	container_id = msg.get("containerID","")
	image_id = msg.get("imageID","")
	image_name = msg.get("imageName","")

	# Verificar se as ações estão presentes
	if 'Actions' in config:
		actions = config['Actions']
		
		if msg["notificate"] in actions:
			action = actions[msg["notificate"]]
			if 'ByContainerID' in action and container_id in action['ByContainerID']:
				action_name = action['ByContainerID'][container_id]
				message = '{"containerID":"%s", "action":"%s"}' % (container_id, action_name)
				return make_message(message)

			if 'ByContainerImageID' in action and image_id in action['ByContainerImageID']:
				action_name = action['ByContainerImageID'][image_id]
				message = '{"containerID":"%s", "action":"%s"}' % (container_id, action_name)
				return make_message(message)

			if 'ByContainerImageName' in action and image_name in action['ByContainerImageName']:
				action_name = action['ByContainerImageName'][image_name]
				message = '{"containerID":"%s", "action":"%s"}' % (container_id, action_name)
				return make_message(message)

			if 'Default' in action:
				action_name = action['Default']
				message = '{"containerID":"%s", "action":"%s"}' % (container_id, action_name)
				return make_message(message)
		else:
			print("No actions to", msg["notificate"])



class BidirectionalService(bidirectional_pb2_grpc.BidirectionalServicer):
	def GetServerResponse(self, request_iterator, context):
		for message in request_iterator:
			resultado = resolver(message)
			yield resultado
			


def serve():
	global config
	server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
	bidirectional_pb2_grpc.add_BidirectionalServicer_to_server(BidirectionalService(), server)
	if "PORT" in config:
		server.add_insecure_port('[::]:' + config["PORT"])
	else:
		server.add_insecure_port('[::]:' + "50051")
	server.start()
	print("Serving...")
	server.wait_for_termination()


if __name__ == '__main__':
	global config
	try:
		with open('config.yaml', 'r') as file:
			config = yaml.safe_load(file)
	except:
		print("Cant load config file")
		config = {}
	serve()

