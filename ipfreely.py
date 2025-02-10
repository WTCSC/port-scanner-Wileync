
import ipaddress #imports ipaddress module allows us to manipulate ips
import subprocess #imports subprocess module allowing us to ping
import platform #imports platform module to identify the users operating system
import concurrent.futures #Imports module for concurrent execution using threads
import logging #imports logging module allowing us to track errors
import argparse #imports arparse to do commandline input
import re #imports regular expression

# Configure logging
logging.basicConfig(filename="ping_errors.log", level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s") #sets format for errors that get logged

def ping_host(ip): #defines our function
    """Pings a single host and returns response time or failure."""
    param = "-n" if platform.system().lower() == "windows" else "-c"  # Windows uses -n, Linux/macOS uses -c
    try:
        result = subprocess.run(["ping", param, "1", str(ip)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2) #runs ping and times out after 2 seconds

        if result.returncode == 0: #if no errors
            output = result.stdout #give resule
            match = re.search(r"time[=<](\d+\.?\d*)", output)  # Extract response time 
            if match:
                response_time = match.group(1)
                return f"{ip} is UP       - Response Time: {response_time} ms" #gives our responses for UP with time
            return f"{ip} is UP       - Response Time Unknown" #gives our response for UP if time was unknown
        
        elif "timed out" in result.stdout.lower() or "unreachable" in result.stdout.lower() or "timed out" in result.stderr.lower(): #if we get timed out or unreachible
            error_message = f"{ip} is DOWN - Connection Timed Out" #display error message for that ip
        else:
            error_message = f"{ip} is DOWN - Unknown Error" #display unknown error message for that ip

        logging.error(f"Ping to {ip} failed: {result.stderr.strip()}") #logs if ping failed
        return error_message # returns our error message
    
    except subprocess.TimeoutExpired: #if the ping takes to long we get request timed out response
        logging.error(f"Ping to {ip} failed: Request Timed Out")
        return f"{ip} is DOWN - Request Timed Out"

    except Exception as e: #if we get an unexpected error return down with error message
        logging.error(f"Ping to {ip} failed: {str(e)}") #add the error to log
        return f"{ip} is DOWN - Error: {str(e)}" #reponse down

def ippinger(network_cidr, max_threads=50): #speed up our output time by going over a bunch at the same time.
    """Finds all available hosts and pings them using multithreading."""
    try:
        network = ipaddress.ip_network(network_cidr, strict=False) #checks network
    except ValueError as e:
        print(f"Invalid network address: {e}") #returns invalid network address and error
        return

    hosts = list(network.hosts())  # Get all usable hosts

    print(f"Pinging {len(hosts)} hosts in {network} using {max_threads} threads...") #pings all our hosts

    with concurrent.futures.ThreadPoolExecutor(max_threads) as executor:
        results = executor.map(ping_host, hosts)  # Ping hosts in parallel

    for result in results: #prings all our results for all the ips
        print(result)

# Command-line argument parsing
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ping all hosts in a given subnet.")
    parser.add_argument("network", help="Network CIDR block (e.g., 192.168.1.0/24)")
    args = parser.parse_args()

    ippinger(args.network) #calls our function
