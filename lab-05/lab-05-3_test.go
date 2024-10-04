package bgp

import (
	"fmt"
	"log"
	"testing"
	"time"

	"github.com/open-traffic-generator/conformance/helpers/table"
	"github.com/open-traffic-generator/snappi/gosnappi"
)

func TestEbgpRoutePrefix(t *testing.T) {

	testConst := map[string]interface{}{
		"controller_location": "172.18.0.62:40051",
		"p1_location":         "eth1",
		"p2_location":         "eth2",
		"pktRate":             uint64(50),
		"pktCount":            uint32(100),
		"pktSize":             uint32(128),
		"txMac":               "00:00:01:01:01:01",
		"txIp":                "1.1.1.1",
		"txGateway":           "1.1.1.2",
		"txPrefix":            uint32(24),
		"txAs":                uint32(1111),
		"rxMac":               "00:00:01:01:01:02",
		"rxIp":                "1.1.1.2",
		"rxGateway":           "1.1.1.1",
		"rxPrefix":            uint32(24),
		"rxAs":                uint32(1112),
		"txRouteCount":        uint32(1),
		"rxRouteCount":        uint32(1),
		"txNextHopV4":         "1.1.1.3",
		"txNextHopV6":         "::1:1:1:3",
		"rxNextHopV4":         "1.1.1.4",
		"rxNextHopV6":         "::1:1:1:4",
		"txAdvRouteV4":        "10.10.10.1",
		"rxAdvRouteV4":        "20.20.20.1",
		"txAdvRouteV6":        "::10:10:10:1",
		"rxAdvRouteV6":        "::20:20:20:1",
	}

	api := gosnappi.NewApi()

	// api.NewHttpTransport().SetLocation("https://172.18.0.63:8443")
	api.NewGrpcTransport().SetLocation(testConst["controller_location"].(string))

	c := ebgpRoutePrefixConfig(testConst)

	api.SetConfig(c)

	startProtocols(t, api)

	/* Check if BGP sessions are up and expected routes are Txed and Rxed */
	waitFor(t,
		func() bool { return ebgpRoutePrefixBgpMetricsOk(t, api, testConst) },
		waitForOpts{FnName: "waiting for bgp neighbours", Interval: 2 * time.Second, Timeout: 30 * time.Second},
	)

	/* Check if each BGP session recieved routes with expected attributes */
	waitFor(t,
		func() bool { return ebgpRoutePrefixBgpPrefixesOk(t, api, testConst) },
		waitForOpts{FnName: "wait for bgp route prefixes", Interval: 2 * time.Second, Timeout: 30 * time.Second},
	)

	startTransmit(t, api)

	waitFor(t,
		func() bool { return ebgpRoutePrefixFlowMetricsOk(t, api, testConst) },
		waitForOpts{FnName: "wait for flow metrics", Interval: 1 * time.Second, Timeout: 30 * time.Second},
	)
}

type waitForOpts struct {
	FnName   string
	Interval time.Duration
	Timeout  time.Duration
}

func ebgpRoutePrefixConfig(tc map[string]interface{}) gosnappi.Config {

	c := gosnappi.NewConfig()

	ptx := c.Ports().Add().SetName("ptx").SetLocation(tc["p1_location"].(string))
	prx := c.Ports().Add().SetName("prx").SetLocation(tc["p2_location"].(string))

	dtx := c.Devices().Add().SetName("dtx")
	drx := c.Devices().Add().SetName("drx")

	dtxEth := dtx.Ethernets().
		Add().
		SetName("dtxEth").
		SetMac(tc["txMac"].(string)).
		SetMtu(1500)

	dtxEth.Connection().SetPortName(ptx.Name())

	dtxIp := dtxEth.
		Ipv4Addresses().
		Add().
		SetName("dtxIp").
		SetAddress(tc["txIp"].(string)).
		SetGateway(tc["txGateway"].(string)).
		SetPrefix(tc["txPrefix"].(uint32))

	dtxBgp := dtx.Bgp().
		SetRouterId(tc["txIp"].(string))

	dtxBgpv4 := dtxBgp.
		Ipv4Interfaces().Add().
		SetIpv4Name(dtxIp.Name())

	dtxBgpv4Peer := dtxBgpv4.
		Peers().
		Add().
		SetAsNumber(tc["txAs"].(uint32)).
		SetAsType(gosnappi.BgpV4PeerAsType.EBGP).
		SetPeerAddress(tc["txGateway"].(string)).
		SetName("dtxBgpv4Peer")

	dtxBgpv4Peer.LearnedInformationFilter().SetUnicastIpv4Prefix(true).SetUnicastIpv6Prefix(true)

	dtxBgpv4PeerRrV4 := dtxBgpv4Peer.
		V4Routes().
		Add().
		SetNextHopIpv4Address(tc["txNextHopV4"].(string)).
		SetName("dtxBgpv4PeerRrV4").
		SetNextHopAddressType(gosnappi.BgpV4RouteRangeNextHopAddressType.IPV4).
		SetNextHopMode(gosnappi.BgpV4RouteRangeNextHopMode.MANUAL)

	dtxBgpv4PeerRrV4.Addresses().Add().
		SetAddress(tc["txAdvRouteV4"].(string)).
		SetPrefix(32).
		SetCount(tc["txRouteCount"].(uint32)).
		SetStep(1)

	dtxBgpv4PeerRrV4.Advanced().
		SetMultiExitDiscriminator(50).
		SetOrigin(gosnappi.BgpRouteAdvancedOrigin.EGP)

	dtxBgpv4PeerRrV4.Communities().Add().
		SetAsNumber(1).
		SetAsCustom(2).
		SetType(gosnappi.BgpCommunityType.MANUAL_AS_NUMBER)

	dtxBgpv4PeerRrV4AsPath := dtxBgpv4PeerRrV4.AsPath().
		SetAsSetMode(gosnappi.BgpAsPathAsSetMode.INCLUDE_AS_SET)

	dtxBgpv4PeerRrV4AsPath.Segments().Add().
		SetAsNumbers([]uint32{1112, 1113}).
		SetType(gosnappi.BgpAsPathSegmentType.AS_SEQ)

	dtxBgpv4PeerRrV6 := dtxBgpv4Peer.
		V6Routes().
		Add().
		SetNextHopIpv6Address(tc["txNextHopV6"].(string)).
		SetName("dtxBgpv4PeerRrV6").
		SetNextHopAddressType(gosnappi.BgpV6RouteRangeNextHopAddressType.IPV6).
		SetNextHopMode(gosnappi.BgpV6RouteRangeNextHopMode.MANUAL)

	dtxBgpv4PeerRrV6.Addresses().Add().
		SetAddress(tc["txAdvRouteV6"].(string)).
		SetPrefix(128).
		SetCount(tc["txRouteCount"].(uint32)).
		SetStep(1)

	dtxBgpv4PeerRrV6.Advanced().
		SetMultiExitDiscriminator(50).
		SetOrigin(gosnappi.BgpRouteAdvancedOrigin.EGP)

	dtxBgpv4PeerRrV6.Communities().Add().
		SetAsNumber(1).
		SetAsCustom(2).
		SetType(gosnappi.BgpCommunityType.MANUAL_AS_NUMBER)

	dtxBgpv4PeerRrV6AsPath := dtxBgpv4PeerRrV6.AsPath().
		SetAsSetMode(gosnappi.BgpAsPathAsSetMode.INCLUDE_AS_SET)

	dtxBgpv4PeerRrV6AsPath.Segments().Add().
		SetAsNumbers([]uint32{1112, 1113}).
		SetType(gosnappi.BgpAsPathSegmentType.AS_SEQ)

	drxEth := drx.Ethernets().
		Add().
		SetName("drxEth").
		SetMac(tc["rxMac"].(string)).
		SetMtu(1500)

	drxEth.Connection().SetPortName(prx.Name())

	drxIp := drxEth.
		Ipv4Addresses().
		Add().
		SetName("drxIp").
		SetAddress(tc["rxIp"].(string)).
		SetGateway(tc["rxGateway"].(string)).
		SetPrefix(tc["rxPrefix"].(uint32))

	drxBgp := drx.Bgp().
		SetRouterId(tc["rxIp"].(string))

	drxBgpv4 := drxBgp.
		Ipv4Interfaces().Add().
		SetIpv4Name(drxIp.Name())

	drxBgpv4Peer := drxBgpv4.
		Peers().
		Add().
		SetAsNumber(tc["rxAs"].(uint32)).
		SetAsType(gosnappi.BgpV4PeerAsType.EBGP).
		SetPeerAddress(tc["rxGateway"].(string)).
		SetName("drxBgpv4Peer")

	drxBgpv4Peer.LearnedInformationFilter().SetUnicastIpv4Prefix(true).SetUnicastIpv6Prefix(true)

	drxBgpv4PeerRrV4 := drxBgpv4Peer.
		V4Routes().
		Add().
		SetNextHopIpv4Address(tc["rxNextHopV4"].(string)).
		SetName("drxBgpv4PeerRrV4").
		SetNextHopAddressType(gosnappi.BgpV4RouteRangeNextHopAddressType.IPV4).
		SetNextHopMode(gosnappi.BgpV4RouteRangeNextHopMode.MANUAL)

	drxBgpv4PeerRrV4.Addresses().Add().
		SetAddress(tc["rxAdvRouteV4"].(string)).
		SetPrefix(32).
		SetCount(tc["rxRouteCount"].(uint32)).
		SetStep(1)

	drxBgpv4PeerRrV4.Advanced().
		SetMultiExitDiscriminator(50).
		SetOrigin(gosnappi.BgpRouteAdvancedOrigin.EGP)

	drxBgpv4PeerRrV4.Communities().Add().
		SetAsNumber(1).
		SetAsCustom(2).
		SetType(gosnappi.BgpCommunityType.MANUAL_AS_NUMBER)

	drxBgpv4PeerRrV4AsPath := drxBgpv4PeerRrV4.AsPath().
		SetAsSetMode(gosnappi.BgpAsPathAsSetMode.INCLUDE_AS_SET)

	drxBgpv4PeerRrV4AsPath.Segments().Add().
		SetAsNumbers([]uint32{4444}).
		SetType(gosnappi.BgpAsPathSegmentType.AS_SEQ)

	drxBgpv4PeerRrV6 := drxBgpv4Peer.
		V6Routes().
		Add().
		SetNextHopIpv6Address(tc["rxNextHopV6"].(string)).
		SetName("drxBgpv4PeerRrV6").
		SetNextHopAddressType(gosnappi.BgpV6RouteRangeNextHopAddressType.IPV6).
		SetNextHopMode(gosnappi.BgpV6RouteRangeNextHopMode.MANUAL)

	drxBgpv4PeerRrV6.Addresses().Add().
		SetAddress(tc["rxAdvRouteV6"].(string)).
		SetPrefix(128).
		SetCount(tc["rxRouteCount"].(uint32)).
		SetStep(1)

	drxBgpv4PeerRrV6.Advanced().
		SetMultiExitDiscriminator(50).
		SetOrigin(gosnappi.BgpRouteAdvancedOrigin.EGP)

	drxBgpv4PeerRrV6.Communities().Add().
		SetAsNumber(1).
		SetAsCustom(2).
		SetType(gosnappi.BgpCommunityType.MANUAL_AS_NUMBER)

	drxBgpv4PeerRrV6AsPath := drxBgpv4PeerRrV6.AsPath().
		SetAsSetMode(gosnappi.BgpAsPathAsSetMode.INCLUDE_AS_SET)

	drxBgpv4PeerRrV6AsPath.Segments().Add().
		SetAsNumbers([]uint32{4444}).
		SetType(gosnappi.BgpAsPathSegmentType.AS_SEQ)

	for i := 1; i <= 4; i++ {
		flow := c.Flows().Add()
		flow.Duration().FixedPackets().SetPackets(tc["pktCount"].(uint32))
		flow.Rate().SetPps(tc["pktRate"].(uint64))
		flow.Size().SetFixed(tc["pktSize"].(uint32))
		flow.Metrics().SetEnable(true)
	}

	ftxV4 := c.Flows().Items()[0]
	ftxV4.SetName("ftxV4")
	ftxV4.TxRx().Device().
		SetTxNames([]string{dtxBgpv4PeerRrV4.Name()}).
		SetRxNames([]string{drxBgpv4PeerRrV4.Name()})

	ftxV4Eth := ftxV4.Packet().Add().Ethernet()
	ftxV4Eth.Src().SetValue(dtxEth.Mac())

	ftxV4Ip := ftxV4.Packet().Add().Ipv4()
	ftxV4Ip.Src().SetValue(tc["txAdvRouteV4"].(string))
	ftxV4Ip.Dst().SetValue(tc["rxAdvRouteV4"].(string))

	ftxV4Tcp := ftxV4.Packet().Add().Tcp()
	ftxV4Tcp.SrcPort().SetValue(5000)
	ftxV4Tcp.DstPort().SetValue(6000)

	ftxV6 := c.Flows().Items()[1]
	ftxV6.SetName("ftxV6")
	ftxV6.TxRx().Device().
		SetTxNames([]string{dtxBgpv4PeerRrV6.Name()}).
		SetRxNames([]string{drxBgpv4PeerRrV6.Name()})

	ftxV6Eth := ftxV6.Packet().Add().Ethernet()
	ftxV6Eth.Src().SetValue(dtxEth.Mac())

	ftxV6Ip := ftxV6.Packet().Add().Ipv6()
	ftxV6Ip.Src().SetValue(tc["txAdvRouteV6"].(string))
	ftxV6Ip.Dst().SetValue(tc["rxAdvRouteV6"].(string))

	ftxV6Tcp := ftxV6.Packet().Add().Tcp()
	ftxV6Tcp.SrcPort().SetValue(5000)
	ftxV6Tcp.DstPort().SetValue(6000)

	frxV4 := c.Flows().Items()[2]
	frxV4.SetName("frxV4")
	frxV4.TxRx().Device().
		SetTxNames([]string{drxBgpv4PeerRrV4.Name()}).
		SetRxNames([]string{dtxBgpv4PeerRrV4.Name()})

	frxV4Eth := frxV4.Packet().Add().Ethernet()
	frxV4Eth.Src().SetValue(drxEth.Mac())

	frxV4Ip := frxV4.Packet().Add().Ipv4()
	frxV4Ip.Src().SetValue(tc["rxAdvRouteV4"].(string))
	frxV4Ip.Dst().SetValue(tc["txAdvRouteV4"].(string))

	frxV4Tcp := frxV4.Packet().Add().Tcp()
	frxV4Tcp.SrcPort().SetValue(6000)
	frxV4Tcp.DstPort().SetValue(5000)

	frxV6 := c.Flows().Items()[3]
	frxV6.SetName("frxV6")
	frxV6.TxRx().Device().
		SetTxNames([]string{drxBgpv4PeerRrV6.Name()}).
		SetRxNames([]string{dtxBgpv4PeerRrV6.Name()})

	frxV6Eth := frxV6.Packet().Add().Ethernet()
	frxV6Eth.Src().SetValue(drxEth.Mac())

	frxV6Ip := frxV6.Packet().Add().Ipv6()
	frxV6Ip.Src().SetValue(tc["rxAdvRouteV6"].(string))
	frxV6Ip.Dst().SetValue(tc["txAdvRouteV6"].(string))

	frxV6Tcp := frxV6.Packet().Add().Tcp()
	frxV6Tcp.SrcPort().SetValue(6000)
	frxV6Tcp.DstPort().SetValue(5000)

	return c
}

func ebgpRoutePrefixBgpMetricsOk(t *testing.T, api gosnappi.Api, tc map[string]interface{}) bool {
	for _, m := range getBgpv4Metrics(t, api) {
		if m.SessionState() == gosnappi.Bgpv4MetricSessionState.DOWN ||
			m.RoutesAdvertised() != 2*uint64(tc["txRouteCount"].(uint32)) ||
			m.RoutesReceived() != 2*uint64(tc["rxRouteCount"].(uint32)) {
			return false
		}
	}
	return true
}

func ebgpRoutePrefixBgpPrefixesOk(t *testing.T, api gosnappi.Api, tc map[string]interface{}) bool {
	prefixCount := 0
	for _, m := range getBgpPrefixes(t, api) {
		for _, p := range m.Ipv4UnicastPrefixes().Items() {
			for _, key := range []string{"tx", "rx"} {
				if p.Ipv4Address() == tc[key+"AdvRouteV4"].(string) && p.Ipv4NextHop() == tc[key+"NextHopV4"].(string) {
					prefixCount += 1
				}
			}
		}
		for _, p := range m.Ipv6UnicastPrefixes().Items() {
			for _, key := range []string{"tx", "rx"} {
				if p.Ipv6Address() == tc[key+"AdvRouteV6"].(string) && p.Ipv6NextHop() == tc[key+"NextHopV6"].(string) {
					prefixCount += 1
				}
			}
		}
	}
	return prefixCount == 4
}

func ebgpRoutePrefixFlowMetricsOk(t *testing.T, api gosnappi.Api, tc map[string]interface{}) bool {
	pktCount := uint64(tc["pktCount"].(uint32))

	for _, m := range getFlowMetrics(t, api) {
		if m.Transmit() != gosnappi.FlowMetricTransmit.STOPPED ||
			m.FramesTx() != pktCount ||
			m.FramesRx() != pktCount {
			return false
		}

	}

	return true
}

func startProtocols(t *testing.T, api gosnappi.Api) {
	cs := gosnappi.NewControlState()
	cs.Protocol().All().SetState(gosnappi.StateProtocolAllState.START)

	if _, err := api.SetControlState(cs); err != nil {
		t.Fatal(err)
	}
}

func startTransmit(t *testing.T, api gosnappi.Api) {
	cs := gosnappi.NewControlState()
	cs.Traffic().FlowTransmit().SetState(gosnappi.StateTrafficFlowTransmitState.START)

	if _, err := api.SetControlState(cs); err != nil {
		t.Fatal(err)
	}
}

func getFlowMetrics(t *testing.T, api gosnappi.Api) []gosnappi.FlowMetric {

	t.Log("Getting flow metrics ...")

	mr := gosnappi.NewMetricsRequest()
	mr.Flow()
	res, _ := api.GetMetrics(mr)

	tb := table.NewTable(
		"Flow Metrics",
		[]string{
			"Name",
			"State",
			"Frames Tx",
			"Frames Rx",
			"FPS Tx",
			"FPS Rx",
			"Bytes Tx",
			"Bytes Rx",
		},
		15,
	)
	for _, v := range res.FlowMetrics().Items() {
		if v != nil {
			tb.AppendRow([]interface{}{
				v.Name(),
				v.Transmit(),
				v.FramesTx(),
				v.FramesRx(),
				v.FramesTxRate(),
				v.FramesRxRate(),
				v.BytesTx(),
				v.BytesRx(),
			})
		}
	}

	t.Log(tb.String())
	return res.FlowMetrics().Items()
}

func getBgpv4Metrics(t *testing.T, api gosnappi.Api) []gosnappi.Bgpv4Metric {
	t.Log("Getting bgpv4 metrics ...")

	mr := gosnappi.NewMetricsRequest()
	mr.Bgpv4()
	res, _ := api.GetMetrics(mr)

	tb := table.NewTable(
		"BGPv4 Metrics",
		[]string{
			"Name",
			"State",
			"Routes Adv.",
			"Routes Rec.",
		},
		15,
	)
	for _, v := range res.Bgpv4Metrics().Items() {
		if v != nil {
			tb.AppendRow([]interface{}{
				v.Name(),
				v.SessionState(),
				v.RoutesAdvertised(),
				v.RoutesReceived(),
			})
		}
	}

	t.Log(tb.String())
	return res.Bgpv4Metrics().Items()
}

func getBgpPrefixes(t *testing.T, api gosnappi.Api) []gosnappi.BgpPrefixesState {

	t.Log("Getting BGP Prefixes ...")

	sr := gosnappi.NewStatesRequest()
	sr.BgpPrefixes()
	res, _ := api.GetStates(sr)
	log.Println(res)

	tb := table.NewTable(
		"BGP Prefixes",
		[]string{
			"Name",
			"IPv4 Address",
			"IPv4 Next Hop",
			"IPv6 Address",
			"IPv6 Next Hop",
			"MED",
			"Local Preference",
		},
		20,
	)

	for _, v := range res.BgpPrefixes().Items() {

		for _, w := range v.Ipv4UnicastPrefixes().Items() {
			row := []interface{}{
				v.BgpPeerName(), fmt.Sprintf("%s/%d", w.Ipv4Address(), w.PrefixLength()), w.Ipv4NextHop(), "",
			}

			if w.HasIpv6NextHop() {
				row = append(row, w.Ipv6NextHop())
			} else {
				row = append(row, "")
			}

			if w.HasMultiExitDiscriminator() {
				row = append(row, w.MultiExitDiscriminator())
			} else {
				row = append(row, "")
			}

			if w.HasLocalPreference() {
				row = append(row, w.LocalPreference())
			} else {
				row = append(row, "")
			}

			tb.AppendRow(row)
		}
		for _, w := range v.Ipv6UnicastPrefixes().Items() {
			row := []interface{}{v.BgpPeerName(), ""}

			if w.HasIpv4NextHop() {
				row = append(row, w.Ipv4NextHop())
			} else {
				row = append(row, "")
			}
			row = append(row, fmt.Sprintf("%s/%d", w.Ipv6Address(), w.PrefixLength()), w.Ipv6NextHop())

			if w.HasMultiExitDiscriminator() {
				row = append(row, w.MultiExitDiscriminator())
			} else {
				row = append(row, "")
			}

			if w.HasLocalPreference() {
				row = append(row, w.LocalPreference())
			} else {
				row = append(row, "")
			}
			tb.AppendRow(row)
		}
	}

	t.Log(tb.String())
	return res.BgpPrefixes().Items()
}

func waitFor(t *testing.T, fn func() bool, opts waitForOpts) {

	if opts.Interval == 0 {
		opts.Interval = 500 * time.Millisecond
	}
	if opts.Timeout == 0 {
		opts.Timeout = 10 * time.Second
	}

	start := time.Now()
	t.Logf("Waiting for %s ...\n", opts.FnName)

	for {

		if fn() {
			t.Logf("Done waiting for %s\n", opts.FnName)
			return
		}

		if time.Since(start) > opts.Timeout {
			t.Fatalf("ERROR: Timeout occurred while waiting for %s\n", opts.FnName)
		}
		time.Sleep(opts.Interval)
	}
}
