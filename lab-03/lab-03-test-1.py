import logging as log
import snappi
from datetime import datetime
import time

   
def Test_ibgp_route_prefix():
    test_const = {
        "pktRate": 100,
        "pktCount": 1000,
        "pktSize": 128,
        "1Mac": "00:00:01:01:01:01",
        "1Ip": "192.168.11.2",
        "1Gateway": "192.168.11.1",
        "1Prefix": 24,
        "2VlanStart": 101,
        "2IpStart": "192.168.101.2",
        "2SubnetCount": 3
    }

    api = snappi.api(location="https://clab-lab-03-ixia-c:8443", verify=False)
    
    c = ibgp_route_prefix_config(api, test_const)

    api.set_config(c)
    
    start_protocols(api)
    
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

    rx_endpoints = []
    for i in range(1,tc["2SubnetCount"]+1):
        mac = "00:00:01:02:01:"+format("%02x" % i)
        ip = "192.168." + str(100+i) + ".2"
        gw_ip = "192.168." + str(100+i) + ".1"
        vlan_id = 100 + i
        d2_eth = d2.ethernets.add(name="d2_eth_"+ str(i))
        d2_eth.connection.port_name = p2.name
        d2_eth.set(mac=mac, mtu=1500)

        d2_vlan = d2_eth.vlans.add(name="d2_vlan_"+str(i))
        d2_vlan.id=vlan_id
        
        d2_ip = d2_eth.ipv4_addresses.add(name="d2_ip_"+str(i))
        rx_endpoints.append(d2_ip.name)
        d2_ip.set(address=ip, gateway=gw_ip, prefix=24)


    f = c.flows.add()
    f.name = "f1"
    f.duration.fixed_packets.packets = tc["pktCount"]
    f.rate.pps = tc["pktRate"]
    f.size.fixed = tc["pktSize"]
    f.metrics.enable = True

    f.tx_rx.device.set(
        tx_names=[d1_ip.name], rx_names=rx_endpoints
    )

    f_eth = f.packet.add().ethernet
    f_ip = f.packet.add().ipv4
    f_eth.src.value = d1_eth.mac
    f_ip.src.value = tc["1Ip"]
    f_ip.dst.increment.set(start = tc["2IpStart"], step = "0.0.1.0", count = tc["2SubnetCount"])
    f_ip.priority.dscp.phb.values = [10,20,30]
    
    f.egress_packet.ethernet()
    eg_vlan = f.egress_packet.add().vlan
    # eg_vlan.id.metric_tags.add(name="vladIdRx")
    eg_ip = f.egress_packet.add().ipv4
    eg_ip.priority.raw.metric_tags.add(name="dscpValuesRx", length=6)

    return c

def flow_metrics_ok(api, tc):
    for m in get_flow_metrics(api):
        if (
            m.transmit != m.STOPPED
            or m.frames_tx != tc["pktCount"]
            or m.frames_rx != tc["pktCount"]
        ):
            return False
    return True


def get_flow_metrics(api):

    print("%s Getting flow metrics    ..." % datetime.now())
    req = api.metrics_request()
    req.flow.flow_names = []

    metrics = api.get_metrics(req).flow_metrics
    tb_flow = Table(
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
        tb_flow.append_row(
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
        if len(m.tagged_metrics) > 0:
            tb_tags = Table(
                "Tagged Metrics",
                [
                    "DscpValue",
                    "Frames Rx",
                    "FPS Rx",
                    "Bytes Rx",
                ],
            )
            for t in m.tagged_metrics:
                dscpValue=int(t.tags[0].value.hex,16)
                # dscpValue=t.tags[0].value.hex
                tb_tags.append_row(
                    [
                        dscpValue,
                        t.frames_rx,
                        t.frames_rx_rate,
                        t.bytes_rx,
                    ]
                )
    print(tb_flow)
    if 'tb_tags' in locals(): 
        print(tb_tags)
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
