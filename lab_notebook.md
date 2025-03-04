# Distributed System Simulation Lab Notebook

## Design Decisions

### Overall Architecture
- We're implementing a simulation of 3 virtual machines running at different clock rates
- Each virtual machine is implemented as a Python object running in its own thread
- Communication between machines is handled via TCP sockets
- Each machine maintains its own logical clock following Lamport's logical clock rules

### Virtual Machine Design
- Each VM has:
  - A unique ID
  - A clock rate (1-6 ticks per second)
  - A logical clock
  - A message queue for incoming messages
  - Socket connections to other VMs
  - A dedicated log file

### Communication Protocol
- Simple text-based protocol where messages contain the sender's logical clock value
- TCP sockets ensure reliable delivery of messages
- Each VM listens on a specific port and connects to the ports of other VMs

### Clock Synchronization
- Using Lamport's logical clock algorithm:
  - Increment clock on internal events
  - When sending a message, increment clock and include it in the message
  - When receiving a message, set local clock to max(local_clock, received_clock) + 1

### Logging Strategy
- Each VM logs to its own file to avoid synchronization issues
- Log entries include:
  - System timestamp (for analysis)
  - Event type (internal, send, receive)
  - Queue length (for receive events)
  - Logical clock value

### Simulation Control
- Main program initializes VMs with random clock rates
- Runs the simulation for a fixed time (60 seconds)
- Gracefully shuts down all VMs at the end

## Implementation Notes

- Using Python's threading module for concurrency
- Using standard socket library for network communication
- Using queue.Queue for thread-safe message queuing
- Using Python's logging module for structured logging

## Experimental Observations

(This section will be filled in after running the experiments)

## Implementation Details

### Robust Communication
- Added connection retry logic to handle race conditions during startup
- Implemented timeout handling for socket operations
- Added reconnection logic if a connection fails during message sending
- Used a lock to protect access to the connections dictionary

### Improved Logging
- Structured log format with timestamps and event types
- Clear distinction between INTERNAL, SEND, and RECEIVE events
- Logging queue length for analysis of message backlog
- Logging final logical clock value when machine stops

### Error Handling
- Graceful handling of connection failures
- Proper cleanup of resources when stopping
- Timeout-based loop control to allow clean shutdown

### Thread Safety
- Using thread-safe Queue for message handling
- Using locks for shared resource access
- Daemon threads to ensure clean program exit

## Experiment Plan

For each experiment, we'll run the simulation for 60 seconds with 3 virtual machines.

### Experiment 1: Default Settings
- Clock rates: Random between 1-6 ticks/second
- Event probabilities: 30% send, 70% internal (as specified)

### Experiment 2: Faster Clocks
- Clock rates: Random between 4-6 ticks/second
- Event probabilities: 30% send, 70% internal

### Experiment 3: More Communication
- Clock rates: Random between 1-6 ticks/second
- Event probabilities: 60% send, 40% internal

### Experiment 4: Uniform Clock Rate
- Clock rates: All machines at 3 ticks/second
- Event probabilities: 30% send, 70% internal

### Experiment 5: Extreme Clock Difference
- Clock rates: 1, 3, and 6 ticks/second
- Event probabilities: 30% send, 70% internal

For each experiment, we'll analyze:
1. Logical clock drift between machines
2. Message queue lengths
3. Frequency and size of logical clock jumps
4. Correlation between clock rates and logical clock progression 

## Experiment Execution

We've created a main.py script that can run all five experiments or a specific one:

```python main.py  # Run all experiments
python main.py --experiment 1  # Run a specific experiment 
```

Each experiment runs for 60 seconds by default, but this can be changed with the --duration parameter.

## Analysis Tools

We've created an analyze_logs.py script to help analyze the results of our experiments. This script:

1. Parses the log files from each machine
2. Calculates statistics about logical clock jumps and queue lengths
3. Counts different types of events
4. Generates plots showing:
   - Logical clock progression over time
   - Message queue lengths over time

To run the analysis:

```
python analyze_logs.py
```

The script will generate PNG files with the plots for each experiment.

## Expected Results

We expect to observe:

1. In experiments with varying clock rates, faster machines will process more events and have higher logical clock values
2. Machines with slower clock rates will likely have longer message queues
3. When a slow machine receives a message from a fast machine, we expect to see larger jumps in the logical clock
4. Higher communication probability should lead to more synchronization between machines
5. Uniform clock rates should result in more consistent logical clock progression across machines

These hypotheses will be tested and analyzed after running the experiments.
