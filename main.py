import sys

from devices import init_network

if __name__ == "__main__":

    if len(sys.argv) == 1:
        print("No arguments provided. It will be set to 1200 bytes.")
        data_size = 1200
    elif len(sys.argv) != 2 or sys.argv[1] == "--help" or (not sys.argv[1].isdigit()):
        print("Usage: python main.py <data_size_in_bytes>")
        sys.exit(1)
    else:
        data_size = int(sys.argv[1])
        if data_size <= 0 :
            print("Data size must be greater than 0.")
            sys.exit(1)

    host_a, host_b, router = init_network()

    print("Starting Simulation...")

    host_a.send(data_size)

    print("\nSimulation Complete.")