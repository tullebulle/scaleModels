import socket
import threading
import time
import random
import queue
import logging
from datetime import datetime
import os

class VirtualMachine:
    def __init__(self, machine_id, clock_rate, port, other_ports, communication_probability=0.3, experiment_number=None):
        """
        Initialize a virtual machine.
        
        Args:
            machine_id: Identifier for this machine
            clock_rate: Number of clock ticks per second (1-6)
            port: Port this machine listens on
            other_ports: Ports of other machines to connect to
            communication_probability: Probability of send events (0.0-1.0)
            experiment_number: Number of the experiment (for log file naming)
        """
        self.machine_id = machine_id
        self.clock_rate = clock_rate
        self.port = port
        self.other_ports = other_ports
        self.communication_probability = communication_probability
        self.experiment_number = experiment_number
        self.logical_clock = 0
        self.message_queue = queue.Queue()
        self.running = False
        
        # Ensure logs directory exists
        if not os.path.exists("logs"):
            os.makedirs("logs")
        
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(f"VM-{machine_id}")
        self.logger.handlers = []  # Remove default handlers
        
        # Use experiment number in log file name if provided
        if experiment_number is not None:
            log_filename = os.path.join("logs", f"experiment_{experiment_number}_vm_{machine_id}.log")
        else:
            log_filename = os.path.join("logs", f"vm_{machine_id}.log")
        
        file_handler = logging.FileHandler(log_filename)
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        self.logger.setLevel(logging.INFO)
        
        # Set up socket for listening
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('localhost', self.port))
        self.server_socket.listen(5)
        
        # Connections to other machines
        self.connections = {}  # Map port to connection
        self.connection_lock = threading.Lock()
    
    def connect_to_others(self):
        """Connect to other virtual machines."""
        for port in self.other_ports:
            # Try to connect multiple times with backoff
            for attempt in range(5):
                try:
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.connect(('localhost', port))
                    with self.connection_lock:
                        self.connections[port] = client_socket
                    self.logger.info(f"Connected to machine on port {port}")
                    break
                except ConnectionRefusedError:
                    if attempt < 4:  # Don't log on the last attempt
                        self.logger.info(f"Connection attempt {attempt+1} to port {port} failed, retrying...")
                        time.sleep(1)  # Wait before retrying
                    else:
                        self.logger.error(f"Failed to connect to machine on port {port} after multiple attempts")
    
    def listen_for_messages(self):
        """Listen for incoming messages and add them to the queue."""
        self.server_socket.settimeout(1.0)  # Set timeout to allow checking running flag
        
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()
            except socket.timeout:
                continue  # Just a timeout, continue the loop
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error accepting connection: {e}")
    
    def handle_client(self, client_socket):
        """Handle messages from a connected client."""
        client_socket.settimeout(1.0)  # Set timeout to allow checking running flag
        
        while self.running:
            try:
                data = client_socket.recv(1024)
                if not data:
                    break
                
                # Parse the received logical clock time
                received_time = int(data.decode())
                self.message_queue.put(received_time)
            except socket.timeout:
                continue  # Just a timeout, continue the loop
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error handling client: {e}")
                break
        
        client_socket.close()
    
    def send_message(self, target_ports):
        """
        Send the logical clock to specified machines.
        
        Args:
            target_ports: List of ports to send to
        """
        message = str(self.logical_clock).encode()
        
        with self.connection_lock:
            for port in target_ports:
                if port in self.connections:
                    try:
                        self.connections[port].send(message)
                    except Exception as e:
                        self.logger.error(f"Error sending to port {port}: {e}")
                        # Try to reconnect
                        try:
                            self.connections[port].close()
                            new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            new_socket.connect(('localhost', port))
                            self.connections[port] = new_socket
                            self.connections[port].send(message)
                            self.logger.info(f"Reconnected to port {port} and sent message")
                        except Exception as reconnect_error:
                            self.logger.error(f"Failed to reconnect to port {port}: {reconnect_error}")
    
    def run(self):
        """Run the virtual machine."""
        self.running = True
        
        # Start listening for messages
        listener_thread = threading.Thread(target=self.listen_for_messages, daemon=True)
        listener_thread.start()
        
        # Wait a moment for all machines to start their listeners
        time.sleep(2)
        
        # Connect to other machines
        self.connect_to_others()
        
        self.logger.info(f"Machine {self.machine_id} starting with clock rate {self.clock_rate}")
        
        # Main clock cycle
        while self.running:
            cycle_start = time.time()
            
            # Process a message if available
            if not self.message_queue.empty():
                received_time = self.message_queue.get()
                self.logical_clock = max(self.logical_clock, received_time) + 1
                queue_length = self.message_queue.qsize()
                self.logger.info(f"RECEIVE event, queue length: {queue_length}, logical clock: {self.logical_clock}")
            else:
                # No message, generate random event
                event = random.random()  # Generate a random float between 0 and 1
                
                if event < self.communication_probability:
                    # Communication events (30% by default)
                    sub_event = random.randint(1, 3)
                    
                    if sub_event == 1:
                        # Send to one machine
                        target_port = random.choice(self.other_ports)
                        self.logical_clock += 1
                        self.send_message([target_port])
                        self.logger.info(f"SEND event to port {target_port}, logical clock: {self.logical_clock}")
                    
                    elif sub_event == 2:
                        # Send to another machine
                        target_port = random.choice(self.other_ports)
                        self.logical_clock += 1
                        self.send_message([target_port])
                        self.logger.info(f"SEND event to port {target_port}, logical clock: {self.logical_clock}")
                    
                    elif sub_event == 3:
                        # Send to all machines
                        self.logical_clock += 1
                        self.send_message(self.other_ports)
                        self.logger.info(f"SEND event to ALL machines, logical clock: {self.logical_clock}")
                else:
                    # Internal event
                    self.logical_clock += 1
                    self.logger.info(f"INTERNAL event, logical clock: {self.logical_clock}")
            
            # Sleep to maintain clock rate
            elapsed = time.time() - cycle_start
            sleep_time = (1.0 / self.clock_rate) - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def stop(self):
        """Stop the virtual machine."""
        self.running = False
        
        # Close all connections
        with self.connection_lock:
            for conn in self.connections.values():
                try:
                    conn.close()
                except:
                    pass
            self.connections.clear()
        
        # Close server socket
        try:
            self.server_socket.close()
        except:
            pass
        
        self.logger.info(f"Machine {self.machine_id} stopped. Final logical clock: {self.logical_clock}")