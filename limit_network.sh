#!/bin/bash
tc qdisc add dev eth0 root tbf rate 256kbit latency 50ms burst 1540
