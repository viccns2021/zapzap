import grpc
from concurrent import futures
import chat2_pb2
import chat2_pb2_grpc
import threading
import queue
import random  # Adicionado para escolher assinante aleatório em canal simples

class ChatService(chat2_pb2_grpc.ChatServiceServicer):
    def __init__(self):
        self.channels = {}

    def CreateChannel(self, request, context):
        channel_name = request.channel_name
        channel_type = request.channel_type
        if channel_name not in self.channels:
            self.channels[channel_name] = {
                "type": channel_type,
                "subscribers": []
            }
            return chat2_pb2.ChannelResponse(message=f"Canal '{channel_name}' criado como {'simples' if channel_type == chat2_pb2.SIMPLE else 'múltiplo'}.")
        else:
            return chat2_pb2.ChannelResponse(message=f"Canal '{channel_name}' já existe.")

    def DeleteChannel(self, request, context):
        channel_name = request.channel_name
        if channel_name in self.channels:
            for client_queue in self.channels[channel_name]["subscribers"]:
                client_queue.put(None)
            del self.channels[channel_name]
            return chat2_pb2.ChannelResponse(message=f"Canal '{channel_name}' apagado.")
        else:
            return chat2_pb2.ChannelResponse(message=f"Canal '{channel_name}' não existe.")

    def ListChannels(self, request, context):
        channel_list = []
        for channel_name, channel_info in self.channels.items():
            channel_list.append(chat2_pb2.ChannelInfo(
                channel_name=channel_name, 
                channel_type=channel_info["type"]
            ))
        return chat2_pb2.ChannelList(channels=channel_list)

    def subscribe_to_channel(self, channel_name):
        if channel_name in self.channels:
            client_queue = queue.Queue()
            self.channels[channel_name]["subscribers"].append(client_queue)
            return client_queue
        else:
            raise ValueError(f"Canal '{channel_name}' não existe.")

    def Chat(self, request_iterator, context):
        first_request = next(request_iterator)
        channel_name = first_request.channel_name
        client_queue = self.subscribe_to_channel(channel_name)

        def send_messages():
            for message in request_iterator:
                channel_info = self.channels[channel_name]
                if channel_info["type"] == chat2_pb2.SIMPLE:
                    subscriber = random.choice(channel_info["subscribers"])
                    subscriber.put(message)
                else:
                    for subscriber in channel_info["subscribers"]:
                        subscriber.put(message)

        threading.Thread(target=send_messages, daemon=True).start()

        while True:
            message = client_queue.get()
            if message is None:
                break
            yield message

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chat2_service = ChatService()
    chat2_pb2_grpc.add_ChatServiceServicer_to_server(chat2_service, server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Servidor gRPC iniciado na porta 50051.")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
