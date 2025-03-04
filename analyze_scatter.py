import os
import re
import pandas as pd
import matplotlib.pyplot as plt

# Define the experiment configurations to match your main.py
EXPERIMENTS = {
    12: {"custom_clock_rates": [1,3,6], "communication_probability": 0.1},
    13: {"custom_clock_rates": [1,3,6], "communication_probability": 0.3},
    14: {"custom_clock_rates": [1,3,6], "communication_probability": 0.6},
    15: {"custom_clock_rates": [1,3,6], "communication_probability": 0.9},
}

def analyze_experiment_results(experiment_dir="logs_for_scatter"):
    results = []
    
    # Pattern to match your log filenames
    log_pattern = re.compile(r"experiment_(\d+)_vm_(\d+)\.log")
    
    # Group log files by experiment
    experiments = {}
    for filename in os.listdir(experiment_dir):
        match = log_pattern.match(filename)
        if match:
            exp_num = int(match.group(1))
            # Only process experiments 12-15
            if exp_num not in EXPERIMENTS:
                continue
                
            vm_id = int(match.group(2))
            
            if exp_num not in experiments:
                experiments[exp_num] = []
            
            experiments[exp_num].append((vm_id, os.path.join(experiment_dir, filename)))
    
    # Process each experiment
    for exp_num, log_files in experiments.items():
        # Get experiment parameters from our configuration
        comm_prob = EXPERIMENTS[exp_num]["communication_probability"]
        
        # Extract final state from each VM's log
        vm_results = []
        
        for vm_id, log_file in log_files:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                
                # Get the last few lines to find final state
                final_clock = None
                for line in reversed(lines):
                    if "logical clock:" in line:
                        clock_match = re.search(r"logical clock: (\d+)", line)
                        if clock_match:
                            final_clock = int(clock_match.group(1))
                            break
                
                # Find maximum queue length
                max_queue_length = 0
                for line in lines:
                    if "queue length:" in line:
                        queue_match = re.search(r"queue length: (\d+)", line)
                        if queue_match:
                            queue_len = int(queue_match.group(1))
                            max_queue_length = max(max_queue_length, queue_len)
                
                # Extract clock rate from log
                clock_rate = None
                for line in lines:
                    if "starting with clock rate" in line:
                        rate_match = re.search(r"clock rate (\d+)", line)
                        if rate_match:
                            clock_rate = int(rate_match.group(1))
                            break
                
                vm_results.append({
                    'vm_id': vm_id,
                    'clock_rate': clock_rate,
                    'final_clock': final_clock,
                    'max_queue_length': max_queue_length
                })
        
        # Calculate max clock difference
        if len(vm_results) > 1:
            final_clocks = [vm['final_clock'] for vm in vm_results if vm['final_clock'] is not None]
            max_clock_diff = max(final_clocks) - min(final_clocks) if final_clocks else 0
            
            # Add experiment summary
            results.append({
                'experiment': exp_num,
                'comm_prob': comm_prob,
                'vm_results': vm_results,
                'max_clock_diff': max_clock_diff
            })
    
    results.sort(key=lambda x: x['experiment'])
    return results

def create_scatter_plots(results):
    # Extract data for plotting
    plot_data = []
    for exp in results:
        exp_num = exp['experiment']
        max_clock_diff = exp['max_clock_diff']
        comm_prob = exp['comm_prob']
        
        for vm in exp['vm_results']:
            plot_data.append({
                'experiment': exp_num,
                'vm_id': vm['vm_id'],
                'clock_rate': vm['clock_rate'],
                'max_queue_length': vm['max_queue_length'],
                'final_clock': vm['final_clock'],
                'max_clock_diff': max_clock_diff,
                'comm_prob': comm_prob
            })
    
    df = pd.DataFrame(plot_data)
    
    # Create figure with multiple subplots
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    
    # 1. Communication Probability vs Max Queue Length
    for vm_id in sorted(df['vm_id'].unique()):
        subset = df[df['vm_id'] == vm_id]
        axes[0].scatter(subset['comm_prob'], subset['max_queue_length'], 
                       label=f'VM{vm_id} (Rate: {subset["clock_rate"].iloc[0]})', alpha=0.7, s=80)
        axes[0].plot(subset['comm_prob'], subset['max_queue_length'], alpha=0.5)
    
    axes[0].set_xlabel('Communication Probability')
    axes[0].set_ylabel('Maximum Queue Length')
    axes[0].set_title('Effect of Communication Probability on Queue Length')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # 2. Communication Probability vs Max Clock Difference
    exp_summary = df.groupby(['experiment', 'comm_prob'])['max_clock_diff'].first().reset_index()
    axes[1].scatter(exp_summary['comm_prob'], exp_summary['max_clock_diff'], s=100, color='red')
    axes[1].plot(exp_summary['comm_prob'], exp_summary['max_clock_diff'], 'r--', alpha=0.5)
    
    axes[1].set_xlabel('Communication Probability')
    axes[1].set_ylabel('Maximum Clock Difference')
    axes[1].set_title('Effect of Communication Probability on Clock Synchronization')
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('comm_prob_analysis.png', dpi=300)
    plt.show()

# Run the analysis
results = analyze_experiment_results()
create_scatter_plots(results)