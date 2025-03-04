import time
import random
import threading
import argparse
import os
import glob
import shutil
from virtual_machine import VirtualMachine

def ensure_logs_directory():
    """Create logs directory if it doesn't exist."""
    if not os.path.exists("logs"):
        os.makedirs("logs")
        print("Created logs directory")

def clean_log_files(experiment_number=None):
    """
    Remove old log files to ensure clean experiment runs.
    
    Args:
        experiment_number: If provided, only remove logs for this experiment
    """
    ensure_logs_directory()
    
    if experiment_number:
        # Remove logs for a specific experiment
        pattern = os.path.join("logs", f"experiment_{experiment_number}_vm_*.log")
        files_to_remove = glob.glob(pattern)
    else:
        # Remove all log files
        files_to_remove = glob.glob(os.path.join("logs", "experiment_*_vm_*.log"))
    
    for file in files_to_remove:
        try:
            os.remove(file)
            print(f"Removed old log file: {file}")
        except Exception as e:
            print(f"Error removing {file}: {e}")

def run_experiment(experiment_number, duration=60, custom_clock_rates=None, communication_probability=0.3):
    """
    Run a single experiment with the specified parameters.
    
    Args:
        experiment_number: Number of the experiment (for logging)
        duration: Duration in seconds to run the experiment
        custom_clock_rates: Optional list of clock rates to use instead of random ones
        communication_probability: Probability of send events (1-3 out of 10)
    """
    print(f"\n=== Starting Experiment {experiment_number} ===")
    
    # Ensure logs directory exists
    ensure_logs_directory()
    
    # Clean up old log files for this experiment
    clean_log_files(experiment_number)
    
    # Print experiment parameters
    print(f"Experiment {experiment_number} parameters:")
    print(f"  Clock rates: {custom_clock_rates if custom_clock_rates else 'Random 1-6'}")
    print(f"  Communication probability: {communication_probability}")
    print(f"  Duration: {duration} seconds")
    
    # Define ports for the three machines
    ports = [5001, 5002, 5003]
    
    # Create virtual machines with specified or random clock rates
    machines = []
    for i in range(3):
        if custom_clock_rates:
            clock_rate = custom_clock_rates[i]
        else:
            clock_rate = random.randint(1, 6)
            
        other_ports = [p for p in ports if p != ports[i]]
        vm = VirtualMachine(
            machine_id=i,
            clock_rate=clock_rate,
            port=ports[i],
            other_ports=other_ports,
            communication_probability=communication_probability,
            experiment_number=experiment_number
        )
        machines.append(vm)
        print(f"Machine {i} created with clock rate {clock_rate}")
    
    # Start the machines in separate threads
    threads = []
    for vm in machines:
        thread = threading.Thread(target=vm.run)
        thread.daemon = True
        thread.start()
        threads.append(thread)
    
    # Let the simulation run for the specified duration
    try:
        start_time = time.time()
        print(f"Simulation running for {duration} seconds...")
        
        # Use a more precise timing approach
        while time.time() - start_time < duration:
            remaining = duration - (time.time() - start_time)
            if remaining > 0:
                time.sleep(min(1.0, remaining))  # Sleep in smaller increments
                
        actual_duration = time.time() - start_time
        print(f"Simulation completed after {actual_duration:.2f} seconds")
    except KeyboardInterrupt:
        print("Simulation interrupted")
    
    # Stop all machines
    for vm in machines:
        vm.stop()
    
    print(f"Experiment {experiment_number} complete. Check the logs folder for results.")
    
    # Give some time for logs to flush and connections to close
    time.sleep(2)

def main():
    parser = argparse.ArgumentParser(description='Run distributed system simulation experiments')
    parser.add_argument('--experiment', type=int, choices=range(1, 6), help='Run a specific experiment (1-5)')
    parser.add_argument('--duration', type=int, default=60, help='Duration in seconds for each experiment')
    parser.add_argument('--clean', action='store_true', help='Clean all log files before running')
    args = parser.parse_args()
    
    # Ensure logs directory exists
    ensure_logs_directory()
    
    if args.clean:
        clean_log_files()
        print("All log files cleaned.")
        if not args.experiment:
            return
    
    if args.experiment:
        # Run a specific experiment
        if args.experiment == 1:
            # Default settings
            run_experiment(1, args.duration)
        elif args.experiment == 2:
            # Faster clocks
            run_experiment(2, args.duration, custom_clock_rates=[random.randint(4, 6) for _ in range(3)])
        elif args.experiment == 3:
            # More communication
            run_experiment(3, args.duration, communication_probability=0.6)
        elif args.experiment == 4:
            # Uniform clock rate
            run_experiment(4, args.duration, custom_clock_rates=[3, 3, 3])
        elif args.experiment == 5:
            # Extreme clock difference
            run_experiment(5, args.duration, custom_clock_rates=[1, 3, 6])
    else:
        # Run all experiments
        for i in range(1, 6):
            if i == 1:
                # Default settings
                run_experiment(1, args.duration)
            elif i == 2:
                # Faster clocks
                run_experiment(2, args.duration, custom_clock_rates=[random.randint(4, 6) for _ in range(3)])
            elif i == 3:
                # More communication
                run_experiment(3, args.duration, communication_probability=0.6)
            elif i == 4:
                # Uniform clock rate
                run_experiment(4, args.duration, custom_clock_rates=[3, 3, 3])
            elif i == 5:
                # Extreme clock difference
                run_experiment(5, args.duration, custom_clock_rates=[1, 3, 6])

if __name__ == "__main__":
    main()