from time     import time
from datetime import datetime
from snappi   import snappi
from paramiko import SSHClient, AutoAddPolicy
import os
import time

def Traffic_Test():

    ## This script does following:
    ## - Send packets back and forth between the two ports
    ## - Take one of the DUTs link down to trigger the convergence
    ## - Wait for traffic to stop and calculate the convergence time

    test_const = {
        "pktRate": 100,
        "pktCount": 5000,
        "pktSize": 100,
        "1Mac": "00:00:01:01:01:01",
        "1Ip": "192.168.11.2",
        "1Gateway": "192.168.11.1",
        "1Prefix": 24,
        "2Mac": "00:00:01:01:02:01",
        "2Ip": "192.168.22.2",
        "2Gateway": "192.168.22.1",
        "2Prefix": 24,
        "dutName": "clab-ixsrlx3-srl1",
        "dutInterface": "ethernet-1/3"
    }
    
    api = snappi.api(location="https://clab-ixsrlx3-ixia-c:8443", verify=False)

    create_config(api, test_const)

    start_protocols(api)
    
    time.sleep(2)
    
    start_transmit(api)
    
    print("%s TOTAL  \t\tTx_Frames\tRx_Frames"% datetime.now())
    wait_for(lambda:get_flow_statistics(api))
    
    dut_link_operation(test_const,"disable")
    
    print("%s TOTAL  \t\tTx_Frames\tRx_Frames"% datetime.now())
    wait_for(lambda:get_flow_statistics(api),60,2)
    
    get_convergence_time(api,test_const)
    
    dut_link_operation(test_const,"enable")

def create_config(api, test_const):
        # Configure a new API instance where the location points to controller
    # Ixia-C:       location = "https://<tgen-ip>:<port>"
    # IxNetwork:    location = "https://<tgen-ip>:<port>", ext="ixnetwork"

    print("")
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
    d1_eth.mac = test_const["1Mac"]

    d1_ip = d1_eth.ipv4_addresses.add(name="d1_ip")
    d1_ip.set(address=test_const["1Ip"], gateway=test_const["1Gateway"], prefix=test_const["1Prefix"])

    d2_eth = device2.ethernets.add(name="d2_eth")
    d2_eth.connection.port_name = port2.name
    d2_eth.mac = test_const["2Mac"]

    d2_ip = d2_eth.ipv4_addresses.add(name="d2_ip")
    d2_ip.set(address=test_const["2Ip"], gateway=test_const["2Gateway"], prefix=test_const["2Prefix"])


    # Configure traffic flow
    flow1 = configuration.flows.add(name="Device 1 > Device 2")

    # Enabling flow metrics for flow statistics
    flow1.metrics.enable = True

    # Configure source and destination endpoints
    flow1.tx_rx.device.tx_names = ["d1_ip"]
    flow1.tx_rx.device.rx_names = ["d2_ip"]

    # Configure packet size, rate, and duration
    flow1.size.fixed = test_const["pktSize"]
    flow1.duration.fixed_packets.packets = test_const["pktCount"]
    flow1.rate.pps = test_const["pktRate"]

    # Configure packet with Ethernet, IPv4 headers
    flow1.packet.ethernet().ipv4()
    eth1, ip1 = flow1.packet[0], flow1.packet[1]

    # Configure source and destination MAC addresses
    eth1.src.value = test_const["1Mac"]

    # Configure source and destination IPv4 addresses
    ip1.src.value, ip1.dst.value = test_const["1Ip"], test_const["2Ip"]


    print("%s Starting configuration apply                          ... " % datetime.now())
    api.set_config(configuration)

def start_protocols(api):
    print("%s Starting protocols    ..." % datetime.now())
    cs = api.control_state()
    cs.choice = cs.PROTOCOL
    cs.protocol.choice = cs.protocol.ALL
    cs.protocol.all.state = cs.protocol.all.START
    api.set_control_state(cs)

def start_transmit(api):
    print("%s Starting transmit on all flows    ..." % datetime.now())
    cs = api.control_state()
    cs.choice = cs.TRAFFIC
    cs.traffic.choice = cs.traffic.FLOW_TRANSMIT
    cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.START
    api.set_control_state(cs)

def get_flow_statistics(api):

    # Create a flow statistics request and filter based on flow names
    mr = api.metrics_request()
    mr.flow.flow_names = ["Device 1 > Device 2"]
    m = api.get_metrics(mr).flow_metrics[0]

    print("%s TOTAL  \t\t%d\t\t%d" % (datetime.now(), m.frames_tx, m.frames_rx))
    if m.transmit == m.STOPPED:
        return True
    return False

def get_convergence_time(api,tc):
    mr = api.metrics_request()
    mr.flow.flow_names = ["Device 1 > Device 2"]
    m = api.get_metrics(mr).flow_metrics[0]
    
    convergence = (m.frames_tx - m.frames_rx)/tc["pktRate"]
    print("%s Convergence time was %s" % (datetime.now(), convergence))

def wait_for(func, timeout=60, interval=2):

    # Keeps calling the `func` until it returns true or `timeout` occurs every `interval` seconds.

    start = time.time()

    while time.time() - start <= timeout:
        if func():
            return True
        time.sleep(interval)

    return False

def dut_link_operation(test_const,state):
    client = SSHClient()
    client.load_host_keys(os.path.expanduser('~')+'/.ssh/known_hosts')
    client.load_system_host_keys
    client.set_missing_host_key_policy(AutoAddPolicy())
    dutCmd = "sr_cli -ec set interface {} admin-state {}".format(test_const["dutInterface"],state)
    try:
        client.connect(test_const["dutName"],port=22,username="linuxadmin",password="NokiaSrl1!",timeout=10)
        print("Reseting the DUT %s" %test_const["dutName"])
        stdin,stdout,stderr = client.exec_command(dutCmd)
        print(f'stdout:" {stdout.read().decode("utf8")}')
        print(f'stderr:" {stderr.read().decode("utf8")}')
        client.close()
        return 0
    except:
        print("ERROR connecting to {0}".format(test_const["dutName"]))
        print("ERROR connecting with errors". stderr)
        return 1

if __name__ == "__main__":
    Traffic_Test()
