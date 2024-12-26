simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.feature1_exact MyIngress.set_actionselect1 0x0->0x20 => 1 1";

simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.feature2_exact MyIngress.set_actionselect2 0x0->0xBFB => 1 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.feature2_exact MyIngress.set_actionselect2 0xBFC->0x13B7 => 2 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.feature2_exact MyIngress.set_actionselect2 0x13B8->0x9561 => 3 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.feature2_exact MyIngress.set_actionselect2 0x9562->0xBEE4 => 4 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.feature2_exact MyIngress.set_actionselect2 0xBEE5->0xC032 => 5 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.feature2_exact MyIngress.set_actionselect2 0xC033->0xFFFF => 6 1";

simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.feature3_exact MyIngress.set_actionselect3 0x0->0x43 => 1 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.feature3_exact MyIngress.set_actionselect3 0x44->0x11B => 2 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.feature3_exact MyIngress.set_actionselect3 0x11C->0xFFFF => 3 1";

simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.ipv4_exact MyIngress.ipv4_forward 1->1 1->1 1->1 => 0x0A000104 4 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.ipv4_exact MyIngress.ipv4_forward 1->1 1->1 2->3 => 0x0A000104 4 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.ipv4_exact MyIngress.ipv4_forward 1->1 2->2 1->3 => 0x0A000100 0 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.ipv4_exact MyIngress.ipv4_forward 1->1 3->3 1->3 => 0x0A000104 4 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.ipv4_exact MyIngress.ipv4_forward 1->1 4->4 1->2 => 0x0A000104 4 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.ipv4_exact MyIngress.ipv4_forward 1->1 4->4 3->3 => 0x0A000103 3 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.ipv4_exact MyIngress.ipv4_forward 1->1 5->5 1->3 => 0x0A000100 0 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.ipv4_exact MyIngress.ipv4_forward 1->1 6->6 1->3 => 0x0A000104 4 1";
