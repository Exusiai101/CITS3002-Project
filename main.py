import sys

from devices import init_network

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("No arguments provided. It will be set to 500 bytes.")
        data_size = 500
    elif len(sys.argv) != 2 or sys.argv[1] == "--help" or (not sys.argv[1].isdigit()):
        print("Usage: python main.py <data_size_in_bytes>")
        sys.exit(1)
    else:
        data_size = int(sys.argv[1])

    host_a, host_b, router = init_network()

    print("Starting Simulation...")

    host_a.send(data_size)

    print("\nSimulation Complete.")