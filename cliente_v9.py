import grpc
import chat2_pb2
import chat2_pb2_grpc
import threading
import queue
import time

# Função para enviar mensagens ao servidor
def send_messages(stub, name, channel_name, message_queue):
    yield chat2_pb2.ChatMessage(name=name, message="", channel_name=channel_name)
    while True:
        message = message_queue.get()
        yield chat2_pb2.ChatMessage(name=name, message=message, channel_name=channel_name)

# Função para receber mensagens do servidor
def receive_messages(response_iterator, channel_name, ready_event):
    try:
        ready_event.set()  # Indica que a thread de recebimento está pronta
        for message in response_iterator:
            if message.message:  # Ignorar mensagens vazias
                print(f"[{channel_name}] {message.name}: {message.message}")
    except grpc.RpcError as e:
        print(f"Erro ao receber mensagens do canal {channel_name}: {e.details()}")

def run():
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = chat2_pb2_grpc.ChatServiceStub(channel)
        name = input("Enter your name: ")

        active_channels = {}

        while True:
            print("\n1. Criar canal")
            print("2. Apagar canal")
            print("3. Listar canais")
            print("4. Entrar em um canal")
            print("5. Enviar mensagem")
            choice = input("Escolha uma opção: ")

            if choice == '1':
                channel_name = input("Nome do canal a ser criado: ")
                channel_type_input = input("Tipo do canal (simples/múltiplo): ").strip().lower()
                if channel_type_input == 'simples':
                    channel_type = chat2_pb2.SIMPLE
                elif channel_type_input == 'múltiplo':
                    channel_type = chat2_pb2.MULTIPLE
                else:
                    print("Tipo de canal inválido. Tente novamente.")
                    continue

                try:
                    response = stub.CreateChannel(chat2_pb2.ChannelRequest(channel_name=channel_name, channel_type=channel_type))
                    print(response.message)
                except grpc.RpcError as e:
                    print(f"Erro ao criar canal: {e.details()}")
            elif choice == '2':
                channel_name = input("Nome do canal a ser apagado: ")
                try:
                    response = stub.DeleteChannel(chat2_pb2.ChannelRequest(channel_name=channel_name))
                    print(response.message)
                except grpc.RpcError as e:
                    print(f"Erro ao apagar canal: {e.details()}")
            elif choice == '3':
                try:
                    response = stub.ListChannels(chat2_pb2.Empty())
                    for channel in response.channels:
                        channel_type = 'simples' if channel.channel_type == chat2_pb2.SIMPLE else 'múltiplo'
                        print(f"Canal: {channel.channel_name}, Tipo: {channel_type}")
                except grpc.RpcError as e:
                    print(f"Erro ao listar canais: {e.details()}")
            elif choice == '4':
                channel_name = input("Nome do canal a entrar: ")
                if channel_name not in active_channels:
                    message_queue = queue.Queue()
                    active_channels[channel_name] = message_queue
                    ready_event = threading.Event()
                    response_iterator = stub.Chat(send_messages(stub, name, channel_name, message_queue))
                    threading.Thread(target=receive_messages, args=(response_iterator, channel_name, ready_event), daemon=True).start()
                    ready_event.wait()  # Espera até que a thread de recebimento esteja pronta

                while True:
                    message = input("Enter message: ")
                    if message == 'Sair*':
                        print(f"Saindo do canal {channel_name}...")
                        break
                    active_channels[channel_name].put(message)
                    
            else:
                print("Opção inválida. Tente novamente.")

if __name__ == "__main__":
    run()
