import logging as log
import snappi
from datetime import datetime
import time

   
def Test_ibgp_route_prefix():
    # TODO: add support for BGP for IPv6 as well
    test_const = {
        "pktRate": 50,
        "pktCount": 1500,
        "pktSize": 128,
        "trafficDuration": 20,
        "1Mac": "00:00:01:01:01:01",
        "1Ip": "192.168.11.2",
        "1Gateway": "192.168.11.1",
        "1Prefix": 24,
        "1As": 65001,
        "2Mac": "00:00:01:01:01:02",
        "2Ip": "192.168.22.2",
        "2Gateway": "192.168.22.1",
        "2Prefix": 24,
        "2As": 65001,
        "routeCount": 10,
        "1AdvRoute": "101.10.10.1",
        "2AdvRoute": "201.20.20.1",
    }

    api = snappi.api(location="https://clab-ixsrl-ixia-c:8443", verify=False)
    c = ibgp_route_prefix_config(api, test_const)

    api.set_config(c)
    
    start_protocols(api)
    
    wait_for(lambda: bgp_metrics_ok(api, test_const),"correct bgp peering")
    
    get_bgp_prefixes(api)
    
    start_transmit(api)
    
    wait_for(lambda: flow_metrics_ok(api, test_const), "flow metrics",2,90)


def ibgp_route_prefix_config(api, tc):
    c = api.config()
    p1 = c.ports.add(name="p1", location="eth1")
    p2 = c.ports.add(name="p2", location="eth2")

    d1 = c.devices.add(name="d1")
    d2 = c.devices.add(name="d2")

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
        as_number=tc["1As"], as_type=d1_bgpv4_peer.IBGP, peer_address=tc["1Gateway"]
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
        as_number=tc["2As"], as_type=d2_bgpv4_peer.IBGP, peer_address=tc["2Gateway"]
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
        address=tc["2AdvRoute"], prefix=32, count=tc["routeCount"], step=1
    )


    for i in range(2):
        f = c.flows.add()
        f.duration.fixed_packets.packets = tc["pktCount"]
        f.rate.pps = tc["pktRate"]
        f.size.fixed = tc["pktSize"]
        f.metrics.enable = True

    f1 = c.flows[0]
    f1.name = "f1"
    f1.tx_rx.device.set(
        tx_names=[d1_bgpv4_peer_rrv4.name], rx_names=[d2_bgpv4_peer_rrv4.name]
    )

    f1_eth, f1_ip = f1.packet.ethernet().ipv4()
    f1_eth.src.value = d1_eth.mac
    f1_ip.src.increment.start = tc["1AdvRoute"]
    f1_ip.src.increment.count = tc["routeCount"]
    f1_ip.dst.increment.start = tc["2AdvRoute"]
    f1_ip.dst.increment.count = tc["routeCount"]

    f2 = c.flows[1]
    f2.name = "f2"
    f2.tx_rx.device.set(
        tx_names=[d2_bgpv4_peer_rrv4.name],rx_names=[d1_bgpv4_peer_rrv4.name]
    )

    f2_eth, f2_ip = f2.packet.ethernet().ipv4()
    f2_eth.src.value = d2_eth.mac
    f2_ip.src.increment.start = tc["2AdvRoute"]
    f2_ip.src.increment.count = tc["routeCount"]
    f2_ip.dst.increment.start = tc["1AdvRoute"]
    f2_ip.dst.increment.count = tc["routeCount"]

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


def flow_metrics_ok(api, tc):
    for m in get_flow_metrics(api):
        if (
            m.transmit != m.STOPPED
            or m.frames_tx != tc["pktCount"]
            or m.frames_rx != tc["pktCount"]
        ):
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
