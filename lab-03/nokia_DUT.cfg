

--{ + running }--[  ]--
A:srlinux# info network-instance DEFAULT
    network-instance DEFAULT {
        admin-state enable
        interface ethernet-1/1.0 {
            interface-ref {
                interface ethernet-1/1
                subinterface 0
            }
        }
        interface ethernet-1/2.0 {
            interface-ref {
                interface ethernet-1/2
                subinterface 0
            }
        }
        protocols {
            bgp {
                autonomous-system 65537
                router-id 192.0.2.5
                afi-safi ipv6-unicast {
                    admin-state enable
                }
                group BGP-PEER-GROUP1 {
                    afi-safi ipv6-unicast {
                        admin-state enable
                        export-policy PERMIT-ALL
                        import-policy PERMIT-ALL
                    }
                }
                group BGP-PEER-GROUP2 {
                    afi-safi ipv6-unicast {
                        admin-state enable
                        export-policy PERMIT-ALL
                        import-policy PERMIT-ALL
                    }
                }
                neighbor 2001:db8::2 {
                    peer-as 65536
                    peer-group BGP-PEER-GROUP1
                    afi-safi ipv6-unicast {
                        admin-state enable
                    }
                }
                neighbor 2001:db8::6 {
                    peer-as 65538
                    peer-group BGP-PEER-GROUP2
                    afi-safi ipv6-unicast {
                        admin-state enable
                    }
                }
            }
            gribi {
                admin-state enable
            }
        }
    }
--{ + running }--[  ]--
A:srlinux# interface ethernet-1/9 admin-state
--{ + running }--[  ]--
A:srlinux#
--{ + running }--[  ]--
A:srlinux#
--{ + running }--[  ]--
A:srlinux# info interface ethernet-1/1
    interface ethernet-1/1 {
        description "To ATE"
        admin-state enable
        subinterface 0 {
            ipv4 {
                admin-state enable
                address 192.0.2.1/30 {
                }
            }
            ipv6 {
                admin-state enable
                address 2001:db8::1/126 {
                }
            }
        }
    }
--{ + running }--[  ]--
A:srlinux# info interface ethernet-1/2
    interface ethernet-1/2 {
        description "To ATE"
        admin-state enable
        subinterface 0 {
            ipv4 {
                admin-state enable
                address 192.0.2.5/30 {
                }
            }
            ipv6 {
                admin-state enable
                address 2001:db8::5/126 {
                }
            }
        }
    }
--{ + running }--[  ]--
A:srlinux# info interface ethernet-1/1
    interface ethernet-1/1 {
        description "To ATE"
        admin-state enable
        subinterface 0 {
            ipv4 {
                admin-state enable
                address 192.0.2.1/30 {
                }
            }
            ipv6 {
                admin-state enable
                address 2001:db8::1/126 {
                }
            }
        }
    }
--{ + running }--[  ]--
A:srlinux# info interface ethernet-1/2
    interface ethernet-1/2 {
        description "To ATE"
        admin-state enable
        subinterface 0 {
            ipv4 {
                admin-state enable
                address 192.0.2.5/30 {
                }
            }
            ipv6 {
                admin-state enable
                address 2001:db8::5/126 {
                }
            }
        }
    }
--{ + running }--[  ]--
A:srlinux# info system al
Parsing error: Unknown token 'al'. Options are ['#', '>', '>>', 'aaa', 'authentication', 'banner', 'boot', 'clock', 'configuration', 'dhcp-server', 'dns', 'event-handler', 'ftp-server', 'gnmi-server', 'gribi-server', 'information', 'json-rpc-server', 'lacp', 'lldp', 'load-balancing', 'logging', 'maintenance', 'management', 'mirroring', 'mpls', 'mtu', 'multicast', 'name', 'netconf-server', 'network-instance', 'ntp', 'p4rt-server', 'packet-link-qualification', 'protocols', 'sflow', 'snmp', 'ssh-server', 'tls', 'trace-options', '|']
--{ + running }--[  ]--
A:srlinux# info routing-policy
    routing-policy {
        policy PERMIT-ALL {
            statement 20 {
                action {
                    policy-result accept
                }
            }
        }
    }
--{ + running }--[  ]--
A:srlinux#
