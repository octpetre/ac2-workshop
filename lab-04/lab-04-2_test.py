import logging as log
import snappi
from datetime import datetime
import time

   
def Test_ibgp_route_prefix():
    test_const = {
        "pktRate": 1000,
        "pktCount": 15000,
        "pktSize": 100,
        "bgpAs": 65001,
        "1Mac": "00:00:01:01:01:01",
        "1Ip": "192.168.11.2",
        "1Gateway": "192.168.11.1",
        "1Prefix": 24,
        "2Mac": "00:00:01:01:02:01",
        "2Ip": "192.168.22.2",
        "2Gateway": "192.168.22.1",
        "2Prefix": 24,
        "3Mac": "00:00:01:01:03:01",
        "3Ip": "192.168.33.2",
        "3Gateway": "192.168.33.1",
        "3Prefix": 24,
        "routeCount": 5,
        "1AdvRoute": "101.10.10.1",
        "startDstRoute": "201.30.30.1",
    }

    api = snappi.api(location="https://clab-lab-04-ixia-c:8443", verify=False)
    c = ibgp_route_prefix_config(api, test_const)

    api.set_config(c)
    
    start_protocols(api)
    
    wait_for(lambda: bgp_metrics_ok(api, test_const),"correct bgp peering",2,60)
    
    get_bgp_prefixes(api)
    
    start_transmit(api)
    
    start = time.time()

    while True:
        get_flow_metrics(api)
        get_port_metrics(api)
        if time.time() - start > (test_const["pktCount"]/test_const["pktRate"])/2:
            break
        time.sleep(2)

    # withdraw_routes(api)
    
    link_operation(api, "down")

    time.sleep(2)
    
    get_bgp_prefixes(api)    
    
    wait_for(lambda: traffic_stopped(api), "traffic stopped",2,90)

    get_convergence_time(api,test_const)
    
    link_operation(api, "up")


def ibgp_route_prefix_config(api, tc):
    c = api.config()
    p1 = c.ports.add(name="p1", location="eth1")
    p2 = c.ports.add(name="p2", location="eth2")
    p3 = c.ports.add(name="p3", location="eth3")


    d1 = c.devices.add(name="d1")
    d2 = c.devices.add(name="d2")
    d3 = c.devices.add(name="d3")

    d1_eth = d1.ethernets.add(name="d1_eth")
    d1_eth.connection.port_name = p1.name
    d1_eth.mac = tc["1Mac"]
    d1_eth.mtu = 1500

    d1_ip = d1_eth.ipv4_addresses.add(name="d1_ip")
    d1_ip.set(address=tc["1Ip"], gateway=tc["1Gateway"], prefix=tc["1Prefix"])

    d1.bgp.router_id = tc["1Ip"]
    d1_bgpv4 = d1.bgp.ipv4_interfaces.add(ipv4_name=d1_ip.name)

    d1_bgpv4_peer = d1_bgpv4.peers.add(name="d1_bgpv4_peer")
    d1_bgpv4_peer.set(
        as_number=tc["bgpAs"], as_type=d1_bgpv4_peer.IBGP, peer_address=tc["1Gateway"]
    )
    d1_bgpv4_peer.learned_information_filter.set(
        unicast_ipv4_prefix=True, unicast_ipv6_prefix=True
    )
    d1_bgpv4_peer_rrv4 = d1_bgpv4_peer.v4_routes.add(name="d1_bgpv4_peer_rrv4")
    d1_bgpv4_peer_rrv4.set(
        next_hop_ipv4_address=tc["1Ip"],
        next_hop_address_type=d1_bgpv4_peer_rrv4.IPV4,
        next_hop_mode=d1_bgpv4_peer_rrv4.MANUAL,
    )
    d1_bgpv4_peer_rrv4.addresses.add(
        address=tc["1AdvRoute"], prefix=32, count=tc["routeCount"], step=1
    )

    d2_eth = d2.ethernets.add(name="d2_eth")
    d2_eth.connection.port_name = p2.name
    d2_eth.mac = tc["2Mac"]
    d2_eth.mtu = 1500

    d2_ip = d2_eth.ipv4_addresses.add(name="d2_ip")
    d2_ip.set(address=tc["2Ip"], gateway=tc["2Gateway"], prefix=tc["2Prefix"])

    d2.bgp.router_id = tc["2Ip"]

    d2_bgpv4 = d2.bgp.ipv4_interfaces.add()
    d2_bgpv4.ipv4_name = d2_ip.name

    d2_bgpv4_peer = d2_bgpv4.peers.add(name="d2_bgpv4_peer")
    d2_bgpv4_peer.set(
        as_number=tc["bgpAs"], as_type=d2_bgpv4_peer.IBGP, peer_address=tc["2Gateway"]
    )
    d2_bgpv4_peer.learned_information_filter.set(
        unicast_ipv4_prefix=True, unicast_ipv6_prefix=True
    )

    d2_bgpv4_peer_rrv4 = d2_bgpv4_peer.v4_routes.add(name="d2_bgpv4_peer_rrv4")
    d2_bgpv4_peer_rrv4.set(
        next_hop_ipv4_address=tc["2Ip"],
        next_hop_address_type=d2_bgpv4_peer_rrv4.IPV4,
        next_hop_mode=d2_bgpv4_peer_rrv4.MANUAL,
    )
    d2_bgpv4_peer_rrv4.addresses.add(
        address=tc["startDstRoute"], prefix=32, count=tc["routeCount"], step=1
    )
    d2_bgpv4_peer_rrv4.advanced.set(
        local_preference = 200,
        multi_exit_discriminator = 100
    )
    
    d3_eth = d3.ethernets.add(name="d3_eth")
    d3_eth.connection.port_name = p3.name
    d3_eth.mac = tc["3Mac"]
    d3_eth.mtu = 1500

    d3_ip = d3_eth.ipv4_addresses.add(name="d3_ip")
    d3_ip.set(address=tc["3Ip"], gateway=tc["3Gateway"], prefix=tc["3Prefix"])

    d3.bgp.router_id = tc["3Ip"]

    d3_bgpv4 = d3.bgp.ipv4_interfaces.add()
    d3_bgpv4.ipv4_name = d3_ip.name

    d3_bgpv4_peer = d3_bgpv4.peers.add(name="d3_bgpv4_peer")
    d3_bgpv4_peer.set(
        as_number=tc["bgpAs"], as_type=d3_bgpv4_peer.IBGP, peer_address=tc["3Gateway"]
    )
    d3_bgpv4_peer.learned_information_filter.set(
        unicast_ipv4_prefix=True, unicast_ipv6_prefix=True
    )

    d3_bgpv4_peer_rrv4 = d3_bgpv4_peer.v4_routes.add(name="d3_bgpv4_peer_rrv4")
    d3_bgpv4_peer_rrv4.set(
        next_hop_ipv4_address=tc["3Ip"],
        next_hop_address_type=d2_bgpv4_peer_rrv4.IPV4,
        next_hop_mode=d2_bgpv4_peer_rrv4.MANUAL,
    )
    d3_bgpv4_peer_rrv4.addresses.add(
        address=tc["startDstRoute"], prefix=32, count=tc["routeCount"], step=1
    )
    d3_bgpv4_peer_rrv4.advanced.set(
        local_preference = 150,
        multi_exit_discriminator = 200
    )
    
    f = c.flows.add()
    f.duration.fixed_packets.packets = tc["pktCount"]
    f.rate.pps = tc["pktRate"]
    f.size.fixed = tc["pktSize"]
    f.metrics.enable = True

    f.name = "bgpFlow"
    f.tx_rx.device.set(
        tx_names=[d1_bgpv4_peer_rrv4.name], rx_names=[d2_bgpv4_peer_rrv4.name,d3_bgpv4_peer_rrv4.name]
    )

    f_eth, f_ip = f.packet.ethernet().ipv4()
    f_eth.src.value = d1_eth.mac
    f_ip.src.increment.start = tc["1AdvRoute"]
    f_ip.src.increment.count = tc["routeCount"]
    f_ip.dst.increment.start = tc["startDstRoute"]
    f_ip.dst.increment.count = tc["routeCount"]

    return c


def bgp_metrics_ok(api, tc):
    for m in get_bgpv4_metrics(api):
        if (
            m.session_state == m.DOWN
            or m.routes_advertised < tc["routeCount"]
            or m.routes_received < tc["routeCount"]
        ):
            return False
    return True


def traffic_stopped(api):
    for m in get_flow_metrics(api):
        get_port_metrics(api)
        if m.transmit != m.STOPPED:
            return False
    return True


def get_bgpv4_metrics(api):
    print("%s Getting bgpv4 metrics    ..." % datetime.now())
    req = api.metrics_request()
    req.bgpv4.peer_names = []

    metrics = api.get_metrics(req).bgpv4_metrics

    tb = Table(
        "BGPv4 Metrics",
        [
            "Name",
            "State",
            "Routes Adv.",
            "Routes Rec.",
        ],
    )

    for m in metrics:
        tb.append_row(
            [
                m.name,
                m.session_state,
                m.routes_advertised,
                m.routes_received,
            ]
        )

    print(tb)
    return metrics


def get_bgp_prefixes(api):
    print("%s Getting BGP prefixes    ..." % datetime.now())
    req = api.states_request()
    req.bgp_prefixes.bgp_peer_names = []
    bgp_prefixes = api.get_states(req).bgp_prefixes

    tb = Table(
        "BGP Prefixes",
        [
            "Name",
            "IPv4 Address",
            "IPv4 Next Hop",
            "IPv6 Address",
            "IPv6 Next Hop",
        ],
        20,
    )

    for b in bgp_prefixes:
        for p in b.ipv4_unicast_prefixes:
            tb.append_row(
                [
                    b.bgp_peer_name,
                    "{}/{}".format(p.ipv4_address, p.prefix_length),
                    p.ipv4_next_hop,
                    "",
                    "" if p.ipv6_next_hop is None else p.ipv6_next_hop,
                ]
            )
        for p in b.ipv6_unicast_prefixes:
            tb.append_row(
                [
                    b.bgp_peer_name,
                    "",
                    "" if p.ipv4_next_hop is None else p.ipv4_next_hop,
                    "{}/{}".format(p.ipv6_address, p.prefix_length),
                    p.ipv6_next_hop,
                ]
            )

    print(tb)
    return bgp_prefixes


def get_flow_metrics(api):

    print("%s Getting flow metrics    ..." % datetime.now())
    req = api.metrics_request()
    req.flow.flow_names = []

    metrics = api.get_metrics(req).flow_metrics

    tb = Table(
        "Flow Metrics",
        [
            "Name",
            "State",
            "Frames Tx",
            "Frames Rx",
            "FPS Tx",
            "FPS Rx",
            "Bytes Tx",
            "Bytes Rx",
        ],
    )

    for m in metrics:
        tb.append_row(
            [
                m.name,
                m.transmit,
                m.frames_tx,
                m.frames_rx,
                m.frames_tx_rate,
                m.frames_rx_rate,
                m.bytes_tx,
                m.bytes_rx,
            ]
        )
    print(tb)
    return metrics


def get_port_metrics(api):

    print("%s Getting port metrics    ..." % datetime.now())
    req = api.metrics_request()
    req.port.port_names = []

    metrics = api.get_metrics(req).port_metrics

    tb = Table(
        "Port Metrics",
        [
            "Name",
            "State",
            "Frames Tx",
            "Frames Rx",
            "FPS Tx",
            "FPS Rx",
            "Bytes Tx",
            "Bytes Rx",
            "Bytes Tx Rate",
            "Bytes Rx Rate",
        ],
    )

    for m in metrics:
        tb.append_row(
            [
                m.name,
                m.transmit,
                m.frames_tx,
                m.frames_rx,
                m.frames_tx_rate,
                m.frames_rx_rate,
                m.bytes_tx,
                m.bytes_rx,
                m.bytes_tx_rate,
                m.bytes_rx_rate,
            ]
        )
    print(tb)
    return metrics


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


def stop_transmit(api):
    print("%s Stopping transmit    ..." % datetime.now())
    cs = api.control_state()
    cs.choice = cs.TRAFFIC
    cs.traffic.choice = cs.traffic.FLOW_TRANSMIT
    cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.STOP
    api.set_control_state(cs)


def withdraw_routes(api):
    print("%s Withdraw routes from port 2    ..." % datetime.now())
    cs = api.control_state()
    cs.choice = cs.PROTOCOL
    cs.protocol.choice = cs.protocol.ROUTE
    cs.protocol.route.names = ["d2_bgpv4_peer_rrv4"]
    cs.protocol.route.state = cs.protocol.route.WITHDRAW
    api.set_control_state(cs)


def link_operation(api, operation):
    print("%s Bringing %s port 2    ..." % (datetime.now(),operation))
    cs = api.control_state()
    cs.choice = cs.PORT
    cs.port.choice = cs.port.LINK
    cs.port.link.port_names = ["p2"]
    if operation == "down":
        cs.port.link.state = cs.port.link.DOWN
    else:
        cs.port.link.state = cs.port.link.UP
    api.set_control_state(cs)


def get_convergence_time(api,tc):
    mr = api.metrics_request()
    mr.flow.flow_names = ["bgpFlow"]
    m = api.get_metrics(mr).flow_metrics[0]
    
    convergence = (m.frames_tx - m.frames_rx)/tc["pktRate"]
    print("%s Convergence time was %ss" % (datetime.now(), convergence))



def wait_for(func, condition_str, interval_seconds=None, timeout_seconds=None):
    """
    Keeps calling the `func` until it returns true or `timeout_seconds` occurs
    every `interval_seconds`. `condition_str` should be a constant string
    implying the actual condition being tested.

    Usage
    -----
    If we wanted to poll for current seconds to be divisible by `n`, we would
    implement something similar to following:
    ```
    import time
    def wait_for_seconds(n, **kwargs):
        condition_str = 'seconds to be divisible by %d' % n

        def condition_satisfied():
            return int(time.time()) % n == 0

        poll_until(condition_satisfied, condition_str, **kwargs)
    ```
    """
    if interval_seconds is None:
        interval_seconds = 1
    if timeout_seconds is None:
        timeout_seconds = 60
    start_seconds = int(time.time())

    print('\n\nWaiting for %s ...' % condition_str)
    while True:
        if func():
            print('Done waiting for %s' % condition_str)
            break
        if (int(time.time()) - start_seconds) >= timeout_seconds:
            msg = 'Time out occurred while waiting for %s' % condition_str
            raise Exception(msg)

        time.sleep(interval_seconds)
    

class Table(object):
    def __init__(self, title, headers, col_width=15):
        self.title = title
        self.headers = headers
        self.col_width = col_width
        self.rows = []

    def append_row(self, row):
        diff = len(self.headers) - len(row)
        for i in range(0, diff):
            row.append("_")

        self.rows.append(row)

    def __str__(self):
        out = ""
        border = "-" * (len(self.headers) * self.col_width)

        out += "\n"
        out += border
        out += "\n%s\n" % self.title
        out += border
        out += "\n"

        for h in self.headers:
            out += ("%%-%ds" % self.col_width) % str(h)
        out += "\n"

        for row in self.rows:
            for r in row:
                out += ("%%-%ds" % self.col_width) % str(r)
            out += "\n"
        out += border
        out += "\n\n"

        return out


if __name__ == "__main__":
    Test_ibgp_route_prefix()
