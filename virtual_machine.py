import socket
import time
import random
import queue
import logging
from datetime import datetime
import os
import threading  # Use threading for the listener instead of multiprocessing

class VirtualMachine:
    def __init__(self, machine_id, clock_rate, port, other_ports, communication_probability=0.3, experiment_number=1):
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
        self.running = False
        
        # These will be initialized in run() to avoid pickling issues
        self.message_queue = None
        self.server_socket = None
        self.connections = None
        self.connection_lock = None
        self.logger = None
    
    def _setup_logging(self):
        """Set up logging for this VM."""
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(f"VM-{self.machine_id}")
        logger.handlers = []  # Remove default handlers
        
        # Use experiment number in log file name
        log_filename = os.path.join("logs", f"experiment_{self.experiment_number}_vm_{self.machine_id}.log")
  
        file_handler = logging.FileHandler(log_filename)
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Add a console handler for debugging
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def connect_to_others(self):
        """Connect to other virtual machines."""
        self.logger.info(f"VM{self.machine_id}: Starting to connect to other machines")
        for port in self.other_ports:
            # Try to connect multiple times with backoff
            for attempt in range(5):
                try:
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.connect(('localhost', port))
                    with self.connection_lock:
                        self.connections[port] = client_socket
                    self.logger.info(f"VM{self.machine_id}: Connected to machine on port {port}")
                    break
                except ConnectionRefusedError:
                    if attempt < 4:  # Don't log on the last attempt
                        self.logger.info(f"VM{self.machine_id}: Connection attempt {attempt+1} to port {port} failed, retrying...")
                        time.sleep(1)  # Wait before retrying
                    else:
                        self.logger.error(f"VM{self.machine_id}: Failed to connect to machine on port {port} after multiple attempts")
    
    def listen_for_messages(self):
        """Listen for incoming messages and add them to the queue."""
        self.logger.info(f"VM{self.machine_id}: Starting message listener")
        self.server_socket.settimeout(1.0)  # Set timeout to allow checking running flag
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                self.logger.info(f"VM{self.machine_id}: Accepted connection from {addr}")
                # Handle the client in the same thread
                self.handle_client(client_socket)
            except socket.timeout:
                continue  # Just a timeout, continue the loop
            except Exception as e:
                if self.running:
                    self.logger.error(f"VM{self.machine_id}: Error accepting connection: {e}")
                break
        self.logger.info(f"VM{self.machine_id}: Message listener stopped")
    
    def handle_client(self, client_socket):
        """Handle messages from a connected client."""
        try:
            data = client_socket.recv(1024)
            if data:
                # Parse the received logical clock time
                received_time = int(data.decode())
                self.message_queue.put(received_time)
                self.logger.info(f"VM{self.machine_id}: Received message with clock {received_time}")
        except Exception as e:
            if self.running:
                self.logger.error(f"VM{self.machine_id}: Error handling client: {e}")
        
        # Close the client socket when done
        try:
            client_socket.close()
        except Exception as e:
            self.logger.error(f"VM{self.machine_id}: Error closing client socket: {e}")
    
    def send_message(self, target_ports):
        """
        Send the current logical clock time to the specified target ports.
        
        Args:
            target_ports: List of ports to send the message to
        """
        # Prepare the message (just the logical clock time as a string)
        message = str(self.logical_clock).encode()
        
        # Send to each target port
        with self.connection_lock:
            for port in target_ports:
                if port in self.connections:
                    try:
                        self.connections[port].send(message)
                        self.logger.info(f"VM{self.machine_id}: Sent message to port {port}")
                    except Exception as e:
                        self.logger.error(f"VM{self.machine_id}: Error sending to port {port}: {e}")
                        # Try to reconnect
                        try:
                            self.connections[port].close()
                            new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            new_socket.connect(('localhost', port))
                            self.connections[port] = new_socket
                            self.connections[port].send(message)
                            self.logger.info(f"VM{self.machine_id}: Reconnected to port {port} and sent message")
                        except Exception as reconnect_error:
                            self.logger.error(f"VM{self.machine_id}: Failed to reconnect to port {port}: {reconnect_error}")
                else:
                    self.logger.error(f"VM{self.machine_id}: No connection to port {port}")
    
    def run(self):
        """Run the virtual machine."""
        try:
            # Initialize components here instead of in __init__ to avoid pickling issues
            self.message_queue = queue.Queue()
            self.connections = {}
            self.connection_lock = threading.Lock()  # Use threading.Lock instead of multiprocessing.Lock
            self.logger = self._setup_logging()
            
            self.logger.info(f"VM{self.machine_id}: Initializing with clock rate {self.clock_rate}")
            
            # Set up socket for listening
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('localhost', self.port))
            self.server_socket.listen(5)
            self.logger.info(f"VM{self.machine_id}: Server socket bound to port {self.port}")
            
            self.running = True
            
            # Start listening for messages in a separate thread (not process)
            self.logger.info(f"VM{self.machine_id}: Starting listener thread")
            listener_thread = threading.Thread(target=self.listen_for_messages)
            listener_thread.daemon = True
            listener_thread.start()
            
            # Wait a moment for all machines to start their listeners
            self.logger.info(f"VM{self.machine_id}: Waiting for other machines to start")
            time.sleep(2)
            
            # Connect to other machines
            self.connect_to_others()
            
            self.logger.info(f"VM{self.machine_id}: Starting main clock cycle")
            
            # Main clock cycle
            while self.running:
                cycle_start = time.time()
                
                # Process a message if available
                if not self.message_queue.empty():
                    received_time = self.message_queue.get()
                    self.logical_clock = max(self.logical_clock, received_time) + 1
                    queue_length = self.message_queue.qsize()
                    self.logger.info(f"VM{self.machine_id}: RECEIVE event, queue length: {queue_length}, logical clock: {self.logical_clock}")
                else:
                    # No message, generate random event
                    event = random.random()  # Generate a random float between 0 and 1
                    self.logical_clock += 1
                    
                    if event < self.communication_probability:
                        # Communication events (30% by default)
                        sub_event = random.randint(1, 3)
                        
                        if sub_event == 1:
                            # Send to one machine
                            target_port = self.other_ports[0]
                            self.send_message([target_port])
                            self.logger.info(f"VM{self.machine_id}: SEND event to port {target_port}, logical clock: {self.logical_clock}")
                        
                        elif sub_event == 2:
                            # Send to another machine
                            target_port = self.other_ports[1]
                            self.send_message([target_port])
                            self.logger.info(f"VM{self.machine_id}: SEND event to port {target_port}, logical clock: {self.logical_clock}")
                        
                        elif sub_event == 3:
                            # Send to all machines
                            self.send_message(self.other_ports)
                            self.logger.info(f"VM{self.machine_id}: SEND event to ALL machines, logical clock: {self.logical_clock}")
                    else:
                        # Internal event
                        self.logger.info(f"VM{self.machine_id}: INTERNAL event, logical clock: {self.logical_clock}")
                
                # Sleep to maintain clock rate
                elapsed = time.time() - cycle_start
                sleep_time = (1.0 / self.clock_rate) - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    self.logger.error(f"VM{self.machine_id}: Handling the time step took longer than the clock time, at logical clock: {self.logical_clock}")
        
        except Exception as e:
            self.logger.error(f"VM{self.machine_id}: Unexpected error in run(): {e}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    def stop(self):
        """Stop the virtual machine."""
        if hasattr(self, 'logger') and self.logger:
            self.logger.info(f"VM{self.machine_id}: Stopping")
            
        self.running = False
        
        if hasattr(self, 'logger') and self.logger:
            # Close all connections
            if hasattr(self, 'connection_lock') and self.connection_lock and hasattr(self, 'connections') and self.connections:
                with self.connection_lock:
                    for conn in self.connections.values():
                        try:
                            conn.close()
                        except Exception as e:
                            self.logger.info(f'VM{self.machine_id}: Error closing connection: {e}')
                    self.connections.clear()
            
            # Close server socket
            if hasattr(self, 'server_socket') and self.server_socket:
                try:
                    self.server_socket.close()
                except Exception as e:
                    self.logger.info(f'VM{self.machine_id}: Error closing server socket: {e}')
            
            self.logger.info(f"VM{self.machine_id}: Stopped. Final logical clock: {self.logical_clock}")