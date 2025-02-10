import ipaddress #allows for manipulation of the ip addresses
import subprocess #Provides use of shell commands
import platform #identifys the operating system and changes ping syntax
import concurrent.futures #lets us multitread to speed up our ip scanning
import logging #lets us log errors
import argparse #lets us pass in arguments
import socket #Lets us check the ports if theyre open or closed
import time #Lets us measure latency for how long the pings take

#All done with help from chat GPT and tweaking of format and information from the IPfreely assianment.

# Configure logging
logging.basicConfig(filename="network_scan.log", level=logging.INFO, #allows for us to log to our network_scan.log file
                    format="%(asctime)s - %(levelname)s - %(message)s") #creates the format for the logging

def ping_host(ip): #defines our Ip function
    param = "-n" if platform.system().lower() == "windows" else "-c" #determines if were using windows or linux/macOS to find the number of packets to send
    try:
        start_time = time.time() #starts time
        result = subprocess.run(["ping", param, "1", str(ip)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2) #takes the ip and pings it using subprocess and takes not of errors and the output
        latency = (time.time() - start_time) * 1000  # Times latency to see how long it took to ping the ipaddress and returns it in miliseconds
        return (result.returncode == 0, round(latency, 2)) #times out if the ip doesnt ping within 2 seconds, returns 0 or good if less than 2 second scan
    except Exception as e: #e for error
        logging.error(f"Ping error for {ip}: {e}") #Logs the error
        return (False, None) #returns false

def parse_ports(port_input): #Defines our function to take in the specified ports
    ports = set() #sets up our port list
    for part in port_input.split(","): #for the ports in our requested list, split the ports at the comma.
        if "-" in part: #if there is a dash
            start, end = map(int, part.split("-")) #sets up range for first and last port and all inbetween
            ports.update(range(start, end + 1)) #adds a port to avoid duplicate
        else:
            ports.add(int(part)) #or just take the given port
    return sorted(ports) #return the ports sorted by value

def scan_ports(ip, ports, timeout=2): #sets up our scanning port function.
    open_ports = [] #sets up a dictionary of port information
    for port in ports: #for each of the ports we specified
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: #Sets up a TCP request to check the port
            s.settimeout(timeout) #creates timeout if it takes too long to check
            if s.connect_ex((str(ip), port)) == 0: #If sucessful check, return 0 as no errors.
                open_ports.append(port) #appends the port information if the port is open.
    return open_ports #returns to terminal

def network_scanner(network_cidr, ports=None, max_threads=50): #checks the network
    try:
        network = ipaddress.ip_network(network_cidr, strict=False) #identifies active hosts from our subnet, converts our CIDR notation to the ip list
    except ValueError as e: #If wrong format, returns error
        print(f"Invalid network address: {e}") #if error, returns "Invalid network address:"followed by the error encountered
        return

    hosts = list(network.hosts()) #checks hosts
    print(f"Scanning {len(hosts)} hosts in {network} using {max_threads} threads...\n") #allows us to scan a bunch of hosts in parralell at the same time to speed up the process.

    # Step 1: Ping all hosts to find active ones
    active_hosts = {} #creates a list of active hosts to print
    with concurrent.futures.ThreadPoolExecutor(max_threads) as executor: #pools hosts to scan at the same time
        results = {host: executor.submit(ping_host, host) for host in hosts} #pools hosts to scan at the same time

    for host, future in results.items(): #for all hosts
        is_up, latency = future.result() #if the ip address is up or active, add latency
        status = "UP" if is_up else "DOWN" #return up if its up, otherwise return down
        latency_info = f" (Latency: {latency} ms)" if is_up else "" #takes in latency information
        print(f"{host}  - {status}{latency_info}") #Prints in our format for host, its status and how long it took, its latency
        if is_up: #if its up
            active_hosts[host] = latency #display

    if not active_hosts: #if no active hosts are found in the subnet, return no active hosts found
        print("\nNo active hosts found.") #the print
        return

    print(f"\n{len(active_hosts)} active hosts found. Scanning specified ports...\n") #prints how many active hosts were found and says scanning ports for active ips

    # Step 2: Scan specified ports on active hosts
    if ports:
        parsed_ports = parse_ports(ports) #if parsed ports are up
        with concurrent.futures.ThreadPoolExecutor(max_threads) as executor: #multithreads to read multiple hosts ports at the same time
            port_results = {host: executor.submit(scan_ports, host, parsed_ports) for host in active_hosts} #Displays results

        for host, future in port_results.items(): #for hosts in the successful port scans
            open_ports = future.result() #grabs all open ports
            if open_ports: #if theyre open ports
                print(f"{host}  - UP (Latency: {active_hosts[host]} ms) - Ports:", end=" ") #print format for host, up status, latency, and the active ports
                print(", ".join([f"{port} (OPEN)" for port in open_ports])) #prints all output
            else:
                print(f"{host}  - UP (Latency: {active_hosts[host]} ms) - Ports: None (Closed)") #prints hosts and same format except for if the ports are closed

# Command-line argument parsing
if __name__ == "__main__": #sets main
    parser = argparse.ArgumentParser(description="Scan a network for active hosts and open ports.") #scans the network
    parser.add_argument("network", help="Network CIDR block (e.g., 192.168.1.0/24)") #takes in the ip address in CIDR notation
    parser.add_argument("-p", "--ports", help="Ports to scan (e.g., 80, 22-100, 443)") #takes all our specified ports to be scanned
    args = parser.parse_args()

    network_scanner(args.network, args.ports) #calls our function and the arguments
