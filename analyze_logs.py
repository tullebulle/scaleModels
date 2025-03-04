import re
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import glob
import os

def ensure_logs_directory():
    """Create logs directory if it doesn't exist."""
    if not os.path.exists("logs"):
        os.makedirs("logs")
        print("Created logs directory")

def parse_log_file(filename):
    """Parse a log file and extract timestamps, event types, and logical clock values."""
    events = []
    pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - (.*)'
    
    try:
        with open(filename, 'r') as f:
            for line in f:
                match = re.match(pattern, line)
                if match:
                    timestamp_str, message = match.groups()
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                    
                    # Extract event type and logical clock
                    if 'INTERNAL event' in message:
                        event_type = 'INTERNAL'
                        logical_clock = int(message.split('logical clock: ')[1])
                        queue_length = None
                    elif 'SEND event' in message:
                        event_type = 'SEND'
                        logical_clock = int(message.split('logical clock: ')[1])
                        queue_length = None
                    elif 'RECEIVE event' in message:
                        event_type = 'RECEIVE'
                        logical_clock = int(message.split('logical clock: ')[1])
                        queue_length = int(message.split('queue length: ')[1].split(',')[0])
                    else:
                        continue  # Skip other log messages
                    
                    events.append({
                        'timestamp': timestamp,
                        'event_type': event_type,
                        'logical_clock': logical_clock,
                        'queue_length': queue_length
                    })
    except FileNotFoundError:
        print(f"Warning: Log file {filename} not found")
    
    return events

def analyze_experiment(experiment_number):
    """Analyze the logs from a specific experiment."""
    print(f"\n=== Analyzing Experiment {experiment_number} ===")
    
    # Ensure output directory for plots exists
    if not os.path.exists("plots"):
        os.makedirs("plots")
    
    # Check if log files exist for this experiment
    log_files = glob.glob(os.path.join("logs", f"experiment_{experiment_number}_vm_*.log"))
    if not log_files:
        print(f"No log files found for experiment {experiment_number}")
        return
    
    # Parse logs for all three machines
    logs = []
    for i in range(3):
        filename = os.path.join("logs", f"experiment_{experiment_number}_vm_{i}.log")
        events = parse_log_file(filename)
        logs.append(events)
        print(f"Machine {i}: {len(events)} events recorded")
    
    # Calculate statistics
    for i, events in enumerate(logs):
        if not events:
            print(f"No events found for machine {i}")
            continue
            
        # Calculate logical clock jumps
        jumps = [events[j]['logical_clock'] - events[j-1]['logical_clock'] 
                for j in range(1, len(events))]
        
        avg_jump = sum(jumps) / len(jumps) if jumps else 0
        max_jump = max(jumps) if jumps else 0
        
        # Calculate queue statistics
        queue_lengths = [e['queue_length'] for e in events if e['queue_length'] is not None]
        avg_queue = sum(queue_lengths) / len(queue_lengths) if queue_lengths else 0
        max_queue = max(queue_lengths) if queue_lengths else 0
        
        print(f"\nMachine {i} Statistics:")
        print(f"  Final logical clock value: {events[-1]['logical_clock'] if events else 0}")
        print(f"  Total events: {len(events)}")
        print(f"  Events per second: {len(events) / 60:.2f}")
        print(f"  Average logical clock jump: {avg_jump:.2f}")
        print(f"  Maximum logical clock jump: {max_jump}")
        print(f"  Average queue length: {avg_queue:.2f}")
        print(f"  Maximum queue length: {max_queue}")
        
        # Count event types
        event_types = {}
        for e in events:
            event_types[e['event_type']] = event_types.get(e['event_type'], 0) + 1
        
        print("  Event counts:")
        for event_type, count in event_types.items():
            print(f"    {event_type}: {count}")
    
    # Plot logical clock progression
    plt.figure(figsize=(10, 6))
    for i, events in enumerate(logs):
        if not events:
            continue
            
        timestamps = [(e['timestamp'] - events[0]['timestamp']).total_seconds() for e in events]
        logical_clocks = [e['logical_clock'] for e in events]
        
        plt.plot(timestamps, logical_clocks, label=f"Machine {i}")
    
    plt.xlabel('Time (seconds)')
    plt.ylabel('Logical Clock Value')
    plt.title(f'Logical Clock Progression - Experiment {experiment_number}')
    plt.legend()
    plt.grid(True)
    plt.ylim(bottom=0)  # Start y-axis at 0
    plt.tight_layout()
    plt.savefig(os.path.join("plots", f'experiment_{experiment_number}_clocks.png'))
    
    # Plot queue lengths
    plt.figure(figsize=(10, 6))
    for i, events in enumerate(logs):
        if not events:
            continue
            
        receive_events = [e for e in events if e['event_type'] == 'RECEIVE']
        if not receive_events:
            continue
            
        timestamps = [(e['timestamp'] - events[0]['timestamp']).total_seconds() for e in receive_events]
        queue_lengths = [e['queue_length'] for e in receive_events]
        
        plt.plot(timestamps, queue_lengths, label=f"Machine {i}")
    
    plt.xlabel('Time (seconds)')
    plt.ylabel('Queue Length')
    plt.title(f'Message Queue Lengths - Experiment {experiment_number}')
    plt.legend()
    plt.grid(True)
    plt.ylim(bottom=0)  # Start y-axis at 0
    plt.tight_layout()
    plt.savefig(os.path.join("plots", f'experiment_{experiment_number}_queues.png'))

def main():
    # Ensure logs directory exists
    ensure_logs_directory()
    
    # Check which experiments have log files
    experiments = set()
    for filename in glob.glob(os.path.join("logs", "experiment_*_vm_*.log")):
        try:
            exp_num = int(os.path.basename(filename).split("_")[1])
            experiments.add(exp_num)
        except:
            continue
    
    if not experiments:
        print("No experiment log files found in the logs directory.")
        return
    
    print(f"Found log files for experiments: {sorted(experiments)}")
    
    for experiment in sorted(experiments):
        analyze_experiment(experiment)

if __name__ == "__main__":
    main() 