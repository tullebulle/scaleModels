import time
import random
import multiprocessing
import argparse
import os
import glob

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

def run_vm(vm):
    """Function to run a virtual machine in a separate process."""
    try:
        vm.run()
    except Exception as e:
        print(f"Error in VM process: {e}")

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
    
    # Start the machines in separate processes
    processes = []
    for vm in machines:
        process = multiprocessing.Process(target=run_vm, args=(vm,))
        process.daemon = True
        process.start()
        processes.append(process)
    
    # Let the simulation run for the specified duration
    try:
        start_time = time.time()
        print(f"Simulation running for {duration} seconds...")
        
        # Use a more precise timing approach
        while True:
            remaining = duration - (time.time() - start_time)
            if remaining > 0:
                time.sleep(min(1.0, remaining))  # Sleep in smaller increments
            else:
                break  

        actual_duration = time.time() - start_time
        print(f"Simulation completed after {actual_duration:.2f} seconds")
    except KeyboardInterrupt:
        print("Simulation interrupted")
    
    # Stop all machines and terminate processes
    for vm in machines:
        vm.stop()
    
    for process in processes:
        process.terminate()
        process.join(timeout=2)
    
    print(f"Experiment {experiment_number} complete. Check the logs folder for results.")
    
    # Give some time for logs to flush and connections to close
    time.sleep(2)

def main():
    EXPERIMENTS = {
        1: {"custom_clock_rates": None,
            "communication_probability": None},
        2: {"custom_clock_rates": [6,4,4],
            "communication_probability": None},
        3: {"custom_clock_rates": [3,3,3],
            "communication_probability": None},
        4: {"custom_clock_rates": [1,3,6],
            "communication_probability": None},
        5: {"custom_clock_rates": [5,3,2],
            "communication_probability": None},
        6: {"custom_clock_rates": [5,3,2],
            "communication_probability": 0.6},
        7: {"custom_clock_rates": [3,3,3],
            "communication_probability": 0.9},
        8: {"custom_clock_rates": [4,4,6],
            "communication_probability": 0.9},
        9: {"custom_clock_rates": [1,1,6],
            "communication_probability": 0.9},
        10: {"custom_clock_rates": [1,4,6],
            "communication_probability": 0.9},
        11: {"custom_clock_rates": [5,3,2],
            "communication_probability": 0.9},
        12: {"custom_clock_rates": [1,3,6],
            "communication_probability": 0.1},
        13: {"custom_clock_rates": [1,3,6],
            "communication_probability": 0.3},
        14: {"custom_clock_rates": [1,3,6],
            "communication_probability": 0.6},
        15: {"custom_clock_rates": [1,3,6],
            "communication_probability": 0.9},
    }

    parser = argparse.ArgumentParser(description='Run distributed system simulation experiments')
    parser.add_argument('--experiment', type=int, choices=range(1, len(EXPERIMENTS)+1), help='Run a specific experiment (1-15)')
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
    
    # Set the start method for multiprocessing
    multiprocessing.set_start_method('spawn', force=True)
    
    experiment_numbers = [args.experiment] if args.experiment else [i+1 for i in range(len(EXPERIMENTS))]
    for experiment_number in experiment_numbers:
        custom_clock_rates = EXPERIMENTS[experiment_number]['custom_clock_rates']
        communication_probability = EXPERIMENTS[experiment_number]['communication_probability']

        if not custom_clock_rates: custom_clock_rates = [random.randint(1, 6) for _ in range(3)]
        if not communication_probability: communication_probability = 0.3
        
        run_experiment(experiment_number, duration=args.duration, 
                      custom_clock_rates=custom_clock_rates, 
                      communication_probability=communication_probability)

if __name__ == "__main__":
    main()