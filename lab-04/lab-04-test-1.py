from time     import time
from datetime import datetime
from snappi   import snappi
import time

def Traffic_Test():

    ## This script does following:
    ## - Send packets back and forth between the two ports
    ## - Validate that total packets sent and received on both interfaces is as expected using port metrics.

    starttime = datetime.now()

    # Configure a new API instance where the location points to controller
    # Ixia-C:       location = "https://<tgen-ip>:<port>"
    # IxNetwork:    location = "https://<tgen-ip>:<port>", ext="ixnetwork"

    print("")
    api = snappi.api(location="https://clab-ixsrl-ixia-c:8443", verify=False)
    print("%s Starting connection to controller                     ... " % datetime.now())

    # Create an empty configuration to be pushed to controller
    configuration = api.config()

    # Configure two ports where the location points to the port location:
    # Ixia-C:       port.location = "localhost:5555"
    # IxNetwork:    port.location = "<chassisip>;card;port"

    port1, port2 = (
        configuration.ports
        .port(name="Port-1", location="eth1")
        .port(name="Port-2", location="eth2")
    )

    # Configure devices
    device1 = configuration.devices.add(name="Device1")
    device2 = configuration.devices.add(name="Device2")

    d1_eth = device1.ethernets.add(name="d1_eth")
    d1_eth.connection.port_name = port1.name
    d1_eth.mac = "00:AA:00:00:01:00"

    d1_ip = d1_eth.ipv4_addresses.add(name="d1_ip")
    d1_ip.set(address="192.168.11.2", gateway="192.168.11.1", prefix=24)

    d2_eth = device2.ethernets.add(name="d2_eth")
    d2_eth.connection.port_name = port2.name
    d2_eth.mac = "00:AA:00:00:02:00"

    d2_ip = d2_eth.ipv4_addresses.add(name="d2_ip")
    d2_ip.set(address="192.168.22.2", gateway="192.168.22.1", prefix=24)


    # Configure traffic flow
    flow1 = configuration.flows.add(name="Flow #1 - Device 1 > Device 2")

    # Enabling flow metrics for flow statistics
    flow1.metrics.enable = True

    # Configure source and destination endpoints
    flow1.tx_rx.device.tx_names = ["d1_ip"]
    flow1.tx_rx.device.rx_names = ["d2_ip"]

    # Configure packet size, rate, and duration
    flow1.size.fixed = 128
    flow1.duration.fixed_packets.packets = 2000
    flow1.rate.pps = 100

    # Configure packet with Ethernet, IPv4 headers
    flow1.packet.ethernet().ipv4()
    eth1, ip1 = flow1.packet[0], flow1.packet[1]

    # Configure source and destination MAC addresses
    eth1.src.value = "00:AA:00:00:01:00"

    # Configure source and destination IPv4 addresses
    ip1.src.value, ip1.dst.value = "192.168.11.2", "192.168.22.2"


    print("%s Starting configuration apply                          ... " % datetime.now())
    api.set_config(configuration)


    print("%s Starting protocols                                    ... " % datetime.now())
    cs = api.control_state()
    cs.protocol.all.state = cs.protocol.all.START

    time.sleep(2)
    
    print("%s Starting transmit on all flows                        ... " % datetime.now())
    cs = api.control_state()
    cs.choice = cs.TRAFFIC
    cs.traffic.choice = cs.traffic.FLOW_TRANSMIT
    cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.START
    api.set_control_state(cs)

    print("%s Starting statistics verification on all ports         ... " % datetime.now())
    print("====================================================================================")
    print("\t\t\t\t\t\tExpected\tTx\t\tRx")
    assert wait_for(lambda: verify_statistics(api, configuration)), "%s Test is FAILED in %s" % (datetime.now(), datetime.now() - starttime)
    print("====================================================================================")
    print("%s Test is PASSED in %s                                      " % (datetime.now(), datetime.now() - starttime))
    print("")


def verify_statistics(api, configuration):

    # Create a port statistics request and filter based on port names
    statistics = api.metrics_request()
    statistics.port.port_names = [p.name for p in configuration.ports]

    # Create a filter to include only sent and received packet statistics
    statistics.port.column_names = [statistics.port.FRAMES_TX, statistics.port.FRAMES_RX]

    # Collect port statistics
    results = api.get_metrics(statistics)

    # Calculate total frames sent and received across all ports
    total_frames_tx = sum([m.frames_tx for m in results.port_metrics])
    total_frames_rx = sum([m.frames_rx for m in results.port_metrics])
    total_expected  = sum([f.duration.fixed_packets.packets for f in configuration.flows])

    print("%s TOTAL  \t\t%d\t\t%d\t\t%d" % (datetime.now(), total_expected, total_frames_tx, total_frames_rx))

    return total_expected == total_frames_tx and total_frames_rx >= total_expected


def wait_for(func, timeout=30, interval=1):

    # Keeps calling the `func` until it returns true or `timeout` occurs every `interval` seconds.

    import time

    start = time.time()

    while time.time() - start <= timeout:
        if func():
            return True
        time.sleep(interval)

    return False


if __name__ == "__main__":
    Traffic_Test()
